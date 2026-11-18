# ADR 0001 · Arquitectura Medallion en SQL Server

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Necesitamos separar datos crudos, limpios y listos para negocio, con trazabilidad, en una herramienta que pidan los empleadores en Ecuador (banca, consultoras y sector público usan mayoritariamente SQL Server/Power BI).

## Decisión
Una base `EcuadorMonitor` con esquemas `bronze` (crudo, solo-append, con `source_name`, `extracted_at`, `batch_id`), `silver` (3FN, limpio, MERGE) y `gold` (estrella + vistas de KPIs). Scripts versionados en `sql/` y ejecutados con `sqlcmd` desde el pipeline.

## Alternativas consideradas
Base única sin capas (más simple pero sin linaje ni reproceso); Lakehouse en Fabric/Databricks (moderno pero con costo y fuera del alcance local); PostgreSQL (válido, menos demandado en el mercado objetivo).

## Consecuencias
Se puede reprocesar silver/gold desde bronze sin volver a llamar a las APIs; la auditoría es directa. Costo: más objetos que mantener. La migración a Lakehouse es directa porque las capas ya existen (ver Guía de estudio).
