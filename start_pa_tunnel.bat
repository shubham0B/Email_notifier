@echo off
title Dean Office - PA Cloud Portal Tunnel
echo =======================================================
echo 🚀 STARTING SECURE CLOUDFLARE TUNNEL FOR PA PORTAL
echo =======================================================
echo.
echo Make sure the local WhatsApp Gateway is running (port 3000)...
echo Starting tunnel to http://localhost:3000 ...
echo.
cloudflared.exe tunnel --url http://localhost:3000
pause
