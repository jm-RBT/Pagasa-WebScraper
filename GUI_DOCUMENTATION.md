# PDF Annotation GUI - Complete Documentation

## Overview

`pdf_annotation_gui.py` is a comprehensive graphical user interface tool for annotating PAGASA typhoon bulletin PDFs with extracted JSON data. It provides a professional split-view interface with a PDF viewer on the left and an editable JSON editor on the right, enabling seamless annotation and validation workflows.

---

## Quick Start

### Launch the GUI

```powershell
python pdf_annotation_gui.py
```

The application will:
1. Scan `dataset/pdfs/` recursively for all PDF files
2. Display the first PDF in the viewer
3. Automatically extract data using `TyphoonBulletinExtractor`
4. Show extracted JSON in the editor for review/editing
5. Allow you to navigate through all PDFs

---

## Features

### 1. Split-View Interface ✓

**Left Panel - PDF Viewer**
- High-quality PDF rendering at 144 DPI using pypdfium2
- Multi-page navigation with Previous/Next page controls
- Scrollable canvas for large documents
- Current page indicator (e.g., "Page 1 of 5")
- Handles PDFs with multiple pages seamlessly

**Right Panel - JSON Editor**
- Syntax-highlighted text editor for JSON data
- Real-time JSON validation with error highlighting
- Clear indication of valid/invalid JSON state
- Editable content before saving
- Displays extracted typhoon bulletin data in JSON format

### 2. Automatic PDF Analysis ✓

- **Recursive Scanning**: Scans `dataset/pdfs/` and all subdirectories
- **Background Processing**: Non-blocking UI during analysis
- **Progress Indicators**: Shows progress during PDF extraction
- **Error Handling**: Gracefully handles extraction failures
- **Auto-Load Existing**: Loads previously saved annotations automatically

### 3. Navigation & Control ✓

| Button | Action |
|--------|--------|
| **Previous** | Go to previous PDF without saving |
| **Next** | Go to next PDF without saving |
| **Save & Next** | Validate JSON, save annotation, then move to next PDF |
| **Quit** | Exit application with confirmation dialog |

**Progress Display**: Shows "File X of Y: filename.pdf" to track progress

### 4. Annotation Management ✓

- **Auto-Save**: Saves annotations to `dataset/pdfs_annotation/`
- **Structure Preservation**: Maintains directory hierarchy from source PDFs
- **JSON Format**: Saves as `<filename>.json`
- **Auto-Load**: Automatically loads existing annotations if present
- **Directory Creation**: Creates output directories as needed

### 5. User Experience ✓

- Responsive UI with threading for long-running operations
- Informative error messages for common issues
- "No PDFs found" warning if directory is empty
- Extraction failure notifications with error details
- JSON validation before saving with user feedback
- Confirmation dialogs for destructive operations (quit)

---

## Architecture

### System Design

```
                         MAIN APPLICATION
                         ┌─────────────────┐
                         │ PDFAnnotationApp│
                         │  (Controller)   │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         ┌──────────▼──────────┐     ┌─────────▼─────────┐
         │    PDFViewer        │     │    JSONEditor     │
         │   (Left Panel)      │     │   (Right Panel)   │
         └──────────┬──────────┘     └─────────┬─────────┘
                    │                           │
         ┌──────────▼──────────┐     ┌─────────▼─────────┐
         │   pypdfium2 PDF     │     │  ScrolledText     │
         │     Rendering       │     │   JSON Editing    │
         │   - Page navigation │     │  - Validation     │
         │   - Zoom support    │     │  - Syntax check   │
         │   - Scrolling       │     │  - Error display  │
         └─────────────────────┘     └───────────────────┘
```

### Data Flow

```
1. Scan dataset/pdfs/ recursively
         │
         ▼
2. Load PDF file
         │
         ▼
3. PDFViewer renders first page
         │
         ▼
4. Trigger TyphoonBulletinExtractor (background thread)
         │
         ▼
5. Return JSON data
         │
         ▼
6. JSONEditor displays extracted data
         │
         ▼
7. User edits JSON
         │
         ▼
8. Validate JSON on Save button
         │
         ▼
9. Save annotation to dataset/pdfs_annotation/
         │
         ▼
10. Navigate to next PDF (repeat from step 2)
```

### Component Architecture

```
PDFAnnotationApp (Main Controller)
├── PDFViewer (Left Panel)
│   ├── pypdfium2 for rendering
│   ├── Canvas for display
│   ├── Page navigation controls
│   └── Scroll handling
└── JSONEditor (Right Panel)
    ├── ScrolledText widget
    ├── JSON validation
    ├── Syntax highlighting
    └── Error messages
```

### File Structure

```
dataset/
├── pdfs/                    # Source PDFs
│   └── pagasa-YY-TC##/
│       └── PAGASA_YY-TC##_Name_TCTYPE#NUM.pdf
└── pdfs_annotation/         # Output annotations
    └── pagasa-YY-TC##/
        └── PAGASA_YY-TC##_Name_TCTYPE#NUM.json
```

---

## User Interface Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ 📄 PAGASA PDF Annotation Tool          File 1 of 10: file.pdf        │
├────────────────────────────────┬──────────────────────────────────────┤
│                                │                                      │
│  ┌──────────────────────────┐ │  {                                  │
│  │                          │ │    "updated_datetime": "2022-...",  │
│  │                          │ │    "typhoon_location": "...",       │
│  │      PDF PREVIEW         │ │    "typhoon_windspeed": "...",      │
│  │    (144 DPI Render)      │ │    "typhoon_movement": "...",       │
│  │                          │ │    "signal_warning_tags1": {        │
│  │                          │ │      "Luzon": "...",                │
│  │                          │ │      "Visayas": "...",              │
│  │                          │ │      "Mindanao": "...",             │
│  │                          │ │      "Other": "..."                 │
│  │                          │ │    },                               │
│  │                          │ │    ...                              │
│  │                          │ │  }                                  │
│  │  (Page 1 of 5)           │ │                                      │
│  │  Scrollable              │ │  ✓ Valid JSON                       │
│  │                          │ │                                      │
│  └──────────────────────────┘ │                                      │
│                                │                                      │
│  [◀ Prev Page] [Next Page ▶]  │                                      │
│                                │                                      │
├────────────────────────────────┴──────────────────────────────────────┤
│                                                                        │
│  [Previous]  [Save & Next]  [Next]                        [Quit]      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow Example

### Typical Annotation Session

1. **Start Application**
   ```powershell
   python pdf_annotation_gui.py
   ```
   - Application opens
   - PDFs are discovered from `dataset/pdfs/`
   - First PDF loads automatically

2. **Review Extracted Data**
   - PDF displays on left panel
   - Extracted JSON shows on right panel
   - Verify extracted fields are correct

3. **Edit if Needed**
   - Click in JSON editor
   - Modify any fields that need correction
   - Editor shows validation status in real-time

4. **Save and Continue**
   - Click "Save & Next" button
   - Application validates JSON syntax
   - Saves annotation to `dataset/pdfs_annotation/`
   - Loads next PDF automatically

5. **Navigate as Needed**
   - Use "Previous" to go back without saving
   - Use "Next" to skip without saving
   - Use "Save & Next" for normal workflow

6. **Complete Session**
   - Process all PDFs
   - Click "Quit" to exit

---

## Requirements

### System Requirements

- **Python**: 3.8.10 or higher
- **Display**: Requires display server (Windows, X11, Wayland)
- **Memory**: ~500MB RAM recommended
- **Storage**: Space for annotation files (typically <100KB per PDF)

### Python Dependencies

All dependencies are in `requirements.txt`:

| Package | Purpose |
|---------|---------|
| `tkinter` | GUI framework (standard library) |
| `pypdfium2` | PDF rendering |
| `pdfplumber` | PDF text extraction (for TyphoonBulletinExtractor) |
| `pillow` | Image processing |
| `pandas` | Data manipulation (for TyphoonBulletinExtractor) |
| `psutil` | System resource monitoring |
| `requests` | URL handling |

### Installation

1. **Verify Python 3.8.10+**
   ```powershell
   python --version
   ```

2. **Create and Activate Virtual Environment**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Verify Installation**
   ```powershell
   python verify_install.py
   ```

---

## JSON Data Format

The GUI works with PAGASA PDF extracted JSON in the following format:

```json
{
  "updated_datetime": "2022-10-08 5:00 PM",
  "typhoon_location": "440 km Northeast of Infanta, Quezon",
  "typhoon_windspeed": "Maximum sustained winds of 175 kph",
  "typhoon_movement": "West-southwest at 20 kph",
  "signal_warning_tags1": {
    "Luzon": "Extreme winds with frequent damaging gusts...",
    "Visayas": null,
    "Mindanao": null,
    "Other": null
  },
  "signal_warning_tags2": {
    "Luzon": "...",
    "Visayas": "...",
    "Mindanao": null,
    "Other": null
  },
  "signal_warning_tags3": { ... },
  "signal_warning_tags4": { ... },
  "signal_warning_tags5": { ... },
  "rainfall_warning_tags1": { ... },
  "rainfall_warning_tags2": { ... },
  "rainfall_warning_tags3": { ... }
}
```

---

## Troubleshooting

### GUI Won't Start

**Error: "No module named 'pypdfium2'"**
- Solution: Install with `pip install pypdfium2`

**Error: "Cannot find display"**
- Cause: Running in WSL1 without X server
- Solution: Use WSL2 with Windows Terminal, or run natively on Windows

**Error: "Module tkinter not found"**
- Cause: tkinter not included in Python installation
- Solution: 
  - Windows: Reinstall Python and check "tcl/tk and IDLE"
  - Linux: `sudo apt install python3-tk`
  - macOS: Should be included; try `brew install python-tk@3.x`

### PDF Not Rendering

**Issue: Blank PDF panel**
- Check if PDF file is corrupted: `python analyze_pdf.py "path/to/pdf.pdf"`
- Verify PDF is not encrypted or password-protected

**Issue: Slow PDF loading**
- Normal for large PDFs (100+ pages)
- Can take 2-3 seconds to render first page

### JSON Validation Error

**Error: "Invalid JSON" when saving**
- Check JSON syntax before editing
- Look for missing commas, quotes, or brackets
- Use an online JSON validator for debugging

**Error: Annotation didn't save**
- Check that `dataset/pdfs_annotation/` directory exists
- Verify write permissions to that directory
- Check terminal output for specific error messages

### Extraction Incomplete

**Issue: Some fields are null**
- This is normal for some PDFs (not all signals are always issued)
- Manual editing can fill in missing data if available
- Only save if data is correct

---

## Integration with Other Tools

### With `analyze_pdf.py`

Use the annotation GUI to verify and improve extractions done by `analyze_pdf.py`:

```powershell
# Extract single PDF
python analyze_pdf.py "path/to/pdf.pdf" --json > temp.json

# Then use GUI to review and edit the JSON
python pdf_annotation_gui.py
# (Load the temp.json data into the GUI for review)
```

### With `test_accuracy.py`

Use annotations created in the GUI for accuracy testing:

```powershell
# After annotating PDFs in the GUI
python test_accuracy.py --detailed

# This compares your GUI annotations with extraction results
```

---

## Performance Characteristics

- **PDF Loading**: 1-3 seconds per page (depends on PDF complexity)
- **JSON Extraction**: 3-5 seconds in background
- **Memory Usage**: ~200-300 MB during operation
- **UI Responsiveness**: Threading ensures UI stays responsive during extraction

---

## Keyboard Shortcuts

Currently, the GUI supports button clicks. For faster workflow:

1. **Use Tab key**: Navigate between buttons
2. **Use Space/Enter**: Activate focused button
3. **Click in editor**: To start editing JSON

---

## Advanced Usage

### Processing Large Batches

For processing 100+ PDFs:

1. Start the GUI as normal
2. Use "Save & Next" consistently (don't use "Next" without saving)
3. GUI will process files sequentially
4. Average time: ~30-60 seconds per PDF
5. Estimated time for 100 PDFs: 1-2 hours

### Batch Verification

After annotating all PDFs:

```powershell
# Test accuracy of your annotations
python test_accuracy.py --metrics

# This shows how well the extractor performed
```

---

## Development Notes

### Class Structure

- **PDFAnnotationApp**: Main application controller
- **PDFViewer**: Left panel PDF rendering
- **JSONEditor**: Right panel JSON editing

### Threading

- Extraction runs in background thread to keep UI responsive
- Safe thread synchronization using queue mechanism

### Configuration

All paths are configured in the script:
- `dataset/pdfs/` - Source PDFs (configurable in code)
- `dataset/pdfs_annotation/` - Output annotations (configurable in code)

---

## See Also

- [README.md](README.md) - Main project documentation
- `pdf_annotation_gui.py` - Source code (922 lines)
- `typhoon_extraction_ml.py` - Extraction engine used by GUI
