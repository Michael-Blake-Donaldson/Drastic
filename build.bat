@echo off
setlocal EnableDelayedExpansion
title DRASTIC Planner — Build

echo.
echo ============================================================
echo   DRASTIC Planner  ^|  Desktop Build Script
echo ============================================================
echo.

REM ---------------------------------------------------------------
REM 0. Verify the virtual environment exists
REM ---------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\
    echo         Run first:  python -m venv .venv
    echo                     .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM 1. Install / upgrade build dependencies inside the venv
REM ---------------------------------------------------------------
echo [1/4] Installing build dependencies ...
.venv\Scripts\pip install --quiet --upgrade pyinstaller pyinstaller-hooks-contrib pillow
if errorlevel 1 (
    echo [ERROR] pip failed.  Check your internet connection or proxy settings.
    pause
    exit /b 1
)
echo       Done.
echo.

REM ---------------------------------------------------------------
REM 2. Build the Windows icon if a PNG source exists
REM ---------------------------------------------------------------
echo [2/4] Preparing application icon ...
if exist "assets\icon-source.png" (
    .venv\Scripts\python.exe tools\make_icon.py
    if errorlevel 1 (
        echo [ERROR] Icon generation failed.
        pause
        exit /b 1
    )
    echo       Using assets\icon.ico
) else (
    echo       No assets\icon-source.png found.  Building without a custom icon.
)
echo.

REM ---------------------------------------------------------------
REM 3. Clean previous artefacts, then run PyInstaller
REM ---------------------------------------------------------------
echo [3/4] Building with PyInstaller ...
if exist "dist\DRASTIC"  rmdir /s /q "dist\DRASTIC"
if exist "build\DRASTIC" rmdir /s /q "build\DRASTIC"

.venv\Scripts\pyinstaller drastic.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed.  See output above for details.
    pause
    exit /b 1
)

echo.
echo       Executable:  dist\DRASTIC\DRASTIC.exe
echo.

REM ---------------------------------------------------------------
REM 4. Compile the Inno Setup installer (if ISCC.exe is available)
REM ---------------------------------------------------------------
echo [4/4] Creating Windows installer ...

set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"       set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "!ISCC!"=="" (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "(Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source"`) do set "ISCC=%%I"
)

if "!ISCC!"=="" (
    echo       Inno Setup not found.
    echo       Download from:  https://jrsoftware.org/isinfo.php
    echo       Then re-run this script to produce  installer\Output\DRASTIC_Planner_Setup.exe
    goto :done
)

"!ISCC!" "installer\drastic_setup.iss"
if errorlevel 1 (
    echo [WARNING] Inno Setup compilation failed.  See output above.
    goto :done
)

echo.
echo       Installer:  installer\Output\DRASTIC_Planner_Setup.exe

:done
echo.
echo ============================================================
echo   Build complete.
echo ============================================================
echo.
pause
endlocal
