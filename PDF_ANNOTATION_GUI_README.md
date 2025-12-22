# PDF Annotation GUI - User Guide

## Overview

`pdf_annotation_gui.py` is a graphical user interface tool for annotating PAGASA typhoon bulletin PDFs with extracted JSON data. It provides a split-view interface with a PDF viewer on the left and an editable JSON editor on the right.

## Features

- **Split View Layout**: PDF viewer (left) and JSON editor (right) in a resizable interface
- **Automatic PDF Discovery**: Recursively finds all PDFs in `dataset/pdfs/`
- **Automatic Extraction**: Uses `TyphoonBulletinExtractor` to extract data from PDFs
- **Editable JSON**: Edit extracted data before saving
- **Real-time Validation**: JSON syntax validation with error highlighting
- **Navigation**: Previous, Next, Save & Next buttons
- **Progress Tracking**: File counter showing "File X of Y: filename.pdf"
- **Background Processing**: Non-blocking PDF analysis with progress indicators
- **Annotation Persistence**: Saves annotations to `dataset/pdfs_annotation/` preserving directory structure
- **Existing Annotation Loading**: Automatically loads existing annotations if present

## Requirements

### Python Version
- Python 3.8.10 or higher

### Dependencies
All dependencies are in `requirements.txt`:
- `tkinter` (standard library, included with Python)
- `pypdfium2` (for PDF rendering)
- `pdfplumber` (used by extraction module)
- `pillow` (PIL for image processing)
- `pandas` (used by extraction module)
- `torch` and `transformers` (ML components)

### System Requirements
- **Display**: GUI requires a display server (X11, Wayland, or Windows)
- **Memory**: ~500MB RAM recommended for PDF processing
- **Storage**: Space for annotation files (typically small, <100KB per PDF)

## Installation

1. **Ensure Python 3.8.10+ is installed**:
   ```bash
   python --version
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python verify_install.py
   ```

## Usage

### Basic Usage

1. **Place PDFs in the source directory**:
   ```bash
   dataset/pdfs/
   ```
   
   The tool will recursively find all PDF files in this directory and subdirectories.

2. **Run the GUI**:
   ```bash
   python pdf_annotation_gui.py
   ```

3. **The interface will open**:
   - Left panel: PDF viewer with page navigation
   - Right panel: Extracted JSON data (editable)
   - Top: File counter showing current progress
   - Bottom: Navigation and action buttons

### Workflow

1. **Automatic Loading**: When a PDF is selected, the tool automatically:
   - Displays the PDF in the viewer
   - Extracts data using `TyphoonBulletinExtractor`
   - Populates the JSON editor with extracted data

2. **Review and Edit**:
   - Review the PDF in the left panel
   - Edit the JSON in the right panel if needed
   - Use page navigation buttons to view multi-page PDFs

3. **Save Annotations**:
   - Click **"Save & Next"** to save and move to the next file
   - Click **"Next"** to skip without saving
   - Click **"Previous"** to go back

4. **Re-analyze**: Click **"Re-analyze"** to re-extract data from the current PDF

### Keyboard Shortcuts

- **Ctrl+Z / Ctrl+Y**: Undo/Redo in JSON editor (standard text editing)
- **Ctrl+A**: Select all in JSON editor
- **Ctrl+C / Ctrl+V**: Copy/Paste in JSON editor

### Output Structure

Annotations are saved to:
```
dataset/pdfs_annotation/<relative_path>/<filename>.json
```

For example:
```
dataset/pdfs/pagasa-20-19W/PAGASA_20-19W_Pepito_SWB#02.pdf
→ dataset/pdfs_annotation/pagasa-20-19W/PAGASA_20-19W_Pepito_SWB#02.json
```

This preserves the directory structure from the source.

## JSON Format

The extracted JSON follows the TyphoonHubType structure:

```json
{
  "updated_datetime": "2024-11-16 11:00:00",
  "typhoon_location_text": "...",
  "typhoon_windspeed": "...",
  "typhoon_movement": "...",
  "signal_warning_tags1": {
    "Luzon": "location1, location2",
    "Visayas": null,
    "Mindanao": null,
    "Other": null
  },
  "signal_warning_tags2": { ... },
  "signal_warning_tags3": { ... },
  "signal_warning_tags4": { ... },
  "signal_warning_tags5": { ... },
  "rainfall_warning_tags1": { ... },
  "rainfall_warning_tags2": { ... },
  "rainfall_warning_tags3": { ... }
}
```

## Troubleshooting

### "No PDFs Found"
- Ensure PDFs are in `dataset/pdfs/`
- Check file extensions are `.pdf` (lowercase)

### "Extractor Init Failed"
- Verify `typhoon_extraction_ml.py` is in the same directory
- Ensure `bin/consolidated_locations.csv` exists
- Check all dependencies are installed

### "Invalid JSON" Error
- JSON syntax error in the editor
- Check for missing commas, brackets, or quotes
- Use an online JSON validator if needed

### PDF Rendering Issues
- Ensure `pypdfium2` is installed correctly
- Try re-installing: `pip install --force-reinstall pypdfium2`

### GUI Not Opening
- Verify tkinter is installed (usually comes with Python)
- On Linux, install: `sudo apt-get install python3-tk`
- Check display server is running

### Performance Issues
- Large PDFs (>50 pages) may take longer to render
- Close other applications to free memory
- Consider processing PDFs in smaller batches

## Advanced Usage

### Batch Processing Status

The tool maintains state automatically:
- Existing annotations are loaded if present
- You can stop and resume at any time
- Progress is implicit (saved annotations vs. total files)

### Custom Extraction Rules

To modify extraction logic:
1. Edit `typhoon_extraction_ml.py`
2. Restart the GUI to reload the extractor
3. Use **"Re-analyze"** button to re-process PDFs

### Validation Before Saving

The tool validates JSON syntax before saving:
- Invalid JSON will show an error
- Save button will not proceed until JSON is valid
- Error messages indicate the issue

## Code Structure

### Classes

1. **PDFViewer**: PDF rendering and display widget
   - Handles PDF loading with `pypdfium2`
   - Provides page navigation
   - Manages canvas and scrolling

2. **JSONEditor**: JSON editing widget with validation
   - Syntax highlighting (basic)
   - Real-time validation
   - Status indicator

3. **PDFAnnotationApp**: Main application controller
   - Manages application state
   - Coordinates PDF loading and extraction
   - Handles navigation and file management

### Key Methods

- `load_pdf_list()`: Discovers PDFs in dataset/pdfs/
- `analyze_pdf_async()`: Extracts data in background thread
- `save_current_annotation()`: Validates and saves JSON
- `get_annotation_path()`: Computes annotation file path

## Architecture

```
┌─────────────────────────────────────────────────┐
│         PDF Annotation GUI (Tkinter)            │
├─────────────────────────────────────────────────┤
│  PDFViewer  │  JSONEditor  │  Navigation        │
│  (pypdfium2)│  (Text+Valid)│  (Buttons)         │
├─────────────────────────────────────────────────┤
│     TyphoonBulletinExtractor (Background)       │
│  - LocationMatcher                              │
│  - DateTimeExtractor                            │
│  - SignalWarningExtractor                       │
│  - RainfallWarningExtractor                     │
├─────────────────────────────────────────────────┤
│     File System (dataset/pdfs/)                 │
└─────────────────────────────────────────────────┘
```

## Development

### Running in Development Mode

```bash
# With verbose output
python pdf_annotation_gui.py 2>&1 | tee annotation_log.txt

# Testing with sample PDFs
mkdir -p dataset/pdfs/test
cp sample.pdf dataset/pdfs/test/
python pdf_annotation_gui.py
```

### Testing

Create a test PDF:
```bash
mkdir -p dataset/pdfs/test
# Add a sample PAGASA bulletin PDF
cp /path/to/sample.pdf dataset/pdfs/test/
```

Run the tool and verify:
1. PDF loads and displays correctly
2. Extraction completes without errors
3. JSON is valid and editable
4. Annotations save to correct location

## Best Practices

1. **Regular Saves**: Use "Save & Next" frequently
2. **Backup**: Keep backups of `dataset/pdfs_annotation/`
3. **Review**: Always review extracted data for accuracy
4. **Validation**: Ensure JSON is valid before saving
5. **Organization**: Maintain directory structure in source PDFs

## Limitations

- **Single PDF at a time**: Processes one PDF at a time for accuracy
- **Memory usage**: Large PDFs require more memory
- **Extraction accuracy**: ML extraction may not be 100% accurate
- **Manual review needed**: Always review and correct extracted data

## Support

For issues or questions:
1. Check this README
2. Review `typhoon_extraction_ml.py` documentation
3. Check `analyze_pdf.py` for extraction examples
4. Verify dependencies with `verify_install.py`

## Version History

- **v1.0.0**: Initial release with core features
  - Split-view GUI
  - Automatic extraction
  - JSON editing and validation
  - Background processing
  - Navigation controls

## License

Part of the Pagasa-WebScraper project.
