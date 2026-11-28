@echo off
REM Windows: double-click to open One Take Studio (starts it if it is not running).
cd /d "%~dp0"
set PY=.venv\Scripts\python.exe
if not exist %PY% set PY=python
%PY% -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5178/api/status', timeout=1)" >nul 2>&1
if errorlevel 1 (
  if not exist projects mkdir projects
  start "" /min %PY% -m engine open --no-browser
  timeout /t 4 /nobreak >nul
)
start "" http://localhost:5178/
