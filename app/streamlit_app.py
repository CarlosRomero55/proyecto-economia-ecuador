"""Punto de entrada de la app (Streamlit multipágina con st.navigation).

Ejecutar en local:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n import t  # noqa: E402

st.set_page_config(page_title="Ecuador Trade & Economy Monitor", page_icon="📈", layout="wide")

# Selector de idioma: parámetros fijos + key, para que Streamlit conserve la
# elección entre páginas; las páginas leen st.session_state["lang"]
with st.sidebar:
    choice = st.radio("Idioma / Language", ["Español", "English"], horizontal=True, key="lang_choice")
st.session_state["lang"] = "es" if choice == "Español" else "en"
lang = st.session_state["lang"]

PAGES = Path(__file__).resolve().parent / "pages"
nav = st.navigation([
    st.Page(PAGES / "1_resumen.py", title=t("p_summary", lang), icon="🏠", default=True),
    st.Page(PAGES / "2_canasta.py", url_path="canasta", title=t("p_basket", lang), icon="🧺"),
    st.Page(PAGES / "3_petroleo.py", url_path="petroleo", title=t("p_oil", lang), icon="🛢️"),
    st.Page(PAGES / "4_region.py", url_path="region", title=t("p_region", lang), icon="🌎"),
    st.Page(PAGES / "5_proyeccion.py", url_path="proyeccion", title=t("p_forecast", lang), icon="🔭"),
    st.Page(PAGES / "6_calidad.py", url_path="calidad", title=t("p_quality", lang), icon="🧪"),
])
nav.run()
