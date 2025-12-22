#!/bin/bash
# Quick Start Guide for PDF Annotation GUI
# Run this script to check prerequisites and launch the GUI

echo "================================================"
echo "  PDF Annotation GUI - Quick Start Checker"
echo "================================================"
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

required_version="3.8.10"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "   ✓ Python version is compatible"
else
    echo "   ✗ Python 3.8.10+ required"
    exit 1
fi
echo ""

# Check if dataset directory exists
echo "[2/5] Checking directory structure..."
if [ -d "dataset/pdfs" ]; then
    pdf_count=$(find dataset/pdfs -name "*.pdf" -type f | wc -l)
    echo "   ✓ dataset/pdfs/ exists"
    echo "   Found $pdf_count PDF file(s)"
    if [ $pdf_count -eq 0 ]; then
        echo "   ⚠ Warning: No PDFs found. Add PDFs to dataset/pdfs/ first."
    fi
else
    echo "   ⚠ Warning: dataset/pdfs/ not found. Creating..."
    mkdir -p dataset/pdfs
    echo "   ✓ Created dataset/pdfs/"
    echo "   Add your PDF files to this directory"
fi
echo ""

# Check required files
echo "[3/5] Checking required files..."
files_ok=true

if [ -f "pdf_annotation_gui.py" ]; then
    echo "   ✓ pdf_annotation_gui.py found"
else
    echo "   ✗ pdf_annotation_gui.py not found"
    files_ok=false
fi

if [ -f "typhoon_extraction_ml.py" ]; then
    echo "   ✓ typhoon_extraction_ml.py found"
else
    echo "   ✗ typhoon_extraction_ml.py not found"
    files_ok=false
fi

if [ -f "bin/consolidated_locations.csv" ]; then
    echo "   ✓ bin/consolidated_locations.csv found"
else
    echo "   ⚠ Warning: bin/consolidated_locations.csv not found"
    echo "     Extraction may not work properly"
fi

if [ "$files_ok" = false ]; then
    echo ""
    echo "   ✗ Required files missing. Cannot continue."
    exit 1
fi
echo ""

# Check dependencies
echo "[4/5] Checking Python dependencies..."
deps_ok=true

# Check each dependency
for dep in pdfplumber pandas pillow pypdfium2 torch transformers; do
    if python -c "import $dep" 2>/dev/null; then
        echo "   ✓ $dep installed"
    else
        echo "   ✗ $dep not installed"
        deps_ok=false
    fi
done

# Check tkinter (special case)
if python -c "import tkinter" 2>/dev/null; then
    echo "   ✓ tkinter available"
else
    echo "   ✗ tkinter not available"
    echo "     On Ubuntu/Debian: sudo apt-get install python3-tk"
    deps_ok=false
fi

if [ "$deps_ok" = false ]; then
    echo ""
    echo "   Install dependencies with: pip install -r requirements.txt"
    echo ""
    read -p "   Install now? (y/n): " install_choice
    if [ "$install_choice" = "y" ] || [ "$install_choice" = "Y" ]; then
        echo "   Installing dependencies..."
        pip install -r requirements.txt
        echo ""
        echo "   ✓ Dependencies installed"
    else
        echo "   Skipping installation. Run 'pip install -r requirements.txt' manually."
        exit 1
    fi
fi
echo ""

# Final check
echo "[5/5] Final verification..."
if python -c "from typhoon_extraction_ml import TyphoonBulletinExtractor" 2>/dev/null; then
    echo "   ✓ Extraction module imports successfully"
else
    echo "   ✗ Cannot import TyphoonBulletinExtractor"
    echo "     Check that all dependencies are installed"
    exit 1
fi
echo ""

# All checks passed
echo "================================================"
echo "  ✓ All checks passed!"
echo "================================================"
echo ""
echo "Starting PDF Annotation GUI..."
echo ""

# Launch the GUI
python pdf_annotation_gui.py

# Exit with the GUI's exit code
exit $?
