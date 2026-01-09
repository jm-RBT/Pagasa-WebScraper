# OCR Setup Guide

This guide explains how to install OCR support for processing image-based/scanned PDFs with the advisory scraper.

## Quick Start

### 1. Install Python Dependencies

```bash
# Install all dependencies including OCR support
pip install -r requirements.txt
```

Or install OCR libraries separately:

```bash
pip install pytesseract pdf2image
```

### 2. Install Tesseract OCR Engine (System Package)

The Tesseract OCR engine must be installed as a system package:

#### Ubuntu/Debian/WSL
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### macOS
```bash
brew install tesseract
```

#### Windows
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer
3. Add Tesseract to your system PATH

### 3. Verify Installation

Test that OCR is working:

```bash
python -c "import pytesseract; print('pytesseract:', pytesseract.__version__)"
python -c "from pdf2image import convert_from_path; print('pdf2image: OK')"
tesseract --version
```

## Usage

Once installed, the advisory scraper will automatically use OCR when it detects image-based PDFs:

```bash
# Auto-detects and uses OCR if needed
python advisory_scraper.py "scanned-document.pdf"

# Force OCR mode
python advisory_scraper.py --ocr "document.pdf"
```

## Troubleshooting

### "tesseract is not installed" error
- Make sure you installed the **system package** (step 2 above), not just the Python library
- Verify installation: `tesseract --version`

### "Unable to get page count" error (Windows)
- Install poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
- Add poppler's bin directory to your system PATH

### "No such file or directory: 'tesseract'" error (macOS)
- Ensure tesseract is installed: `brew install tesseract`
- Check PATH: `which tesseract`

## Optional: OCR is Not Required

The advisory scraper works fine without OCR for regular text-based PDFs. OCR is only needed for:
- Scanned documents
- Image-based PDFs
- PDFs without a text layer

If you don't need OCR support, you can skip this installation and the script will work normally for text-based PDFs.
