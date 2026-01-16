#!/usr/bin/env python
"""
Test scrape_bulletin module
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modular.scrape_bulletin import scrape_bulletin

def test_scrape():
    """Test bulletin scraping"""
    print("Testing modular PAGASA bulletin scraper...")
    print("=" * 80)
    
    html_file = "bin/PAGASA BULLETIN PAGE/PAGASA.html"
    
    if not Path(html_file).exists():
        print(f"[ERROR] Test file not found: {html_file}")
        return False
    
    print(f"\n[TEST] Scraping: {html_file}")
    
    try:
        result = scrape_bulletin(html_file)
        
        if not result:
            print("\n[FAIL] scrape_bulletin() returned empty result")
            return False
        
        print(f"\n[SUCCESS] Found {len(result)} typhoon(s)")
        print("=" * 80)
        
        for i, pdf_links in enumerate(result, 1):
            print(f"\nTyphoon {i}: {len(pdf_links)} PDF(s)")
            for j, url in enumerate(pdf_links[:3], 1):
                print(f"  [{j}] {url[:100]}...")
            if len(pdf_links) > 3:
                print(f"  ... and {len(pdf_links) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"\n[FAIL] Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_scrape()
    sys.exit(0 if success else 1)
