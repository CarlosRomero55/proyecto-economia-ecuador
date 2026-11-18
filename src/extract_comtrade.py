"""Extracción de exportaciones anuales desde UN Comtrade (comtradeapicall) hacia bronze.

Por cada país reportante y año se hacen 3 llamadas:
  1. Todos los capítulos HS a 2 dígitos (cmdCode="AG2"), destino = Mundo.
  2. Total + productos clave a 4 dígitos (camarón, banano, cacao, flores, atún).
  3. Total por país de destino (para el HHI de destinos).
El plan gratuito permite ~500 llamadas/día: se pausa entre llamadas y se
reanuda por año gracias a los watermarks (ver ADR 0003).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import pandas as pd

from src import config

log = config.get_logger("extract_comtrade")
SOURCE = "un_comtrade"
PAUSE_SECONDS = 1.5
KEEP_COLS = [
    "refYear", "reporterCode", "reporterISO", "flowCode", "partnerCode", "partnerISO",
    "partnerDesc", "partner2Code", "motCode", "customsCode", "cmdCode", "cmdDesc",
    "aggrLevel", "primaryValue", "fobvalue", "netWgt", "isAggregate",
]
KEY_HS4 = [c for c in config.KEY_PRODUCTS if len(c) == 4]
QUERIES = {
    "hs2_world": {"cmdCode": "AG2", "partnerCode": "0"},
    "hs4_world": {"cmdCode": ",".join(["TOTAL"] + KEY_HS4), "partnerCode": "0"},
    "total_by_partner": {"cmdCode": "TOTAL", "partnerCode": None},
}


class ComtradeAuthError(RuntimeError):
    """La API rechazó la llave o no hay llave configurada."""


def normalize(df: pd.DataFrame | None, query_name: str) -> pd.DataFrame:
    """Deja solo las columnas útiles (si alguna falta, queda en nulo)."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=KEEP_COLS + ["query_name"])
    out = df.reindex(columns=KEEP_COLS).copy()
    out["cmdCode"] = out["cmdCode"].astype(str)
    out["query_name"] = query_name
    return out


def _call(reporter_code: int, year: int, query: dict) -> pd.DataFrame | None:
    """Una llamada a la API, con caché JSON en data/raw/comtrade."""
    import comtradeapicall  # import diferido: solo se necesita al extraer

    cache_dir = config.DATA_RAW / "comtrade"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"{reporter_code}_{year}_{query['cmdCode'].replace(',', '-')}_{query['partnerCode']}.json"
    if cache.exists():
        return pd.DataFrame(json.loads(cache.read_text(encoding="utf-8")))
    for attempt in range(1, 5):
        try:
            df = comtradeapicall.getFinalData(
                config.COMTRADE_KEY, typeCode="C", freqCode="A", clCode="HS",
                period=str(year), reporterCode=str(reporter_code), cmdCode=query["cmdCode"],
                flowCode="X", partnerCode=query["partnerCode"], partner2Code=None,
                customsCode=None, motCode=None, maxRecords=100000,
                format_output="JSON", breakdownMode="classic", includeDesc=True,
            )
        except Exception as err:  # la librería lanza errores genéricos
            text = str(err)
            if "401" in text or "403" in text or "Access denied" in text:
                raise ComtradeAuthError("UN Comtrade rechazó la llave. Revisa COMTRADE_SUBSCRIPTION_KEY en .env") from err
            log.warning("Comtrade %s/%s intento %s falló: %s", reporter_code, year, attempt, text[:200])
            time.sleep(2 ** attempt)
            continue
        time.sleep(PAUSE_SECONDS)
        if df is None:
            # comtradeapicall devuelve None cuando la respuesta es un error HTTP
            time.sleep(2 ** attempt)
            continue
        cache.write_text(df.to_json(orient="records"), encoding="utf-8")
        return df
    raise RuntimeError(f"Comtrade no respondió para reporter={reporter_code} año={year}")


def extract(batch_id: str, years_by_reporter: dict[str, list[int]]) -> pd.DataFrame:
    """Descarga los años pedidos por país. Devuelve un DataFrame listo para bronze."""
    if not config.COMTRADE_KEY:
        raise ComtradeAuthError("Falta COMTRADE_SUBSCRIPTION_KEY en .env")
    frames = []
    for iso3, years in years_by_reporter.items():
        code = config.COMTRADE_REPORTERS[iso3]
        for year in years:
            for qname, q in QUERIES.items():
                frames.append(normalize(_call(code, year, q), qname))
            log.info("Comtrade %s %s descargado", iso3, year)
    df = pd.concat(frames, ignore_index=True) if frames else normalize(None, "")
    df = df.rename(columns={
        "refYear": "ref_year", "reporterCode": "reporter_code", "reporterISO": "reporter_iso",
        "flowCode": "flow_code", "partnerCode": "partner_code", "partnerISO": "partner_iso",
        "partnerDesc": "partner_desc", "partner2Code": "partner2_code", "motCode": "mot_code",
        "customsCode": "customs_code", "cmdCode": "cmd_code", "cmdDesc": "cmd_desc",
        "aggrLevel": "aggr_level", "primaryValue": "primary_value", "fobvalue": "fob_value",
        "netWgt": "net_wgt", "isAggregate": "is_aggregate",
    })
    # Tipos estables para bronze: enteros nulos como Int64 y banderas como texto
    for col in ["ref_year", "reporter_code", "partner_code", "partner2_code", "mot_code", "aggr_level"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["is_aggregate"] = df["is_aggregate"].astype("string")
    df["source_name"] = SOURCE
    df["extracted_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    df["batch_id"] = batch_id
    return df


def load_bronze(engine, df: pd.DataFrame) -> int:
    from src import db
    return db.append(engine, df, "bronze", "comtrade_raw")
