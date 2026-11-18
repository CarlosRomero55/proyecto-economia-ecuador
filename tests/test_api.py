"""Pruebas de la API con el backend Parquet sobre el snapshot sintético."""
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(synthetic_dir, monkeypatch):
    monkeypatch.setenv("API_BACKEND", "parquet")
    monkeypatch.setenv("APP_DATA_DIR", str(synthetic_dir))
    import api.main as m
    importlib.reload(m)
    return TestClient(m.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "backend": "parquet"}


def test_indicators(client):
    r = client.get("/indicators", params={"country": "ECU", "indicator": "NE.EXP.GNFS.ZS"})
    assert r.status_code == 200 and len(r.json()) == 25
    assert client.get("/indicators", params={"country": "ZZZ"}).status_code == 404


def test_basket(client):
    r = client.get("/trade/basket", params={"year": 2024})
    body = r.json()
    assert r.status_code == 200 and len(body) == 8
    assert sum(x["share"] for x in body) == pytest.approx(1)


def test_diversification_y_validacion(client):
    assert {x["iso3"] for x in client.get("/diversification", params={"countries": "ECU,PER"}).json()} == {"ECU", "PER"}
    assert client.get("/diversification", params={"countries": "EC1"}).status_code == 422


def test_compare_ultimo_anio_comun(client):
    body = client.get("/compare").json()
    assert body["year"] == 2024 and len(body["values"]) == 5


def test_oil_sensitivity_y_last_run(client):
    assert client.get("/oil-sensitivity").json()[0]["elasticity_beta"] == pytest.approx(1.1)
    assert client.get("/pipeline/last-run").json()["status"] == "success"
