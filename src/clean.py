"""Limpieza bronze → silver.

Cada regla tiene un identificador (WB01, CT03, OIL02...) y se registra con
el número de filas afectadas en un CleaningLog. Ese registro se guarda en
silver.cleaning_log y alimenta docs/data_quality_report.md.
Las funciones son puras (DataFrame → DataFrame) para poder probarlas sin base.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src import config, harmonize


@dataclass
class CleaningLog:
    rows: list[dict] = field(default_factory=list)

    def add(self, rule_id: str, source: str, description: str, affected: int) -> None:
        self.rows.append({"rule_id": rule_id, "source_name": source,
                          "description": description, "rows_affected": int(affected)})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["rule_id", "source_name", "description", "rows_affected"])


# ---------------------------------------------------------------- Banco Mundial
def clean_worldbank(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    src = "world_bank_wdi"
    df = raw.copy()
    log.add("WB00", src, "Filas recibidas desde bronze", len(df))

    # WB01: registros sin ISO3 no se pueden unir con otras fuentes
    mask = df["country_iso3"].isna() | (df["country_iso3"].astype(str).str.len() != 3)
    log.add("WB01", src, "Se descartan filas sin código ISO3 válido", mask.sum())
    df = df[~mask]

    # WB02: el año llega como texto; se tipa y se descarta lo no numérico o fuera de alcance
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    mask = df["year"].isna() | (df["year"] < config.START_YEAR) | (df["year"] > config.END_YEAR)
    log.add("WB02", src, "Año no numérico o fuera de 2000–hoy", mask.sum())
    df = df[~mask].astype({"year": "int64"})

    # WB03: duplicados por re-extracción: gana la extracción más reciente
    df = df.sort_values("extracted_at")
    dup = df.duplicated(["country_iso3", "indicator_code", "year"], keep="last")
    log.add("WB03", src, "Duplicados país-indicador-año (se conserva la extracción más reciente)", dup.sum())
    df = df[~dup]

    # WB04: valores nulos = año aún no publicado o no reportado. Se eliminan
    # (formato largo: solo se guarda lo observado) y luego se interpolan
    # únicamente huecos interiores de 1 año, marcados con is_interpolated=1.
    nulls = df["value"].isna()
    log.add("WB04", src, "Valores nulos (año no publicado o no reportado) eliminados", nulls.sum())
    df = df[~nulls]
    df = df[["country_iso3", "indicator_code", "year", "value", "obs_status", "source_name", "batch_id"]]
    df = df.assign(is_interpolated=0)
    filled = interpolate_single_gaps(df)
    log.add("WB05", src, "Huecos interiores de 1 año interpolados linealmente (is_interpolated=1)",
            int(filled["is_interpolated"].sum()))
    return filled.sort_values(["country_iso3", "indicator_code", "year"]).reset_index(drop=True)


def interpolate_single_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """Rellena solo huecos de exactamente un año entre dos observaciones reales.

    Justificación: permite graficar series continuas sin inventar tendencias;
    huecos de 2+ años o en los extremos se dejan vacíos.
    """
    out = [df]
    for (iso, ind), g in df.groupby(["country_iso3", "indicator_code"]):
        s = g.set_index("year")["value"]
        for y in range(int(s.index.min()) + 1, int(s.index.max())):
            if y not in s.index and (y - 1) in s.index and (y + 1) in s.index:
                out.append(pd.DataFrame([{
                    "country_iso3": iso, "indicator_code": ind, "year": y,
                    "value": (s[y - 1] + s[y + 1]) / 2, "obs_status": "interpolated",
                    "source_name": g["source_name"].iloc[0], "batch_id": g["batch_id"].iloc[0],
                    "is_interpolated": 1,
                }]))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- Comtrade
def clean_comtrade(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    src = "un_comtrade"
    df = raw.copy()
    log.add("CT00", src, "Filas recibidas desde bronze", len(df))

    # CT01: solo exportaciones
    mask = df["flow_code"].astype(str) != "X"
    log.add("CT01", src, "Flujos distintos de exportación (X)", mask.sum())
    df = df[~mask]

    # CT02: solo totales (sin desagregar por modo de transporte, aduana o socio secundario)
    p2 = pd.to_numeric(df["partner2_code"], errors="coerce").fillna(0)
    mot = pd.to_numeric(df["mot_code"], errors="coerce").fillna(0)
    cus = df["customs_code"].fillna("C00").astype(str)
    mask = (p2 != 0) | (mot != 0) | (cus != "C00")
    log.add("CT02", src, "Desgloses por transporte/aduana/socio secundario (se conservan solo totales)", mask.sum())
    df = df[~mask]

    # CT03: código numérico de reportante → ISO3
    df["reporter_iso3"] = harmonize.comtrade_to_iso3(df["reporter_code"])
    mask = df["reporter_iso3"].isna()
    log.add("CT03", src, "Reportantes fuera del catálogo maestro de países", mask.sum())
    df = df[~mask]

    # CT04: valor nulo o negativo no es un dato de comercio válido
    df["value_usd"] = pd.to_numeric(df["primary_value"], errors="coerce")
    mask = df["value_usd"].isna() | (df["value_usd"] < 0)
    log.add("CT04", src, "Valor de exportación nulo o negativo", mask.sum())
    df = df[~mask]

    # CT05: código HS normalizado y nivel (0 = total, 2 = capítulo, 4 = partida)
    df["hs_code"] = df["cmd_code"].astype(str).str.strip().str.upper()
    df["hs_level"] = np.where(df["hs_code"] == "TOTAL", 0, df["hs_code"].str.len())
    mask = ~df["hs_level"].isin([0, 2, 4])
    log.add("CT05", src, "Códigos HS con nivel distinto de total/2/4 dígitos", mask.sum())
    df = df[~mask]

    # CT06: socio "Mundo" vs socios país; áreas especiales se marcan (no se borran)
    df["partner_code"] = pd.to_numeric(df["partner_code"], errors="coerce").fillna(0).astype("int64")
    df["is_world"] = (df["partner_code"] == 0).astype(int)
    special = harmonize.is_special_partner(df["partner_code"], df["partner_iso"]) & (df["is_world"] == 0)
    df["is_special_partner"] = special.astype(int)
    log.add("CT06", src, "Socios que no son países (áreas n.e.s., zonas especiales) marcados", special.sum())

    # CT07: duplicados (misma consulta repetida o capítulo que llegó en dos consultas)
    df["year"] = pd.to_numeric(df["ref_year"], errors="coerce").astype("int64")
    df = df.sort_values("extracted_at")
    key = ["reporter_iso3", "partner_code", "year", "hs_code"]
    dup = df.duplicated(key, keep="last")
    log.add("CT07", src, "Duplicados reportante-socio-año-HS (gana la extracción más reciente)", dup.sum())
    df = df[~dup]

    df["partner_iso3"] = np.where(df["is_world"] == 1, "WLD", df["partner_iso"].fillna("UNK"))
    df["net_weight_kg"] = pd.to_numeric(df["net_wgt"], errors="coerce")
    cols = ["reporter_iso3", "partner_code", "partner_iso3", "partner_desc", "year", "hs_code", "hs_level",
            "value_usd", "net_weight_kg", "is_world", "is_special_partner", "source_name", "batch_id", "cmd_desc"]
    return df[cols].reset_index(drop=True)


# ---------------------------------------------------------------- Petróleo
def clean_oil(raw: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    src = "oil_prices"
    df = raw.copy()
    log.add("OIL00", src, "Filas recibidas desde bronze", len(df))

    # OIL01: '.', '…' o vacío = dato faltante
    df["price_usd_bbl"] = pd.to_numeric(df["value_raw"], errors="coerce")
    mask = df["price_usd_bbl"].isna() | (df["price_usd_bbl"] <= 0)
    log.add("OIL01", src, "Precios faltantes ('.', '…') o no positivos", mask.sum())
    df = df[~mask]

    # OIL02: período AAAA-MM → fecha del primer día del mes
    df["price_month"] = pd.to_datetime(df["period"] + "-01", errors="coerce")
    mask = df["price_month"].isna()
    log.add("OIL02", src, "Períodos con formato inválido", mask.sum())
    df = df[~mask]

    # OIL03: si hay dos fuentes para el mismo mes, gana el Pink Sheet (fuente principal)
    df["priority"] = np.where(df["source_name"] == "wb_pink_sheet", 0, 1)
    df = df.sort_values(["priority", "extracted_at"], ascending=[True, False])
    dup = df.duplicated(["series", "price_month"], keep="first")
    log.add("OIL03", src, "Meses repetidos entre fuentes (prioridad: Pink Sheet > FRED)", dup.sum())
    df = df[~dup]
    return df[["series", "price_month", "price_usd_bbl", "source_name", "batch_id"]].sort_values(
        ["series", "price_month"]).reset_index(drop=True)


def oil_annual(oil: pd.DataFrame) -> pd.DataFrame:
    """Serie mensual → anual (promedio simple de los meses disponibles)."""
    df = oil.assign(year=oil["price_month"].dt.year)
    g = df.groupby(["series", "year"])
    return g["price_usd_bbl"].mean().to_frame("avg_price").join(g.size().to_frame("months")).reset_index()
