@echo off
setlocal
REM 
set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto run
set "PY=%LocalAppData%\Programs\Python\Python313\python.exe"
if exist "%PY%" goto run

echo Python not found. Expected one of:
echo   %%LocalAppData%%\Programs\Python\Python312\python.exe
echo   %%LocalAppData%%\Programs\Python\Python313\python.exe
echo Install Python 3.12+ from python.org or: winget install Python.Python.3.12
echo.
echo Also turn OFF Store aliases: Settings -^> Apps -^> App execution aliases -^> python.exe / python3.exe
pause
exit /b 1

:run
cd /d "%~dp0"
"%PY%" -m pip install -r requirements.txt
"%PY%" app.py
