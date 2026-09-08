@echo off
setlocal
cd /d "%~dp0"
echo ============================================================
echo Executing Dean Email Automation and WhatsApp Digest
echo ============================================================
python -X utf8 main.py --live --today --gateway
echo.
echo Process completed at %date% %time%
