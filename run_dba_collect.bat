@echo off
call .venv\Scripts\activate

echo === DC RADAR - DBA COLLECT ===

set SOURCE_WATCHLIST_FILE=source_watchlist_slow.csv
python -m app.contractor_site_crawler
python -m app.project_extractor
python -m app.project_page_expander
python -m app.project_fact_extractor
set SOURCE_WATCHLIST_FILE=

echo DBA collect completato
pause
