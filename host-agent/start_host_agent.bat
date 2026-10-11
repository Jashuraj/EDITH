@echo off
REM EDITH host agent launcher (first run: start_host_agent.bat --gateway http://127.0.0.1:3000 --code 123456)
cd /d "%~dp0"
where python >nul 2>nul || (echo Python 3.9+ is required: https://www.python.org/downloads/ & pause & exit /b 1)
python -c "import PIL" 2>nul || python -m pip install --user -r requirements.txt
python edith_host_agent.py %*
pause
