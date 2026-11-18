"""Página 6 · Calidad y pipeline: arquitectura, última ejecución, filas por capa y reglas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from common import base_layout, footer, lang, load, require_data  # noqa: E402
from i18n import t  # noqa: E402

l = lang()
st.title(t("p_quality", l))
data = require_data()

st.subheader(t("arch_title", l))
st.graphviz_chart("""
digraph {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#F3F5F8", color="#9aa4b2", fontname="Helvetica"];
  wb [label="Banco Mundial\\nWDI API"]; ct [label="UN Comtrade\\nAPI"]; oil [label="Pink Sheet / FRED"]; bce [label="BCE (CSV manual)"];
  py [label="Python\\nextract · clean · validate"];
  subgraph cluster_sql { label="SQL Server · EcuadorMonitor"; color="#1F4E79";
    br [label="bronze\\ncrudo + linaje"]; sv [label="silver\\n3FN + MERGE"]; gd [label="gold\\nestrella + KPIs"]; }
  pbi [label="Power BI"]; api [label="FastAPI"]; pq [label="Parquet snapshot"]; app [label="Streamlit Cloud"];
  wb -> py; ct -> py; oil -> py; bce -> py; py -> br -> sv -> gd; gd -> pbi; gd -> api; gd -> pq -> app;
}""")

runs = load("pipeline_runs")
if runs is not None and not runs.empty:
    last = runs.sort_values("run_id").iloc[-1]
    st.subheader(t("last_run", l))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Batch", str(last["batch_id"]))
    c2.metric(t("status", l), str(last["status"]))
    c3.metric(t("duration", l), f"{last['duration_seconds']:.0f}" if last["duration_seconds"] == last["duration_seconds"] else "—")
    c4.metric("Gold rows", f"{int(last['rows_gold']):,}" if last["rows_gold"] == last["rows_gold"] else "—")

counts = load("layer_counts")
if counts is not None and not counts.empty:
    st.subheader(t("rows_layer", l))
    agg = counts.groupby("layer", as_index=False)["row_count"].sum().set_index("layer").reindex(["bronze", "silver", "gold"]).reset_index()
    fig = go.Figure(go.Bar(x=agg["layer"], y=agg["row_count"], marker=dict(color="#2a78d6", line=dict(color="white", width=2)),
                           text=agg["row_count"].map(lambda v: f"{v:,.0f}"), textposition="outside",
                           hovertemplate="%{x}: %{y:,}<extra></extra>"))
    fig.update_layout(showlegend=False, hovermode="closest")
    st.plotly_chart(base_layout(fig, t("rows_layer", l), "", 320), width="stretch")
    with st.expander("Detalle por tabla" if l == "es" else "Per-table detail"):
        st.dataframe(counts.sort_values(["layer", "table_name"]), hide_index=True, width="stretch")

rules = load("cleaning_rules")
if rules is not None and not rules.empty:
    st.subheader(t("rules", l))
    st.dataframe(rules[["rule_id", "source_name", "description", "rows_affected"]], hide_index=True, width="stretch")

rec = load("source_reconciliation")
if rec is not None and not rec.empty:
    st.subheader(t("recon", l))
    r = rec[rec["iso3"] == "ECU"].sort_values("year")
    fr = go.Figure()
    for col, name, color in [("oil_share_comtrade", "UN Comtrade (HS 27)", "#2a78d6"),
                             ("fuel_share_worldbank", "World Bank TX.VAL.FUEL.ZS.UN", "#eb6834"),
                             ("oil_share_bce", "BCE", "#1baf7a")]:
        if col in r and r[col].notna().any():
            fr.add_trace(go.Scatter(x=r["year"], y=r[col] * 100, name=name, mode="lines+markers",
                                    line=dict(color=color, width=2), marker=dict(size=8)))
    st.plotly_chart(base_layout(fr, t("recon", l), "%", 360), width="stretch")
    st.caption("Diferencias esperadas: el indicador del Banco Mundial usa exportaciones de mercancías y su propia "
               "clasificación de combustibles (SITC 3); Comtrade usa el capítulo HS 27." if l == "es" else
               "Expected differences: the World Bank indicator uses merchandise exports and its own fuels "
               "classification (SITC 3); Comtrade uses HS chapter 27.")
footer()
