# OCR Setup Guide

This guide explains how to install OCR support for processing image-based/scanned PDFs with the advisory scraper.

## EasyOCR - Pure Python OCR

The script uses **EasyOCR** for OCR functionality - a pure Python library that requires no system installation.

**Pure Python library - no system installation needed!**

```bash
# Quick install (Python 3.8.10 compatible)
pip install -r requirements-ocr-easyocr.txt

# OR install manually:
pip install easyocr pdf2image
```

**Pros:**
- ✅ No system-level installation required
- ✅ Works without admin/sudo permissions
- ✅ Easy to install on any platform (Windows, Linux, macOS)
- ✅ Good accuracy
- ✅ Supports multiple languages

**Cons:**
- ⚠️ First run downloads model (~100MB)
- ⚠️ Uses more memory than text-based PDF extraction

**Perfect for:** Users without admin rights, Windows users, quick setup

---

## Installation Steps

### Step 1: Install Core Dependencies

First, install the core dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Install EasyOCR

```bash
# Install Python dependencies (Python 3.8.10 compatible)
pip install -r requirements-ocr-easyocr.txt

# OR install manually:
pip install easyocr pdf2image

# That's it! No system package needed.
```

### Step 3: Verify Installation

**Verify installation:**
```bash
python -c "import easyocr; print('EasyOCR: OK')"
python -c "from pdf2image import convert_from_path; print('pdf2image: OK')"
```

---

## Usage

Once installed, the advisory scraper will automatically use OCR when it detects image-based PDFs:

```bash
# Auto-detects and uses OCR if needed
python advisory_scraper.py "scanned-document.pdf"

# Force OCR mode
python advisory_scraper.py --ocr "document.pdf"
```

## Troubleshooting

### "Unable to get page count" error (Windows)
- Install poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases
- Add poppler's bin directory to your system PATH

### EasyOCR model download issues
- EasyOCR downloads models (~100MB) on first run
- Ensure you have a stable internet connection
- Models are cached in `~/.EasyOCR/` directory

### Memory issues
- EasyOCR may use significant memory for large images
- Consider reducing PDF DPI if experiencing issues
- Close other applications to free up memory

## Optional: OCR is Not Required

The advisory scraper works fine without OCR for regular text-based PDFs. OCR is only needed for:
- Scanned documents
- Image-based PDFs
- PDFs without a text layer

If you don't need OCR support, you can skip this installation and the script will work normally for text-based PDFs.
