"""Validaciones contra SQL Server real. Se saltan si no hay conexión (p. ej. en CI)."""
import pytest

from src import validate


@pytest.fixture(scope="module")
def engine():
    try:
        from src import db
        eng = db.get_engine()
        with eng.connect() as c:
            c.exec_driver_sql("SELECT 1 FROM silver.etl_runs WHERE 1 = 0")
        return eng
    except Exception as err:  # sin driver, sin servidor o base sin crear
        pytest.skip(f"SQL Server no disponible: {err.__class__.__name__}")


@pytest.mark.parametrize("name,sql,critical", validate.CHECKS, ids=[c[0][:40] for c in validate.CHECKS])
def test_validaciones(engine, name, sql, critical):
    from src import db
    violations = int(db.scalar(engine, sql) or 0)
    if critical:
        assert violations == 0, f"{name}: {violations}"


def test_cobertura_ecuador(engine):
    cov = validate.coverage(engine)
    ecu = cov[(cov["iso3"] == "ECU")]
    assert (ecu["first_year"] <= 2001).all(), "Faltan los primeros años de la serie"


def test_reconciliacion_python_sql(engine):
    rec = validate.reconciliation_python_vs_sql(engine)
    assert rec["abs_diff"].max() < 0.01
