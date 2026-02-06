# Modular PAGASA WebScraper

This directory contains the modular, library version of the PAGASA typhoon bulletin scraper and analyzer. These files are designed to be imported and used programmatically in other projects like **Workbench**.

## Purpose

The modular files provide a clean, reusable API for integrating PAGASA typhoon data extraction into other systems without running command-line scripts.

## Main Entry Point

The primary function to use is `get_pagasa_data()` from `typhoonhub.py`:

```python
from modular import get_pagasa_data

# Get data from live PAGASA URL
result = get_pagasa_data()

# Or use a custom source
result = get_pagasa_data(source="path/to/bulletin.html")
result = get_pagasa_data(source="path/to/bulletin.pdf")
result = get_pagasa_data(source="https://example.com/bulletin")
```

## Return Format

The `get_pagasa_data()` function returns a dictionary with this structure:

```python
{
    'typhoon_name': str,           # Name of the typhoon
    'pdf_url': str,                # URL or path to the PDF source
    'data': {                      # Extracted bulletin data
        'typhoon_name': str,
        'typhoon_location_text': str,
        'typhoon_windspeed': str,
        'typhoon_movement': str,
        'updated_datetime': str,
        
        # Signal warnings by level (1-5)
        'signal_warning_tags1': {
            'Luzon': str,
            'Visayas': str,
            'Mindanao': str,
            'Other': str
        },
        # ... signal_warning_tags2 through signal_warning_tags5 ...
        
        # Rainfall warnings (from live advisory)
        'rainfall_warning_tags1': list,  # Red alert locations
        'rainfall_warning_tags2': list,  # Orange alert locations
        'rainfall_warning_tags3': list,  # Yellow alert locations
    }
}
```

Returns `None` on failure.

## Files

### Core Files

- **`typhoonhub.py`** - Main entry point with `get_pagasa_data()` function
- **`typhoon_extraction.py`** - Core extraction engine (TyphoonBulletinExtractor)
- **`analyze_pdf.py`** - PDF analysis wrapper with safety checks
- **`scrape_bulletin.py`** - Web scraper for PAGASA bulletin page
- **`advisory_scraper.py`** - Rainfall advisory extractor
- **`__init__.py`** - Package initialization

### Key Differences from Main Scripts

The modular files differ from the main scripts in several ways:

1. **No CLI Interface**: No command-line argument parsing or `if __name__ == "__main__"` blocks
2. **Library Usage**: Designed to be imported, not executed
3. **Minimal Output**: Uses `sys.stderr` for warnings/errors, not verbose stdout
4. **Return Values**: Functions return data structures instead of printing results
5. **Path Handling**: Smart path resolution for `bin/consolidated_locations.csv` that works from any working directory

## Integration Example

See `examples/example_workbench_integration.py` for comprehensive usage examples including:

1. Basic usage with live PAGASA data
2. Using custom sources (HTML files, URLs, PDFs)
3. Direct PDF analysis
4. Workbench integration pattern

## Requirements

All modular files use the same dependencies as the main project:

- beautifulsoup4
- requests
- pdfplumber
- pandas

See `requirements.txt` in the project root.

## Usage in Workbench

To integrate into Workbench:

```python
import sys
from pathlib import Path

# Add PAGASA scraper to Python path
scraper_path = Path("/path/to/Pagasa-WebScraper")
sys.path.insert(0, str(scraper_path))

# Import and use
from modular import get_pagasa_data

def fetch_pagasa_data():
    """Fetch latest PAGASA typhoon data for Workbench"""
    result = get_pagasa_data()
    
    if not result:
        return {'error': 'Failed to fetch PAGASA data'}
    
    # Format for your application
    return {
        'typhoon_name': result['typhoon_name'],
        'location': result['data']['typhoon_location_text'],
        'wind_speed': result['data']['typhoon_windspeed'],
        'warnings': result['data']['signal_warning_tags1'],
        # ... etc
    }
```

## Testing

Run the comprehensive test suite:

```bash
# From project root
python3 -c "
from modular import get_pagasa_data
from modular.typhoon_extraction import TyphoonBulletinExtractor

# Test imports
print('✓ Imports successful')

# Test with sample PDF
result = get_pagasa_data(source='dataset/pdfs/sample.pdf')
if result:
    print(f'✓ Extracted: {result[\"typhoon_name\"]}')
"
```

## Updates

This modular package was last updated on 2026-02-06 to:
- Fix path resolution for `bin/consolidated_locations.csv`
- Fix typo in TARGET_URL constant
- Ensure compatibility when imported from different working directories
- Maintain API compatibility with Workbench integration

## License

Copyright (c) 2026 JMontero, Adotac
Licensed under the MIT License. See LICENSE file in the project root for details.
