"""Precio mensual del petróleo (Brent y WTI) hacia bronze.

Fuente principal: World Bank Commodity Price Data (Pink Sheet), hoja
"Monthly Prices". Respaldo: FRED (DCOILBRENTEU / DCOILWTICO), promedio mensual.
La elección está documentada en docs/adr/0005-fuente-precio-petroleo.md.
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone

import pandas as pd

from src import config, http_utils

log = config.get_logger("extract_oil")
PERIOD_RE = re.compile(r"^(\d{4})M(\d{2})$")
SERIES = {"CRUDE_BRENT": "brent", "CRUDE_WTI": "wti"}
NAME_HINTS = {"Crude oil, Brent": "brent", "Crude oil, WTI": "wti"}


def parse_pink_sheet(content: bytes) -> pd.DataFrame:
    """Lee la hoja 'Monthly Prices' sin depender de la fila exacta del encabezado.

    Busca la fila que contiene los códigos/nombres de las series y la columna
    de períodos con formato AAAAMmm (p. ej. 2020M04).
    """
    raw = pd.read_excel(io.BytesIO(content), sheet_name="Monthly Prices", header=None)
    col_map: dict[int, str] = {}
    for _, row in raw.head(15).iterrows():
        for j, cell in row.items():
            cell = str(cell).strip()
            if cell in SERIES:
                col_map[j] = SERIES[cell]
            elif cell in NAME_HINTS and j not in col_map:
                col_map[j] = NAME_HINTS[cell]
    if set(col_map.values()) != {"brent", "wti"}:
        raise ValueError("No se encontraron las columnas de Brent/WTI en el Pink Sheet")
    rows = []
    for _, row in raw.iterrows():
        m = PERIOD_RE.match(str(row.iloc[0]).strip())
        if not m:
            continue
        for j, series in col_map.items():
            rows.append({"period": f"{m.group(1)}-{m.group(2)}", "series": series, "value_raw": str(row.iloc[j])})
    df = pd.DataFrame(rows)
    df["source_name"] = "wb_pink_sheet"
    return df


def parse_fred(payload: dict, series: str) -> pd.DataFrame:
    """Observaciones mensuales de FRED; '.' significa dato faltante."""
    rows = [{"period": o["date"][:7], "series": series, "value_raw": o["value"]}
            for o in payload.get("observations", [])]
    df = pd.DataFrame(rows, columns=["period", "series", "value_raw"])
    df["source_name"] = "fred"
    return df


def fetch_fred() -> pd.DataFrame:
    if not config.FRED_API_KEY:
        raise RuntimeError("Falló el Pink Sheet y no hay FRED_API_KEY en .env para el respaldo")
    frames = []
    for sid, series in {"DCOILBRENTEU": "brent", "DCOILWTICO": "wti"}.items():
        params = {"series_id": sid, "api_key": config.FRED_API_KEY, "file_type": "json",
                  "frequency": "m", "aggregation_method": "avg",
                  "observation_start": f"{config.START_YEAR}-01-01"}
        raw = http_utils.get(config.FRED_API, params, subdir="fred", use_cache=False)
        frames.append(parse_fred(json.loads(raw), series))
    return pd.concat(frames, ignore_index=True)


def extract(batch_id: str) -> pd.DataFrame:
    try:
        content = http_utils.get(config.PINK_SHEET_URL, subdir="pink_sheet", suffix=".xlsx", use_cache=False)
        df = parse_pink_sheet(content)
        log.info("Pink Sheet: %s filas", len(df))
    except Exception as err:
        log.warning("Pink Sheet no disponible (%s). Uso FRED como respaldo.", err)
        df = fetch_fred()
    df = df[df["period"] >= f"{config.START_YEAR}-01"].reset_index(drop=True)
    df["extracted_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    df["batch_id"] = batch_id
    return df


def load_bronze(engine, df: pd.DataFrame) -> int:
    from src import db
    return db.append(engine, df, "bronze", "oil_price_raw")
