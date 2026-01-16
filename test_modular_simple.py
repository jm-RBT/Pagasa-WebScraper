#!/usr/bin/env python
"""
Simple test script for the modular PAGASA WebScraper package.
Tests PDF analysis with a local file.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path to import modular package
sys.path.insert(0, str(Path(__file__).parent))

from modular.analyze_pdf import analyze_pdf

def test_analyze_pdf():
    """Test the PDF analysis functionality"""
    print("Testing modular PAGASA PDF analyzer...")
    print("=" * 80)
    
    # Find a PDF file to test
    pdf_files = list(Path("dataset/pdfs").rglob("*.pdf"))
    if not pdf_files:
        print("[ERROR] No PDF files found in dataset/pdfs/")
        return False
    
    # Use the first PDF
    test_pdf = str(pdf_files[0])
    print(f"\n[TEST] Analyzing PDF: {Path(test_pdf).name}")
    print(f"[TEST] Full path: {test_pdf}")
    
    try:
        result = analyze_pdf(test_pdf, low_cpu_mode=False)
        
        if result is None:
            print("\n[FAIL] analyze_pdf() returned None")
            return False
        
        print("\n[SUCCESS] PDF analysis completed!")
        print("=" * 80)
        
        # Display summary
        print(f"\nExtracted Data Fields:")
        print(f"  - Issued: {result.get('updated_datetime', 'N/A')}")
        print(f"  - Location: {result.get('typhoon_location_text', 'N/A')[:80]}...")
        print(f"  - Wind Speed: {result.get('typhoon_windspeed', 'N/A')}")
        print(f"  - Movement: {result.get('typhoon_movement', 'N/A')}")
        
        # Check signal warnings
        signal_count = 0
        for level in range(1, 6):
            tag = result.get(f'signal_warning_tags{level}', {})
            if isinstance(tag, dict):
                for ig in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                    if tag.get(ig):
                        signal_count += 1
        
        print(f"  - Signal Warnings: {signal_count} island group entries")
        
        # Output as JSON (first 50 lines)
        print("\n" + "=" * 80)
        print("JSON OUTPUT (excerpt):")
        print("=" * 80)
        json_output = json.dumps(result, indent=2)
        lines = json_output.split('\n')
        for line in lines[:50]:
            print(line)
        if len(lines) > 50:
            print(f"  ... ({len(lines) - 50} more lines)")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_analyze_pdf()
    sys.exit(0 if success else 1)
