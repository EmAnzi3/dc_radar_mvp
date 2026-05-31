@echo off
call .venv\Scripts\activate

echo === DC RADAR - STAGE 1 COLLECT ===

python -m app.mase_parser
python -m app.mase_document_parser
python -m app.terna_ingest
python -m app.query_generator
python -m app.local_authority_queries
set SOURCE_WATCHLIST_FILE=source_watchlist_default.csv
python -m app.contractor_site_crawler
set SOURCE_WATCHLIST_FILE=
REM python -m app.project_page_expander

echo Stage 1 collect completato
pause


