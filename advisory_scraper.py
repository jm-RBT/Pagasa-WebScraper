#!/usr/bin/env python
"""
PAGASA Weather Advisory PDF Extractor

Extracts rainfall warning data from PAGASA weather advisory PDFs.
Parses tables to extract locations affected by different rainfall warning levels.
Includes OCR support for image-based PDFs.

Usage:
    python advisory_scraper.py                    # Scrape from live URL
    python advisory_scraper.py --random           # Test random PDF from dataset
    python advisory_scraper.py --path "file.pdf"  # Test specific PDF
    python advisory_scraper.py --url "http://..." # Extract from URL
    python advisory_scraper.py --ocr "file.pdf"   # Force OCR for image-based PDF
    
Output: JSON with rainfall warnings categorized by island groups
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
import pandas as pd
import time

# Optional OCR imports - EasyOCR only (pure Python, no system install needed)
OCR_AVAILABLE = False

try:
    import easyocr
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    pass


# Configuration
TARGET_URL = "https://www.pagasa.dost.gov.ph/weather/weather-advisory"
OUTPUT_DIR = Path(__file__).parent / "dataset" / "pdfs_advisory"
CONSOLIDATED_CSV = Path(__file__).parent / "bin" / "consolidated_locations.csv"


class LocationMatcher:
    """Matches location names from PDFs to Philippine administrative divisions"""
    
    REGION_MAPPING = {
        'Ilocos Region': 'Luzon',
        'Cagayan Valley': 'Luzon',
        'Central Luzon': 'Luzon',
        'CALABARZON': 'Luzon',
        'MIMAROPA': 'Luzon',
        'Bicol Region': 'Luzon',
        'Western Visayas': 'Visayas',
        'Central Visayas': 'Visayas',
        'Eastern Visayas': 'Visayas',
        'Zamboanga Peninsula': 'Mindanao',
        'Northern Mindanao': 'Mindanao',
        'Davao Region': 'Mindanao',
        'SOCCSKSARGEN': 'Mindanao',
        'Caraga': 'Mindanao',
        'Bangsamoro': 'Mindanao',
        'BARMM': 'Mindanao',
        'National Capital Region': 'Luzon',
        'NCR': 'Luzon',
        'Cordillera Administrative Region': 'Luzon',
        'CAR': 'Luzon',
    }
    
    def __init__(self, consolidated_csv_path: str = None):
        """Load consolidated locations mapping"""
        if consolidated_csv_path is None:
            consolidated_csv_path = str(CONSOLIDATED_CSV)
        
        self.locations_df = pd.read_csv(consolidated_csv_path)
        self.priority = {'Province': 5, 'Region': 4, 'City': 3, 'Municipality': 2, 'Barangay': 1}
        
        self.location_dict = {}
        self.island_groups_dict = {'Luzon': set(), 'Visayas': set(), 'Mindanao': set()}
        
        grouped = {}
        for _, row in self.locations_df.iterrows():
            name_key = row['location_name'].lower()
            priority = self.priority.get(row['location_type'], 0)
            island_group = row['island_group']
            
            if name_key not in grouped:
                grouped[name_key] = {'priority': priority, 'island_group': island_group}
            elif priority > grouped[name_key]['priority']:
                grouped[name_key] = {'priority': priority, 'island_group': island_group}
        
        for name_key, info in grouped.items():
            self.location_dict[name_key] = info['island_group']
            if info['island_group'] in self.island_groups_dict:
                self.island_groups_dict[info['island_group']].add(name_key)
    
    def find_island_group(self, location_name: str) -> Optional[str]:
        """Find which island group a location belongs to"""
        if not location_name:
            return None
        
        name_lower = location_name.lower().strip()
        
        if name_lower in self.location_dict:
            return self.location_dict[name_lower]
        
        for known_location, island_group in self.location_dict.items():
            if name_lower in known_location or known_location in name_lower:
                return island_group
        
        for region_name, island_group in self.REGION_MAPPING.items():
            if region_name.lower() == name_lower:
                return island_group
            if region_name.lower() in name_lower or name_lower in region_name.lower():
                return island_group
        
        return None


class RainfallAdvisoryExtractor:
    """Extracts rainfall advisory data from PAGASA PDFs"""
    
    def __init__(self):
        self.location_matcher = LocationMatcher()
    
    def parse_locations_text(self, text: str) -> List[str]:
        """Parse location text into individual locations"""
        if not text or text.strip() == '-' or text.strip() == '':
            return []
        
        # Split by comma and newline
        locations = re.split(r'[,\n]+', text)
        
        # Clean each location
        cleaned = []
        for loc in locations:
            loc = loc.strip()
            if loc and loc != '-':
                cleaned.append(loc)
        
        return cleaned
    
    def categorize_locations_by_island(self, locations: List[str]) -> Dict[str, List[str]]:
        """Categorize locations by island groups"""
        island_groups = {
            'Luzon': [],
            'Visayas': [],
            'Mindanao': [],
            'Other': []
        }
        
        for location in locations:
            island = self.location_matcher.find_island_group(location)
            if island and island in island_groups:
                island_groups[island].append(location)
            else:
                island_groups['Other'].append(location)
        
        return island_groups
    
    def extract_rainfall_tables(self, pdf_path: str, use_ocr: bool = False) -> List[List[List]]:
        """Extract all rainfall forecast tables from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return []
                
                # Check if PDF has extractable text
                page = pdf.pages[0]
                has_text = len(page.chars) > 0
                
                # If no text and OCR is available, try OCR
                if not has_text and OCR_AVAILABLE:
                    print("[INFO] PDF is image-based, attempting OCR extraction...")
                    return self.extract_tables_with_ocr(pdf_path)
                elif not has_text and not OCR_AVAILABLE:
                    print("[WARNING] PDF is image-based but OCR is not available")
                    print("[INFO] Install EasyOCR: pip install -r requirements-ocr-easyocr.txt")
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
    
    def extract_tables_with_ocr(self, pdf_path: str) -> List[List[List]]:
        """Extract tables using OCR for image-based PDFs"""
        if not OCR_AVAILABLE:
            print("[ERROR] OCR libraries not available")
            return []
        
        try:
            # Convert PDF to images
            print("[OCR] Using EasyOCR method...")
            print("[OCR] Converting PDF to images...")
            images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            
            if not images:
                return []
            
            # Extract text from first page using EasyOCR
            print("[OCR] Extracting text from image...")
            reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            result = reader.readtext(images[0], detail=0)
            text = '\n'.join(result)
            
            if not text.strip():
                print("[WARNING] OCR extracted no text")
                return []
            
            # Parse the OCR text into a table structure
            print("[OCR] Parsing extracted text...")
            table = self.parse_ocr_text_to_table(text)
            
            if table:
                return [table]
            
            return []
            
        except Exception as e:
            print(f"[ERROR] OCR extraction failed: {e}")
            return []
    
    def parse_ocr_text_to_table(self, text: str) -> Optional[List[List]]:
        """Parse OCR text into table structure"""
        lines = text.split('\n')
        table = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for rainfall amount patterns
            if any(pattern in line.lower() for pattern in ['>200', '> 200', '100', '200', '50', 'mm', 'rainfall', 'forecast']):
                # Try to parse as a table row
                # Split by multiple spaces or tabs
                parts = re.split(r'\s{2,}|\t+', line)
                if len(parts) >= 2:
                    table.append(parts)
        
        return table if table else None
    
    def extract_rainfall_warnings(self, pdf_path: str, use_ocr: bool = False) -> Dict:
        """
        Extract rainfall warnings from PDF
        
        Returns:
            Dict with structure:
            {
                'red': {'Luzon': [...], 'Visayas': [...], 'Mindanao': [...], 'Other': [...]},
                'orange': {...},
                'yellow': {...}
            }
        """
        tables = self.extract_rainfall_tables(pdf_path, use_ocr=use_ocr)
        
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
                    # Categorize by island groups
                    categorized = self.categorize_locations_by_island(all_locations)
                    
                    # Merge with existing warnings
                    for island, locs in categorized.items():
                        if locs:
                            warnings[warning_level][island].extend(locs)
        
        # Remove duplicates and sort
        for level in warnings:
            for island in warnings[level]:
                warnings[level][island] = sorted(list(set(warnings[level][island])))
        
        return warnings
    
    def _empty_warnings(self) -> Dict:
        """Return empty warnings structure"""
        return {
            'red': {'Luzon': [], 'Visayas': [], 'Mindanao': [], 'Other': []},
            'orange': {'Luzon': [], 'Visayas': [], 'Mindanao': [], 'Other': []},
            'yellow': {'Luzon': [], 'Visayas': [], 'Mindanao': [], 'Other': []}
        }
    
    def format_for_output(self, warnings: Dict) -> Dict:
        """Format warnings for JSON output - convert lists to comma-separated strings or null"""
        formatted = {}
        for level in warnings:
            formatted[level] = {}
            for island in warnings[level]:
                locs = warnings[level][island]
                if locs:
                    formatted[level][island] = ', '.join(locs)
                else:
                    formatted[level][island] = None
        return formatted


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


def extract_from_pdf(pdf_path: str, use_ocr: bool = False) -> Dict:
    """Extract rainfall warnings from a single PDF"""
    print(f"\n{'='*70}")
    print(f"Extracting from: {Path(pdf_path).name}")
    print('='*70)
    
    extractor = RainfallAdvisoryExtractor()
    warnings = extractor.extract_rainfall_warnings(pdf_path, use_ocr=use_ocr)
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
  python advisory_scraper.py --ocr "file.pdf"         # Use OCR for image-based PDF
        """
    )
    
    parser.add_argument('source', nargs='?', help='PDF file path or URL (auto-detected)')
    parser.add_argument('--random', action='store_true', help='Extract from random PDF in dataset')
    parser.add_argument('--ocr', action='store_true', help='Use OCR for image-based PDFs (requires easyocr+pdf2image)')
    parser.add_argument('--json', action='store_true', help='Output only JSON (no progress messages)')
    
    args = parser.parse_args()
    
    # Check OCR availability if requested
    if args.ocr and not OCR_AVAILABLE:
        print("[ERROR] OCR requested but libraries not available")
        print("\n[INFO] Install EasyOCR:")
        print("    pip install -r requirements-ocr-easyocr.txt")
        print("\nOR manually:")
        print("    pip install easyocr pdf2image")
        return 1
    
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
                result = extract_from_pdf(args.source, use_ocr=args.ocr)
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
