#!/usr/bin/env python
"""
PAGASA Weather Advisory PDF Extractor

Extracts rainfall warning data from PAGASA weather advisory PDFs.
Parses tables to extract locations affected by different rainfall warning levels.

Usage:
    python advisory_scraper.py                    # Scrape from live URL
    python advisory_scraper.py --random           # Test random PDF from dataset
    python advisory_scraper.py --path "file.pdf"  # Test specific PDF
    python advisory_scraper.py --url "http://..." # Extract from URL
    
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
    
    def extract_rainfall_table(self, pdf_path: str) -> Optional[List[List]]:
        """Extract rainfall forecast table from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) == 0:
                    return None
                
                # Extract tables from first page
                tables = pdf.pages[0].extract_tables()
                
                if not tables:
                    return None
                
                # Find the rainfall forecast table
                for table in tables:
                    if table and len(table) > 0:
                        # Check if this is a rainfall forecast table
                        first_row = ' '.join(str(cell or '') for cell in table[0]).lower()
                        if 'rainfall' in first_row or 'forecast' in first_row:
                            return table
                
                # If no specific table found, return first table
                return tables[0] if tables else None
                
        except Exception as e:
            print(f"[ERROR] Failed to extract table from PDF: {e}")
            return None
    
    def extract_rainfall_warnings(self, pdf_path: str) -> Dict:
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
        table = self.extract_rainfall_table(pdf_path)
        
        if not table:
            print("[WARNING] No rainfall table found in PDF")
            return self._empty_warnings()
        
        warnings = self._empty_warnings()
        
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
