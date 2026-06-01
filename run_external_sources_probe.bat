@echo off
setlocal

echo === DC RADAR - EXTERNAL SOURCES PROBE ===

set PYTHON=.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    echo ERRORE: virtualenv non trovata in .venv\Scripts\python.exe
    exit /b 1
)

echo.
echo [1/13] External facts review export
"%PYTHON%" -m app.external_sources.external_facts_review_export
if errorlevel 1 exit /b 1

echo.
echo [2/13] Regional environmental probe
"%PYTHON%" -m app.external_sources.regional_environmental_probe
if errorlevel 1 exit /b 1

echo.
echo [3/13] Regional environmental curator
"%PYTHON%" -m app.external_sources.regional_environmental_curator
if errorlevel 1 exit /b 1

echo.
echo [4/13] Draft external enriched report
"%PYTHON%" -m app.external_sources.draft_external_enriched_report
if errorlevel 1 exit /b 1

echo.
echo [5/13] DataCenterMap probe
"%PYTHON%" -m app.external_sources.datacentermap_probe
if errorlevel 1 exit /b 1

echo.
echo [6/13] DataCenterMap curator
"%PYTHON%" -m app.external_sources.datacentermap_curator
if errorlevel 1 exit /b 1

echo.
echo [7/13] DataCenterMap new candidates export
"%PYTHON%" -m app.external_sources.datacentermap_new_candidates_export
if errorlevel 1 exit /b 1

echo.
echo [8/13] DataCenterMap validation queue
"%PYTHON%" -m app.external_sources.datacentermap_validation_queue
if errorlevel 1 exit /b 1

echo.
echo [9/13] DataCenterMap validation summary
"%PYTHON%" -m app.external_sources.datacentermap_validation_summary
if errorlevel 1 exit /b 1

echo.
echo [10/13] DataCenterMap candidate review draft
"%PYTHON%" -m app.external_sources.datacentermap_promotion_draft
if errorlevel 1 exit /b 1

echo.
echo [11/13] External candidates site page
"%PYTHON%" -m app.external_sources.external_candidates_site
if errorlevel 1 exit /b 1

echo.
echo [12/13] External candidates project pages
"%PYTHON%" -m app.external_sources.external_candidates_project_pages
if errorlevel 1 exit /b 1

echo.
echo [13/13] Promote external candidates to homepage
"%PYTHON%" -m app.external_sources.promote_external_candidates_to_homepage
if errorlevel 1 exit /b 1

echo.
echo External sources probe completato
pause
