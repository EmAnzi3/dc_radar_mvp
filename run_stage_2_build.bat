@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 2 BUILD ===

python -m app.project_extractor
python -m app.project_fact_extractor
python -m app.developer_master
python -m app.manual_leads

echo Stage 2 build completato
pause
