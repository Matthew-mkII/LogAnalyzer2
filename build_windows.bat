@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "DIST_DIR=dist\LogAnalyzer2"

if not exist "la2\Scripts\activate.bat" (
    echo [1/5] Creating virtual environment...
    python -m venv la2
)

call la2\Scripts\activate.bat

echo [2/5] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements-build.txt

echo [3/5] Building LogAnalyzer2.exe ...
pyinstaller --noconfirm LogAnalyzer2.spec

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo [4/5] Copying license files for distribution...
if not exist "%DIST_DIR%" (
    echo Distribution folder not found: %DIST_DIR%
    exit /b 1
)

copy /Y LICENSE "%DIST_DIR%\" >nul
if errorlevel 1 (
    echo Failed to copy LICENSE
    exit /b 1
)

copy /Y THIRD_PARTY_NOTICES.txt "%DIST_DIR%\" >nul
if errorlevel 1 (
    echo Failed to copy THIRD_PARTY_NOTICES.txt
    exit /b 1
)

if not exist "licenses\" (
    echo licenses folder not found
    exit /b 1
)

if not exist "%DIST_DIR%\licenses\" mkdir "%DIST_DIR%\licenses"
copy /Y licenses\*.txt "%DIST_DIR%\licenses\" >nul
if errorlevel 1 (
    echo Failed to copy licenses folder
    exit /b 1
)

echo [5/5] Done.
echo Output: %DIST_DIR%\LogAnalyzer2.exe
echo License files copied to %DIST_DIR%
echo Copy the entire %DIST_DIR% folder when distributing.

endlocal
