# Pagasa WebScraper

High-accuracy PAGASA typhoon bulletin PDF extraction and annotation tool. Extracts signal warnings, rainfall alerts, typhoon location, movement, and wind speed with 94.2% accuracy.

## Quick Start

### 1. Setup Virtual Environment (REQUIRED)

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Verify Installation

```powershell
python verify_install.py
```

---

## Scripts & Usage

### 1. Analyze Single PDF: `analyze_pdf.py`

Analyze individual PAGASA PDF bulletins with accurate data extraction.

**Basic Usage:**
```powershell
# Specific PDF file
python analyze_pdf.py "dataset/pdfs/pagasa-22-TC08/PAGASA_22-TC08_Henry_TCA#01.pdf"

# Random PDF from dataset
python analyze_pdf.py --random

# PDF from URL
python analyze_pdf.py "https://example.com/bulletin.pdf"
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `<path>` | string | PDF file path or URL |
| `--random` | flag | Select random PDF from dataset |
| `--metrics` | flag | Show CPU, memory, and execution time metrics |
| `--low-cpu` | flag | Limit CPU usage to ~30% (good for background processing) |
| `--json` | flag | Output raw JSON data only |

**Examples:**
```powershell
# Show performance metrics
python analyze_pdf.py --random --metrics

# Low CPU mode for background use
python analyze_pdf.py "path/to/file.pdf" --low-cpu

# Get JSON output
python analyze_pdf.py --random --json

# Combine flags
python analyze_pdf.py --random --low-cpu --metrics
```

**Features:**
- ✓ Extracts TCWS signal warnings (1-5) by island group (Luzon, Visayas, Mindanao)
- ✓ Extracts rainfall warnings (3 levels) with affected locations
- ✓ Extracts datetime issued, wind speed, and movement
- ✓ Automatic PDF safety checks
- ✓ Optional performance metrics (CPU, memory, time)
- ✓ Support for local files and remote URLs

**Performance (typical):**
- Execution time: 5-7 seconds per PDF
- CPU usage: 97% (normal) or ~30% (low-CPU mode)
- Memory: 90-110 MB

---

### 2. Batch Process All PDFs: `typhoon_extraction_ml.py`

Extract data from all PDFs in the dataset directory.

**Basic Usage:**
```powershell
python typhoon_extraction_ml.py
```

**Arguments:**

| Argument | Type | Description | Default |
|----------|------|-------------|---------|
| `<directory>` | string | Path to directory with PDFs | `dataset/pdfs` |
| `--output` | string | JSON file to save results | `bin/extracted_typhoon_data.json` |

**Examples:**
```powershell
# Process all PDFs in dataset/pdfs/ (default)
python typhoon_extraction_ml.py

# Process custom directory
python typhoon_extraction_ml.py "path/to/pdfs"

# Specify output file
python typhoon_extraction_ml.py "dataset/pdfs" --output "results.json"
```

**Output:**
- Generates JSON file with extracted data from all PDFs
- Each entry includes: source file, location, movement, wind speed, datetime, and all warning tags
- Summary: total extracted bulletins, success count

---

### 3. Test Extraction Accuracy: `test_accuracy.py`

Validate extraction accuracy by comparing against ground truth annotations.

**Basic Usage:**
```powershell
# Test all annotations
python test_accuracy.py

# Test specific bulletin
python test_accuracy.py "PAGASA_22-TC08_Henry_TCA"

# Test single annotation file
python test_accuracy.py "PAGASA_22-TC08_Henry_TCA#01"
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `<bulletin>` | string | Bulletin name or annotation file to test |
| `--detailed` | flag | Show field-by-field results |
| `--verbose` | flag | Show all test results (including passes) |
| `--metrics` | flag | Show detailed accuracy metrics |

**Examples:**
```powershell
# Detailed field results
python test_accuracy.py --detailed

# Show everything
python test_accuracy.py "PAGASA_22-TC08_Henry_TCA" --verbose

# Combined
python test_accuracy.py --detailed --metrics
```

**Features:**
- ✓ Auto-matches annotations with PDFs
- ✓ Tests all 12 fields: location, movement, wind speed, datetime, signal tags (1-5), rainfall tags (1-3)
- ✓ Accuracy thresholds: PASS (≥65%), WARN (58-65%), FAIL (<58%)
- ✓ Field-level and test-level metrics

---

### 4. PDF Annotation GUI: `pdf_annotation_gui.py`

Interactive GUI for manually annotating PDFs with extracted JSON data.

**Basic Usage:**
```powershell
python pdf_annotation_gui.py
```

**Features:**
- Split-view interface: PDF viewer (left) + JSON editor (right)
- Automatic PDF discovery from `dataset/pdfs/`
- Auto-extraction using TyphoonBulletinExtractor
- Real-time JSON validation
- Navigation: Previous, Next, Save & Next buttons
- Saves annotations to `dataset/pdfs_annotation/`

See [GUI_DOCUMENTATION.md](GUI_DOCUMENTATION.md) for detailed GUI features and architecture.

---

## Project Structure

```
dataset/
├── pdfs/                    # Source PDF bulletins
│   └── pagasa-YY-TC##/
│       └── PAGASA_YY-TC##_Name_TCTYPE#NUM.pdf
├── pdfs_annotation/         # Ground truth annotations
│   └── pagasa-YY-TC##/
│       └── PAGASA_YY-TC##_Name_TCTYPE#NUM.json
└── psgc_csv/               # Philippine administrative divisions

bin/
├── consolidated_locations.csv       # 43,761 location mappings
└── extracted_typhoon_data.json      # Batch extraction output

typhoon_extraction_ml.py             # Main extraction engine
analyze_pdf.py                       # Single PDF analysis tool
test_accuracy.py                     # Accuracy validation
pdf_annotation_gui.py                # Annotation GUI
verify_install.py                    # Installation verifier
requirements.txt                     # Python dependencies
```

---

## Extraction Accuracy

Current accuracy: **94.2%** (441/468 fields matched)

Tested on 39 typhoon bulletins across different formats:
- Henry (100% accuracy)
- Uwan TCA (91.7% accuracy)  
- Uwan TCB (83.3-91.7% accuracy)

The extraction engine handles:
- Multi-format PAGASA bulletins
- Complex signal table layouts
- Rainfall warnings with multiple affected locations
- Datetime parsing from various formats
- Wind speed extraction in different units

---

## Dependencies

All dependencies are listed in `requirements.txt`:
- `pdfplumber` - PDF text extraction
- `pandas` - Data manipulation
- `psutil` - System resource monitoring
- `requests` - URL handling
- `pypdfium2` - PDF rendering (for GUI)
- `pillow` - Image processing (for GUI)
- `tkinter` - GUI framework (standard library)

---

## Troubleshooting

**Virtual environment not activating?**
- Ensure PowerShell execution policy allows scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**PDF not extracting?**
- Check PDF structure with: `python analyze_pdf.py "path/to/pdf.pdf" --json`
- Ensure `bin/consolidated_locations.csv` exists

**GUI not starting?**
- Verify `pypdfium2` is installed: `pip install pypdfium2`
- Ensure display server is available (not in WSL1)

---

## Development

For implementation details, see:
- [GUI_DOCUMENTATION.md](GUI_DOCUMENTATION.md) - GUI architecture and features
