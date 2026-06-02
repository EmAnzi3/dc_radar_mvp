@echo off
setlocal

echo === DC RADAR - DATACENTER DISCOVERY PIPELINE ===

set PYTHON=.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    echo ERRORE: virtualenv non trovata in .venv\Scripts\python.exe
    exit /b 1
)

echo.
echo [1/1] Run consolidated discovery pipeline
"%PYTHON%" -m app.external_sources.datacenter_discovery_pipeline
if errorlevel 1 exit /b 1

echo.
echo Data center discovery pipeline completata
pause
