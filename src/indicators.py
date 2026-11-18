"""Cálculo de indicadores de negocio (funciones puras y probadas).

KPIs (fórmulas en docs/plan.md):
  * HHI = Σ (participación_i × 100)²  → 0 a 10 000. Más alto = más concentrado.
  * Número equivalente de productos = 10 000 / HHI (cuántos productos "iguales"
    generarían la misma concentración; más fácil de explicar en una entrevista).
  * CAGR = (valor_final / valor_inicial)^(1/años) − 1
  * Elasticidad al Brent = pendiente β de ln(exportaciones) = α + β·ln(Brent)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import config


def hhi(values: pd.Series | np.ndarray) -> float:
    v = np.asarray(values, dtype="float64")
    v = v[~np.isnan(v) & (v > 0)]
    if v.size == 0 or v.sum() == 0:
        return float("nan")
    shares = v / v.sum() * 100
    return float(np.sum(shares ** 2))


def equivalent_count(hhi_value: float) -> float:
    return float("nan") if not hhi_value or np.isnan(hhi_value) else 10000.0 / hhi_value


def cagr(start_value: float, end_value: float, years: int) -> float:
    if years <= 0 or start_value is None or end_value is None or start_value <= 0 or end_value <= 0:
        return float("nan")
    return (end_value / start_value) ** (1 / years) - 1


def elasticity(exports: pd.Series, price: pd.Series) -> dict:
    """Regresión log-log por MCO. Devuelve beta, alfa, R² y n.

    Interpretación: β = 1,2 significa que si el Brent sube 10 %, las
    exportaciones petroleras tienden a subir ~12 % en el mismo año.
    Es una asociación, no una relación causal demostrada.
    """
    df = pd.DataFrame({"x": price, "y": exports}).dropna()
    df = df[(df["x"] > 0) & (df["y"] > 0)]
    if len(df) < 5:
        return {"beta": float("nan"), "alpha": float("nan"), "r2": float("nan"), "n": len(df)}
    lx, ly = np.log(df["x"].to_numpy()), np.log(df["y"].to_numpy())
    beta, alpha = np.polyfit(lx, ly, 1)
    pred = alpha + beta * lx
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    return {"beta": float(beta), "alpha": float(alpha), "r2": 1 - ss_res / ss_tot if ss_tot else float("nan"), "n": len(df)}


def export_basket(trade: pd.DataFrame) -> pd.DataFrame:
    """Canasta exportadora por país y año (destino = Mundo).

    Entrada: filas de silver.trade_flows. Salida: una fila por país-año-grupo
    con value_usd y share. 'other' = total − Σ productos clave, para que la
    canasta sume exactamente el total (sin doble conteo entre HS2 y HS4).
    """
    w = trade[trade["is_world"] == 1]
    rows = []
    for (iso, year), g in w.groupby(["reporter_iso3", "year"]):
        by_code = g.set_index("hs_code")["value_usd"]
        total = by_code.get("TOTAL")
        if total is None or pd.isna(total):
            total = g.loc[g["hs_level"] == 2, "value_usd"].sum()
        if not total:
            continue
        key_sum = 0.0
        for code, (group, _, _) in config.KEY_PRODUCTS.items():
            val = float(by_code.get(code, 0.0) or 0.0)
            key_sum += val
            rows.append({"reporter_iso3": iso, "year": int(year), "product_group": group, "value_usd": val})
        rows.append({"reporter_iso3": iso, "year": int(year), "product_group": config.OTHER_GROUP[0],
                     "value_usd": max(float(total) - key_sum, 0.0)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out.assign(share=pd.Series(dtype="float64"))
    out["share"] = out["value_usd"] / out.groupby(["reporter_iso3", "year"])["value_usd"].transform("sum")
    return out


def diversification(trade: pd.DataFrame) -> pd.DataFrame:
    """HHI por producto (capítulos HS2) y por destino (países socios), por país-año."""
    w2 = trade[(trade["is_world"] == 1) & (trade["hs_level"] == 2)]
    prod = w2.groupby(["reporter_iso3", "year"])["value_usd"].apply(hhi).rename("hhi_product")
    dest_rows = trade[(trade["is_world"] == 0) & (trade["is_special_partner"] == 0) & (trade["hs_code"] == "TOTAL")]
    dest = dest_rows.groupby(["reporter_iso3", "year"])["value_usd"].apply(hhi).rename("hhi_destination")
    out = pd.concat([prod, dest], axis=1).reset_index()
    out["equiv_products"] = out["hhi_product"].map(equivalent_count)
    out["equiv_destinations"] = out["hhi_destination"].map(equivalent_count)
    return out


def oil_dependency(basket: pd.DataFrame) -> pd.DataFrame:
    """Participación petrolera y no petrolera de las exportaciones por país-año."""
    tot = basket.groupby(["reporter_iso3", "year"])["value_usd"].sum().rename("total_exports_usd")
    oil = basket[basket["product_group"] == "oil"].set_index(["reporter_iso3", "year"])["value_usd"].rename("oil_exports_usd")
    df = pd.concat([tot, oil], axis=1).fillna({"oil_exports_usd": 0}).reset_index()
    df["non_oil_exports_usd"] = df["total_exports_usd"] - df["oil_exports_usd"]
    df["oil_share"] = df["oil_exports_usd"] / df["total_exports_usd"]
    return df


def product_cagr(basket: pd.DataFrame, iso3: str, start: int, end: int) -> pd.DataFrame:
    b = basket[basket["reporter_iso3"] == iso3].pivot_table(index="year", columns="product_group", values="value_usd")
    rows = []
    for grp in b.columns:
        s, e = b[grp].get(start), b[grp].get(end)
        rows.append({"product_group": grp, "start_year": start, "end_year": end,
                     "start_value": s, "end_value": e, "cagr": cagr(s, e, end - start)})
    return pd.DataFrame(rows).sort_values("cagr", ascending=False)


def index_base(df: pd.DataFrame, value_col: str, base_year: int, by: str = "reporter_iso3") -> pd.Series:
    """Índice base_year = 100 para comparar países de tamaños distintos."""
    base = df[df["year"] == base_year].set_index(by)[value_col]
    return df[value_col] / df[by].map(base) * 100
