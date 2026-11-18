# Automatización

## Ejecución manual
```powershell
.venv\Scripts\activate
python -m src.pipeline --full          # primera vez (2000 a la fecha; Comtrade puede tardar por la cuota)
python -m src.pipeline --incremental   # actualizaciones
```

## Prueba de idempotencia (sin duplicados)
Ejecuta el pipeline dos veces seguidas y compara:
```sql
SELECT 'indicator_values' t, COUNT(*) n FROM EcuadorMonitor.silver.indicator_values
UNION ALL SELECT 'trade_flows', COUNT(*) FROM EcuadorMonitor.silver.trade_flows
UNION ALL SELECT 'fact_trade', COUNT(*) FROM EcuadorMonitor.gold.fact_trade;
```
Los conteos de silver y gold deben ser iguales tras la segunda ejecución (bronze sí crece: guarda cada lote como historial).
La prueba `tests/test_quality_db.py` verifica además unicidad de claves.

## Tarea programada de Windows
`run_scheduled.bat` activa el entorno, corre el modo incremental y guarda el log en `logs/scheduled_AAAAMMDD.log`.

Registrar (una sola vez, en PowerShell, desde la carpeta del repo):
```powershell
schtasks /Create /TN "EcuadorMonitor\PipelineIncremental" /TR "\"$PWD\run_scheduled.bat\"" /SC WEEKLY /D MON /ST 07:30 /F
```
Verificar y probar:
```powershell
schtasks /Query /TN "EcuadorMonitor\PipelineIncremental" /V /FO LIST
schtasks /Run /TN "EcuadorMonitor\PipelineIncremental"
```
Quitarla: `schtasks /Delete /TN "EcuadorMonitor\PipelineIncremental" /F`

Semanal es suficiente: los datos son anuales (Comtrade, Banco Mundial) y mensuales (crudo).

## Refrescar la demo pública
Después de una ejecución exitosa: `git add app/data docs/insights.md docs/data_quality_report.md && git commit -m "chore(snapshot): actualiza datos" && git push`.
Streamlit Cloud redespliega solo.
