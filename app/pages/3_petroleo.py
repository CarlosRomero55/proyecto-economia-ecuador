"""Página 3 · Dependencia del petróleo: exportaciones petroleras vs Brent, con eventos.

Regla de diseño: nunca doble eje. Exportaciones y Brent van en dos gráficos
alineados (mismo eje X) y en un índice 2000 = 100 comparable.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import analytics  # noqa: E402
from common import (COUNTRY_COLORS, COUNTRY_NAMES, add_events, base_layout, events_caption, footer,  # noqa: E402
                    lang, load, require_data)
from i18n import t  # noqa: E402

l = lang()
st.title(t("p_oil", l))
data = require_data()
dep = data["oil_dependency"]
brent = data["oil_price_annual"].query("series == 'brent'").sort_values("year")
events = load("economic_events")
e = dep[dep["iso3"] == "ECU"].sort_values("year")

k = analytics.kpis(data)
st.markdown(
    f"**{t('k_beta', l)}: {analytics._fmt_num(k['oil_elasticity'], l, 2)}** "
    f"(R² {analytics._fmt_num(k['oil_elasticity_r2'], l, 2)}). "
    + ("Asociación anual en logaritmos; no implica causalidad." if l == "es" else "Annual log-log association; not causal."))

c1, c2 = st.columns(2)
f1 = go.Figure(go.Scatter(x=e["year"], y=e["oil_exports_usd"] / 1e9, mode="lines+markers",
                          name="Ecuador", line=dict(color=COUNTRY_COLORS["ECU"], width=2), marker=dict(size=8)))
f1.update_layout(showlegend=False)
c1.plotly_chart(add_events(base_layout(f1, t("oil_exports", l)), events, l), width="stretch")
f2 = go.Figure(go.Scatter(x=brent["year"], y=brent["avg_price_usd_bbl"], mode="lines+markers", name="Brent",
                          line=dict(color="#52514e", width=2), marker=dict(size=8)))
f2.update_layout(showlegend=False)
c2.plotly_chart(add_events(base_layout(f2, t("brent", l)), events, l), width="stretch")
st.caption(events_caption(events, l))

st.subheader(t("oil_share_title", l))
fig = go.Figure()
for iso in ["ECU", "PER", "COL", "CHL"]:
    d = dep[dep["iso3"] == iso].sort_values("year")
    if d.empty:
        continue
    fig.add_trace(go.Scatter(x=d["year"], y=d["oil_share"] * 100, name=COUNTRY_NAMES[l][iso], mode="lines",
                             line=dict(color=COUNTRY_COLORS[iso], width=3 if iso == "ECU" else 2)))
st.plotly_chart(add_events(base_layout(fig, t("oil_share_title", l), "%"), events, l), width="stretch")

m = data["oil_price_monthly"] if "oil_price_monthly" in data else None
if m is not None and not m.empty:
    fm = go.Figure()
    for s, color in [("brent", "#2a78d6"), ("wti", "#eb6834")]:
        d = m[m["series"] == s].sort_values("price_month")
        fm.add_trace(go.Scatter(x=d["price_month"], y=d["price_usd_bbl"], name=s.upper(), mode="lines",
                                line=dict(color=color, width=2)))
    st.plotly_chart(add_events(base_layout(fm, t("monthly_brent", l), "USD/bbl", 360), events, l, annual=False),
                    width="stretch")
footer()
