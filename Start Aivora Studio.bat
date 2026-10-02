@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto dependencies

set "PYTHON_CMD="

where.exe py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    where.exe python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    where.exe python3 >nul 2>nul
    if not errorlevel 1 (
        python3 -c "import sys; sys.exit(0 if sys.version_info.major == 3 else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python3"
    )
)

if not defined PYTHON_CMD (
    echo Python 3 is not installed or could not be started.
    echo Install Python 3 from python.org, then run this file again.
    echo Make sure the Python launcher or Python command is available.
    pause
    exit /b 1
)

echo Creating the Aivora Studio Python environment...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto setup_failed

:dependencies
".venv\Scripts\python.exe" -c "import tkinterdnd2, PIL, mutagen, imageio_ffmpeg, PySide6" >nul 2>nul
if errorlevel 1 (
    echo Installing Aivora Studio dependencies...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto setup_failed
)

echo Starting Aivora Studio...
".venv\Scripts\python.exe" -m aivora_studio
if errorlevel 1 goto launch_failed
exit /b 0

:setup_failed
echo.
echo Setup failed. Check your Python installation and internet connection.
pause
exit /b 1

:launch_failed
echo.
echo Aivora Studio closed with an error.
pause
exit /b 1
