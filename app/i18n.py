"""Textos de la app en español e inglés."""
from __future__ import annotations

TEXTS = {
    "app_title": {"es": "Ecuador Trade & Economy Monitor", "en": "Ecuador Trade & Economy Monitor"},
    "language": {"es": "Idioma", "en": "Language"},
    "hook": {
        "es": "En los últimos 20 años, ¿Ecuador diversificó de verdad su canasta exportadora o solo cambió el petróleo por el camarón? ¿Cómo se compara con Perú, Colombia y Chile?",
        "en": "Over the last 20 years, did Ecuador truly diversify its export basket, or did it just swap oil for shrimp? How does it compare with Peru, Colombia and Chile?",
    },
    "no_data": {
        "es": "Todavía no hay datos en app/data/. Ejecuta `python -m src.pipeline --full` y haz commit del snapshot.",
        "en": "No data yet in app/data/. Run `python -m src.pipeline --full` and commit the snapshot.",
    },
    "updated": {"es": "Datos actualizados", "en": "Data updated"},
    "sources": {"es": "Fuentes", "en": "Sources"},
    # Páginas
    "p_summary": {"es": "Resumen", "en": "Summary"},
    "p_basket": {"es": "Canasta exportadora", "en": "Export basket"},
    "p_oil": {"es": "Dependencia del petróleo", "en": "Oil dependence"},
    "p_region": {"es": "Ecuador vs la región", "en": "Ecuador vs the region"},
    "p_forecast": {"es": "Proyección y metodología", "en": "Forecast & methodology"},
    "p_quality": {"es": "Calidad y pipeline", "en": "Quality & pipeline"},
    # KPIs
    "k_exports": {"es": "Exportaciones totales", "en": "Total exports"},
    "k_oil_share": {"es": "Peso del petróleo", "en": "Oil share"},
    "k_hhi": {"es": "HHI por producto", "en": "Product HHI"},
    "k_equiv": {"es": "Productos equivalentes", "en": "Equivalent products"},
    "k_beta": {"es": "Elasticidad al Brent", "en": "Brent elasticity"},
    "k_vs": {"es": "vs", "en": "vs"},
    "main_finding": {"es": "Hallazgo principal", "en": "Main finding"},
    "all_findings": {"es": "Los seis hallazgos", "en": "All six findings"},
    "f_data": {"es": "Dato", "en": "Data"},
    "f_interp": {"es": "Interpretación", "en": "Interpretation"},
    "f_impl": {"es": "Implicación", "en": "Implication"},
    # Canasta
    "country": {"es": "País", "en": "Country"},
    "year": {"es": "Año", "en": "Year"},
    "basket_title": {"es": "Composición de las exportaciones (USD corrientes)", "en": "Export composition (current USD)"},
    "basket_share_toggle": {"es": "Ver como % del total", "en": "Show as % of total"},
    "ranking_title": {"es": "Ranking de productos en", "en": "Product ranking in"},
    "product": {"es": "Producto", "en": "Product"},
    "value_usd": {"es": "Valor (USD)", "en": "Value (USD)"},
    "share": {"es": "Participación", "en": "Share"},
    # Petróleo
    "oil_exports": {"es": "Exportaciones petroleras (USD mil millones)", "en": "Oil exports (USD bn)"},
    "brent": {"es": "Brent promedio anual (USD/bbl)", "en": "Brent annual average (USD/bbl)"},
    "oil_chart_title": {"es": "Las exportaciones petroleras siguen al Brent", "en": "Oil exports track Brent"},
    "oil_share_title": {"es": "Peso del petróleo en las exportaciones", "en": "Oil's share of exports"},
    "monthly_brent": {"es": "Brent y WTI mensual (USD/bbl)", "en": "Monthly Brent and WTI (USD/bbl)"},
    # Región
    "indicator": {"es": "Indicador", "en": "Indicator"},
    "countries": {"es": "Países", "en": "Countries"},
    "region_index_title": {"es": "Exportaciones no petroleras, índice 2000 = 100", "en": "Non-oil exports, index 2000 = 100"},
    "hhi_title": {"es": "Concentración por producto (HHI, menor = más diversificado)", "en": "Product concentration (HHI, lower = more diversified)"},
    "interpolated_note": {"es": "Los puntos huecos son valores interpolados (huecos de 1 año).", "en": "Hollow markers are interpolated values (1-year gaps)."},
    # Proyección
    "forecast_title": {"es": "Proyección de exportaciones no petroleras de Ecuador", "en": "Ecuador non-oil exports forecast"},
    "forecast_horizon": {"es": "Años a proyectar", "en": "Years to forecast"},
    "forecast_band": {"es": "Intervalo de 80 %", "en": "80% interval"},
    "observed": {"es": "Observado", "en": "Observed"},
    "forecast": {"es": "Proyección", "en": "Forecast"},
    "method_md": {
        "es": """**Modelo:** tendencia log-lineal con errores ARIMA(1,0,0) sobre exportaciones no petroleras anuales (statsmodels en el notebook; aquí, versión ligera con numpy para no instalar statsmodels en la nube).

**Supuestos:** la tendencia histórica continúa; no se modelan precios, tipo de cambio de socios, clima (El Niño) ni cambios de política.

**Limitaciones:** pocos puntos anuales (~25), cifras en USD corrientes (incluyen inflación de precios), Comtrade puede revisar los últimos años. El intervalo refleja solo la variabilidad histórica.

**Correlación no es causalidad:** la elasticidad al Brent describe una asociación anual, no un efecto causal.""",
        "en": """**Model:** log-linear trend with AR(1) errors on annual non-oil exports (statsmodels in the notebook; here a light numpy version so the cloud app does not need statsmodels).

**Assumptions:** the historical trend continues; prices, partner exchange rates, weather (El Niño) and policy changes are not modeled.

**Limitations:** few annual points (~25), current USD (includes price inflation), Comtrade may revise recent years. The interval reflects only historical variability.

**Correlation is not causation:** the Brent elasticity describes an annual association, not a causal effect.""",
    },
    # Calidad
    "arch_title": {"es": "Arquitectura", "en": "Architecture"},
    "last_run": {"es": "Última ejecución del pipeline", "en": "Last pipeline run"},
    "rows_layer": {"es": "Filas por capa", "en": "Rows per layer"},
    "rules": {"es": "Reglas de limpieza del último lote", "en": "Cleaning rules in the last batch"},
    "recon": {"es": "Validación cruzada de la participación petrolera", "en": "Cross-check of oil share"},
    "status": {"es": "Estado", "en": "Status"},
    "duration": {"es": "Duración (s)", "en": "Duration (s)"},
}


def t(key: str, lang: str) -> str:
    entry = TEXTS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry["es"]
