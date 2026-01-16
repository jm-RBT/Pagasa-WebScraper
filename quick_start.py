#!/usr/bin/env python
"""
Quick Start Guide for Modular PAGASA WebScraper

This script demonstrates the simplest way to use the modular package.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path if running as standalone script
sys.path.insert(0, str(Path(__file__).parent))

from modular.main import get_pagasa_data

def main():
    """
    Quick start example: Get PAGASA typhoon data and save to JSON
    """
    print("Quick Start: Getting PAGASA Typhoon Data")
    print("=" * 80)
    
    # Option 1: Use live PAGASA URL (requires internet)
    # result = get_pagasa_data()
    
    # Option 2: Use local HTML file (for testing offline)
    html_file = "bin/PAGASA BULLETIN PAGE/PAGASA.html"
    if Path(html_file).exists():
        print(f"Using local file: {html_file}")
        result = get_pagasa_data(source=html_file)
    else:
        print("Using live PAGASA URL")
        result = get_pagasa_data()
    
    # Check if data was retrieved
    if result is None:
        print("\n[ERROR] Failed to retrieve data")
        print("Check stderr for error messages")
        return 1
    
    # Display summary
    print("\n[SUCCESS] Data retrieved!")
    print(f"Typhoon: {result['typhoon_name']}")
    print(f"PDF: {result['pdf_url']}")
    
    data = result['data']
    print(f"\nBulletin Details:")
    print(f"  Issued: {data.get('updated_datetime', 'N/A')}")
    print(f"  Wind Speed: {data.get('typhoon_windspeed', 'N/A')}")
    print(f"  Movement: {data.get('typhoon_movement', 'N/A')}")
    
    # Save to JSON file
    output_file = "typhoon_data.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\n[SAVED] Data written to: {output_file}")
    print("\nYou can now:")
    print("  - View the JSON file: cat typhoon_data.json")
    print("  - Parse with jq: cat typhoon_data.json | jq '.data.typhoon_windspeed'")
    print("  - Import in Python: json.load(open('typhoon_data.json'))")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
