#!/usr/bin/env python
"""
PAGASA Weather Advisory PDF Extractor

Extracts rainfall warning data from PAGASA weather advisory PDFs.
Parses tables to extract locations affected by different rainfall warning levels.

Note: Only works with text-based PDFs (not scanned images).

Usage:
    python advisory_scraper.py                    # Scrape from live URL
    python advisory_scraper.py --random           # Test random PDF from dataset
    python advisory_scraper.py "file.pdf"         # Test specific PDF
    python advisory_scraper.py "http://..."       # Extract from URL
    
Output: JSON with rainfall warnings as lists of locations per warning level
"""

import requests
import sys
import os
import re
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import pdfplumber
import time


# Configuration
TARGET_URL = "https://www.pagasa.dost.gov.ph/weather/weather-advisory"
OUTPUT_DIR = Path(__file__).parent / "dataset" / "pdfs_advisory"


class RainfallAdvisoryExtractor:
    """Extracts rainfall advisory data from PAGASA PDFs"""
    
    def __init__(self):
        pass
    
    def parse_locations_text(self, text: str) -> List[str]:
        """
        Parse location text into individual locations.
        Handles directional modifiers and "and" connectors properly.
        """
        if not text or text.strip() == '-' or text.strip() == '':
            return []
        
        # Directional prefixes that should be combined with following word (e.g., "Northern Samar")
        directional_prefixes = ['Northern', 'Southern', 'Eastern', 'Western', 'Central', 
                                'North', 'South', 'East', 'West', 'Greater']
        
        # Directional suffixes that should be combined with previous word (e.g., "Negros Occidental")
        directional_suffixes = ['Occidental', 'Oriental']
        
        # Replace newlines with spaces first to keep multi-word locations together
        # Then split by commas only
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Normalize multiple spaces to single space
        text = ' '.join(text.split())
        
        # Split by comma only
        parts = [p.strip() for p in text.split(',')]
        
        # Process each part
        locations = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            
            # Skip empty parts, dashes, or standalone "and"
            if not part or part == '-' or part.lower() == 'and':
                i += 1
                continue
            
            # Check if this is a directional prefix that should be combined with next part
            if part in directional_prefixes and i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                # Skip "and" in between if present
                if next_part.lower() == 'and' and i + 2 < len(parts):
                    next_part = parts[i + 2].strip()
                    i += 1  # Skip the "and"
                
                # Combine directional with location name
                if next_part and next_part != '-' and next_part.lower() != 'and':
                    combined = f"{part} {next_part}"
                    locations.append(combined)
                    i += 2  # Skip both parts
                    continue
                else:
                    # Standalone directional, keep as is (unusual but possible)
                    locations.append(part)
                    i += 1
                    continue
            
            # Check if next part is a directional suffix that should be combined with current part
            if i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                if next_part in directional_suffixes:
                    # Combine current location with directional suffix
                    combined = f"{part} {next_part}"
                    locations.append(combined)
                    i += 2  # Skip both parts
                    continue
            
            # Handle parts that start with "and" (e.g., "and Guimaras")
            if part.lower().startswith('and '):
                actual_location = part[4:].strip()  # Remove "and " prefix
                if actual_location and actual_location != '-':
                    locations.append(actual_location)
                i += 1
                continue
            
            # Regular location - add it
            locations.append(part)
            i += 1
        
        return locations
    

    
    def extract_rainfall_tables(self, pdf_path: str) -> List[List[List]]:
        """Extract all rainfall forecast tables from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return []
                
                # Check if PDF has extractable text
                page = pdf.pages[0]
                has_text = len(page.chars) > 0
                
                # If no text, cannot extract
                if not has_text:
                    print("[WARNING] PDF is image-based (scanned document) with no extractable text")
                    print("[INFO] This script only works with text-based PDFs")
                    return []
                
                # Extract tables from first page
                tables = page.extract_tables()
                
                if not tables:
                    return []
                
                # Find all rainfall forecast tables
                rainfall_tables = []
                for table in tables:
                    if table and len(table) > 0:
                        # Check if this is a rainfall forecast table
                        first_row = ' '.join(str(cell or '') for cell in table[0]).lower()
                        if 'rainfall' in first_row or 'forecast' in first_row:
                            rainfall_tables.append(table)
                
                # If no specific table found but we have tables, return all of them
                if not rainfall_tables and tables:
                    rainfall_tables = tables
                
                return rainfall_tables
                
        except Exception as e:
            print(f"[ERROR] Failed to extract tables from PDF: {e}")
            return []
    
    def extract_rainfall_warnings(self, pdf_path: str) -> Dict:
        """
        Extract rainfall warnings from PDF
        
        Returns:
            Dict with structure:
            {
                'red': [...],
                'orange': [...],
                'yellow': [...]
            }
        """
        tables = self.extract_rainfall_tables(pdf_path)
        
        if not tables:
            print("[WARNING] No rainfall tables found in PDF")
            return self._empty_warnings()
        
        print(f"[INFO] Processing {len(tables)} table(s)")
        
        warnings = self._empty_warnings()
        
        # Process each table
        for table_idx, table in enumerate(tables):
            print(f"[INFO] Processing table {table_idx + 1}/{len(tables)}")
            
            # Parse table rows
            for row in table:
                if not row or len(row) < 2:  # Need at least rainfall amount and one location column
                    continue
                
                # Get rainfall range from first column
                rainfall_col = str(row[0]).lower() if row[0] else ''
                
                # Determine warning level based on rainfall amount
                warning_level = None
                if '>200' in rainfall_col or '> 200' in rainfall_col:
                    warning_level = 'red'
                elif re.search(r'100\s*[-–]\s*200', rainfall_col):
                    warning_level = 'orange'
                elif re.search(r'50\s*[-–]\s*100', rainfall_col):
                    warning_level = 'yellow'
                
                if not warning_level:
                    continue
                
                # Extract locations from "Today" column (2nd column, index 1)
                # and "Tomorrow" column (3rd column, index 2)
                today_locs = self.parse_locations_text(row[1] if len(row) > 1 else '')
                tomorrow_locs = self.parse_locations_text(row[2] if len(row) > 2 else '')
                
                # Combine locations from both columns
                all_locations = list(set(today_locs + tomorrow_locs))
                
                if all_locations:
                    # Add locations directly to warning level
                    warnings[warning_level].extend(all_locations)
        
        # Remove duplicates and sort
        for level in warnings:
            warnings[level] = sorted(list(set(warnings[level])))
        
        return warnings
    
    def _empty_warnings(self) -> Dict:
        """Return empty warnings structure"""
        return {
            'red': [],
            'orange': [],
            'yellow': []
        }
    
    def format_for_output(self, warnings: Dict) -> Dict:
        """Format warnings for JSON output - return lists directly"""
        return warnings


def setup_output_directory():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_page_html(url):
    """Fetch HTML content from a URL"""
    print(f"[INFO] Fetching page from: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch page: {e}")
        return None


def _has_advisory_classes(class_attr):
    """Check if element has required advisory classes"""
    return class_attr and 'col-md-12' in class_attr and 'article-content' in class_attr and 'weather-advisory' in class_attr


def extract_pdfs_from_advisory_elements(html_content, base_url):
    """Extract PDF links from advisory elements"""
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_urls = []
    
    advisory_elements = soup.find_all('div', class_=_has_advisory_classes)
    
    if not advisory_elements:
        advisory_elements = soup.find_all('div', class_='article-content weather-advisory')
        if not advisory_elements:
            advisory_elements = soup.find_all('div', class_='weather-advisory')
    
    for element in advisory_elements:
        links = element.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            if href.endswith('.pdf') or '.pdf' in href.lower():
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                if href not in pdf_urls:
                    pdf_urls.append(href)
    
    return pdf_urls


def download_pdf(pdf_url, output_dir):
    """Download a PDF file"""
    try:
        parsed_url = urlparse(pdf_url)
        filename = os.path.basename(parsed_url.path)
        
        if not filename or not filename.endswith('.pdf'):
            filename = f"advisory_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        output_path = output_dir / filename
        
        if output_path.exists():
            print(f"[INFO] File already exists: {filename}")
            return output_path
        
        print(f"[INFO] Downloading: {filename}")
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[SUCCESS] Saved: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Failed to download PDF: {e}")
        return None


def extract_from_pdf(pdf_path: str) -> Dict:
    """Extract rainfall warnings from a single PDF"""
    print(f"\n{'='*70}")
    print(f"Extracting from: {Path(pdf_path).name}")
    print('='*70)
    
    extractor = RainfallAdvisoryExtractor()
    warnings = extractor.extract_rainfall_warnings(pdf_path)
    formatted = extractor.format_for_output(warnings)
    
    result = {
        'source_file': str(pdf_path),
        'rainfall_warnings': formatted
    }
    
    return result


def scrape_and_extract():
    """Scrape PDFs from live URL and extract data"""
    print("="*70)
    print("PAGASA WEATHER ADVISORY SCRAPER & EXTRACTOR")
    print("="*70)
    
    setup_output_directory()
    
    # Fetch HTML
    html_content = fetch_page_html(TARGET_URL)
    if not html_content:
        return None
    
    # Extract PDF URLs
    pdf_urls = extract_pdfs_from_advisory_elements(html_content, TARGET_URL)
    
    if not pdf_urls:
        print("[INFO] No PDFs found on the page")
        return None
    
    print(f"\n[INFO] Found {len(pdf_urls)} PDF(s)")
    
    # Download and extract from first PDF
    if pdf_urls:
        pdf_path = download_pdf(pdf_urls[0], OUTPUT_DIR)
        if pdf_path:
            return extract_from_pdf(str(pdf_path))
    
    return None


def extract_from_url(url: str) -> Dict:
    """Download and extract from PDF URL"""
    print("="*70)
    print("EXTRACTING FROM URL")
    print("="*70)
    
    setup_output_directory()
    pdf_path = download_pdf(url, OUTPUT_DIR)
    
    if pdf_path:
        return extract_from_pdf(str(pdf_path))
    return None


def extract_random_from_dataset() -> Dict:
    """Extract from random PDF in dataset"""
    print("="*70)
    print("EXTRACTING FROM RANDOM PDF")
    print("="*70)
    
    pdf_files = list(OUTPUT_DIR.glob('*.pdf'))
    
    if not pdf_files:
        print("[ERROR] No PDFs found in dataset directory")
        return None
    
    pdf_path = random.choice(pdf_files)
    return extract_from_pdf(str(pdf_path))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract rainfall warnings from PAGASA weather advisory PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python advisory_scraper.py                          # Scrape from live URL
  python advisory_scraper.py --random                 # Test random PDF from dataset
  python advisory_scraper.py "file.pdf"               # Test specific PDF (auto-detected)
  python advisory_scraper.py "http://..."             # Extract from URL (auto-detected)
        """
    )
    
    parser.add_argument('source', nargs='?', help='PDF file path or URL (auto-detected)')
    parser.add_argument('--random', action='store_true', help='Extract from random PDF in dataset')
    parser.add_argument('--json', action='store_true', help='Output only JSON (no progress messages)')
    
    args = parser.parse_args()
    
    result = None
    
    try:
        if args.random:
            # Extract from random dataset PDF
            result = extract_random_from_dataset()
        elif args.source:
            # Auto-detect if source is URL or file path
            if args.source.startswith('http://') or args.source.startswith('https://'):
                # It's a URL
                result = extract_from_url(args.source)
            else:
                # It's a file path
                result = extract_from_pdf(args.source)
        else:
            # Default: scrape from live URL
            result = scrape_and_extract()
        
        if result:
            if args.json:
                # JSON only mode
                print(json.dumps(result, indent=2))
            else:
                # Pretty output
                print("\n" + "="*70)
                print("EXTRACTION RESULTS")
                print("="*70)
                print(json.dumps(result, indent=2))
                print()
            
            return 0
        else:
            print("\n[ERROR] Extraction failed")
            return 1
            
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Extraction cancelled by user")
        sys.exit(1)
