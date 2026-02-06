#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Using the Modular PAGASA WebScraper in Workbench or Other Projects

This example demonstrates how to integrate the modular PAGASA scraper
into another project (like Workbench) by importing and using the
get_pagasa_data() function.

Copyright (c) 2026 JMontero, Adotac
Licensed under the MIT License. See LICENSE file in the project root for details.
"""

# Option 1: If modular package is in Python path
# from modular import get_pagasa_data

# Option 2: If you need to add the path manually
import sys
from pathlib import Path

# Add the Pagasa-WebScraper directory to Python path
# Adjust this path to where you've placed the scraper
SCRAPER_PATH = Path(__file__).parent.parent  # Go up from examples/ to project root
# OR: SCRAPER_PATH = Path("/path/to/Pagasa-WebScraper")

sys.path.insert(0, str(SCRAPER_PATH))

# Now import the main function
from modular import get_pagasa_data


def example_basic_usage():
    """
    Example 1: Basic usage - Get data from live PAGASA URL
    
    This fetches the latest typhoon bulletin from PAGASA's website.
    """
    print("=" * 70)
    print("EXAMPLE 1: Basic Usage - Live PAGASA Data")
    print("=" * 70)
    
    # Call with no arguments to use live PAGASA URL
    result = get_pagasa_data()
    
    if result:
        print(f"\n✓ Successfully retrieved data:")
        print(f"  Typhoon Name: {result['typhoon_name']}")
        print(f"  PDF URL: {result['pdf_url']}")
        print(f"  Location: {result['data'].get('typhoon_location_text', 'N/A')}")
        print(f"  Wind Speed: {result['data'].get('typhoon_windspeed', 'N/A')}")
        print(f"  Movement: {result['data'].get('typhoon_movement', 'N/A')}")
        
        # Access signal warnings
        data = result['data']
        for level in range(1, 6):
            tag_key = f'signal_warning_tags{level}'
            if tag_key in data:
                signal_data = data[tag_key]
                if any(signal_data.get(ig) for ig in ['Luzon', 'Visayas', 'Mindanao']):
                    print(f"\n  Signal {level} Areas:")
                    for island in ['Luzon', 'Visayas', 'Mindanao']:
                        if signal_data.get(island):
                            print(f"    {island}: {signal_data[island][:100]}...")
        
        # Access rainfall warnings (from live advisory)
        if 'rainfall_warning_tags1' in data:
            print(f"\n  Rainfall Warnings:")
            print(f"    Red: {len(data['rainfall_warning_tags1'])} locations")
            print(f"    Orange: {len(data['rainfall_warning_tags2'])} locations")
            print(f"    Yellow: {len(data['rainfall_warning_tags3'])} locations")
        
        return result
    else:
        print("\n✗ Failed to retrieve data")
        return None


def example_custom_source():
    """
    Example 2: Use custom source - HTML file or URL
    
    This allows you to test with a saved HTML file or custom URL.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Custom Source")
    print("=" * 70)
    
    # Example with a custom URL (e.g., web archive)
    custom_url = "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
    
    result = get_pagasa_data(source=custom_url)
    
    if result:
        print(f"\n✓ Data from custom source:")
        print(f"  Typhoon: {result['typhoon_name']}")
        print(f"  PDF: {result['pdf_url'][:60]}...")
    else:
        print("\n✗ Failed to retrieve data from custom source")
    
    return result


def example_direct_pdf():
    """
    Example 3: Analyze a specific PDF file
    
    This allows you to analyze a downloaded PDF directly.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Direct PDF Analysis")
    print("=" * 70)
    
    # Example with a local PDF file
    # Replace with actual PDF path
    pdf_path = "dataset/pdfs/pagasa-20-19W/PAGASA_20-19W_Pepito_SWB#02.pdf"
    
    if not Path(pdf_path).exists():
        print(f"\n⚠ PDF not found: {pdf_path}")
        print("  (This example requires a sample PDF)")
        return None
    
    result = get_pagasa_data(source=pdf_path)
    
    if result:
        print(f"\n✓ PDF analysis successful:")
        print(f"  Typhoon: {result['typhoon_name']}")
        print(f"  Issued: {result['data'].get('updated_datetime', 'N/A')}")
    else:
        print("\n✗ Failed to analyze PDF")
    
    return result


def example_workbench_integration():
    """
    Example 4: How to use in Workbench
    
    This shows how Workbench would typically call the scraper
    to get PAGASA data for display or processing.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Workbench Integration Pattern")
    print("=" * 70)
    
    # In Workbench, you would call this function
    # to get fresh PAGASA data whenever needed
    
    try:
        # Get latest data
        data = get_pagasa_data()
        
        if not data:
            return {
                'status': 'error',
                'message': 'Failed to retrieve PAGASA data'
            }
        
        # Format for Workbench display
        workbench_data = {
            'status': 'success',
            'typhoon': {
                'name': data['typhoon_name'],
                'location': data['data'].get('typhoon_location_text'),
                'wind_speed': data['data'].get('typhoon_windspeed'),
                'movement': data['data'].get('typhoon_movement'),
                'issued_time': data['data'].get('updated_datetime'),
            },
            'warnings': {
                'signal_1': data['data'].get('signal_warning_tags1', {}),
                'signal_2': data['data'].get('signal_warning_tags2', {}),
                'signal_3': data['data'].get('signal_warning_tags3', {}),
                'signal_4': data['data'].get('signal_warning_tags4', {}),
                'signal_5': data['data'].get('signal_warning_tags5', {}),
            },
            'rainfall': {
                'red': data['data'].get('rainfall_warning_tags1', []),
                'orange': data['data'].get('rainfall_warning_tags2', []),
                'yellow': data['data'].get('rainfall_warning_tags3', []),
            },
            'source': {
                'pdf_url': data['pdf_url'],
            }
        }
        
        print("\n✓ Data formatted for Workbench:")
        print(f"  Status: {workbench_data['status']}")
        print(f"  Typhoon: {workbench_data['typhoon']['name']}")
        print(f"  Has warnings: {bool(workbench_data['warnings'])}")
        print(f"  Has rainfall data: {bool(any(workbench_data['rainfall'].values()))}")
        
        return workbench_data
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "PAGASA WebScraper - Modular Usage Examples" + " " * 16 + "║")
    print("╚" + "═" * 68 + "╝")
    
    # Example 1: Basic usage with live data
    # Uncomment to test with live PAGASA website
    # example_basic_usage()
    
    # Example 2: Custom source
    # Uncomment to test with custom URL
    # example_custom_source()
    
    # Example 3: Direct PDF analysis
    # Uncomment if you have a sample PDF
    # example_direct_pdf()
    
    # Example 4: Workbench integration
    print("\n[INFO] Demonstrating Workbench integration pattern...")
    print("[INFO] (Using local PDF since we don't have internet access)")
    
    # For testing, use a local PDF if available
    sample_pdfs = list(Path("dataset/pdfs").rglob("*.pdf"))
    if sample_pdfs:
        # Temporarily modify example_workbench_integration to use local PDF
        import types
        original_get_data = get_pagasa_data
        
        def mock_get_data(source=None):
            # Use a local PDF for testing
            return original_get_data(source=str(sample_pdfs[0]))
        
        # Replace temporarily
        globals()['get_pagasa_data'] = mock_get_data
        result = example_workbench_integration()
        # Restore
        globals()['get_pagasa_data'] = original_get_data
    else:
        result = example_workbench_integration()
    
    print("\n" + "=" * 70)
    print("Examples completed. To run with live data, uncomment the desired")
    print("example function calls in the main() function.")
    print("=" * 70)


if __name__ == "__main__":
    main()
