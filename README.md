# Ecuador Trade & Economy Monitor

[![App](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)](APP_URL)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-2022-CC2927?logo=microsoftsqlserver&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-PBIP-F2C811?logo=powerbi&logoColor=black)

> **En los últimos 20 años, ¿Ecuador diversificó de verdad su canasta exportadora o solo cambió el petróleo por el
> camarón? ¿Cómo se compara con Perú, Colombia y Chile?**

Proyecto de datos de punta a punta con fuentes **públicas y oficiales** (Banco Mundial, UN Comtrade, Pink Sheet),
de 2000 a la fecha: extracción por API, arquitectura Medallion en SQL Server, pruebas de calidad, API REST,
app pública bilingüe y dashboard de Power BI.

🔗 **App en vivo:** [APP_URL](APP_URL) · 📊 **Hallazgos:** [docs/insights.md](docs/insights.md) · 🧭 **Decisiones:** [docs/adr](docs/adr/README.md)

## El problema
Ecuador está dolarizado desde 2000: los dólares entran sobre todo por exportaciones, remesas, inversión extranjera
y deuda. El petróleo fue el principal generador de divisas y sus caídas de precio (2008–2009, 2014–2016, 2020)
golpearon la economía; luego crecieron el camarón, el banano, el cacao y la minería. El proyecto mide:

1. **Dependencia** — cuánto pesa todavía el petróleo.
2. **Diversificación** real o aparente, con el índice HHI (por producto y por destino).
3. **Vulnerabilidad** — elasticidad de las exportaciones al precio del Brent.
4. **Comparación** con Perú, Colombia, Chile y América Latina.

## Arquitectura
```mermaid
flowchart LR
    WB[Banco Mundial<br/>WDI API] --> PY
    CT[UN Comtrade<br/>API] --> PY
    PS[Pink Sheet / FRED] --> PY
    BCE[BCE<br/>CSV manual] -.-> PY
    PY[Python<br/>extract · clean · validate] --> B[(bronze<br/>crudo + linaje)]
    subgraph SQL Server · EcuadorMonitor
      B --> S[(silver<br/>3FN + MERGE)] --> G[(gold<br/>estrella + KPIs)]
    end
    G --> PBI[Power BI]
    G --> API[FastAPI]
    G --> PQ[Snapshot Parquet] --> ST[Streamlit Cloud]
```

| Capa | Contenido |
|---|---|
| bronze | Respuestas crudas de cada API, solo-append, con `source_name`, `extracted_at`, `batch_id` |
| silver | Modelo 3FN con PK/FK/CHECK; upsert con `MERGE` (idempotente); watermarks y registro de ejecuciones |
| gold | Estrella (Kimball) + vistas de KPIs: canasta, dependencia, HHI, CAGR, elasticidad, comparación regional |

## Stack
Python (pandas, requests, SQLAlchemy, pyodbc, statsmodels) · SQL Server 2022 (T-SQL, MERGE, vistas, procedimientos)
· pytest · FastAPI · Streamlit + Plotly · Power BI (PBIP, DAX) · Jupyter · Git (Conventional Commits) · Programador de tareas de Windows.

## Cómo ejecutarlo
Requisitos: Windows con SQL Server 2022 (Developer o Express), ODBC Driver 18, `sqlcmd`, Python 3.11+ y una llave
gratuita de [UN Comtrade](https://comtradeplus.un.org).

```powershell
git clone https://github.com/CarlosRomero55/proyecto-economia-ecuador.git
cd proyecto-economia-ecuador
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # completa COMTRADE_SUBSCRIPTION_KEY (y SQL_SERVER si usas SQLEXPRESS)
python -m src.pipeline --full # crea la base, extrae, limpia, valida, construye gold y exporta el snapshot
pytest -q
streamlit run app/streamlit_app.py
uvicorn api.main:app --reload  # http://127.0.0.1:8000/docs
```
Ejecutar notebooks con salidas: `jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb`.
Automatización semanal: [docs/automatizacion.md](docs/automatizacion.md).

### Refrescar la app pública
`python -m src.pipeline --incremental` → `git add app/data docs/insights.md docs/data_quality_report.md` → commit → push.
Streamlit Cloud redespliega solo ([docs/deploy_streamlit.md](docs/deploy_streamlit.md)).

## App (6 páginas, ES/EN)
Resumen (KPIs y hallazgo principal) · Canasta exportadora · Dependencia del petróleo · Ecuador vs la región ·
Proyección y metodología · Calidad y pipeline.

<!-- Capturas: agregar docs/img/*.png después de publicar la app -->

## Hallazgos
Los seis hallazgos (dato → interpretación → implicación) se generan desde la base en
[docs/insights.md](docs/insights.md) y son los mismos que muestra la app.

## Fuentes
| Fuente | Uso | Acceso |
|---|---|---|
| [Banco Mundial — World Development Indicators](https://data.worldbank.org) | PIB, crecimiento, inflación, exportaciones/PIB, remesas, IED, desempleo, combustibles/exportaciones | API v2, sin llave |
| [UN Comtrade](https://comtradeplus.un.org) | Exportaciones por capítulo HS2 y productos clave HS4, por destino | API con llave gratuita |
| [Banco Mundial — Commodity Price Data (Pink Sheet)](https://www.worldbank.org/en/research/commodity-markets) | Brent y WTI mensual | Excel mensual |
| [FRED](https://fred.stlouisfed.org) | Respaldo de Brent/WTI | API con llave gratuita |
| [Banco Central del Ecuador](https://www.bce.fin.ec) | Validación petrolera / no petrolera (opcional) | CSV manual |

La fecha de extracción de cada lote está en `silver.etl_runs` y en `app/data/metadata.json`.

## Limitaciones
- Cifras de comercio en USD corrientes (mezclan precio y volumen); las comparaciones usan participaciones, HHI e índices.
- Comtrade publica con rezago y revisa años recientes; el modo incremental vuelve a pedirlos.
- El crudo ecuatoriano cotiza con descuento frente al Brent; la elasticidad describe una asociación, no causalidad.
- Análisis descriptivo y neutral: no evalúa políticas ni gobiernos.

## Documentación
[Plan y KPIs](docs/plan.md) · [ER](docs/er_diagram.md) · [Diccionario](docs/data_dictionary.md) ·
[Metodología](docs/methodology.md) · [Calidad](docs/data_quality_report.md) · [ADRs](docs/adr/README.md) ·
[Power BI](powerbi/GUIA_POWERBI.md) · [Guía de estudio](docs/GUIA_DE_ESTUDIO.md)

---
Autor: **Carlos Romero** — Ingeniero en TI · Business Intelligence, Ciencia de Datos y Automatización · Guayaquil, Ecuador.
