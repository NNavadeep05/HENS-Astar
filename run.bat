@echo off
:: run.bat — One-click launcher for the HENS A* Search project
:: Installs dependencies and runs main.py

echo.
echo ======================================================
echo   HENS A* Search — Classical AI Project
echo ======================================================
echo.

:: Try to find Python
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto :run
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python3
    goto :run
)
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto :run
)

echo  ERROR: Python not found on PATH.
echo  Please install Python 3.9+ from https://python.org
echo  and make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:run
echo  Found Python: %PYTHON%
echo.
echo  Installing dependencies...
%PYTHON% -m pip install -r requirements.txt --quiet
echo.
echo  Running HENS A* Search...
echo.
%PYTHON% main.py
pause
