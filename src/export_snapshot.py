"""Exporta las tablas y vistas gold que usa la app a app/data/*.parquet.

Streamlit Community Cloud corre en Linux sin driver ODBC y no alcanza el
SQL Server local, así que la app lee este snapshot liviano (ADR 0008).
Para refrescar la demo: correr el pipeline y hacer commit de app/data/.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from src import config

log = config.get_logger("export_snapshot")
MAX_MB = 5

# nombre del archivo -> consulta sobre gold
SNAPSHOT_QUERIES = {
    "export_basket": "SELECT * FROM gold.vw_export_basket",
    "oil_dependency": "SELECT * FROM gold.vw_oil_dependency",
    "diversification": "SELECT * FROM gold.vw_diversification",
    "product_cagr": "SELECT * FROM gold.vw_product_cagr",
    "oil_price_monthly": "SELECT f.series, d.[date] AS price_month, CAST(f.price_usd_bbl AS FLOAT) AS price_usd_bbl, "
                         "f.source_name FROM gold.fact_oil_price f JOIN gold.dim_date d ON d.date_key = f.date_key",
    "oil_price_annual": "SELECT * FROM gold.vw_oil_price_annual",
    "oil_sensitivity": "SELECT * FROM gold.vw_oil_sensitivity",
    "regional_compare": "SELECT * FROM gold.vw_regional_compare",
    "exports_index": "SELECT * FROM gold.vw_exports_index",
    "economic_events": "SELECT * FROM gold.vw_economic_events",
    "source_reconciliation": "SELECT * FROM gold.vw_source_reconciliation",
    "pipeline_runs": "SELECT TOP (20) * FROM gold.vw_pipeline_runs ORDER BY run_id DESC",
    "layer_counts": "SELECT * FROM gold.vw_layer_counts",
    "cleaning_rules": "SELECT * FROM gold.vw_cleaning_rules WHERE batch_id = "
                      "(SELECT TOP (1) batch_id FROM silver.etl_runs WHERE status = 'success' ORDER BY run_id DESC)",
    "dim_country": "SELECT iso3, name_es, name_en, is_aggregate, is_focus FROM gold.dim_country",
    "dim_product": "SELECT hs_code, hs_level, product_group, name_es, name_en, is_key_product FROM gold.dim_product",
}


def export(engine, out_dir=config.APP_DATA_DIR) -> dict[str, int]:
    from src import db
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, sql in SNAPSHOT_QUERIES.items():
        df = db.read_sql(engine, sql)
        path = out_dir / f"{name}.parquet"
        df.to_parquet(path, index=False, compression="zstd")
        size_mb = path.stat().st_size / 1_048_576
        if size_mb > MAX_MB:
            raise RuntimeError(f"{path.name} pesa {size_mb:.1f} MB (> {MAX_MB} MB): agrégalo antes de versionarlo")
        counts[name] = len(df)
    write_metadata(out_dir, counts, engine)
    log.info("Snapshot exportado: %s", counts)
    return counts


def write_metadata(out_dir, counts: dict[str, int], engine=None) -> dict:
    from src import db
    last = None
    if engine is not None:
        last = db.read_sql(engine, "SELECT TOP (1) batch_id, finished_at FROM silver.etl_runs "
                                   "WHERE status = 'success' ORDER BY run_id DESC")
    meta = {
        "exported_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_successful_batch": None if last is None or last.empty else str(last.iloc[0]["batch_id"]),
        "rows_per_table": counts,
        "sources": [
            {"name": "World Bank — World Development Indicators", "url": "https://data.worldbank.org", "codes": list(config.WB_INDICATORS)},
            {"name": "UN Comtrade", "url": "https://comtradeplus.un.org", "codes": list(config.KEY_PRODUCTS)},
            {"name": "World Bank — Commodity Price Data (Pink Sheet) / FRED", "url": "https://www.worldbank.org/en/research/commodity-markets", "codes": ["CRUDE_BRENT", "CRUDE_WTI"]},
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
