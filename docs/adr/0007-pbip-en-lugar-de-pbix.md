# ADR 0007 · PBIP en lugar de .pbix

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
El `.pbix` es binario: no se puede revisar en un pull request ni ver diferencias en Git.

## Decisión
Guardar el informe como **Power BI Project (.pbip)** con modelo TMDL dentro de `powerbi/`. Como un TMDL generado sin abrir Power BI Desktop puede quedar inválido, el repositorio entrega `powerbi/model.md` (tablas, relaciones y medidas DAX listas para copiar) y Carlos guarda el `.pbip` desde Desktop.

## Alternativas consideradas
Versionar el `.pbix` (binario, pesado); no versionar Power BI.

## Consecuencias
El modelo y las medidas quedan en texto plano y con historial. Exige Power BI Desktop reciente (formato PBIP/TMDL activado).
