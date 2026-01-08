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

### 1. Wayback Machine Advisory Scraper: `wayback_advisory_scraper.py` ⭐ **NEW**

Scrape weather advisory PDFs from archived PAGASA pages using the Wayback Machine API.

**Basic Usage:**
```bash
# Get PDFs from latest snapshot
python wayback_advisory_scraper.py

# Get PDFs from all available snapshots
python wayback_advisory_scraper.py --all

# Get PDFs from latest 10 snapshots
python wayback_advisory_scraper.py --all --limit 10

# Get PDFs from all 2024 snapshots
python wayback_advisory_scraper.py --all --year 2024
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `--all` | flag | Process all available snapshots (not just latest) |
| `--limit` | integer | Maximum number of snapshots to process |
| `--year` | integer | Filter snapshots by year (e.g., 2024) |

**Features:**
- ✓ Uses Wayback Machine public API to find archived snapshots
- ✓ Headless HTML parsing with BeautifulSoup
- ✓ Targets elements with class "col-md-12 article-content weather-advisory"
- ✓ Automatically extracts and downloads PDFs
- ✓ Saves PDFs to `dataset/pdfs_advisory/` with timestamp prefixes
- ✓ Handles Wayback Machine URL unwrapping
- ✓ Comprehensive error handling and progress logging
- ✓ Avoids duplicate downloads
- ✓ Rate limiting to be respectful to servers

**Target URL:**
```
https://www.pagasa.dost.gov.ph/weather/weather-advisory
```

**Output Location:**
```
dataset/pdfs_advisory/
```

**How It Works:**
1. Queries Wayback Machine API for snapshots of the target URL
2. Fetches HTML content from archived snapshots
3. Parses HTML to find weather advisory elements
4. Extracts PDF links from those elements
5. Downloads PDFs with timestamp prefixes for easy tracking

---

### 2. Web Scraper: `scrape_bulletin.py`

Extract PDF links from PAGASA Severe Weather Bulletin page (organized by typhoon).

**Basic Usage:**
```powershell
# Use default HTML file (bin/PAGASA.html)
python scrape_bulletin.py

# Specific HTML file
python scrape_bulletin.py "path/to/pagasa.html"

# From URL (when live)
python scrape_bulletin.py "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `<source>` | string | HTML file path or URL (optional, defaults to bin/PAGASA.html) |

**Examples:**
```powershell
# Default usage (uses bin/PAGASA.html)
python scrape_bulletin.py

# Custom HTML file
python scrape_bulletin.py "wayback_snapshot.html"
```

**Features:**
- ✓ Extracts PDF links from bulletin archive sections
- ✓ Supports multiple typhoons (returns 2D array)
- ✓ Handles wayback machine URLs automatically
- ✓ Outputs both human-readable and JSON formats
- ✓ Distinguishes between different typhoon tabs
- ✓ **Robust HTML parsing with multiple fallback strategies**
- ✓ **Works with different HTML formats and page structures**
- ✓ **Automatically adapts to tab-based or simple layouts**

**Parsing Strategies:**
The scraper uses multiple strategies to ensure compatibility with different HTML formats:
1. **Tab-based navigation** (newer format with multiple typhoons)
2. **Direct archive section search** (older format or single typhoon)
3. **Pattern matching** (fallback for scattered bulletin PDFs)

**Output Format:**
Returns a 2D array where each sub-array contains PDF links for one typhoon:
```json
[
  ["typhoon1_bulletin1.pdf", "typhoon1_bulletin2.pdf"],
  ["typhoon2_bulletin1.pdf", "typhoon2_bulletin2.pdf"]
]
```

---

### 3. Main Pipeline: `main.py` ⭐

**Combines web scraping and PDF analysis in a single automated workflow.**

This script integrates the web scraper with PDF analysis to:
1. Extract typhoon names and PDF links from PAGASA bulletin page
2. Automatically select the latest bulletin for each typhoon
3. Analyze the latest PDF and output results as JSON

**By default, outputs raw JSON to stdout** (ideal for piping, automation, and scripting).
Use `--verbose` flag to see progress messages (sent to stderr).

**Basic Usage:**
```bash
# Use default HTML file (bin/PAGASA.html) - outputs JSON
python main.py

# Specific HTML file - outputs JSON
python main.py "path/to/pagasa.html"

# Show progress messages while outputting JSON
python main.py --verbose

# Save JSON to file
python main.py > output.json

# Parse with jq
python main.py | jq '.data.typhoon_windspeed'
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `<source>` | string | HTML file path or URL (optional, defaults to bin/PAGASA.html) |
| `--verbose` | flag | Show progress messages (sent to stderr, not stdout) |
| `--metrics` | flag | Show CPU, memory, and execution time metrics (to stderr) |
| `--low-cpu` | flag | Limit CPU usage to ~30% during PDF processing |
| `--help` | flag | Show help message |

**Examples:**
```bash
# Pure JSON output (no noise)
python main.py

# JSON with progress tracking
python main.py --verbose

# Save JSON to file (silent)
python main.py > typhoon_data.json

# JSON only, suppress any stderr messages
python main.py 2>/dev/null

# Verbose with metrics
python main.py --verbose --metrics

# Parse specific field with jq
python main.py | jq '.data.typhoon_location_text'

# Use in scripts
WIND_SPEED=$(python main.py | jq -r '.data.typhoon_windspeed')
echo "Current wind speed: $WIND_SPEED"
```

**Features:**
- ✓ **Raw JSON output by default** - no noise, easy to parse
- ✓ **Automatic typhoon name detection** from HTML tabs
- ✓ **Latest bulletin selection** (most recent PDF)
- ✓ **Integrated PDF analysis** with signal and rainfall warnings
- ✓ **Remote PDF download** (with automatic cleanup)
- ✓ **Optional progress tracking** with --verbose flag
- ✓ **Pipe-friendly design** (JSON to stdout, logs to stderr)

**Workflow:**
```
1. Scrape PAGASA bulletin page → Extract typhoon names & PDF links
2. Select latest bulletin → Get most recent PDF URL
3. Analyze PDF → Download (if URL), extract data, cleanup automatically
4. Output JSON → Pure data to stdout
```

**JSON Output Format:**
```json
{
  "typhoon_name": "Typhoon \"Henry\"",
  "pdf_url": "https://pubfiles.pagasa.dost.gov.ph/.../TCB#10_henry.pdf",
  "data": {
    "updated_datetime": "2024-09-04 05:00:00",
    "typhoon_location_text": "18.5°N, 126.3°E",
    "typhoon_windspeed": "150 km/h",
    "typhoon_movement": "West Northwest at 20 km/h",
    "signal_warning_tags1": {...},
    "signal_warning_tags2": {...},
    "rainfall_warning_tags1": {...},
    ...
  }
}
```

**Verbose Output (--verbose flag):**
```
[STEP 1] Scraping PAGASA bulletin page...
Found 1 typhoon(s):
  - Typhoon "Henry": 10 bulletin(s)

[STEP 2] Selecting latest bulletin...
  Typhoon: Typhoon "Henry"
  Latest bulletin: https://pubfiles.pagasa.dost.gov.ph/.../TCB#10_henry.pdf

[STEP 3] Analyzing PDF...
  Downloading PDF from: https://...
  Saved to temporary file: /tmp/...
  Cleaned up temporary file: /tmp/...

(JSON output to stdout)

[SUCCESS] Analysis completed in 12.34s
```

**Use Cases:**
- **Monitoring latest typhoon updates**: Quickly get current bulletin analysis
- **Automated alerts**: Integrate with notification systems
- **Data collection**: Export JSON for storage or further processing
- **Research**: Track typhoon progression over time

---

### 4. Analyze Single PDF: `analyze_pdf.py`

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

### 5. Batch Process All PDFs: `typhoon_extraction.py`

Extract data from all PDFs in the dataset directory.

**Basic Usage:**
```powershell
python typhoon_extraction.py
```

**Arguments:**

| Argument | Type | Description | Default |
|----------|------|-------------|---------|
| `<directory>` | string | Path to directory with PDFs | `dataset/pdfs` |
| `--output` | string | JSON file to save results | `bin/extracted_typhoon_data.json` |

**Examples:**
```powershell
# Process all PDFs in dataset/pdfs/ (default)
python typhoon_extraction.py

# Process custom directory
python typhoon_extraction.py "path/to/pdfs"

# Specify output file
python typhoon_extraction.py "dataset/pdfs" --output "results.json"
```

**Output:**
- Generates JSON file with extracted data from all PDFs
- Each entry includes: source file, location, movement, wind speed, datetime, and all warning tags
- Summary: total extracted bulletins, success count

---

### 6. Test Extraction Accuracy: `test_accuracy.py`

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

### 7. PDF Annotation GUI: `pdf_annotation_gui.py`

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

See [docs/PDF_ANNOTATION_GUI_README.md](docs/PDF_ANNOTATION_GUI_README.md) for detailed user guide and features.
See [docs/GUI_VISUAL_DOCUMENTATION_2025.md](docs/GUI_VISUAL_DOCUMENTATION_2025.md) for complete visual reference with diagrams.

---

## Documentation

The project includes comprehensive documentation:

| Document | Purpose |
|----------|---------|
| [docs/PDF_ANNOTATION_GUI_README.md](docs/PDF_ANNOTATION_GUI_README.md) | User guide for the PDF annotation GUI tool |
| [docs/PDF_ANNOTATION_IMPLEMENTATION.md](docs/PDF_ANNOTATION_IMPLEMENTATION.md) | Technical architecture and code metrics for developers |
| [docs/PDF_ANNOTATION_QUICKREF.md](docs/PDF_ANNOTATION_QUICKREF.md) | Quick reference cheat sheet for GUI controls |
| [docs/GUI_VISUAL_DOCUMENTATION_2025.md](docs/GUI_VISUAL_DOCUMENTATION_2025.md) | Comprehensive visual reference with UI diagrams, colors, layouts, and workflows |
| [docs/PDF_STRUCTURE_ANALYSIS.md](docs/PDF_STRUCTURE_ANALYSIS.md) | Technical analysis of PDF bulletin structure |

---

## Project Structure

```
dataset/
├── pdfs/                    # Source PDF bulletins
│   └── pagasa-YY-TC##/
│       └── PAGASA_YY-TC##_Name_TCTYPE#NUM.pdf
├── pdfs_advisory/           # Weather advisory PDFs from Wayback Machine
│   └── YYYYMMDDHHMMSS_advisory_name.pdf
├── pdfs_annotation/         # Ground truth annotations
│   └── pagasa-YY-TC##/
│       └── PAGASA_YY-TC##_Name_TCTYPE#NUM.json
└── psgc_csv/               # Philippine administrative divisions

bin/
├── consolidated_locations.csv       # 43,761 location mappings
├── extracted_typhoon_data.json      # Batch extraction output
└── PAGASA.html                      # Sample HTML from wayback machine

wayback_advisory_scraper.py          # Wayback Machine advisory scraper
scrape_bulletin.py                   # Web scraper for bulletin page
typhoon_extraction.py                # Main extraction engine
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
- `beautifulsoup4` - HTML parsing for web scraper
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

Comprehensive documentation is available in the `docs/` folder:
- **[GUI_VISUAL_DOCUMENTATION_2025.md](docs/GUI_VISUAL_DOCUMENTATION_2025.md)** - Complete visual reference with interface layouts, color schemes, button specifications, state machines, and workflows
- **[PDF_ANNOTATION_IMPLEMENTATION.md](docs/PDF_ANNOTATION_IMPLEMENTATION.md)** - Technical implementation details, code architecture, and metrics
- **[PDF_STRUCTURE_ANALYSIS.md](docs/PDF_STRUCTURE_ANALYSIS.md)** - Detailed analysis of PAGASA bulletin PDF structure
