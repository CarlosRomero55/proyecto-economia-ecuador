"""Armonización entre fuentes: códigos de país, productos HS y catálogos.

Cada fuente identifica a los países de forma distinta:
  * Banco Mundial: ISO2 en country.id ("EC") e ISO3 en countryiso3code ("ECU").
  * Comtrade: código numérico M49 (218) e ISO3 en reporterISO.
  * BCE: nombre en español ("Ecuador").
La tabla maestra silver.country_codes_map resuelve todo a ISO3.
"""
from __future__ import annotations

import re

import pandas as pd

from src import config

ISO2 = {"ECU": "EC", "PER": "PE", "COL": "CO", "CHL": "CL", "LCN": "ZJ"}
ISO3_RE = re.compile(r"^[A-Z]{3}$")
# Códigos M49 de Comtrade que no son países: Mundo, UE, "n.e.s." regionales,
# bunkers, zonas francas, categorías especiales y "áreas n.e.s."
SPECIAL_PARTNER_CODES = {0, 97, 290, 471, 472, 473, 490, 492, 527, 536, 568, 577, 636, 637, 837, 838, 839, 879, 899}


def country_codes_map() -> pd.DataFrame:
    """Catálogo maestro ISO3 ↔ ISO2 ↔ M49 (Comtrade) ↔ nombres."""
    rows = []
    for iso3, (m49, name_es, name_en, is_agg) in config.COUNTRIES.items():
        rows.append({
            "iso3": iso3, "iso2": ISO2[iso3], "comtrade_code": m49,
            "name_es": name_es, "name_en": name_en,
            "bce_name": name_es if iso3 == "ECU" else None,
            "is_aggregate": int(is_agg),
        })
    return pd.DataFrame(rows)


def products_hs() -> pd.DataFrame:
    """Catálogo de productos clave + grupo 'other'."""
    rows = [
        {"hs_code": code, "hs_level": len(code), "product_group": g, "name_es": es, "name_en": en, "is_key_product": 1}
        for code, (g, es, en) in config.KEY_PRODUCTS.items()
    ]
    rows.append({"hs_code": "TOTAL", "hs_level": 0, "product_group": "total",
                 "name_es": "Total exportaciones", "name_en": "Total exports", "is_key_product": 0})
    return pd.DataFrame(rows)


def product_group(hs_code: str) -> str:
    """Grupo de producto para un código HS (2 o 4 dígitos)."""
    if hs_code in config.KEY_PRODUCTS:
        return config.KEY_PRODUCTS[hs_code][0]
    if hs_code == "TOTAL":
        return "total"
    return config.OTHER_GROUP[0]


def comtrade_to_iso3(codes: pd.Series) -> pd.Series:
    """Convierte códigos M49 de Comtrade a ISO3 usando el catálogo maestro."""
    m = {v[0]: k for k, v in config.COUNTRIES.items() if v[0] is not None}
    return pd.to_numeric(codes, errors="coerce").map(m)


def is_special_partner(partner_code: pd.Series, partner_iso: pd.Series) -> pd.Series:
    """Socios que no son países: Mundo (0), 'áreas n.e.s.', zonas francas, bunkers, etc.

    Regla: el ISO de Comtrade no tiene forma de país (3 letras, p. ej. "W00",
    "S19", "_X") o el código M49 está en la lista de agrupaciones especiales.
    """
    code = pd.to_numeric(partner_code, errors="coerce").fillna(-1)
    iso_ok = partner_iso.fillna("").astype(str).str.match(ISO3_RE)
    return (~iso_ok) | code.isin(SPECIAL_PARTNER_CODES)


def wb_indicators() -> pd.DataFrame:
    return pd.DataFrame([
        {"indicator_code": c, "name_es": es, "name_en": en, "unit": u, "source_name": "world_bank_wdi"}
        for c, (es, en, u) in config.WB_INDICATORS.items()
    ])


def economic_events() -> pd.DataFrame:
    return pd.DataFrame(config.ECONOMIC_EVENTS,
                        columns=["start_date", "end_date", "event_code", "name_es", "name_en"])
