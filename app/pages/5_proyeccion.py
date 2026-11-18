"""Página 5 · Proyección y metodología: forecast con intervalo, supuestos y limitaciones."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import analytics  # noqa: E402
from common import COUNTRY_COLORS, base_layout, footer, lang, require_data  # noqa: E402
from i18n import t  # noqa: E402

l = lang()
st.title(t("p_forecast", l))
data = require_data()
dep = data["oil_dependency"]
e = dep[dep["iso3"] == "ECU"].sort_values("year")

h = st.slider(t("forecast_horizon", l), 1, 8, 5)
fc = analytics.forecast_trend_ar1(e["year"], e["non_oil_exports_usd"], h)

fig = go.Figure()
if not fc.empty:
    fig.add_trace(go.Scatter(x=list(fc["year"]) + list(fc["year"][::-1]),
                             y=list(fc["upper"] / 1e9) + list(fc["lower"][::-1] / 1e9),
                             fill="toself", fillcolor="rgba(42,120,214,0.15)", line=dict(width=0),
                             name=t("forecast_band", l), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc["year"], y=fc["mean"] / 1e9, name=t("forecast", l), mode="lines+markers",
                             line=dict(color=COUNTRY_COLORS["ECU"], width=2, dash="dash"), marker=dict(size=8)))
fig.add_trace(go.Scatter(x=e["year"], y=e["non_oil_exports_usd"] / 1e9, name=t("observed", l), mode="lines+markers",
                         line=dict(color=COUNTRY_COLORS["ECU"], width=2), marker=dict(size=8)))
st.plotly_chart(base_layout(fig, t("forecast_title", l), "USD mil millones" if l == "es" else "USD bn", 460),
                width="stretch")
if not fc.empty:
    show = fc.assign(**{c: (fc[c] / 1e9).round(2) for c in ["mean", "lower", "upper"]})
    st.dataframe(show, hide_index=True, width="stretch")
st.markdown(t("method_md", l))
footer()
