"""API REST sobre la capa gold (FastAPI).

Ejecutar:  uvicorn api.main:app --reload    → documentación en http://127.0.0.1:8000/docs

Backends (variable API_BACKEND):
  * "sql"     (por defecto) — consulta las vistas gold en SQL Server.
  * "parquet" — lee el snapshot de app/data (útil para demos y pruebas sin SQL Server).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parents[1]
PARQUET_DIR = Path(os.getenv("APP_DATA_DIR", ROOT / "app" / "data"))

# vista gold -> archivo del snapshot
VIEWS = {
    "vw_regional_compare": "regional_compare", "vw_export_basket": "export_basket",
    "vw_diversification": "diversification", "vw_oil_sensitivity": "oil_sensitivity",
    "vw_pipeline_runs": "pipeline_runs", "vw_oil_dependency": "oil_dependency",
}

app = FastAPI(
    title="Ecuador Trade & Economy Monitor API",
    description="Indicadores macro, canasta exportadora, diversificación (HHI) y sensibilidad al Brent "
                "para Ecuador, Perú, Colombia, Chile y América Latina (fuentes: Banco Mundial, UN Comtrade).",
    version="1.0.0",
)


def backend() -> str:
    return os.getenv("API_BACKEND", "sql").lower()


def read_view(view: str) -> pd.DataFrame:
    """Lee una vista gold completa desde el backend activo."""
    if backend() == "parquet":
        p = PARQUET_DIR / f"{VIEWS[view]}.parquet"
        if not p.exists():
            raise HTTPException(503, f"Snapshot no disponible: {p.name}")
        return pd.read_parquet(p)
    import sys
    sys.path.insert(0, str(ROOT))
    from src import db  # import diferido: requiere pyodbc + driver ODBC
    return db.read_sql(db.get_engine(), f"SELECT * FROM gold.{view}")


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame → lista JSON nativa (NaN → null, fechas ISO, sin tipos numpy)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def countries_param(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    codes = [c.strip().upper() for c in value.split(",") if c.strip()]
    bad = [c for c in codes if len(c) != 3 or not c.isalpha()]
    if bad:
        raise HTTPException(422, f"Códigos ISO3 inválidos: {bad}")
    return codes


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "backend": backend()}


@app.get("/indicators", tags=["macro"])
def indicators(country: str = Query("ECU", min_length=3, max_length=3),
               indicator: str | None = None,
               start: int = Query(2000, ge=2000), end: int = Query(2100, le=2100)):
    """Serie anual de indicadores del Banco Mundial para un país (formato largo)."""
    df = read_view("vw_regional_compare")
    df = df[(df["iso3"] == country.upper()) & df["year"].between(start, end)]
    if indicator:
        df = df[df["indicator_code"] == indicator]
    if df.empty:
        raise HTTPException(404, "Sin datos para esos filtros")
    return records(df.sort_values(["indicator_code", "year"]))


@app.get("/trade/basket", tags=["trade"])
def trade_basket(country: str = Query("ECU", min_length=3, max_length=3), year: int | None = None):
    """Canasta exportadora (valor y participación por grupo de producto)."""
    df = read_view("vw_export_basket")
    df = df[df["iso3"] == country.upper()]
    if year is not None:
        df = df[df["year"] == year]
    if df.empty:
        raise HTTPException(404, "Sin datos para esos filtros")
    return records(df.sort_values(["year", "rank_in_year"]))


@app.get("/diversification", tags=["trade"])
def diversification(countries: str | None = Query(None, description="ISO3 separados por coma, p. ej. ECU,PER")):
    """HHI por producto y por destino, con su número equivalente."""
    df = read_view("vw_diversification")
    df = df[df["iso3"].isin(countries_param(countries, ["ECU", "PER", "COL", "CHL"]))]
    return records(df.sort_values(["iso3", "year"]))


@app.get("/compare", tags=["macro"])
def compare(indicator: str = "NE.EXP.GNFS.ZS", countries: str | None = None, year: int | None = None):
    """Compara un indicador entre países (por defecto, último año común)."""
    df = read_view("vw_regional_compare")
    df = df[(df["indicator_code"] == indicator) & df["iso3"].isin(countries_param(countries, ["ECU", "PER", "COL", "CHL", "LCN"]))]
    if df.empty:
        raise HTTPException(404, "Indicador sin datos")
    if year is None:
        n = df.groupby("year")["iso3"].nunique()
        year = int(n[n == n.max()].index.max())
    return {"indicator": indicator, "year": year, "values": records(df[df["year"] == year].sort_values("value", ascending=False))}


@app.get("/oil-sensitivity", tags=["oil"])
def oil_sensitivity():
    """Elasticidad log-log de exportaciones (petroleras y totales) al Brent, con R²."""
    return records(read_view("vw_oil_sensitivity"))


@app.get("/pipeline/last-run", tags=["meta"])
def last_run():
    """Última ejecución del pipeline (estado, duración y filas por capa)."""
    df = read_view("vw_pipeline_runs")
    if df.empty:
        raise HTTPException(404, "El pipeline aún no se ha ejecutado")
    return records(df.sort_values("run_id").tail(1))[0]
