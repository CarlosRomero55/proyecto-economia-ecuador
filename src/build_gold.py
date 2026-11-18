"""Construcción de la capa gold (dimensiones, hechos y vistas)."""
from __future__ import annotations

from src import config, db

log = config.get_logger("build_gold")
GOLD_TABLES = ["dim_date", "dim_country", "dim_product", "dim_indicator", "fact_indicator", "fact_trade", "fact_oil_price"]


def build(engine) -> dict[str, int]:
    """Ejecuta gold.usp_build_gold (MERGE idempotente) y devuelve filas por tabla."""
    db.exec_proc(engine, "gold.usp_build_gold")
    counts = {t: int(db.scalar(engine, f"SELECT COUNT(*) FROM gold.{t}")) for t in GOLD_TABLES}
    log.info("Gold construido: %s", counts)
    return counts
