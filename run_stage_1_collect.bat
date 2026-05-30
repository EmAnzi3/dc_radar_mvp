@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 1 COLLECT ===

python -m app.mase_parser
python -m app.mase_document_parser
python -m app.terna_ingest
python -m app.query_generator
python -m app.local_authority_queries
python -m app.contractor_site_crawler
python -m app.project_page_expander

echo Stage 1 collect completato
pause
