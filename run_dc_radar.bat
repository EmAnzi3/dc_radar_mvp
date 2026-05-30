@echo off
call .venv\Scripts\activate
python -m app.run_pipeline
python -m app.build_excel_report
pause
