"""Coherencia entre catálogos de Python y scripts SQL, e idempotencia de los scripts."""
import re

import pandas as pd

from src import config, harmonize

SQL = {p.name: p.read_text(encoding="utf-8") for p in config.SQL_DIR.glob("*.sql")}


def test_country_map_unico():
    m = harmonize.country_codes_map()
    assert m["iso3"].is_unique and m["iso2"].is_unique
    assert m.loc[m["iso3"] == "ECU", "comtrade_code"].iloc[0] == 218
    assert harmonize.comtrade_to_iso3(pd.Series([218, 604, 999])).tolist()[:2] == ["ECU", "PER"]


def test_socios_especiales():
    s = harmonize.is_special_partner(pd.Series([0, 842, 899, 156]), pd.Series(["W00", "USA", "_X", "CHN"]))
    assert s.tolist() == [True, False, True, False]


def test_sql_semillas_cubren_config():
    silver = SQL["02_silver.sql"]
    for code in config.WB_INDICATORS:
        assert f"N'{code}'" in silver, code
    for code in config.KEY_PRODUCTS:
        assert f"N'{code}'" in silver, code
    for iso, (m49, *_rest) in config.COUNTRIES.items():
        assert f"'{iso}'" in silver


def test_sql_idempotente_sin_borrados():
    for name, text in SQL.items():
        upper = text.upper()
        assert "DROP TABLE" not in upper and "DROP DATABASE" not in upper, name
        assert not re.search(r"\bDELETE\s+FROM\b", upper), name
        for m in re.finditer(r"CREATE\s+(PROCEDURE|VIEW)", upper):
            assert upper[max(0, m.start() - 9):m.start()].strip().endswith("OR ALTER") or "OR ALTER" in upper[m.start():m.end() + 10], name


def test_sql_create_table_protegido():
    for name, text in SQL.items():
        n_create = len(re.findall(r"CREATE TABLE", text))
        n_guard = len(re.findall(r"IF OBJECT_ID\(N'[^']+', N'U'\) IS NULL\s*CREATE TABLE", text))
        assert n_create == n_guard, name
