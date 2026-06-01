@echo off
setlocal

echo === DC RADAR - EXTERNAL SOURCES PROBE ===

set PYTHON=.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    echo ERRORE: virtualenv non trovata in .venv\Scripts\python.exe
    exit /b 1
)

"%PYTHON%" -m app.external_sources.external_facts_review_export
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.regional_environmental_probe
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.regional_environmental_curator
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.draft_external_enriched_report
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.datacentermap_probe
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.datacentermap_curator
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.datacentermap_new_candidates_export
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.datacentermap_validation_queue
if errorlevel 1 exit /b 1

"%PYTHON%" -m app.external_sources.datacentermap_validation_summary
if errorlevel 1 exit /b 1

echo External sources probe completato
pause
