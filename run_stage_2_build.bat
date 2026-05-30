@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 2 BUILD ===

python -m app.project_extractor
python -m app.project_fact_extractor
python -m app.developer_master
python -m app.ida_intelligence
python -m app.manual_leads
python -m app.ecosystem_graph

echo Stage 2 build completato
pause
