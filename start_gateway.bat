@echo off
setlocal
title EDITH Gateway
cd /d "%~dp0"
call npx next start -p 3000 -H 0.0.0.0
pause
