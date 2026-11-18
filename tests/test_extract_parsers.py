"""Pruebas de los parsers de cada fuente (sin red: respuestas simuladas)."""
import io

import pandas as pd
import pytest

from src import extract_comtrade, extract_oil, extract_worldbank


def test_parse_worldbank_page():
    payload = [{"page": 1, "pages": 2, "per_page": 1000, "total": 1},
               [{"indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP (current US$)"},
                 "country": {"id": "EC", "value": "Ecuador"}, "countryiso3code": "ECU", "date": "2020",
                 "value": 1.0, "unit": "", "obs_status": "", "decimal": 0}]]
    df, pages = extract_worldbank.parse_page(payload)
    assert pages == 2
    assert df.iloc[0]["country_iso3"] == "ECU" and df.iloc[0]["year"] == "2020"
    assert df.iloc[0]["obs_status"] is None


def test_parse_worldbank_indicador_invalido():
    with pytest.raises(ValueError):
        extract_worldbank.parse_page([{"message": [{"id": "120", "value": "Invalid value"}]}])


def _pink_sheet_bytes():
    """Excel con la misma forma del Pink Sheet: encabezados en filas variables."""
    rows = [["World Bank Commodity Price Data", "", "", "", ""], [""] * 5, [""] * 5, [""] * 5,
            ["", "Crude oil, average", "Crude oil, Brent", "Crude oil, Dubai", "Crude oil, WTI"],
            ["", "($/bbl)", "($/bbl)", "($/bbl)", "($/bbl)"],
            ["", "CRUDE_PETRO", "CRUDE_BRENT", "CRUDE_DUBAI", "CRUDE_WTI"],
            ["2020M03", 32.0, 33.0, 31.0, 30.0], ["2020M04", 21.0, 26.0, 20.0, 16.5], ["2020M05", 30.0, "…", 30.0, 28.0]]
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, sheet_name="Monthly Prices", header=False, index=False)
    return buf.getvalue()


def test_parse_pink_sheet():
    df = extract_oil.parse_pink_sheet(_pink_sheet_bytes())
    assert set(df["series"]) == {"brent", "wti"}
    apr = df[(df["period"] == "2020-04") & (df["series"] == "brent")]
    assert float(apr["value_raw"].iloc[0]) == 26.0
    assert len(df) == 6  # 3 meses × 2 series; el '…' se limpia luego en silver


def test_parse_fred():
    df = extract_oil.parse_fred({"observations": [{"date": "2020-04-01", "value": "26.63"},
                                                  {"date": "2020-05-01", "value": "."}]}, "brent")
    assert list(df["period"]) == ["2020-04", "2020-05"] and df["source_name"].iloc[0] == "fred"


def test_comtrade_normalize_columnas_faltantes():
    out = extract_comtrade.normalize(pd.DataFrame([{"refYear": 2020, "cmdCode": 27, "primaryValue": 1.0}]), "q")
    assert list(out.columns) == extract_comtrade.KEEP_COLS + ["query_name"]
    assert out["cmdCode"].iloc[0] == "27" and pd.isna(out["partnerCode"].iloc[0])


def test_comtrade_sin_llave(monkeypatch):
    monkeypatch.setattr(extract_comtrade.config, "COMTRADE_KEY", "")
    with pytest.raises(extract_comtrade.ComtradeAuthError):
        extract_comtrade.extract("b", {"ECU": [2020]})
