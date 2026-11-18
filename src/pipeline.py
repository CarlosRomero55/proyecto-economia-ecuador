"""Orquestación del pipeline completo: fuentes → bronze → silver → gold → snapshot.

Uso:
    python -m src.pipeline --full          # primera carga (2000 a la fecha)
    python -m src.pipeline --incremental   # solo lo nuevo, según watermarks

Cada ejecución queda registrada en silver.etl_runs. Las cargas a silver y gold
son MERGE, así que ejecutar dos veces no duplica filas (ver docs/automatizacion.md).
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

import pandas as pd

from src import (build_gold, clean, config, db, export_snapshot, extract_bce, extract_comtrade,
                 extract_oil, extract_worldbank, insights, validate)

log = config.get_logger("pipeline")
SQL_FILES = ["00_database.sql", "01_bronze.sql", "02_silver.sql", "03_gold.sql"]


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def setup_database() -> None:
    """Crea/actualiza base, esquemas, tablas, procedimientos y vistas (idempotente)."""
    db.run_sql_file(config.SQL_DIR / SQL_FILES[0], database="master")
    for name in SQL_FILES[1:]:
        db.run_sql_file(config.SQL_DIR / name, database=config.SQL_DATABASE)


def get_watermarks(engine) -> dict[tuple[str, str], str]:
    df = db.read_sql(engine, "SELECT source_name, scope_key, watermark_value FROM silver.etl_watermarks")
    return {(r.source_name, r.scope_key): r.watermark_value for r in df.itertuples()}


def comtrade_years(mode: str, wm: dict) -> dict[str, list[int]]:
    """Años a pedir por reportante. Incremental: desde (watermark − 1) por revisiones."""
    last_full_year = config.END_YEAR - 1  # el año en curso aún no tiene datos anuales
    plan = {}
    for iso3 in config.COMTRADE_REPORTERS:
        start = config.START_YEAR
        if mode == "incremental" and ("un_comtrade", iso3) in wm:
            start = int(wm[("un_comtrade", iso3)]) - 1
        plan[iso3] = list(range(start, last_full_year + 1))
    return plan


def read_bronze_batch(engine, table: str, batch_id: str) -> pd.DataFrame:
    return db.read_sql(engine, f"SELECT * FROM bronze.{table} WHERE batch_id = :b", b=batch_id)


def run(mode: str, skip_comtrade: bool = False) -> int:
    t0 = time.time()
    batch_id = f"{now_utc():%Y%m%dT%H%M%S}_{mode}"
    log.info("=== Inicio pipeline %s (lote %s) ===", mode, batch_id)
    setup_database()
    engine = db.get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO silver.etl_runs (batch_id, run_mode, started_at, status) VALUES (?, ?, ?, 'running')",
            (batch_id, mode, now_utc()))
    try:
        wm = get_watermarks(engine)
        cl = clean.CleaningLog()
        rows_bronze = 0

        # 1) Extracción → bronze
        wb_start = None
        if mode == "incremental" and ("world_bank_wdi", "ALL") in wm:
            wb_start = int(wm[("world_bank_wdi", "ALL")]) - 2
        rows_bronze += extract_worldbank.load_bronze(engine, extract_worldbank.extract(batch_id, wb_start, use_cache=False))
        rows_bronze += extract_oil.load_bronze(engine, extract_oil.extract(batch_id))
        bce_df = extract_bce.extract(batch_id)
        if not bce_df.empty:
            rows_bronze += extract_bce.load_bronze(engine, bce_df)
        if not skip_comtrade:
            ct = extract_comtrade.extract(batch_id, comtrade_years(mode, wm))
            rows_bronze += extract_comtrade.load_bronze(engine, ct)

        # 2) Limpieza → staging → MERGE en silver
        wb = clean.clean_worldbank(read_bronze_batch(engine, "wb_indicator_raw", batch_id), cl)
        db.truncate_and_load(engine, wb, "silver", "stg_indicator_values")
        db.exec_proc(engine, "silver.usp_merge_indicator_values")

        oil = clean.clean_oil(read_bronze_batch(engine, "oil_price_raw", batch_id), cl)
        db.truncate_and_load(engine, oil, "silver", "stg_commodity_prices")
        db.exec_proc(engine, "silver.usp_merge_commodity_prices")

        if not bce_df.empty:
            bce = read_bronze_batch(engine, "bce_trade_raw", batch_id)
            bce = bce[["year", "oil_exports_fob_usd", "non_oil_exports_fob_usd", "source_file", "batch_id"]].dropna(
                subset=["year", "oil_exports_fob_usd", "non_oil_exports_fob_usd"])
            db.truncate_and_load(engine, bce, "silver", "stg_bce_trade_balance")
            db.exec_proc(engine, "silver.usp_merge_bce_trade_balance")

        if not skip_comtrade:
            tf = clean.clean_comtrade(read_bronze_batch(engine, "comtrade_raw", batch_id), cl)
            db.truncate_and_load(engine, tf, "silver", "stg_trade_flows")
            db.exec_proc(engine, "silver.usp_merge_trade_flows")

        db.append(engine, cl.to_frame().assign(batch_id=batch_id), "silver", "cleaning_log")

        # 3) Watermarks (último período con datos)
        for (src, scope, sql) in [
            ("world_bank_wdi", "ALL", "SELECT MAX([year]) FROM silver.indicator_values"),
            ("oil_prices", "ALL", "SELECT CONVERT(CHAR(7), MAX(price_month), 126) FROM silver.commodity_prices"),
        ] + [("un_comtrade", iso, f"SELECT MAX([year]) FROM silver.trade_flows WHERE reporter_iso3 = '{iso}' "
              "AND is_world = 1 AND hs_code = 'TOTAL'") for iso in config.COMTRADE_REPORTERS]:
            val = db.scalar(engine, sql)
            if val is not None:
                db.exec_proc(engine, "silver.usp_set_watermark", source_name=src, scope_key=scope, watermark_value=str(val))

        # 4) Gold + calidad
        gold_counts = build_gold.build(engine)
        checks = validate.run_checks(engine)
        failed = [c for c in checks if c.critical and not c.passed]
        validate.write_report(engine, batch_id)
        if failed:
            raise RuntimeError("Validaciones críticas fallidas: " + "; ".join(f"{c.name} ({c.violations})" for c in failed))

        rows_silver = int(db.scalar(engine, "SELECT (SELECT COUNT(*) FROM silver.indicator_values) + "
                                            "(SELECT COUNT(*) FROM silver.trade_flows) + (SELECT COUNT(*) FROM silver.commodity_prices)"))
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "UPDATE silver.etl_runs SET status='success', finished_at=?, rows_bronze=?, rows_silver=?, rows_gold=?, "
                "[message]=? WHERE batch_id=?",
                (now_utc(), rows_bronze, rows_silver, sum(gold_counts.values()),
                 f"OK en {time.time() - t0:.0f}s", batch_id))

        # 5) Snapshot para Streamlit + insights (después de marcar éxito, para que lo incluyan)
        export_snapshot.export(engine)
        insights.write_all()
        log.info("=== Pipeline OK en %.0fs ===", time.time() - t0)
        return 0
    except Exception as err:
        log.exception("Pipeline falló")
        with engine.begin() as conn:
            conn.exec_driver_sql("UPDATE silver.etl_runs SET status='failed', finished_at=?, [message]=? WHERE batch_id=?",
                                 (now_utc(), str(err)[:2000], batch_id))
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ecuador Trade & Economy Monitor — pipeline ETL")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--full", action="store_true", help="carga completa 2000–hoy")
    g.add_argument("--incremental", action="store_true", help="solo períodos nuevos según watermarks")
    p.add_argument("--skip-comtrade", action="store_true", help="omite Comtrade (útil si se agotó la cuota diaria)")
    a = p.parse_args(argv)
    return run("full" if a.full else "incremental", skip_comtrade=a.skip_comtrade)


if __name__ == "__main__":
    sys.exit(main())
