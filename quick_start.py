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
    
    # Use live PAGASA URL (default behavior)
    print("Fetching data from live PAGASA URL...")
    print("Note: This requires an active internet connection")
    result = get_pagasa_data()
    
    # Check if data was retrieved
    if result is None:
        print("\n[ERROR] Failed to retrieve data")
        print("Check stderr for error messages")
        print("\nTip: You can also use a custom source:")
        print('  result = get_pagasa_data(source="path/to/bulletin.html")')
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
    
    # Display JSON output
    print("\nJSON Output:")
    print(json.dumps(result, indent=2))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
