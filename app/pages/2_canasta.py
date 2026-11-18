"""Página 2 · Canasta exportadora: área apilada 2000–hoy y ranking por año."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from common import (COUNTRY_NAMES, PRODUCT_COLORS, PRODUCT_NAMES, PRODUCT_ORDER, base_layout,  # noqa: E402
                    footer, lang, require_data)
from i18n import t  # noqa: E402

l = lang()
st.title(t("p_basket", l))
data = require_data()
basket = data["export_basket"]

f1, f2 = st.columns([2, 1])
countries = [c for c in ["ECU", "PER", "COL", "CHL"] if c in basket["iso3"].unique()]
iso = f1.selectbox(t("country", l), countries, format_func=lambda c: COUNTRY_NAMES[l][c])
as_share = f2.toggle(t("basket_share_toggle", l), value=False)

b = basket[basket["iso3"] == iso]
pv = b.pivot_table(index="year", columns="product_group", values="share" if as_share else "value_usd").sort_index()
fig = go.Figure()
for g in PRODUCT_ORDER:  # orden fijo = color fijo por producto
    if g not in pv.columns:
        continue
    y = pv[g] * (100 if as_share else 1 / 1e9)
    fig.add_trace(go.Scatter(
        x=pv.index, y=y, name=PRODUCT_NAMES[l][g], stackgroup="one", mode="lines",
        line=dict(width=0.8, color="white"), fillcolor=PRODUCT_COLORS[g],
        hovertemplate="%{y:.1f}" + (" %" if as_share else " bn") + "<extra>" + PRODUCT_NAMES[l][g] + "</extra>"))
y_title = "%" if as_share else ("USD mil millones" if l == "es" else "USD bn")
st.plotly_chart(base_layout(fig, f"{t('basket_title', l)} — {COUNTRY_NAMES[l][iso]}", y_title, 460),
                width="stretch")

years = sorted(b["year"].unique())
year = st.select_slider(t("year", l), options=years, value=years[-1])
r = b[b["year"] == year].sort_values("value_usd", ascending=True)
bar = go.Figure(go.Bar(
    x=r["value_usd"] / 1e9, y=[PRODUCT_NAMES[l][g] for g in r["product_group"]], orientation="h",
    marker=dict(color=[PRODUCT_COLORS[g] for g in r["product_group"]], line=dict(color="white", width=2)),
    text=[f"{s * 100:.1f} %" for s in r["share"]], textposition="outside",
    hovertemplate="%{y}: %{x:.2f} bn<extra></extra>"))
bar.update_layout(showlegend=False, hovermode="closest")
st.plotly_chart(base_layout(bar, f"{t('ranking_title', l)} {year}", "", 380), width="stretch")

table = r.sort_values("value_usd", ascending=False)[["product_group", "value_usd", "share"]].assign(
    product_group=lambda d: d["product_group"].map(PRODUCT_NAMES[l]))
table.columns = [t("product", l), t("value_usd", l), t("share", l)]
st.dataframe(table, hide_index=True, width="stretch",
             column_config={t("value_usd", l): st.column_config.NumberColumn(format="%,.0f"),
                            t("share", l): st.column_config.NumberColumn(format="percent")})
st.caption("Resto = total − productos clave (sin doble conteo entre capítulos HS2 y partidas HS4)."
           if l == "es" else "Other = total − key products (no double counting between HS2 chapters and HS4 headings).")
footer()
