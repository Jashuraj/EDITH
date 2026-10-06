@echo off
title EDITH AI Assistant & Mobile Gateway
cd /d "%~dp0"
echo =====================================================================
echo  STARTING EDITH (E.D.I.T.H.) - SYSTEM & MOBILE AIRLOCK
echo =====================================================================
python -m edith.main serve
pause
