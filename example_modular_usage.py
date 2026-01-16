#!/usr/bin/env python
"""
Example usage of the modular PAGASA WebScraper package.
This demonstrates how to integrate the modular package into your application.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path (only needed if not installed as package)
sys.path.insert(0, str(Path(__file__).parent.parent))

from modular.main import get_pagasa_data
from modular.analyze_pdf import analyze_pdf
from modular.scrape_bulletin import scrape_bulletin

def example_full_pipeline():
    """Example: Full pipeline from live PAGASA URL"""
    print("Example 1: Full Pipeline")
    print("=" * 80)
    
    # Note: This requires internet access to PAGASA website
    # For testing, you can use a local HTML file
    html_file = "bin/PAGASA BULLETIN PAGE/PAGASA.html"
    
    if Path(html_file).exists():
        print(f"Using local file: {html_file}")
        result = get_pagasa_data(source=html_file)
    else:
        print("Using live PAGASA URL")
        result = get_pagasa_data()
    
    if result:
        print(f"\n✓ Successfully retrieved data for: {result['typhoon_name']}")
        print(f"  PDF URL: {result['pdf_url']}")
        print(f"  Issued: {result['data'].get('updated_datetime', 'N/A')}")
        
        # Save to JSON file
        with open("pagasa_output.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Data saved to: pagasa_output.json")
    else:
        print("\n✗ Failed to retrieve data")


def example_pdf_analysis():
    """Example: Analyze a single PDF file"""
    print("\n\nExample 2: PDF Analysis Only")
    print("=" * 80)
    
    # Find a PDF file to analyze
    pdf_files = list(Path("dataset/pdfs").rglob("*.pdf"))
    
    if pdf_files:
        test_pdf = str(pdf_files[0])
        print(f"Analyzing: {Path(test_pdf).name}")
        
        data = analyze_pdf(test_pdf)
        
        if data:
            print(f"\n✓ Analysis successful")
            print(f"  Location: {data.get('typhoon_location_text', 'N/A')[:80]}...")
            print(f"  Wind Speed: {data.get('typhoon_windspeed', 'N/A')}")
            print(f"  Movement: {data.get('typhoon_movement', 'N/A')}")
        else:
            print("\n✗ Analysis failed")
    else:
        print("No PDF files found in dataset/pdfs/")


def example_bulletin_scraping():
    """Example: Scrape bulletin page only"""
    print("\n\nExample 3: Bulletin Scraping Only")
    print("=" * 80)
    
    html_file = "bin/PAGASA BULLETIN PAGE/PAGASA.html"
    
    if Path(html_file).exists():
        print(f"Scraping: {html_file}")
        
        pdf_links = scrape_bulletin(html_file)
        
        if pdf_links:
            print(f"\n✓ Found {len(pdf_links)} typhoon(s)")
            for i, typhoon_pdfs in enumerate(pdf_links, 1):
                print(f"\n  Typhoon {i}:")
                print(f"    Total bulletins: {len(typhoon_pdfs)}")
                if typhoon_pdfs:
                    print(f"    Latest: {typhoon_pdfs[-1][:80]}...")
        else:
            print("\n✗ No typhoons found")
    else:
        print(f"HTML file not found: {html_file}")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("MODULAR PAGASA WEBSCRAPER - USAGE EXAMPLES")
    print("="*80 + "\n")
    
    try:
        example_bulletin_scraping()
        example_pdf_analysis()
        # Uncomment to test full pipeline (requires internet or local HTML with accessible PDFs)
        # example_full_pipeline()
        
        print("\n\n" + "="*80)
        print("Examples completed!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
