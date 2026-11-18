"""Conexión a SQL Server y utilidades de base de datos.

Usa autenticación de Windows (Trusted_Connection) — nunca contraseñas.
pyodbc se importa de forma diferida para que las pruebas y la app de
Streamlit funcionen en equipos sin el driver ODBC.
"""
from __future__ import annotations

import shutil
import subprocess
import urllib.parse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src import config

log = config.get_logger("db")
_ENGINE: Engine | None = None


def connection_string(database: str | None = None) -> str:
    """Cadena ODBC con Trusted_Connection y TrustServerCertificate."""
    db = database or config.SQL_DATABASE
    return (
        f"Driver={{{config.ODBC_DRIVER}}};Server={config.SQL_SERVER};Database={db};"
        "Trusted_Connection=yes;TrustServerCertificate=yes"
    )


def get_engine(database: str | None = None) -> Engine:
    """Engine de SQLAlchemy (mssql+pyodbc) con fast_executemany activado."""
    global _ENGINE
    if _ENGINE is not None and database is None:
        return _ENGINE
    params = urllib.parse.quote_plus(connection_string(database))
    engine = create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        fast_executemany=True,
        pool_pre_ping=True,
    )
    if database is None:
        _ENGINE = engine
    return engine


def run_sql_file(path: Path, database: str | None = "master") -> None:
    """Ejecuta un script .sql con sqlcmd (soporta GO y procedimientos largos)."""
    sqlcmd = shutil.which("sqlcmd")
    if not sqlcmd:
        raise RuntimeError("No se encontró sqlcmd en el PATH. Instala las SQL Server command line tools.")
    cmd = [sqlcmd, "-S", config.SQL_SERVER, "-E", "-C", "-b", "-I", "-f", "65001", "-i", str(path)]
    if database:
        cmd += ["-d", database]
    log.info("Ejecutando %s", path.name)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"Falló {path.name}:\n{res.stdout}\n{res.stderr}")


def exec_proc(engine: Engine, proc: str, **params) -> None:
    """Ejecuta un procedimiento almacenado dentro de una transacción."""
    args = ", ".join(f"@{k}=:{k}" for k in params)
    with engine.begin() as conn:
        conn.execute(text(f"EXEC {proc} {args}"), params)


def read_sql(engine: Engine, sql: str, **params) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def scalar(engine: Engine, sql: str, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def truncate_and_load(engine: Engine, df: pd.DataFrame, schema: str, table: str) -> int:
    """Carga un DataFrame en una tabla de staging (stg_*) previamente vaciada.

    Solo se usa con tablas de staging de silver; bronze es solo-append.
    """
    if not table.startswith("stg_"):
        raise ValueError("truncate_and_load solo se permite en tablas stg_*")
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {schema}.{table}"))
    return append(engine, df, schema, table)


def append(engine: Engine, df: pd.DataFrame, schema: str, table: str) -> int:
    """Inserta filas (append) usando fast_executemany."""
    if df.empty:
        return 0
    df.to_sql(table, engine, schema=schema, if_exists="append", index=False, chunksize=5000)
    return len(df)
