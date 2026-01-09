#!/usr/bin/env python
"""
Example usage of advisory_scraper.

This demonstrates how the advisory extractor works.
"""

def main():
    """Display example usage."""
    print("="*70)
    print("ADVISORY EXTRACTOR - USAGE EXAMPLES")
    print("="*70)
    print()
    print("The advisory extractor parses rainfall warning tables from PDFs:")
    print("  https://www.pagasa.dost.gov.ph/weather/weather-advisory")
    print()
    print("Usage Examples:")
    print("="*70)
    print()
    print("1. Scrape from live URL and extract:")
    print("   python advisory_scraper.py")
    print()
    print("2. Test with random PDF from dataset:")
    print("   python advisory_scraper.py --random")
    print()
    print("3. Test with specific PDF:")
    print("   python advisory_scraper.py --path 'dataset/pdfs_advisory/file.pdf'")
    print()
    print("4. Extract from PDF URL:")
    print("   python advisory_scraper.py --url 'https://example.com/advisory.pdf'")
    print()
    print("5. JSON-only output (for piping):")
    print("   python advisory_scraper.py --json --random")
    print()
    print("="*70)
    print("OUTPUT FORMAT")
    print("="*70)
    print()
    print("JSON with 3 warning levels (red/orange/yellow):")
    print("- Red: >200mm rainfall")
    print("- Orange: 100-200mm rainfall")
    print("- Yellow: 50-100mm rainfall")
    print()
    print("Each level categorizes locations by island groups:")
    print("- Luzon, Visayas, Mindanao, Other")
    print()
    print("Example output:")
    print("""
{
  "source_file": "path/to/file.pdf",
  "rainfall_warnings": {
    "red": {
      "Luzon": "Manila, Quezon City",
      "Visayas": null,
      "Mindanao": null,
      "Other": null
    },
    "orange": {...},
    "yellow": {...}
  }
}
    """)
    print()


if __name__ == "__main__":
    main()
