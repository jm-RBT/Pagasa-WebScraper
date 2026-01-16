#!/usr/bin/env python
"""
Test script for the modular PAGASA WebScraper package.
Tests the main functionality with a local HTML file.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path to import modular package
sys.path.insert(0, str(Path(__file__).parent))

from modular.main import get_pagasa_data

def test_modular():
    """Test the modular implementation"""
    print("Testing modular PAGASA WebScraper...")
    print("=" * 80)
    
    print("\n[TEST] Using live PAGASA URL (requires internet)")
    print("[TEST] Getting PAGASA data...")
    print("Note: This test requires an active internet connection")
    
    try:
        result = get_pagasa_data(low_cpu_mode=False)
        
        if result is None:
            print("\n[FAIL] get_pagasa_data() returned None")
            return False
        
        print("\n[SUCCESS] Data retrieved successfully!")
        print("=" * 80)
        
        # Display summary
        print(f"\nTyphoon Name: {result.get('typhoon_name', 'N/A')}")
        print(f"PDF URL: {result.get('pdf_url', 'N/A')}")
        
        data = result.get('data', {})
        print(f"\nExtracted Data Fields:")
        print(f"  - Issued: {data.get('updated_datetime', 'N/A')}")
        print(f"  - Location: {data.get('typhoon_location_text', 'N/A')[:100]}...")
        print(f"  - Wind Speed: {data.get('typhoon_windspeed', 'N/A')}")
        print(f"  - Movement: {data.get('typhoon_movement', 'N/A')}")
        
        # Check signal warnings
        signal_count = 0
        for level in range(1, 6):
            tag = data.get(f'signal_warning_tags{level}', {})
            if isinstance(tag, dict):
                for ig in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                    if tag.get(ig):
                        signal_count += 1
        
        print(f"\n  - Signal Warnings: {signal_count} island group entries")
        
        # Check rainfall warnings
        rainfall_count = sum([
            len(data.get('rainfall_warning_tags1', [])),
            len(data.get('rainfall_warning_tags2', [])),
            len(data.get('rainfall_warning_tags3', []))
        ])
        print(f"  - Rainfall Warnings: {rainfall_count} total locations")
        
        # Output as JSON
        print("\n" + "=" * 80)
        print("JSON OUTPUT:")
        print("=" * 80)
        print(json.dumps(result, indent=2))
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_modular()
    sys.exit(0 if success else 1)
