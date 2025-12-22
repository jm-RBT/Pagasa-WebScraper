# PDF Annotation GUI - Quick Reference

## Starting the Application

### Windows
```bash
start_annotation_gui.bat
```
or
```bash
python pdf_annotation_gui.py
```

### Linux/macOS
```bash
./start_annotation_gui.sh
```
or
```bash
python pdf_annotation_gui.py
```

## Button Controls

| Button | Function |
|--------|----------|
| **◀ Previous** | Go to previous PDF (no save) |
| **💾 Save & Next** | Save current annotation and move to next PDF |
| **Next ▶** | Go to next PDF without saving |
| **🔄 Re-analyze** | Re-extract data from current PDF (loses edits) |
| **❌ Quit** | Close application |

## PDF Viewer Controls

| Button | Function |
|--------|----------|
| **◀ Prev Page** | Show previous page of PDF |
| **Next Page ▶** | Show next page of PDF |

## Keyboard Shortcuts (JSON Editor)

| Keys | Function |
|------|----------|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+A** | Select all |
| **Ctrl+C** | Copy |
| **Ctrl+V** | Paste |
| **Ctrl+X** | Cut |

## File Locations

| Location | Description |
|----------|-------------|
| `dataset/pdfs/` | Source PDF files (input) |
| `dataset/pdfs_annotation/` | Saved JSON annotations (output) |
| `bin/consolidated_locations.csv` | Location database (required) |

## Status Indicators

| Message | Meaning |
|---------|---------|
| **Ready** | Idle, ready for action |
| **Analyzing [filename]...** | Extracting data from PDF |
| **Extraction complete** | Data ready for review |
| **Saved: [filename]** | Annotation saved successfully |
| **✓ Valid JSON** | JSON syntax is correct |
| **✗ Invalid JSON** | JSON has syntax errors |

## Common Tasks

### Annotate All PDFs
1. Place PDFs in `dataset/pdfs/`
2. Run `python pdf_annotation_gui.py`
3. Review extracted data
4. Edit if needed
5. Click **Save & Next** repeatedly

### Fix a Specific PDF
1. Use **Previous/Next** to navigate to PDF
2. Click **Re-analyze** if needed
3. Edit JSON
4. Click **Save & Next**

### Skip a PDF
1. Click **Next** without saving

### Review Existing Annotation
- Existing annotations load automatically
- Edit and save to update

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| No PDFs found | Add PDFs to `dataset/pdfs/` |
| Extractor failed | Check `bin/consolidated_locations.csv` exists |
| Invalid JSON | Fix syntax errors (check commas, brackets) |
| Can't save | Ensure JSON is valid (green status) |
| PDF won't load | Check PDF is not corrupted |
| GUI frozen | Wait for background processing to complete |

## JSON Structure Quick Reference

```json
{
  "updated_datetime": "YYYY-MM-DD HH:MM:SS",
  "typhoon_location_text": "string",
  "typhoon_windspeed": "string",
  "typhoon_movement": "string",
  "signal_warning_tags1": {
    "Luzon": "location1, location2" or null,
    "Visayas": "locations" or null,
    "Mindanao": "locations" or null,
    "Other": "locations" or null
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

## Tips

✓ Use **Save & Next** for efficient batch processing
✓ Review PDF while editing JSON
✓ Use page navigation for multi-page PDFs
✓ JSON validation happens automatically
✓ Existing annotations load automatically
✓ Re-analyze if extraction looks wrong
✓ Directory structure is preserved in output

## Getting Help

1. Read `PDF_ANNOTATION_GUI_README.md` for full guide
2. Check `PDF_ANNOTATION_IMPLEMENTATION.md` for technical details
3. Review `typhoon_extraction_ml.py` for extraction logic
4. Run `python verify_install.py` to check dependencies

## Support Contact

For issues:
- Check documentation files
- Verify dependencies are installed
- Ensure `typhoon_extraction_ml.py` is present
- Check Python version is 3.8.10+
