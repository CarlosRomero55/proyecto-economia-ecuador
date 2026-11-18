"""Validaciones de calidad de datos sobre silver y gold.

Las mismas reglas se usan en tres lugares:
  * el pipeline (falla si una validación crítica no pasa),
  * pytest (tests/test_quality_db.py, se salta si no hay SQL Server),
  * docs/data_quality_report.md (tabla "antes vs después").
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src import config

# (nombre, consulta que devuelve el número de filas que VIOLAN la regla, es_crítica)
CHECKS: list[tuple[str, str, bool]] = [
    ("Unicidad país-indicador-año en silver.indicator_values",
     "SELECT COUNT(*) FROM (SELECT country_iso3, indicator_code, [year] FROM silver.indicator_values "
     "GROUP BY country_iso3, indicator_code, [year] HAVING COUNT(*) > 1) d", True),
    ("Unicidad reportante-socio-año-HS en silver.trade_flows",
     "SELECT COUNT(*) FROM (SELECT reporter_iso3, partner_code, [year], hs_code FROM silver.trade_flows "
     "GROUP BY reporter_iso3, partner_code, [year], hs_code HAVING COUNT(*) > 1) d", True),
    ("Llaves foráneas sin nulos en gold.fact_trade",
     "SELECT COUNT(*) FROM gold.fact_trade WHERE country_key IS NULL OR product_key IS NULL OR date_key IS NULL", True),
    ("Hechos de comercio sin dimensión de producto",
     "SELECT COUNT(*) FROM gold.fact_trade f LEFT JOIN gold.dim_product p ON p.product_key = f.product_key "
     "WHERE p.product_key IS NULL", True),
    ("Exportaciones negativas", "SELECT COUNT(*) FROM silver.trade_flows WHERE value_usd < 0", True),
    ("Porcentajes fuera de rango (-100 a 100 000)",
     "SELECT COUNT(*) FROM silver.indicator_values v JOIN silver.indicators i ON i.indicator_code = v.indicator_code "
     "WHERE i.unit = '%' AND (v.[value] < -100 OR v.[value] > 100000)", True),
    ("Precio del crudo fuera de 1–300 USD/bbl",
     "SELECT COUNT(*) FROM silver.commodity_prices WHERE price_usd_bbl < 1 OR price_usd_bbl > 300", True),
    ("Participaciones de la canasta que no suman 1 (tolerancia 0,001)",
     "SELECT COUNT(*) FROM (SELECT iso3, [year], SUM(share) s FROM gold.vw_export_basket GROUP BY iso3, [year]) x "
     "WHERE ABS(s - 1) > 0.001", True),
    ("Suma de capítulos HS2 vs TOTAL de Comtrade (diferencia > 2 %)",
     "SELECT COUNT(*) FROM (SELECT reporter_iso3, [year], SUM(CASE WHEN hs_code = 'TOTAL' THEN value_usd END) t, "
     "SUM(CASE WHEN LEN(hs_code) = 2 THEN value_usd END) c FROM silver.trade_flows WHERE is_world = 1 "
     "GROUP BY reporter_iso3, [year]) x WHERE t > 0 AND c > 0 AND ABS(c - t) / t > 0.02", False),
]


def coverage(engine) -> pd.DataFrame:
    """Años con datos por país y fuente (cobertura 2000–hoy)."""
    from src import db
    return db.read_sql(engine, """
        SELECT 'world_bank_wdi' AS source_name, country_iso3 AS iso3, COUNT(DISTINCT [year]) AS years,
               MIN([year]) AS first_year, MAX([year]) AS last_year
        FROM silver.indicator_values GROUP BY country_iso3
        UNION ALL
        SELECT 'un_comtrade', reporter_iso3, COUNT(DISTINCT [year]), MIN([year]), MAX([year])
        FROM silver.trade_flows WHERE is_world = 1 GROUP BY reporter_iso3""")


@dataclass
class CheckResult:
    name: str
    violations: int
    critical: bool

    @property
    def passed(self) -> bool:
        return self.violations == 0


def run_checks(engine) -> list[CheckResult]:
    from src import db
    return [CheckResult(name, int(db.scalar(engine, sql) or 0), crit) for name, sql, crit in CHECKS]


def reconciliation_python_vs_sql(engine, iso3: str = config.FOCUS_COUNTRY) -> pd.DataFrame:
    """Recalcula el HHI por producto en Python y lo compara con la vista SQL."""
    from src import db, indicators
    trade = db.read_sql(engine, "SELECT reporter_iso3, [year], hs_code, LEN(hs_code) AS hs_level, "
                                "CAST(value_usd AS FLOAT) AS value_usd, is_world, is_special_partner "
                                "FROM silver.trade_flows WHERE reporter_iso3 = :iso", iso=iso3)
    trade.loc[trade["hs_code"] == "TOTAL", "hs_level"] = 0
    py = indicators.diversification(trade)[["year", "hhi_product"]].rename(columns={"hhi_product": "hhi_python"})
    sql = db.read_sql(engine, "SELECT [year], hhi_product AS hhi_sql FROM gold.vw_diversification WHERE iso3 = :iso", iso=iso3)
    out = py.merge(sql, on="year", how="outer")
    out["abs_diff"] = (out["hhi_python"] - out["hhi_sql"]).abs()
    return out


def write_report(engine, batch_id: str) -> str:
    """Genera docs/data_quality_report.md con la tabla antes vs después."""
    from src import db
    log = db.read_sql(engine, "SELECT rule_id, source_name, [description], rows_affected FROM silver.cleaning_log "
                              "WHERE batch_id = :b ORDER BY source_name, rule_id", b=batch_id)
    checks = run_checks(engine)
    cov = coverage(engine)
    rec = reconciliation_python_vs_sql(engine)
    before = db.read_sql(engine, """
        SELECT 'world_bank_wdi' AS fuente, COUNT(*) AS filas_bronze FROM bronze.wb_indicator_raw WHERE batch_id = :b
        UNION ALL SELECT 'un_comtrade', COUNT(*) FROM bronze.comtrade_raw WHERE batch_id = :b
        UNION ALL SELECT 'oil_prices', COUNT(*) FROM bronze.oil_price_raw WHERE batch_id = :b""", b=batch_id)
    after = db.read_sql(engine, """
        SELECT 'world_bank_wdi' AS fuente, COUNT(*) AS filas_silver FROM silver.indicator_values
        UNION ALL SELECT 'un_comtrade', COUNT(*) FROM silver.trade_flows
        UNION ALL SELECT 'oil_prices', COUNT(*) FROM silver.commodity_prices""")
    ba = before.merge(after, on="fuente")

    lines = [
        "# Reporte de calidad de datos",
        "",
        f"Generado automáticamente por `src/validate.py` el {datetime.now():%Y-%m-%d %H:%M} (lote `{batch_id}`).",
        "",
        "## Antes vs después",
        "",
        "Filas del lote en bronze (crudo) frente a filas totales en silver (limpio, sin duplicados). "
        "Silver puede tener más filas que el lote si es una carga incremental.",
        "",
        ba.to_markdown(index=False),
        "",
        "## Reglas de limpieza aplicadas",
        "",
        log.to_markdown(index=False) if not log.empty else "_Sin registros para este lote._",
        "",
        "## Validaciones",
        "",
        "| Validación | Filas que la violan | Crítica | Resultado |",
        "|---|---:|:---:|:---:|",
        *[f"| {c.name} | {c.violations} | {'sí' if c.critical else 'no'} | {'OK' if c.passed else 'REVISAR'} |" for c in checks],
        "",
        "## Cobertura de años",
        "",
        cov.to_markdown(index=False),
        "",
        "## Reconciliación Python vs SQL (HHI por producto, Ecuador)",
        "",
        f"Diferencia absoluta máxima: {rec['abs_diff'].max():.6f} puntos de HHI "
        f"({len(rec)} años comparados). Ambos cálculos parten de silver.trade_flows.",
        "",
    ]
    text = "\n".join(lines)
    (config.DOCS_DIR / "data_quality_report.md").write_text(text, encoding="utf-8")
    return text
