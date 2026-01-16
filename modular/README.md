# Modular PAGASA WebScraper

A modular and reusable implementation of the PAGASA typhoon bulletin scraper and analyzer. Designed for programmatic use in other systems.

## Features

- **Modular Design**: All scripts are pure libraries without CLI functionality
- **JSON Output**: Returns structured data as JSON-ready Python dictionaries
- **Silent Operation**: No print statements except for errors and warnings (to stderr)
- **Easy Integration**: Simple API for integration into other projects
- **No Dependencies on Web Archive**: Uses only live PAGASA URLs

## Installation

```bash
pip install beautifulsoup4 requests pandas pdfplumber psutil
```

## Usage

### Basic Usage

```python
from modular.main import get_pagasa_data

# Get data from live PAGASA URL
result = get_pagasa_data()

if result:
    print(f"Typhoon: {result['typhoon_name']}")
    print(f"PDF URL: {result['pdf_url']}")
    
    data = result['data']
    print(f"Issued: {data['updated_datetime']}")
    print(f"Location: {data['typhoon_location_text']}")
    print(f"Wind Speed: {data['typhoon_windspeed']}")
    print(f"Movement: {data['typhoon_movement']}")
```

### Using Custom Source

```python
from modular.main import get_pagasa_data

# Use a local HTML file
result = get_pagasa_data(source="path/to/bulletin.html")

# Use a custom URL
result = get_pagasa_data(source="https://example.com/bulletin")
```

### Low CPU Mode

```python
from modular.main import get_pagasa_data

# Enable low CPU mode to limit CPU usage to ~30%
result = get_pagasa_data(low_cpu_mode=True)
```

## Individual Module Usage

### PDF Analysis Only

```python
from modular.analyze_pdf import analyze_pdf

# Analyze a local PDF file
data = analyze_pdf("path/to/bulletin.pdf")

# Analyze a PDF from URL
data = analyze_pdf("https://example.com/bulletin.pdf")

# With low CPU mode
data = analyze_pdf("path/to/bulletin.pdf", low_cpu_mode=True)
```

### Bulletin Scraping Only

```python
from modular.scrape_bulletin import scrape_bulletin

# Scrape from local HTML file
pdf_links = scrape_bulletin("path/to/bulletin.html")

# Scrape from URL
pdf_links = scrape_bulletin("https://www.pagasa.dost.gov.ph/weather/tropical-cyclone-bulletin")

# Result is a 2D list: [[typhoon1_pdfs], [typhoon2_pdfs], ...]
for i, typhoon_pdfs in enumerate(pdf_links, 1):
    print(f"Typhoon {i}: {len(typhoon_pdfs)} bulletins")
    for pdf_url in typhoon_pdfs:
        print(f"  - {pdf_url}")
```

### Advisory Scraping Only

```python
from modular.advisory_scraper import scrape_and_extract, extract_from_url

# Get rainfall advisory from live PAGASA URL
result = scrape_and_extract()

# Get from custom URL
result = extract_from_url("https://example.com/advisory")

# Access the data
warnings = result['rainfall_warnings']
print(f"Red warnings: {len(warnings['red'])} locations")
print(f"Orange warnings: {len(warnings['orange'])} locations")
print(f"Yellow warnings: {len(warnings['yellow'])} locations")
```

## Output Format

### Main Function Output

```json
{
  "typhoon_name": "PEPITO",
  "pdf_url": "https://pubfiles.pagasa.dost.gov.ph/...",
  "data": {
    "updated_datetime": "2024-11-15 17:00:00",
    "typhoon_location_text": "The center of Typhoon PEPITO...",
    "typhoon_windspeed": "Maximum sustained winds of 185 km/h...",
    "typhoon_movement": "Westward at 30 km/h",
    "signal_warning_tags1": {
      "Luzon": "...",
      "Visayas": "...",
      "Mindanao": null,
      "Other": null
    },
    "signal_warning_tags2": { ... },
    "signal_warning_tags3": { ... },
    "signal_warning_tags4": { ... },
    "signal_warning_tags5": { ... },
    "rainfall_warning_tags1": ["Location1", "Location2", ...],
    "rainfall_warning_tags2": ["Location3", "Location4", ...],
    "rainfall_warning_tags3": ["Location5", "Location6", ...]
  }
}
```

## Error Handling

All modules return `None` on failure and print error messages to `stderr`:

```python
from modular.main import get_pagasa_data
import sys

result = get_pagasa_data()

if result is None:
    print("Failed to get PAGASA data", file=sys.stderr)
    sys.exit(1)
else:
    # Process the data
    pass
```

## Module Structure

```
modular/
├── __init__.py              # Package initialization
├── main.py                  # Main entry point
├── scrape_bulletin.py       # Bulletin page scraper
├── advisory_scraper.py      # Rainfall advisory scraper
├── analyze_pdf.py           # PDF analysis utilities
└── typhoon_extraction.py    # Core extraction engine
```

## Requirements

- Python 3.8+
- beautifulsoup4
- requests
- pandas
- pdfplumber
- psutil

## Notes

- All print statements are directed to `stderr` for errors and warnings
- The modules use relative imports and must be imported as a package
- The `bin/consolidated_locations.csv` file must be present in the parent directory
- No CLI functionality - all modules are pure libraries

## Deployment / Migration to Other Systems

When integrating this modular package into another system, you only need to copy:

1. **The entire `modular/` directory** - Contains all the library code
2. **The `bin/consolidated_locations.csv` file** - Required for location validation (26,808 Philippine locations)

**Directory structure in your project:**
```
your_project/
├── modular/              # Copy this entire directory
│   ├── __init__.py
│   ├── main.py
│   ├── scrape_bulletin.py
│   ├── advisory_scraper.py
│   ├── analyze_pdf.py
│   └── typhoon_extraction.py
└── bin/
    └── consolidated_locations.csv  # Copy this file
```

**Note**: You do NOT need to copy:
- Test files (test_*.py)
- Example files (example_*.py)
- Any HTML files from the bin/ directory
- The original CLI scripts from the root directory

The modular package uses the live PAGASA URL by default, so no local HTML files are required.

## Example Integration

```python
#!/usr/bin/env python
"""
Example integration of modular PAGASA scraper into another application.
"""

import json
import sys
from modular.main import get_pagasa_data

def main():
    # Get PAGASA data
    result = get_pagasa_data()
    
    if result is None:
        print("Error: Could not retrieve PAGASA data", file=sys.stderr)
        return 1
    
    # Save to JSON file
    with open("pagasa_data.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("Data saved to pagasa_data.json")
    
    # Or send to API
    # requests.post("https://api.example.com/typhoon", json=result)
    
    # Or process the data
    data = result['data']
    if data.get('signal_warning_tags5'):
        print("ALERT: Signal #5 in effect!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```
