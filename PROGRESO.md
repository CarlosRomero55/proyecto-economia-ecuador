# PROGRESO

Registro de avance del proyecto. Al iniciar cada sesión, continuar desde el primer pendiente.

## Estado al 2026-11-17

| Fase | Estado | Notas |
|---|---|---|
| 0 · Plan | ✅ Hecho | `docs/plan.md` (10 preguntas, KPIs con fórmula, Mermaid, recorrido de un dato) |
| 1 · Configuración | ✅ Hecho | Estructura, `requirements.txt` fijado (verificado con ruedas Windows + Python 3.14), `.gitignore`, `.env.example` |
| 2 · Base de datos | ✅ Código listo | `sql/00`–`03` idempotentes (sin DROP/DELETE). **Pendiente:** ejecutar en SQL Server local |
| 3 · Conexión | ✅ Código listo | `src/config.py`, `src/db.py` (Trusted_Connection, fast_executemany, logs) |
| 4 · Extracción | ✅ Código listo | Banco Mundial, Comtrade, Pink Sheet/FRED, BCE (manual). **Pendiente:** primera descarga real |
| 5 · Limpieza | ✅ Hecho | 18 reglas trazables (WB, CT, OIL; incluye conteos de entrada) con filas afectadas → `silver.cleaning_log` |
| 6 · Calidad | ✅ Hecho | 60 pruebas en verde; 11 pruebas de base se saltan hasta que exista SQL Server |
| 7 · Gold | ✅ Código listo | Estrella + 13 vistas (canasta, HHI, CAGR, elasticidad, reconciliación) |
| 8 · Orquestación | ✅ Código listo | `--full`/`--incremental`, `run_scheduled.bat`, `schtasks`. **Pendiente:** correr 2 veces y verificar que no se duplican filas |
| 9 · SQL de negocio | ✅ Hecho | 15 consultas en `sql/04_business_queries.sql` |
| 10 · Análisis | ✅ Código listo | 2 notebooks probados de punta a punta con datos sintéticos. **Pendiente:** ejecutarlos con datos reales |
| 11 · API | ✅ Hecho | 6 endpoints + `/health`, pruebas con TestClient |
| 12 · Snapshot | ✅ Código listo | `src/export_snapshot.py` + `metadata.json`. **Pendiente:** generar `app/data/*.parquet` reales |
| 13 · App Streamlit | ✅ Hecho | 6 páginas ES/EN, AppTest en verde, servidor local responde. **Pendiente:** publicar (Carlos) |
| 14 · Power BI | ✅ Especificación | `model.md` (no se generó TMDL a ciegas, ADR 0007), `theme.json`, `GUIA_POWERBI.md`. **Pendiente:** armar visuales (Carlos) |
| 15 · Insights | ⏳ Automático | `src/insights.py` los escribe desde la base al final del pipeline |
| 16 · Comunicación | ✅ Hecho | README, `docs/linkedin.md`, `portfolio.json` (KPIs y hallazgos se completan solos) |
| 17 · Guía de estudio | ✅ Hecho | 14 componentes × 3 preguntas + tabla comparativa |

## Decisiones (ADR)
0001 Medallion en SQL Server · 0002 3FN + estrella · 0003 incremental con watermark · 0004 formato largo ·
0005 Pink Sheet con respaldo FRED · 0006 FastAPI · 0007 PBIP / model.md · 0008 Parquet + Streamlit · 0009 BCE manual.

## Pendientes en el PC de Carlos (en orden)
1. Clonar el repo, crear `.venv` e instalar: `pip install -r requirements.txt`.
2. `copy .env.example .env` y pegar la llave de Comtrade (en el archivo, no en el chat).
3. `python -m src.pipeline --full` → luego `python -m src.pipeline --incremental` (prueba de no duplicados).
4. `pytest -q` (ahora corren también las 11 pruebas contra SQL Server).
5. `jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb notebooks/02_econometrics.ipynb`
6. ~~Subir a GitHub~~ ✅ Hecho: repo `CarlosRomero55/proyecto-economia-ecuador`, commits por componente en ramas por fase fusionadas en `main`. Para trabajar: `git clone https://github.com/CarlosRomero55/proyecto-economia-ecuador.git`.
7. Commit del snapshot real (`app/data`, `docs/insights.md`, `docs/data_quality_report.md`, `portfolio.json`).
8. Publicar en Streamlit Cloud (`docs/deploy_streamlit.md`) y reemplazar `APP_URL` en README y `portfolio.json`.
9. Registrar la tarea programada (`docs/automatizacion.md`).
10. Armar Power BI con `powerbi/GUIA_POWERBI.md` y guardarlo como `.pbip`.
