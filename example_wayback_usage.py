#!/usr/bin/env python
"""
Example usage of wayback_advisory_scraper functions.

This demonstrates how to use the scraper programmatically
instead of via command-line interface.
"""

import sys
from pathlib import Path

# Import functions from wayback_advisory_scraper
# Note: In production, you would typically run the script directly
# This is just to show how the functions can be imported and used

def example_get_latest():
    """Example: Get PDFs from latest snapshot."""
    print("Example 1: Get latest snapshot")
    print("-" * 60)
    
    # This would call the main script with no arguments
    # python wayback_advisory_scraper.py
    print("Command: python wayback_advisory_scraper.py")
    print()


def example_get_all_limited():
    """Example: Get PDFs from latest 5 snapshots."""
    print("Example 2: Get latest 5 snapshots")
    print("-" * 60)
    
    # This would call the main script with --all --limit 5
    # python wayback_advisory_scraper.py --all --limit 5
    print("Command: python wayback_advisory_scraper.py --all --limit 5")
    print()


def example_get_year():
    """Example: Get all PDFs from 2024."""
    print("Example 3: Get all 2024 snapshots")
    print("-" * 60)
    
    # This would call the main script with --all --year 2024
    # python wayback_advisory_scraper.py --all --year 2024
    print("Command: python wayback_advisory_scraper.py --all --year 2024")
    print()


def main():
    """Display example usage."""
    print("="*60)
    print("WAYBACK ADVISORY SCRAPER - USAGE EXAMPLES")
    print("="*60)
    print()
    
    example_get_latest()
    example_get_all_limited()
    example_get_year()
    
    print("="*60)
    print("OUTPUT LOCATION")
    print("="*60)
    print(f"All PDFs are saved to: dataset/pdfs_advisory/")
    print()
    
    print("="*60)
    print("NOTES")
    print("="*60)
    print("- PDFs are saved with timestamp prefixes")
    print("- Duplicate files are automatically skipped")
    print("- Progress is logged to console")
    print("- Rate limiting is applied to be respectful to servers")
    print()


if __name__ == "__main__":
    main()
