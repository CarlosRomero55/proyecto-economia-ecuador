"""Snapshot SINTÉTICO solo para pruebas automatizadas.

Estas cifras son inventadas a propósito y deterministas: sirven para comprobar
que la app, la API y los cálculos funcionan sin SQL Server. Nunca se escriben
en app/data ni se usan en documentos, hallazgos o gráficos publicados.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ISOS = ["ECU", "PER", "COL", "CHL"]
GROUPS = ["oil", "shrimp", "banana", "cocoa", "mining", "flowers", "tuna", "other"]
YEARS = list(range(2000, 2025))


def build() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)
    rows = []
    for iso in ISOS:
        for y in YEARS:
            base = rng.uniform(0.5, 1.5, len(GROUPS)) * (1 + 0.05 * (y - 2000))
            for g, v in zip(GROUPS, base):
                rows.append({"iso3": iso, "year": y, "product_group": g, "value_usd": float(v * 1e9)})
    basket = pd.DataFrame(rows)
    basket["share"] = basket["value_usd"] / basket.groupby(["iso3", "year"])["value_usd"].transform("sum")
    basket["rank_in_year"] = basket.groupby(["iso3", "year"])["value_usd"].rank(ascending=False, method="min").astype(int)

    tot = basket.groupby(["iso3", "year"])["value_usd"].sum().rename("total_exports_usd")
    oil = basket[basket["product_group"] == "oil"].set_index(["iso3", "year"])["value_usd"].rename("oil_exports_usd")
    dep = pd.concat([tot, oil], axis=1).reset_index()
    dep["non_oil_exports_usd"] = dep["total_exports_usd"] - dep["oil_exports_usd"]
    dep["oil_share"] = dep["oil_exports_usd"] / dep["total_exports_usd"]

    div = dep[["iso3", "year"]].copy()
    div["hhi_product"] = rng.uniform(1000, 3000, len(div))
    div["equiv_products"] = 10000 / div["hhi_product"]
    div["n_chapters"] = 90
    div["hhi_destination"] = rng.uniform(800, 2500, len(div))
    div["equiv_destinations"] = 10000 / div["hhi_destination"]
    div["n_destinations"] = 150

    cagr = basket.groupby(["iso3", "product_group"]).agg(start_year=("year", "min"), end_year=("year", "max")).reset_index()
    cagr["start_value"], cagr["end_value"], cagr["cagr"] = 1e9, 2e9, rng.uniform(0.01, 0.12, len(cagr))

    months = pd.date_range("2000-01-01", "2024-12-01", freq="MS")
    oil_m = pd.concat([pd.DataFrame({"series": s, "price_month": months,
                                     "price_usd_bbl": 40 + 30 * np.sin(np.arange(len(months)) / 20) + (5 if s == "brent" else 0),
                                     "source_name": "synthetic"}) for s in ["brent", "wti"]])
    oil_a = oil_m.assign(year=oil_m["price_month"].dt.year).groupby(["series", "year"]).agg(
        avg_price_usd_bbl=("price_usd_bbl", "mean"), months_available=("price_usd_bbl", "size")).reset_index()
    sens = pd.DataFrame([{"iso3": i, "target": tg, "n": 25, "elasticity_beta": 1.1, "r_squared": 0.7}
                         for i in ISOS for tg in ["oil_exports", "total_exports"]])

    ind = []
    for iso in ISOS + ["LCN"]:
        for code, unit in [("NE.EXP.GNFS.ZS", "%"), ("NY.GDP.MKTP.CD", "USD"), ("FP.CPI.TOTL.ZG", "%"),
                           ("NY.GDP.MKTP.KD.ZG", "%"), ("BX.TRF.PWKR.CD.DT", "USD"), ("BX.KLT.DINV.CD.WD", "USD")]:
            for y in YEARS:
                ind.append({"iso3": iso, "country_es": iso, "country_en": iso, "is_aggregate": iso == "LCN",
                            "indicator_code": code, "indicator_es": code, "indicator_en": code, "unit": unit, "year": y,
                            "value": float(rng.uniform(1, 40) * (1e9 if unit == "USD" else 1)), "is_interpolated": y == 2010})
    regional = pd.DataFrame(ind)

    idx = dep.copy()
    base = idx[idx["year"] == 2000].set_index("iso3")
    idx["total_index_2000"] = idx["total_exports_usd"] / idx["iso3"].map(base["total_exports_usd"]) * 100
    idx["non_oil_index_2000"] = idx["non_oil_exports_usd"] / idx["iso3"].map(base["non_oil_exports_usd"]) * 100
    idx = idx[["iso3", "year", "total_exports_usd", "non_oil_exports_usd", "total_index_2000", "non_oil_index_2000"]]

    events = pd.DataFrame([
        {"event_code": "global_crisis", "start_date": pd.Timestamp("2008-07-01"), "end_date": pd.Timestamp("2009-06-30"), "name_es": "Crisis", "name_en": "Crisis"},
        {"event_code": "covid", "start_date": pd.Timestamp("2020-03-01"), "end_date": pd.Timestamp("2020-12-31"), "name_es": "COVID", "name_en": "COVID"},
    ])
    runs = pd.DataFrame([{"run_id": 1, "batch_id": "SYNTH_full", "run_mode": "full", "started_at": pd.Timestamp("2026-01-01 10:00"),
                          "finished_at": pd.Timestamp("2026-01-01 10:05"), "status": "success", "rows_bronze": 100,
                          "rows_silver": 90, "rows_gold": 80, "message": "OK", "duration_seconds": 300}])
    layers = pd.DataFrame([{"layer": l, "table_name": f"t_{l}", "row_count": n} for l, n in [("bronze", 100), ("silver", 90), ("gold", 80)]])
    rules = pd.DataFrame([{"batch_id": "SYNTH_full", "rule_id": "WB01", "source_name": "world_bank_wdi",
                           "description": "regla de prueba", "rows_affected": 3, "logged_at": pd.Timestamp("2026-01-01")}])
    rec = dep[["iso3", "year", "oil_share"]].rename(columns={"oil_share": "oil_share_comtrade"})
    rec["fuel_share_worldbank"] = rec["oil_share_comtrade"] * 0.98
    rec["oil_share_bce"] = np.nan
    return {
        "export_basket": basket, "oil_dependency": dep, "diversification": div, "product_cagr": cagr,
        "oil_price_monthly": oil_m, "oil_price_annual": oil_a, "oil_sensitivity": sens, "regional_compare": regional,
        "exports_index": idx, "economic_events": events, "pipeline_runs": runs, "layer_counts": layers,
        "cleaning_rules": rules, "source_reconciliation": rec,
    }


def write(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = build()
    for name, df in data.items():
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
    (out_dir / "metadata.json").write_text(json.dumps({"exported_at_utc": "SINTÉTICO", "rows_per_table": {k: len(v) for k, v in data.items()}}))
    return out_dir
