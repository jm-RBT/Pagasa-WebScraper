---
applyTo: '**/*.py'
---

# Copilot Instructions for Pagasa WebScraper

## Overview
This repository is a high-accuracy PAGASA typhoon bulletin extraction and annotation tool. It extracts signal warnings, rainfall alerts, typhoon location, movement, and wind speed from PDF bulletins with 94.2% accuracy. The codebase uses rule-based extraction (no ML dependencies) and includes web scraping, PDF parsing, and GUI annotation tools.

## Project Structure
- **`main.py`**: Main pipeline combining web scraping and PDF analysis with parallel execution.
- **`advisory_scraper.py`**: Extracts rainfall warning data from PAGASA weather advisory pages.
- **`scrape_bulletin.py`**: Web scraper for PAGASA Severe Weather Bulletin page, extracts PDF links.
- **`analyze_pdf.py`**: Analyzes individual PAGASA PDF bulletins with accurate data extraction.
- **`typhoon_extraction.py`**: Core extraction engine with TyphoonBulletinExtractor class (rule-based, no ML).
- **`pdf_annotation_gui.py`**: GUI tool for annotating PDFs with extracted JSON data.
- **`test_accuracy.py`**: Validates extraction accuracy against ground truth annotations.
- **`bin/`**: Stores consolidated location database (consolidated_locations.csv) and processed data.
- **`dataset/`**: Contains PDF bulletins, annotations, and administrative division data.
- **`docs/`**: Comprehensive documentation for the PDF annotation GUI tool.
- **`requirements.txt`**: Lists Python dependencies (no ML/OCR dependencies).

## Key Conventions
1. **Python Version**: Use Python 3.8.10+ for compatibility (tested up to Python 3.12).
2. **Extraction Logic**: Uses rule-based extraction with pdfplumber - no ML or OCR dependencies.
3. **Data Parsing**: Follow modular and reusable design patterns for parsing logic. Avoid hardcoding paths or values.
4. **File Naming**: Use descriptive and consistent names for scripts and datasets.
5. **Testing**: Validate extraction accuracy using `test_accuracy.py` against ground truth annotations in `dataset/pdfs_annotation/`.
6. **Location Matching**: All location validation uses `bin/consolidated_locations.csv` (26,808 Philippine locations).

## Developer Workflows
### Setting Up the Environment
1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Install dependencies (ensure you are using the virtual environment's pip):
   ```powershell
   .\.venv\Scripts\pip install -r requirements.txt
   ```
3. Verify the installation:
   ```powershell
   python verify_install.py
   ```

### Running Scripts
- Ensure the virtual environment is activated before running any script.
- Main pipeline (web scraping + PDF analysis):
  ```powershell
  python main.py
  ```
- Extract rainfall advisories:
  ```powershell
  python advisory_scraper.py
  ```
- Scrape bulletin page for PDF links:
  ```powershell
  python scrape_bulletin.py
  ```
- Analyze individual PDFs:
  ```powershell
  python analyze_pdf.py "path/to/pdf"
  ```
- Launch annotation GUI:
  ```powershell
  python pdf_annotation_gui.py
  ```
- Test extraction accuracy:
  ```powershell
  python test_accuracy.py
  ```

### Debugging
- Use `test_accuracy.py` with `--detailed` flag to debug extraction issues.
- Check `bin/consolidated_locations.csv` for location matching problems.
- Use `--verbose` and `--metrics` flags on main scripts for detailed execution logs.
- For GUI issues, check console output when running `pdf_annotation_gui.py`.

## Integration Points
- **External Dependencies**: Ensure all dependencies are listed in `requirements.txt`.
- **Cross-Component Communication**: Scripts share data through the `bin/` directory and `dataset/` folder. Maintain consistent formats.

## Examples
### Adding New PDF Bulletins
1. Place PDF files in the `dataset/pdfs/` folder under the appropriate typhoon ID.
2. Run `python typhoon_extraction.py` to batch process all PDFs.
3. Use `python test_accuracy.py` to validate extraction quality.

### Creating Ground Truth Annotations
1. Run `python pdf_annotation_gui.py` to launch the GUI tool.
2. Review and edit the automatically extracted JSON data.
3. Click "Save & Next" to save annotations to `dataset/pdfs_annotation/`.

### Modifying Extraction Logic
1. Edit extraction classes in `typhoon_extraction.py` (SignalWarningExtractor, RainfallWarningExtractor, etc.).
2. Run `python analyze_pdf.py --random` to test changes on sample PDFs.
3. Use `python test_accuracy.py --detailed` to verify accuracy impact.

## Behavioral Rules for AI Agents
- **DO**:
  - Follow Pythonic best practices.
  - Write clean, maintainable, and well-documented code.
  - Request explicit permission before running commands or modifying files.
- **DO NOT**:
  - Execute commands without user approval.
  - Install packages automatically.
  - Make irreversible changes without confirmation.

## Maintainer
User