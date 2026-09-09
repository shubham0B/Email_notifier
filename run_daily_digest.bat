@echo off
setlocal
cd /d "%~dp0"
echo ============================================================ >> digest_run.log 2>&1
echo Executing Dean Email Automation and WhatsApp Digest at %date% %time% >> digest_run.log 2>&1
echo ============================================================ >> digest_run.log 2>&1
python -X utf8 main.py --live --today --gateway >> digest_run.log 2>&1
echo Process completed at %date% %time% >> digest_run.log 2>&1
echo. >> digest_run.log 2>&1
