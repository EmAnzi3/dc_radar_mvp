@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 3 REPORT ===

python -m app.build_excel_report
python -m app.build_site

echo Stage 3 report completato
pause
