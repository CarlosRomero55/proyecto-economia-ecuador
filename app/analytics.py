"""KPIs y hallazgos calculados a partir del snapshot gold (solo pandas).

Lo usan la app de Streamlit y src/insights.py, así los hallazgos de
docs/insights.md y los de la app salen del mismo código y los mismos datos.
Ninguna cifra está escrita a mano: todo se calcula desde los Parquet.
"""
from __future__ import annotations

import math

import pandas as pd

FOCUS = "ECU"
PEERS = ["PER", "COL", "CHL"]
CRISIS_YEARS = {2009: "2008–2009", 2015: "2014–2016", 2016: "2014–2016", 2020: "2020"}


def _fmt_pct(x: float, lang: str, decimals: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d" if lang == "es" else "n/a"
    s = f"{x * 100:.{decimals}f} %"
    return s.replace(".", ",") if lang == "es" else s.replace(" %", "%")


def _fmt_num(x: float, lang: str, decimals: int = 0) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d" if lang == "es" else "n/a"
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "es" else s


def fmt_usd_bn(x: float, lang: str) -> str:
    return f"USD {_fmt_num(x / 1e9, lang, 1)} " + ("mil millones" if lang == "es" else "bn")


def year_range(dep: pd.DataFrame, iso: str = FOCUS) -> tuple[int, int]:
    years = dep.loc[dep["iso3"] == iso, "year"]
    return int(years.min()), int(years.max())


def kpis(data: dict[str, pd.DataFrame], iso: str = FOCUS) -> dict:
    """Tarjetas KPI del resumen (último año disponible del país)."""
    dep = data["oil_dependency"]
    y0, y1 = year_range(dep, iso)
    d = dep[dep["iso3"] == iso].set_index("year")
    div = data["diversification"]
    dv = div[div["iso3"] == iso].set_index("year")
    sens = data["oil_sensitivity"]
    s = sens[(sens["iso3"] == iso) & (sens["target"] == "oil_exports")]
    return {
        "first_year": y0, "last_year": y1,
        "total_exports_usd": float(d.loc[y1, "total_exports_usd"]),
        "oil_share_first": float(d.loc[y0, "oil_share"]),
        "oil_share_last": float(d.loc[y1, "oil_share"]),
        "hhi_product_first": float(dv["hhi_product"].get(y0, float("nan"))),
        "hhi_product_last": float(dv["hhi_product"].get(y1, float("nan"))),
        "equiv_products_last": float(dv["equiv_products"].get(y1, float("nan"))),
        "oil_elasticity": float(s["elasticity_beta"].iloc[0]) if len(s) else float("nan"),
        "oil_elasticity_r2": float(s["r_squared"].iloc[0]) if len(s) else float("nan"),
    }


def top_products(basket: pd.DataFrame, iso: str, year: int, n: int = 3) -> pd.DataFrame:
    b = basket[(basket["iso3"] == iso) & (basket["year"] == year) & (basket["product_group"] != "other")]
    return b.sort_values("value_usd", ascending=False).head(n)


def findings(data: dict[str, pd.DataFrame], lang: str = "es", names: dict[str, str] | None = None) -> list[dict]:
    """Seis hallazgos (dato → interpretación → implicación), redactados de forma neutral."""
    es = lang == "es"
    names = names or {}
    k = kpis(data)
    y0, y1 = k["first_year"], k["last_year"]
    basket, dep, div = data["export_basket"], data["oil_dependency"], data["diversification"]
    out = []

    # 1. Peso del petróleo
    delta = k["oil_share_last"] - k["oil_share_first"]
    dir_es = "bajó" if delta < 0 else "subió"
    dir_en = "fell" if delta < 0 else "rose"
    out.append({
        "id": "oil_share",
        "title": "Peso del petróleo en las exportaciones" if es else "Oil's weight in exports",
        "data": (f"El petróleo pasó de {_fmt_pct(k['oil_share_first'], lang)} de las exportaciones de Ecuador en {y0} "
                 f"a {_fmt_pct(k['oil_share_last'], lang)} en {y1} ({dir_es} {_fmt_num(abs(delta) * 100, lang, 1)} puntos)."
                 if es else
                 f"Oil went from {_fmt_pct(k['oil_share_first'], lang)} of Ecuador's exports in {y0} to "
                 f"{_fmt_pct(k['oil_share_last'], lang)} in {y1} ({dir_en} {abs(delta) * 100:.1f} points)."),
        "interpretation": ("La participación del crudo depende tanto de los volúmenes como del precio internacional; "
                           "una caída de participación no implica por sí sola menos barriles exportados."
                           if es else "Oil's share depends on both volumes and world prices; a lower share alone "
                           "does not imply fewer barrels exported."),
        "implication": ("Seguir el indicador junto con el precio del Brent evita confundir efecto precio con cambio estructural."
                        if es else "Tracking it alongside Brent avoids confusing a price effect with structural change."),
        "value": k["oil_share_last"],
    })

    # 2. Productos que más crecieron
    tp = top_products(basket, FOCUS, y1, 3)
    cg = data["product_cagr"]
    cg = cg[(cg["iso3"] == FOCUS) & (cg["product_group"] != "other")].sort_values("cagr", ascending=False)
    leader = tp.iloc[0] if len(tp) else None
    fastest = cg.iloc[0] if len(cg) else None
    pname = lambda g: names.get(g, g)
    nonoil = basket[(basket["iso3"] == FOCUS) & (basket["year"] == y1) & (basket["product_group"] != "oil")]
    top3 = nonoil[nonoil["product_group"] != "other"].nlargest(3, "value_usd")["value_usd"].sum()
    top3_nonoil = top3 / nonoil["value_usd"].sum() if nonoil["value_usd"].sum() else float("nan")
    out.append({
        "id": "basket_leaders",
        "title": "Nuevos líderes de la canasta" if es else "New leaders of the basket",
        "data": ((f"En {y1} el primer producto de exportación fue {pname(leader['product_group'])} "
                  f"({_fmt_pct(leader['share'], lang)} del total). El de mayor crecimiento anual compuesto fue "
                  f"{pname(fastest['product_group'])} ({_fmt_pct(fastest['cagr'], lang)} por año entre "
                  f"{int(fastest['start_year'])} y {int(fastest['end_year'])}).") if es else
                 (f"In {y1} the top export was {pname(leader['product_group'])} ({_fmt_pct(leader['share'], lang)} "
                  f"of the total). The fastest compound annual growth was {pname(fastest['product_group'])} "
                  f"({_fmt_pct(fastest['cagr'], lang)} per year between {int(fastest['start_year'])} and "
                  f"{int(fastest['end_year'])}).")) if leader is not None and fastest is not None else "",
        "interpretation": (f"Los tres principales productos no petroleros concentran {_fmt_pct(top3_nonoil, lang)} "
                           f"de las exportaciones no petroleras de {y1}." if es else
                           f"The top three non-oil products account for {_fmt_pct(top3_nonoil, lang)} of {y1} non-oil exports."),
        "implication": ("Sustituir un producto dominante por otro reduce la dependencia del crudo, no necesariamente la concentración."
                        if es else "Replacing one dominant product with another reduces oil dependence, not necessarily concentration."),
        "value": float(leader["share"]) if leader is not None else float("nan"),
    })

    # 3. Diversificación real (HHI)
    peers_last = div[(div["year"] == y1) & (div["iso3"].isin(PEERS))].set_index("iso3")["equiv_products"]
    peers_txt = ", ".join(f"{names.get(i, i)} {_fmt_num(v, lang, 1)}" for i, v in peers_last.items())
    out.append({
        "id": "hhi",
        "title": "¿Diversificación real o aparente?" if es else "Real or apparent diversification?",
        "data": (f"El HHI por producto de Ecuador pasó de {_fmt_num(k['hhi_product_first'], lang)} ({y0}) a "
                 f"{_fmt_num(k['hhi_product_last'], lang)} ({y1}): equivale a {_fmt_num(k['equiv_products_last'], lang, 1)} "
                 f"capítulos de igual tamaño. Pares en {y1}: {peers_txt or 'n/d'}." if es else
                 f"Ecuador's product HHI went from {_fmt_num(k['hhi_product_first'], lang)} ({y0}) to "
                 f"{_fmt_num(k['hhi_product_last'], lang)} ({y1}): equivalent to {_fmt_num(k['equiv_products_last'], lang, 1)} "
                 f"equally sized chapters. Peers in {y1}: {peers_txt or 'n/a'}."),
        "interpretation": ("Un HHI menor indica una canasta menos concentrada; el número equivalente lo vuelve intuitivo."
                           if es else "A lower HHI means a less concentrated basket; the equivalent count makes it intuitive."),
        "implication": ("Medir con HHI, y no solo con la participación del petróleo, distingue diversificación real de sustitución."
                        if es else "Measuring with HHI, not only oil's share, separates real diversification from substitution."),
        "value": k["hhi_product_last"],
    })

    # 4. Sensibilidad al Brent
    beta, r2 = k["oil_elasticity"], k["oil_elasticity_r2"]
    out.append({
        "id": "elasticity",
        "title": "Sensibilidad al precio del crudo" if es else "Sensitivity to oil prices",
        "data": (f"La elasticidad de las exportaciones petroleras de Ecuador al Brent es {_fmt_num(beta, lang, 2)} "
                 f"(R² = {_fmt_num(r2, lang, 2)}): si el Brent sube 10 %, estas exportaciones tienden a moverse "
                 f"cerca de {_fmt_num(beta * 10, lang, 1)} % en el mismo año." if es else
                 f"The elasticity of Ecuador's oil exports to Brent is {beta:.2f} (R² = {r2:.2f}): when Brent rises 10%, "
                 f"these exports tend to move about {beta * 10:.1f}% in the same year."),
        "interpretation": ("Es una asociación estadística anual, no una relación causal: también influyen volúmenes y diferenciales de precio."
                           if es else "It is an annual statistical association, not causality: volumes and price differentials also matter."),
        "implication": ("Los ingresos por exportaciones petroleras amplifican los movimientos del precio internacional."
                        if es else "Oil export revenue amplifies movements in world prices."),
        "value": beta,
    })

    # 5. Episodios de caída del crudo
    d = dep[dep["iso3"] == FOCUS].set_index("year").sort_index()
    chg = d["oil_exports_usd"].pct_change()
    chg_non = d["non_oil_exports_usd"].pct_change()
    shock_years = [y for y in (2009, 2015, 2016, 2020) if y in chg.index and not pd.isna(chg.get(y))]
    parts = [f"{y}: {_fmt_pct(chg.get(y), lang)}" for y in shock_years]
    parts_non = [f"{y}: {_fmt_pct(chg_non.get(y), lang)}" for y in shock_years]
    out.append({
        "id": "shocks",
        "title": "Golpe de los episodios de caída del crudo" if es else "Impact of oil price slumps",
        "data": (("Variación anual de las exportaciones petroleras de Ecuador en años de caída del crudo — " + "; ".join(parts) + ".")
                 if es else ("Annual change in Ecuador's oil exports in oil-slump years — " + "; ".join(parts) + "."))
                if parts else "",
        "interpretation": (("En los mismos años, las exportaciones no petroleras variaron así — " + "; ".join(parts_non) +
                            ". La comparación muestra qué parte del golpe vino del crudo.") if es else
                           ("In the same years, non-oil exports changed as follows — " + "; ".join(parts_non) +
                            ". The comparison shows how much of the shock came from oil.")),
        "implication": ("En una economía dolarizada, menos divisas por exportaciones se transmiten directamente a la liquidez."
                        if es else "In a dollarized economy, fewer export dollars feed directly into domestic liquidity."),
        "value": float(chg.get(2020, float("nan"))) if 2020 in chg.index else float("nan"),
    })

    # 6. Comparación regional
    idx = data["exports_index"]
    common = idx.dropna(subset=["non_oil_index_2000"]).groupby("year")["iso3"].nunique()
    yc = int(common[common == common.max()].index.max()) if len(common) else y1
    row = idx[idx["year"] == yc].set_index("iso3")["non_oil_index_2000"]
    comp = ", ".join(f"{names.get(i, i)} {_fmt_num(v, lang)}" for i, v in row.sort_values(ascending=False).items())
    out.append({
        "id": "regional",
        "title": "Ecuador frente a Perú, Colombia y Chile" if es else "Ecuador vs Peru, Colombia and Chile",
        "data": (f"Índice de exportaciones no petroleras (2000 = 100) en {yc}: {comp}." if es else
                 f"Non-oil export index (2000 = 100) in {yc}: {comp}."),
        "interpretation": ("El índice compara ritmos de crecimiento, no tamaños; un país pequeño puede crecer más rápido desde una base baja."
                           if es else "The index compares growth paths, not size; a small economy can grow faster from a low base."),
        "implication": ("Para comparar niveles conviene complementar con exportaciones como % del PIB (página Región)."
                        if es else "To compare levels, complement with exports as % of GDP (Region page)."),
        "value": float(row.get(FOCUS, float("nan"))),
    })
    return out


def forecast_trend_ar1(years, values, horizon: int = 5, z: float = 1.2816) -> pd.DataFrame:
    """Proyección ligera: tendencia log-lineal + errores AR(1), intervalo de 80 %.

    ln(y_t) = a + b·t + e_t,  e_t = φ·e_{t-1} + u_t,  u ~ N(0, σ²)
    Varianza del error a h pasos: σ²·Σ_{i<h} φ^{2i}. No incluye la
    incertidumbre de los parámetros (por eso el notebook usa statsmodels).
    """
    import numpy as np

    s = pd.Series(list(values), index=list(years)).dropna()
    s = s[s > 0].sort_index()
    if len(s) < 6:
        return pd.DataFrame(columns=["year", "mean", "lower", "upper"])
    tt = np.asarray(s.index, dtype=float)
    ly = np.log(s.to_numpy())
    b, a = np.polyfit(tt, ly, 1)
    e = ly - (a + b * tt)
    phi = float(np.clip(np.polyfit(e[:-1], e[1:], 1)[0], -0.95, 0.95))
    u = e[1:] - phi * e[:-1]
    sigma = float(np.std(u, ddof=2))
    rows, last_e = [], e[-1]
    for h in range(1, horizon + 1):
        yr = int(tt[-1]) + h
        mean_log = a + b * yr + (phi ** h) * last_e
        sd = sigma * np.sqrt(sum(phi ** (2 * i) for i in range(h)))
        rows.append({"year": yr, "mean": float(np.exp(mean_log)),
                     "lower": float(np.exp(mean_log - z * sd)), "upper": float(np.exp(mean_log + z * sd))})
    return pd.DataFrame(rows)
