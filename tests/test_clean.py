"""Pruebas de las reglas de limpieza bronze → silver."""
from datetime import datetime

import pandas as pd
import pytest

from src import clean

T1, T2 = datetime(2026, 1, 1), datetime(2026, 2, 1)


def wb_raw():
    rows = [
        # ECU con hueco de 1 año en 2002 (se interpola) y nulo en 2004 (se elimina)
        ("NY.GDP.MKTP.CD", "EC", "ECU", "2000", 10.0, T1), ("NY.GDP.MKTP.CD", "EC", "ECU", "2001", 12.0, T1),
        ("NY.GDP.MKTP.CD", "EC", "ECU", "2003", 16.0, T1), ("NY.GDP.MKTP.CD", "EC", "ECU", "2004", None, T1),
        # duplicado: gana la extracción más reciente
        ("NY.GDP.MKTP.CD", "EC", "ECU", "2001", 13.0, T2),
        # sin ISO3 y año no numérico
        ("NY.GDP.MKTP.CD", "XX", "", "2001", 1.0, T1), ("NY.GDP.MKTP.CD", "EC", "ECU", "abc", 1.0, T1),
        ("NY.GDP.MKTP.CD", "EC", "ECU", "1999", 1.0, T1),
    ]
    df = pd.DataFrame(rows, columns=["indicator_code", "country_iso2", "country_iso3", "year", "value", "extracted_at"])
    return df.assign(obs_status=None, source_name="world_bank_wdi", batch_id="b1")


def test_clean_worldbank_reglas():
    log = clean.CleaningLog()
    out = clean.clean_worldbank(wb_raw(), log)
    r = log.to_frame().set_index("rule_id")["rows_affected"]
    assert r["WB01"] == 1 and r["WB02"] == 2 and r["WB03"] == 1 and r["WB04"] == 1 and r["WB05"] == 1
    assert out.loc[out["year"] == 2001, "value"].iloc[0] == 13.0
    interp = out[out["is_interpolated"] == 1]
    assert list(interp["year"]) == [2002] and interp["value"].iloc[0] == pytest.approx(14.5)
    assert not out.duplicated(["country_iso3", "indicator_code", "year"]).any()


def comtrade_raw():
    base = dict(reporter_iso="ECU", partner_iso="W00", partner_desc="World", cmd_desc="x", aggr_level=2,
                fob_value=None, net_wgt=None, is_aggregate="True", query_name="q", source_name="un_comtrade", batch_id="b1")
    rows = [
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="TOTAL", primary_value=100.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="27", primary_value=40.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="27", primary_value=41.0, extracted_at=T2),
        dict(ref_year=2020, reporter_code=218, flow_code="M", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="27", primary_value=5.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=2100, customs_code="C00", cmd_code="27", primary_value=5.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=999, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="27", primary_value=5.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="03", primary_value=-1.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=0, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="030617", primary_value=1.0, extracted_at=T1),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=842, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="TOTAL", primary_value=30.0, extracted_at=T1, partner_iso="USA"),
        dict(ref_year=2020, reporter_code=218, flow_code="X", partner_code=899, partner2_code=0, mot_code=0, customs_code="C00", cmd_code="TOTAL", primary_value=3.0, extracted_at=T1, partner_iso="_X"),
    ]
    return pd.DataFrame([{**base, **r} for r in rows])


def test_clean_comtrade_reglas():
    log = clean.CleaningLog()
    out = clean.clean_comtrade(comtrade_raw(), log)
    r = log.to_frame().set_index("rule_id")["rows_affected"]
    assert (r["CT01"], r["CT02"], r["CT03"], r["CT04"], r["CT05"], r["CT06"], r["CT07"]) == (1, 1, 1, 1, 1, 1, 1)
    assert out.loc[out["hs_code"] == "27", "value_usd"].iloc[0] == 41.0
    assert set(out["reporter_iso3"]) == {"ECU"}
    assert out.loc[out["partner_code"] == 0, "partner_iso3"].unique().tolist() == ["WLD"]
    assert out.loc[out["partner_code"] == 899, "is_special_partner"].iloc[0] == 1


def test_clean_oil_prioridad_pink_sheet():
    raw = pd.DataFrame([
        {"period": "2020-04", "series": "brent", "value_raw": "26.6", "source_name": "fred", "extracted_at": T2},
        {"period": "2020-04", "series": "brent", "value_raw": "26.0", "source_name": "wb_pink_sheet", "extracted_at": T1},
        {"period": "2020-05", "series": "brent", "value_raw": ".", "source_name": "fred", "extracted_at": T1},
        {"period": "2020-13", "series": "brent", "value_raw": "30", "source_name": "fred", "extracted_at": T1},
    ]).assign(batch_id="b1")
    log = clean.CleaningLog()
    out = clean.clean_oil(raw, log)
    assert len(out) == 1 and out["price_usd_bbl"].iloc[0] == 26.0 and out["source_name"].iloc[0] == "wb_pink_sheet"
    r = log.to_frame().set_index("rule_id")["rows_affected"]
    assert (r["OIL01"], r["OIL02"], r["OIL03"]) == (1, 1, 1)


def test_oil_annual():
    m = pd.DataFrame({"series": "brent", "price_month": pd.date_range("2020-01-01", periods=12, freq="MS"),
                      "price_usd_bbl": range(1, 13)})
    a = clean.oil_annual(m).iloc[0]
    assert a["avg_price"] == pytest.approx(6.5) and a["months"] == 12
