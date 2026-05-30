@echo off

echo === DC RADAR FULL RUN ===

call run_stage_1_collect.bat
call run_stage_2_build.bat
call run_stage_3_report.bat

echo Full pipeline completata
pause
