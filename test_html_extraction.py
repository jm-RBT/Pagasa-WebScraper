#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for HTML extraction functionality.
"""

from html_bulletin_extractor import HTMLBulletinExtractor
import json

def main():
    """Test HTML extraction with the provided PAGASA.html file"""
    html_file = "bin/PAGASA BULLETIN PAGE/PAGASA.html"
    
    print("Testing HTML Bulletin Extractor")
    print("=" * 80)
    print(f"Source: {html_file}\n")
    
    extractor = HTMLBulletinExtractor()
    typhoons = extractor.extract_all_typhoons(html_file)
    
    if not typhoons:
        print("ERROR: No typhoons extracted")
        return 1
    
    print(f"Successfully extracted {len(typhoons)} typhoon(s)\n")
    
    for idx, typhoon in enumerate(typhoons, 1):
        print(f"Typhoon {idx}: {typhoon.get('typhoon_name', 'Unknown')}")
        print("-" * 80)
        print(f"  Name:         {typhoon.get('typhoon_stripped_name', 'N/A')}")
        print(f"  Full Name:    {typhoon.get('typhoon_name', 'N/A')}")
        print(f"  Issued:       {typhoon.get('updated_datetime', 'N/A')}")
        print(f"  Location:     {typhoon.get('typhoon_location_text', 'N/A')}")
        print(f"  Movement:     {typhoon.get('typhoon_movement', 'N/A')}")
        print(f"  Wind Speed:   {typhoon.get('typhoon_windspeed', 'N/A')}")
        
        # Check signal warnings
        has_signals = False
        for level in range(1, 6):
            tag_key = f'signal_warning_tags{level}'
            tag = typhoon.get(tag_key, {})
            for island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                if tag.get(island_group):
                    if not has_signals:
                        print("\n  Signal Warnings:")
                        has_signals = True
                    print(f"    Level {level} - {island_group}:")
                    print(f"      {tag[island_group][:100]}..." if len(tag[island_group]) > 100 else f"      {tag[island_group]}")
        
        if not has_signals:
            print("\n  Signal Warnings: None")
        
        print()
    
    print("=" * 80)
    print("Test completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
