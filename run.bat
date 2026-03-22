@echo off
where python >nul 2>&1
if %errorlevel%==0 (set PYTHON=python & goto :run)
where python3 >nul 2>&1
if %errorlevel%==0 (set PYTHON=python3 & goto :run)
echo Python not found. Install from https://python.org
pause & exit /b 1
:run
%PYTHON% -m pip install -r requirements.txt --quiet
%PYTHON% main.py
pause
