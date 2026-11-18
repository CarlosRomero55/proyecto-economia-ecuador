"""Pruebas de KPIs, hallazgos y proyección de la app (sobre datos sintéticos)."""
import numpy as np
import pandas as pd

import analytics


def test_kpis(synthetic_data):
    k = analytics.kpis(synthetic_data)
    assert k["first_year"] == 2000 and k["last_year"] == 2024
    assert 0 < k["oil_share_last"] < 1


def test_seis_hallazgos_en_ambos_idiomas(synthetic_data):
    for lang in ["es", "en"]:
        fs = analytics.findings(synthetic_data, lang)
        assert len(fs) == 6
        assert all(f["data"] and f["interpretation"] and f["implication"] for f in fs)


def test_formato_es_en():
    assert analytics._fmt_pct(0.1234, "es") == "12,3 %"
    assert analytics._fmt_pct(0.1234, "en") == "12.3%"
    assert analytics._fmt_num(12345.6, "es") == "12.346"


def test_forecast_tendencia_exacta():
    years = np.arange(2000, 2025)
    vals = 100 * 1.05 ** (years - 2000)
    fc = analytics.forecast_trend_ar1(years, vals, 3)
    assert list(fc["year"]) == [2025, 2026, 2027]
    assert fc["mean"].iloc[0] == __import__("pytest").approx(100 * 1.05 ** 25, rel=1e-6)
    assert (fc["lower"] <= fc["mean"]).all() and (fc["mean"] <= fc["upper"]).all()


def test_forecast_pocos_datos():
    assert analytics.forecast_trend_ar1([2000, 2001], [1, 2]).empty
