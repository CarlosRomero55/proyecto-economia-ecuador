@echo off
REM Ejecuta el pipeline incremental (para el Programador de tareas de Windows).
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i
call .venv\Scripts\activate.bat
python -m src.pipeline --incremental >> "logs\scheduled_%TODAY%.log" 2>&1
set RC=%ERRORLEVEL%
echo Codigo de salida: %RC% >> "logs\scheduled_%TODAY%.log"
exit /b %RC%
