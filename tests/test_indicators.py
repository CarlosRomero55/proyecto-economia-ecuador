"""Pruebas de las fórmulas de negocio (HHI, CAGR, elasticidad, canasta)."""
import math

import numpy as np
import pandas as pd
import pytest

from src import indicators


def test_hhi_monopolio_y_reparto_igual():
    assert indicators.hhi([100]) == pytest.approx(10000)
    assert indicators.hhi([25, 25, 25, 25]) == pytest.approx(2500)
    assert indicators.equivalent_count(2500) == pytest.approx(4)


def test_hhi_ignora_ceros_y_nulos():
    assert indicators.hhi([50, 50, 0, np.nan]) == pytest.approx(5000)
    assert math.isnan(indicators.hhi([]))


def test_cagr():
    assert indicators.cagr(100, 200, 10) == pytest.approx(2 ** 0.1 - 1)
    assert math.isnan(indicators.cagr(0, 200, 10))
    assert math.isnan(indicators.cagr(100, 200, 0))


def test_elasticidad_recupera_beta_conocida():
    p = pd.Series(np.linspace(20, 110, 20))
    x = 3 * p ** 1.5
    r = indicators.elasticity(x, p)
    assert r["beta"] == pytest.approx(1.5, abs=1e-9)
    assert r["r2"] == pytest.approx(1.0)
    assert r["n"] == 20


def test_elasticidad_pocos_datos():
    assert math.isnan(indicators.elasticity(pd.Series([1, 2]), pd.Series([1, 2]))["beta"])


def _trade():
    rows = [
        # total, capítulos y partidas clave de un país-año (destino Mundo)
        ("ECU", 0, 2020, "TOTAL", 0, 1000.0, 1, 0),
        ("ECU", 0, 2020, "27", 2, 400.0, 1, 0),
        ("ECU", 0, 2020, "03", 2, 300.0, 1, 0),
        ("ECU", 0, 2020, "08", 2, 300.0, 1, 0),
        ("ECU", 0, 2020, "0306", 4, 250.0, 1, 0),
        ("ECU", 0, 2020, "0803", 4, 200.0, 1, 0),
        # destinos
        ("ECU", 842, 2020, "TOTAL", 0, 500.0, 0, 0),
        ("ECU", 156, 2020, "TOTAL", 0, 500.0, 0, 0),
        ("ECU", 899, 2020, "TOTAL", 0, 50.0, 0, 1),  # área especial: fuera del HHI
    ]
    return pd.DataFrame(rows, columns=["reporter_iso3", "partner_code", "year", "hs_code", "hs_level", "value_usd",
                                       "is_world", "is_special_partner"])


def test_canasta_suma_total_sin_doble_conteo():
    b = indicators.export_basket(_trade())
    assert b["value_usd"].sum() == pytest.approx(1000)
    other = b.loc[b["product_group"] == "other", "value_usd"].iloc[0]
    assert other == pytest.approx(1000 - 400 - 250 - 200)
    assert b["share"].sum() == pytest.approx(1)


def test_diversificacion_producto_y_destino():
    d = indicators.diversification(_trade()).iloc[0]
    assert d["hhi_product"] == pytest.approx(0.4 ** 2 * 1e4 + 2 * 0.3 ** 2 * 1e4)
    assert d["hhi_destination"] == pytest.approx(5000)


def test_dependencia_petrolera():
    dep = indicators.oil_dependency(indicators.export_basket(_trade())).iloc[0]
    assert dep["oil_share"] == pytest.approx(0.4)
    assert dep["non_oil_exports_usd"] == pytest.approx(600)


def test_indice_base():
    df = pd.DataFrame({"reporter_iso3": ["A", "A", "B", "B"], "year": [2000, 2001, 2000, 2001], "v": [10, 20, 5, 5]})
    assert list(indicators.index_base(df, "v", 2000)) == [100, 200, 100, 100]
