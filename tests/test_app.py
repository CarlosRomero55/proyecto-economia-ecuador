"""Cada página de Streamlit carga sin excepciones (AppTest), con y sin datos."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app"
PAGES = sorted((APP / "pages").glob("*.py"))


@pytest.fixture()
def with_data(synthetic_dir, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(synthetic_dir))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
@pytest.mark.parametrize("lang", ["es", "en"])
def test_paginas_con_datos(page, lang, with_data):
    at = AppTest.from_file(str(page), default_timeout=60)
    at.session_state["lang"] = lang
    at.run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_paginas_sin_datos_muestran_aviso(page, tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(page), default_timeout=60)
    at.run()
    assert not at.exception
    assert any("pipeline" in i.value for i in at.info)


def test_entrypoint(with_data):
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert not at.exception
    assert at.title[0].value == "Ecuador Trade & Economy Monitor"


def test_selector_idioma(with_data):
    at = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at.run()
    assert at.sidebar.radio[0].key == "lang_choice"
    at2 = AppTest.from_file(str(APP / "streamlit_app.py"), default_timeout=60)
    at2.session_state["lang_choice"] = "English"
    at2.run()
    assert not at2.exception and at2.session_state["lang"] == "en"
