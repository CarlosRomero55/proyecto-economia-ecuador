"""Utilidades compartidas por todas las páginas: idioma, datos, colores y pie de fuentes."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from i18n import t

def data_dir() -> Path:
    """Carpeta del snapshot (se lee en cada llamada para permitir APP_DATA_DIR en pruebas)."""
    return Path(os.getenv("APP_DATA_DIR", Path(__file__).resolve().parent / "data"))
REQUIRED = ["export_basket", "oil_dependency", "diversification", "product_cagr", "oil_price_annual",
            "oil_sensitivity", "exports_index", "regional_compare"]

# Colores categóricos en orden fijo, asignados por entidad (nunca por ranking).
# Paleta validada para daltonismo (skill dataviz); "other" y agregados en gris.
PRODUCT_COLORS = {
    "oil": "#2a78d6", "shrimp": "#eb6834", "banana": "#1baf7a", "cocoa": "#eda100",
    "mining": "#e87ba4", "flowers": "#008300", "tuna": "#6250d6", "other": "#a3a29c",
}
PRODUCT_ORDER = list(PRODUCT_COLORS)
COUNTRY_COLORS = {"ECU": "#2a78d6", "PER": "#eb6834", "COL": "#1baf7a", "CHL": "#eda100", "LCN": "#8a8984"}
EVENT_FILL = "rgba(120,120,120,0.12)"
EVENT_SHORT = {"global_crisis": "2008–09", "oil_collapse": "2014–16", "covid": "2020"}
TEXT_MUTED = "#52514e"

PRODUCT_NAMES = {
    "es": {"oil": "Petróleo", "shrimp": "Camarón", "banana": "Banano", "cocoa": "Cacao", "mining": "Minería",
           "flowers": "Flores", "tuna": "Atún (conservas)", "other": "Resto"},
    "en": {"oil": "Oil", "shrimp": "Shrimp", "banana": "Bananas", "cocoa": "Cocoa", "mining": "Mining",
           "flowers": "Flowers", "tuna": "Tuna (prepared)", "other": "Other"},
}
COUNTRY_NAMES = {
    "es": {"ECU": "Ecuador", "PER": "Perú", "COL": "Colombia", "CHL": "Chile", "LCN": "América Latina y el Caribe"},
    "en": {"ECU": "Ecuador", "PER": "Peru", "COL": "Colombia", "CHL": "Chile", "LCN": "Latin America & Caribbean"},
}

SOURCES = {
    "es": "Banco Mundial — World Development Indicators (API v2) · UN Comtrade (exportaciones FOB, HS) · "
          "Banco Mundial — Commodity Price Data (Pink Sheet) / FRED para Brent y WTI.",
    "en": "World Bank — World Development Indicators (API v2) · UN Comtrade (FOB exports, HS) · "
          "World Bank — Commodity Price Data (Pink Sheet) / FRED for Brent and WTI.",
}


def fmt_usd(x: float, l: str) -> str:
    """USD en miles de millones con formato del idioma."""
    v = f"{x / 1e9:,.1f}"
    if l == "es":
        v = v.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"USD {v} mil M"
    return f"USD {v} bn"


def lang() -> str:
    return st.session_state.get("lang", "es")


def names(l: str) -> dict[str, str]:
    return {**PRODUCT_NAMES[l], **COUNTRY_NAMES[l]}


@st.cache_data(show_spinner=False)
def _read(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path)


def load(name: str) -> pd.DataFrame | None:
    p = data_dir() / f"{name}.parquet"
    if not p.exists():
        return None
    return _read(str(p), p.stat().st_mtime)


def load_all() -> dict[str, pd.DataFrame] | None:
    """Todas las tablas del snapshot; None si falta alguna obligatoria."""
    data = {p.stem: load(p.stem) for p in data_dir().glob("*.parquet")}
    if any(data.get(r) is None for r in REQUIRED):
        return None
    return data


def metadata() -> dict:
    p = data_dir() / "metadata.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def require_data() -> dict[str, pd.DataFrame]:
    data = load_all()
    if data is None:
        st.info(t("no_data", lang()))
        footer()
        st.stop()
    return data


def footer() -> None:
    l = lang()
    meta = metadata()
    st.divider()
    upd = meta.get("exported_at_utc", "—")
    st.caption(f"**{t('sources', l)}:** {SOURCES[l]}  \n{t('updated', l)}: {upd}")


def base_layout(fig: go.Figure, title: str, y_title: str = "", height: int = 420) -> go.Figure:
    """Estilo sobrio: rejilla tenue, leyenda arriba, sin doble eje."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)), height=height, margin=dict(l=10, r=10, t=60, b=10),
        plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        font=dict(color="#1B1F24"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#d0d0cc", tickfont=dict(color=TEXT_MUTED))
    fig.update_yaxes(title=y_title, gridcolor="#ececea", zeroline=False, tickfont=dict(color=TEXT_MUTED))
    return fig


def add_events(fig: go.Figure, events: pd.DataFrame | None, l: str, annual: bool = True) -> go.Figure:
    """Sombrea los hitos (2008–2009, 2014–2016, 2020)."""
    if events is None:
        return fig
    for e in events.itertuples():
        x0, x1 = pd.Timestamp(e.start_date), pd.Timestamp(e.end_date)
        if annual:
            x0, x1 = x0.year - 0.5, x1.year + 0.5
        fig.add_vrect(x0=x0, x1=x1, fillcolor=EVENT_FILL, line_width=0, layer="below",
                      annotation_text=EVENT_SHORT.get(e.event_code, ""), annotation_position="top left",
                      annotation_font_size=10, annotation_font_color=TEXT_MUTED)
    return fig


def events_caption(events: pd.DataFrame | None, l: str) -> str:
    if events is None:
        return ""
    label = "Zonas sombreadas" if l == "es" else "Shaded areas"
    items = "; ".join(f"{EVENT_SHORT.get(e.event_code, '')}: {e.name_es if l == 'es' else e.name_en}" for e in events.itertuples())
    return f"{label} — {items}."
