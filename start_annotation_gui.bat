@echo off
REM Quick Start Guide for PDF Annotation GUI (Windows)
REM Double-click this file to check prerequisites and launch the GUI

echo ================================================
echo   PDF Annotation GUI - Quick Start Checker
echo ================================================
echo.

REM Check Python version
echo [1/5] Checking Python version...
python --version 2>nul
if %errorlevel% neq 0 (
    echo    X Python not found. Please install Python 3.8.10+
    pause
    exit /b 1
)
echo    OK Python found
echo.

REM Check if dataset directory exists
echo [2/5] Checking directory structure...
if exist "dataset\pdfs\" (
    echo    OK dataset\pdfs\ exists
    dir /b /s "dataset\pdfs\*.pdf" 2>nul | find /c /v "" > temp_count.txt
    set /p pdf_count=<temp_count.txt
    del temp_count.txt
    echo    Found PDF files
) else (
    echo    Warning: dataset\pdfs\ not found. Creating...
    mkdir "dataset\pdfs"
    echo    OK Created dataset\pdfs\
    echo    Add your PDF files to this directory
)
echo.

REM Check required files
echo [3/5] Checking required files...
set files_ok=1

if exist "pdf_annotation_gui.py" (
    echo    OK pdf_annotation_gui.py found
) else (
    echo    X pdf_annotation_gui.py not found
    set files_ok=0
)

if exist "typhoon_extraction_ml.py" (
    echo    OK typhoon_extraction_ml.py found
) else (
    echo    X typhoon_extraction_ml.py not found
    set files_ok=0
)

if exist "bin\consolidated_locations.csv" (
    echo    OK bin\consolidated_locations.csv found
) else (
    echo    Warning: bin\consolidated_locations.csv not found
    echo       Extraction may not work properly
)

if %files_ok%==0 (
    echo.
    echo    X Required files missing. Cannot continue.
    pause
    exit /b 1
)
echo.

REM Check dependencies
echo [4/5] Checking Python dependencies...
set deps_ok=1

python -c "import pdfplumber" 2>nul
if %errorlevel% neq 0 (
    echo    X pdfplumber not installed
    set deps_ok=0
) else (
    echo    OK pdfplumber installed
)

python -c "import pandas" 2>nul
if %errorlevel% neq 0 (
    echo    X pandas not installed
    set deps_ok=0
) else (
    echo    OK pandas installed
)

python -c "import PIL" 2>nul
if %errorlevel% neq 0 (
    echo    X pillow not installed
    set deps_ok=0
) else (
    echo    OK pillow installed
)

python -c "import pypdfium2" 2>nul
if %errorlevel% neq 0 (
    echo    X pypdfium2 not installed
    set deps_ok=0
) else (
    echo    OK pypdfium2 installed
)

python -c "import tkinter" 2>nul
if %errorlevel% neq 0 (
    echo    X tkinter not available
    echo       Make sure you installed Python with tkinter support
    set deps_ok=0
) else (
    echo    OK tkinter available
)

if %deps_ok%==0 (
    echo.
    echo    Install dependencies with: pip install -r requirements.txt
    echo.
    set /p install_choice="   Install now? (y/n): "
    if /i "%install_choice%"=="y" (
        echo    Installing dependencies...
        pip install -r requirements.txt
        echo.
        echo    OK Dependencies installed
    ) else (
        echo    Skipping installation. Run 'pip install -r requirements.txt' manually.
        pause
        exit /b 1
    )
)
echo.

REM Final check
echo [5/5] Final verification...
python -c "from typhoon_extraction_ml import TyphoonBulletinExtractor" 2>nul
if %errorlevel% neq 0 (
    echo    X Cannot import TyphoonBulletinExtractor
    echo       Check that all dependencies are installed
    pause
    exit /b 1
) else (
    echo    OK Extraction module imports successfully
)
echo.

REM All checks passed
echo ================================================
echo   OK All checks passed!
echo ================================================
echo.
echo Starting PDF Annotation GUI...
echo.

REM Launch the GUI
python pdf_annotation_gui.py

REM Exit
pause
