"""Página 4 · Ecuador vs la región: comparativos normalizados con filtros."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from common import COUNTRY_COLORS, COUNTRY_NAMES, base_layout, footer, lang, require_data  # noqa: E402
from i18n import t  # noqa: E402

l = lang()
st.title(t("p_region", l))
data = require_data()
rc = data["regional_compare"]

# Filtros en una sola fila, arriba de los gráficos
f1, f2 = st.columns([1, 2])
ind_names = rc.drop_duplicates("indicator_code").set_index("indicator_code")["indicator_es" if l == "es" else "indicator_en"]
default_ind = "NE.EXP.GNFS.ZS" if "NE.EXP.GNFS.ZS" in ind_names.index else ind_names.index[0]
ind = f1.selectbox(t("indicator", l), list(ind_names.index), index=list(ind_names.index).index(default_ind),
                   format_func=lambda c: ind_names[c])
all_c = [c for c in ["ECU", "PER", "COL", "CHL", "LCN"] if c in rc["iso3"].unique()]
sel = f2.multiselect(t("countries", l), all_c, default=all_c, format_func=lambda c: COUNTRY_NAMES[l][c])

d = rc[(rc["indicator_code"] == ind) & (rc["iso3"].isin(sel))]
unit = d["unit"].iloc[0] if len(d) else ""
scale = 1e9 if unit == "USD" else 1
fig = go.Figure()
for iso in all_c:  # color fijo por país aunque cambie el filtro
    s = d[d["iso3"] == iso].sort_values("year")
    if s.empty:
        continue
    fig.add_trace(go.Scatter(
        x=s["year"], y=s["value"] / scale, name=COUNTRY_NAMES[l][iso], mode="lines+markers",
        line=dict(color=COUNTRY_COLORS[iso], width=3 if iso == "ECU" else 2, dash="dot" if iso == "LCN" else "solid"),
        marker=dict(size=8, symbol=["circle-open" if i else "circle" for i in s["is_interpolated"]])))
y_title = ("USD mil millones" if l == "es" else "USD bn") if unit == "USD" else unit
st.plotly_chart(base_layout(fig, ind_names.get(ind, ind), y_title), width="stretch")
st.caption(t("interpolated_note", l) + (" Los valores en USD son corrientes (no ajustados por inflación)." if l == "es"
                                        else " USD values are current (not inflation-adjusted)."))

c1, c2 = st.columns(2)
idx = data["exports_index"]
fi = go.Figure()
for iso in ["ECU", "PER", "COL", "CHL"]:
    s = idx[(idx["iso3"] == iso) & idx["iso3"].isin(sel)].sort_values("year")
    if s.empty:
        continue
    fi.add_trace(go.Scatter(x=s["year"], y=s["non_oil_index_2000"], name=COUNTRY_NAMES[l][iso], mode="lines",
                            line=dict(color=COUNTRY_COLORS[iso], width=3 if iso == "ECU" else 2)))
fi.add_hline(y=100, line_color="#c3c2b7", line_width=1)
c1.plotly_chart(base_layout(fi, t("region_index_title", l), "2000 = 100"), width="stretch")

div = data["diversification"]
fh = go.Figure()
for iso in ["ECU", "PER", "COL", "CHL"]:
    s = div[(div["iso3"] == iso) & div["iso3"].isin(sel)].sort_values("year")
    if s.empty:
        continue
    fh.add_trace(go.Scatter(x=s["year"], y=s["hhi_product"], name=COUNTRY_NAMES[l][iso], mode="lines",
                            line=dict(color=COUNTRY_COLORS[iso], width=3 if iso == "ECU" else 2)))
c2.plotly_chart(base_layout(fh, t("hhi_title", l), "HHI (0–10 000)"), width="stretch")
footer()
