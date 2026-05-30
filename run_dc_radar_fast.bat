@echo off
call .venv\Scripts\activate

echo === DC RADAR FAST MODE ===

python -m app.project_fact_extractor
python -m app.developer_master
python -m app.manual_leads
python -m app.build_excel_report

echo Fast pipeline completata
pause
