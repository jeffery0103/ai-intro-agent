@echo off
rem Daily report for Windows Task Scheduler. Binance daily candle closes at 08:00 Taiwan time; run after that.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist reports mkdir reports
python report.py > reports\last_run.log 2>&1
