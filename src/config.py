"""Configuración central del proyecto.

Lee variables del archivo .env y define constantes de negocio (países,
indicadores, productos HS). Todo lo que pueda cambiar entre entornos vive aquí.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Rutas base del repositorio
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
LOG_DIR = ROOT_DIR / "logs"
SQL_DIR = ROOT_DIR / "sql"
APP_DATA_DIR = ROOT_DIR / "app" / "data"
DOCS_DIR = ROOT_DIR / "docs"

load_dotenv(ROOT_DIR / ".env")

# --- Conexión ---------------------------------------------------------------
SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
SQL_DATABASE = os.getenv("SQL_DATABASE", "EcuadorMonitor")
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

# --- Credenciales (nunca se imprimen en logs) -------------------------------
COMTRADE_KEY = os.getenv("COMTRADE_SUBSCRIPTION_KEY", "").strip()
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()

# --- Alcance temporal -------------------------------------------------------
START_YEAR = 2000
END_YEAR = date.today().year

# --- Países -----------------------------------------------------------------
# iso3 -> (código numérico M49 usado por Comtrade, nombre ES, nombre EN, es_agregado)
COUNTRIES = {
    "ECU": (218, "Ecuador", "Ecuador", False),
    "PER": (604, "Perú", "Peru", False),
    "COL": (170, "Colombia", "Colombia", False),
    "CHL": (152, "Chile", "Chile", False),
    "LCN": (None, "América Latina y el Caribe", "Latin America & Caribbean", True),
}
FOCUS_COUNTRY = "ECU"
COMTRADE_REPORTERS = {iso: v[0] for iso, v in COUNTRIES.items() if v[0] is not None}

# --- Indicadores del Banco Mundial -----------------------------------------
# código -> (nombre ES, nombre EN, unidad)
WB_INDICATORS = {
    "NY.GDP.MKTP.CD": ("PIB (USD corrientes)", "GDP (current US$)", "USD"),
    "NY.GDP.MKTP.KD.ZG": ("Crecimiento del PIB (% anual)", "GDP growth (annual %)", "%"),
    "NY.GDP.PCAP.CD": ("PIB per cápita (USD corrientes)", "GDP per capita (current US$)", "USD"),
    "FP.CPI.TOTL.ZG": ("Inflación, precios al consumidor (% anual)", "Inflation, consumer prices (annual %)", "%"),
    "NE.EXP.GNFS.ZS": ("Exportaciones de bienes y servicios (% del PIB)", "Exports of goods and services (% of GDP)", "%"),
    "BX.TRF.PWKR.CD.DT": ("Remesas recibidas (USD corrientes)", "Personal remittances, received (current US$)", "USD"),
    "BX.KLT.DINV.CD.WD": ("IED, entradas netas (USD corrientes)", "FDI, net inflows (BoP, current US$)", "USD"),
    "SL.UEM.TOTL.ZS": ("Desempleo (% de la fuerza laboral)", "Unemployment (% of labor force)", "%"),
    "TX.VAL.FUEL.ZS.UN": ("Combustibles (% de exportaciones de mercancías)", "Fuel exports (% of merchandise exports)", "%"),
}

# --- Productos HS clave -----------------------------------------------------
# código HS -> (grupo, nombre ES, nombre EN)
KEY_PRODUCTS = {
    "27": ("oil", "Petróleo y combustibles", "Oil & fuels"),
    "0306": ("shrimp", "Camarón y crustáceos", "Shrimp & crustaceans"),
    "0803": ("banana", "Banano", "Bananas"),
    "1801": ("cocoa", "Cacao en grano", "Cocoa beans"),
    "26": ("mining", "Minerales metalíferos", "Metal ores"),
    "0603": ("flowers", "Flores", "Cut flowers"),
    "1604": ("tuna", "Conservas de pescado (atún)", "Prepared fish (tuna)"),
}
OTHER_GROUP = ("other", "Resto de productos", "Other products")

# Hitos económicos marcados en gráficos (descripción neutral, sin cifras)
ECONOMIC_EVENTS = [
    ("2008-07-01", "2009-06-30", "global_crisis", "Crisis financiera global y caída del crudo", "Global financial crisis and oil price drop"),
    ("2014-07-01", "2016-02-29", "oil_collapse", "Caída prolongada del precio del petróleo", "Prolonged oil price collapse"),
    ("2020-03-01", "2020-12-31", "covid", "Pandemia de COVID-19 y desplome del crudo", "COVID-19 pandemic and oil price crash"),
]

# --- URLs de fuentes --------------------------------------------------------
WB_API = "https://api.worldbank.org/v2"
# El Pink Sheet cambia de carpeta cada año; se puede sobreescribir desde .env (ver ADR 0005)
PINK_SHEET_URL = os.getenv("PINK_SHEET_URL") or (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
    "related/CMO-Historical-Data-Monthly.xlsx"
)
FRED_API = "https://api.stlouisfed.org/fred/series/observations"


def get_logger(name: str) -> logging.Logger:
    """Logger con salida a consola y a logs/pipeline.log."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        fh = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger
