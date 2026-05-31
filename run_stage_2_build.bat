@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 2 BUILD ===

python -m app.project_extractor
python -m app.project_fact_extractor
python -m app.mase_entity_extractor
python -m app.mercury_fact_extractor
python -m app.international_developer_watchlist
python -m app.international_rankings
python -m app.developer_master
python -m app.ida_intelligence
python -m app.manual_leads
python -m app.ecosystem_graph
python -m app.italy_project_summary
python -m app.italy_rankings
python -m app.developer_enrichment_queries
python -m app.local_authority_intelligence
python -m app.mase_discovery_queries
python -m app.mase_gap_analysis
python -m app.mase_project_matcher
python -m app.local_authority_backlog
python -m app.intelligence_backlog

echo Estrazione facts strutturati da PDF MASE...
python -m app.mase_project_facts_extractor
if errorlevel 1 exit /b 1

echo Consolidamento facts MASE...
python -m app.mase_project_facts_summary
if errorlevel 1 exit /b 1

echo Generazione facts dashboard MASE...
python -m app.mase_project_facts_dashboard
if errorlevel 1 exit /b 1
echo Stage 2 build completato
pause
