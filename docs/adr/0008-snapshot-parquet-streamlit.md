# ADR 0008 · Snapshot Parquet + Streamlit para la demo pública

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Los reclutadores necesitan ver el proyecto sin instalar nada, pero Streamlit Community Cloud (Linux) no alcanza el SQL Server local ni tiene driver ODBC.

## Decisión
El pipeline exporta las vistas gold que usa la app a `app/data/*.parquet` (+ `metadata.json`) y ese snapshot se versiona. La app solo depende de streamlit, pandas, pyarrow y plotly (`app/requirements.txt`). Cada archivo debe pesar < 5 MB (prueba automática).

## Alternativas consideradas
Base en la nube (Azure SQL: costo y credenciales); CSV (más pesado, sin tipos); Power BI Publish to web (no muestra el código ni el pipeline).

## Consecuencias
Demo pública gratuita y rápida. Los datos de la demo se actualizan cuando Carlos corre el pipeline y hace commit del snapshot.
