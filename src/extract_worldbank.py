"""Extracción de indicadores del Banco Mundial (API v2, sin llave) hacia bronze."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from src import config, http_utils

log = config.get_logger("extract_worldbank")
SOURCE = "world_bank_wdi"


def parse_page(payload: list) -> tuple[pd.DataFrame, int]:
    """Convierte una página de la API en DataFrame y devuelve el total de páginas.

    La API responde [metadatos, registros]. Si el indicador no existe, responde
    [{"message": [...]}] — eso se trata como error explícito.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        msg = payload[0].get("message") if isinstance(payload, list) and payload else payload
        raise ValueError(f"Respuesta inesperada del Banco Mundial: {msg}")
    meta, rows = payload[0], payload[1] or []
    records = [
        {
            "indicator_code": r["indicator"]["id"],
            "indicator_name": r["indicator"]["value"],
            "country_iso2": r["country"]["id"],
            "country_iso3": r.get("countryiso3code") or None,
            "country_name": r["country"]["value"],
            "year": r["date"],  # llega como texto; se tipa en silver
            "value": r["value"],
            "obs_status": r.get("obs_status") or None,
        }
        for r in rows
    ]
    return pd.DataFrame(records), int(meta.get("pages", 1))


def fetch_indicator(code: str, start_year: int | None = None, use_cache: bool = True) -> pd.DataFrame:
    """Descarga un indicador para todos los países del alcance, paginando."""
    countries = ";".join(config.COUNTRIES)
    url = f"{config.WB_API}/country/{countries}/indicator/{code}"
    frames, page, pages = [], 1, 1
    while page <= pages:
        params = {"format": "json", "per_page": 1000, "page": page,
                  "date": f"{start_year or config.START_YEAR}:{config.END_YEAR}"}
        raw = http_utils.get(url, params, subdir="worldbank", use_cache=use_cache)
        df, pages = parse_page(json.loads(raw))
        frames.append(df)
        page += 1
    out = pd.concat(frames, ignore_index=True)
    log.info("Indicador %s: %s filas", code, len(out))
    return out


def extract(batch_id: str, start_year: int | None = None, use_cache: bool = True) -> pd.DataFrame:
    """Descarga todos los indicadores y agrega columnas de linaje para bronze.

    En modo incremental `start_year` = watermark - 2, porque el Banco Mundial
    revisa cifras de años recientes (ver ADR 0003).
    """
    frames = [fetch_indicator(code, start_year, use_cache) for code in config.WB_INDICATORS]
    df = pd.concat(frames, ignore_index=True)
    df["value"] = df["value"].astype("float64")
    df["source_name"] = SOURCE
    df["extracted_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    df["batch_id"] = batch_id
    return df


def load_bronze(engine, df: pd.DataFrame) -> int:
    from src import db
    return db.append(engine, df, "bronze", "wb_indicator_raw")
