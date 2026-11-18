"""Balanza comercial petrolera vs no petrolera del Banco Central del Ecuador.

El BCE publica estas cifras en boletines y archivos Excel cuya URL y
estructura cambian, sin una API estable (ver docs/adr/0009-bce-validacion-manual.md).
Por eso este módulo NO descarga: lee un CSV que Carlos guarda a mano en
data/raw/bce/bce_trade_balance.csv con las columnas:

    year,oil_exports_fob_usd,non_oil_exports_fob_usd,source_file

(valores en USD FOB, tal como aparecen en el boletín). Si el archivo no existe,
el pipeline sigue y el reporte de calidad indica que la validación BCE quedó pendiente.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from src import config

log = config.get_logger("extract_bce")
BCE_FILE = config.DATA_RAW / "bce" / "bce_trade_balance.csv"
REQUIRED = {"year", "oil_exports_fob_usd", "non_oil_exports_fob_usd"}


def extract(batch_id: str) -> pd.DataFrame:
    if not BCE_FILE.exists():
        log.warning("No hay archivo BCE en %s: se omite la validación BCE", BCE_FILE)
        return pd.DataFrame()
    df = pd.read_csv(BCE_FILE)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Al CSV del BCE le faltan columnas: {missing}")
    if "source_file" not in df.columns:
        df["source_file"] = BCE_FILE.name
    df["source_name"] = "bce_manual"
    df["extracted_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    df["batch_id"] = batch_id
    return df


def load_bronze(engine, df: pd.DataFrame) -> int:
    from src import db
    return db.append(engine, df, "bronze", "bce_trade_raw")
