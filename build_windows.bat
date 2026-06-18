@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist "la2\Scripts\activate.bat" (
    echo [1/4] Creating virtual environment...
    python -m venv la2
)

call la2\Scripts\activate.bat

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements-build.txt

echo [3/4] Building LogAnalyzer2.exe ...
pyinstaller --noconfirm LogAnalyzer2.spec

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo [4/4] Done.
echo Output: dist\LogAnalyzer2\LogAnalyzer2.exe
echo Copy the entire dist\LogAnalyzer2 folder when distributing.

endlocal
