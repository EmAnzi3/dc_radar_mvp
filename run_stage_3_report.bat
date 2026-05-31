@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 3 REPORT ===

python -m app.build_excel_report
python -m app.build_site

echo Generazione pagina MASE Facts...
python -m app.mase_facts_report
if errorlevel 1 exit /b 1
echo Stage 3 report completato
pause
