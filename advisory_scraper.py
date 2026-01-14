#!/usr/bin/env python
"""
PAGASA Weather Advisory Extractor (Hybrid PDF/HTML)

Extracts rainfall warning data from PAGASA weather advisory pages.
Attempts PDF extraction first (if PDF has text), falls back to HTML DOM parsing for scanned PDFs.

Usage:
    python advisory_scraper.py                    # Scrape from live URL
    python advisory_scraper.py --archive          # Test with web archive URL
    python advisory_scraper.py "http://..."       # Extract from URL
    python advisory_scraper.py "file.pdf"         # Extract from PDF file
    
Output: JSON with rainfall warnings as lists of locations per warning level
"""

import requests
import sys
import os
import re
import json
import csv
import argparse
import html
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment
from typing import Dict, List, Optional, Set
import time
import pdfplumber
import tempfile


# Configuration
TARGET_URL = "https://www.pagasa.dost.gov.ph/weather/weather-advisory"
WEB_ARCHIVE_URL_TEMPLATE = "https://web.archive.org/web/{timestamp}/https://www.pagasa.dost.gov.ph/weather/weather-advisory"
CONSOLIDATED_LOCATIONS_PATH = Path(__file__).parent / "bin" / "consolidated_locations.csv"
# Use system temp directory for temporary PDF storage
OUTPUT_DIR = Path(tempfile.gettempdir()) / "pagasa_advisory_temp"

# Pattern matching constants
PATTERN_SEARCH_WINDOW = 50  # Characters to search backward for pattern boundaries
LOCATION_NAME_PATTERN = r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?'  # Matches single or two-word location names


class RainfallAdvisoryExtractor:
    """Extracts rainfall advisory data from PAGASA HTML pages"""
    
    def __init__(self):
        self.valid_locations = self._load_consolidated_locations()
    
    def _load_consolidated_locations(self) -> Set[str]:
        """Load valid location names from consolidated_locations.csv"""
        locations = set()
        
        if not CONSOLIDATED_LOCATIONS_PATH.exists():
            print(f"[WARNING] Consolidated locations file not found: {CONSOLIDATED_LOCATIONS_PATH}")
            return locations
        
        try:
            with open(CONSOLIDATED_LOCATIONS_PATH, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    location_name = row.get('location_name', '').strip()
                    if location_name:
                        locations.add(location_name)
            
            print(f"[INFO] Loaded {len(locations)} valid locations from CSV")
        except Exception as e:
            print(f"[WARNING] Failed to load consolidated locations: {e}")
        
        return locations
    
    def is_valid_location(self, location: str) -> bool:
        """
        Check if a location is valid using direct match or token-based validation.
        
        If the location is not found directly in the CSV, tokenize it by whitespace
        and check if any of the tokens exist in the CSV. If at least one token is
        found, consider the whole location valid.
        
        Example: "Metro Manila" is not in CSV, but "Manila" is, so "Metro Manila" is valid.
        
        Note: This token-based approach may accept some false positives (e.g., "Invalid Manila"
        would be accepted because "Manila" is in the CSV). However, this is acceptable for 
        PAGASA advisories which use standardized location naming conventions. The benefit of
        accepting legitimate multi-word locations (like "Metro Manila") outweighs the risk
        of false positives in this controlled domain.
        
        Args:
            location: Location name to validate
            
        Returns:
            True if location is valid (direct match or token match), False otherwise
        """
        if not self.valid_locations:
            # No validation data available, accept all locations
            return True
        
        # Direct match - most common case
        if location in self.valid_locations:
            return True
        
        # Token-based validation fallback
        # Split by whitespace and check if any token exists in CSV
        tokens = location.split()
        for token in tokens:
            if token in self.valid_locations:
                return True
        
        return False
    
    def parse_locations_text(self, text: str) -> List[str]:
        """
        Parse location text into individual locations.
        Handles directional modifiers, "and" connectors, and column breaks.
        Stops at double/triple whitespace or "Potential Impacts" text.
        
        Column breaks are indicated by lack of comma after "and Location".
        Example: "and Albay Kalinga" means Albay ends one column, Kalinga starts next.
        """
        if not text or text.strip() == '-' or text.strip() == '':
            return []
        
        # Directional prefixes that should be combined with following word (e.g., "Northern Samar")
        directional_prefixes = ['Northern', 'Southern', 'Eastern', 'Western', 'Central', 
                                'North', 'South', 'East', 'West', 'Greater']
        
        # Directional suffixes that should be combined with previous word (e.g., "Negros Occidental")
        directional_suffixes = ['Occidental', 'Oriental']
        
        # Replace newlines with spaces first
        text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Check for double/triple whitespace - this indicates end of locations
        # Split by multiple spaces (2+) to detect sections
        sections = re.split(r'  +', text)
        if len(sections) > 1:
            # Only use the first section before the large gap
            text = sections[0]
        
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
            
            # Check if this part contains "and Location1 Location2" pattern (column break)
            if part.lower().startswith('and '):
                AND_PREFIX = 'and '
                words = part[len(AND_PREFIX):].strip().split()  # Remove "and " and split
                
                if len(words) >= 2:
                    # Check if first word(s) form a valid location
                    # Try two-word combination first (for directional locations)
                    if words[0] in directional_prefixes and len(words) >= 2:
                        # "and Northern Samar Location2" - check if "Northern Samar" is valid
                        combined = f"{words[0]} {words[1]}"
                        if not self.valid_locations or self.is_valid_location(combined):
                            locations.append(combined)
                            # Continue with remaining words as a new section
                            if len(words) > 2:
                                remaining = ' '.join(words[2:])
                                remaining_locs = self.parse_locations_text(remaining)
                                locations.extend(remaining_locs)
                            i += 1
                            continue
                    
                    # Try single word as location
                    if not self.valid_locations or self.is_valid_location(words[0]):
                        locations.append(words[0])
                        # Continue parsing remaining words as new column
                        if len(words) > 1:
                            remaining = ' '.join(words[1:])
                            remaining_locs = self.parse_locations_text(remaining)
                            locations.extend(remaining_locs)
                        i += 1
                        continue
                    else:
                        # First word after "and" is not a valid location - stop
                        break
                
                elif len(words) == 1:
                    # Just "and Location"
                    if not self.valid_locations or self.is_valid_location(words[0]):
                        locations.append(words[0])
                    else:
                        break
                    i += 1
                    continue
            
            # Check if this part contains multiple words that might be separate locations
            words = part.split()
            
            # Filter out "and" from the beginning (shouldn't happen here but just in case)
            if words and words[0].lower() == 'and':
                words = words[1:]
            
            # If we have multiple words, check if they're a compound location or separate locations
            if len(words) > 2:
                # Try to match as a compound location first
                compound = ' '.join(words)
                if self.valid_locations and self.is_valid_location(compound):
                    locations.append(compound)
                    i += 1
                    continue
                
                # Try pairs for directional combinations
                j = 0
                added = False
                while j < len(words):
                    if j + 1 < len(words):
                        # Check directional prefix
                        if words[j] in directional_prefixes:
                            combined = f"{words[j]} {words[j+1]}"
                            if not self.valid_locations or self.is_valid_location(combined):
                                locations.append(combined)
                                j += 2
                                added = True
                                continue
                        
                        # Check directional suffix
                        if words[j+1] in directional_suffixes:
                            combined = f"{words[j]} {words[j+1]}"
                            if not self.valid_locations or self.is_valid_location(combined):
                                locations.append(combined)
                                j += 2
                                added = True
                                continue
                    
                    # Single word location
                    if self.valid_locations:
                        if self.is_valid_location(words[j]):
                            locations.append(words[j])
                            j += 1
                            added = True
                        else:
                            # Invalid location - but continue to parse rest as potential new column
                            if j < len(words) - 1:
                                remaining = ' '.join(words[j+1:])
                                remaining_locs = self.parse_locations_text(remaining)
                                locations.extend(remaining_locs)
                            return locations
                    else:
                        locations.append(words[j])
                        j += 1
                        added = True
                
                if added:
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
                    
                    # Validate location if we have the list
                    if self.valid_locations:
                        if self.is_valid_location(combined):
                            locations.append(combined)
                            i += 2
                            continue
                        else:
                            # Invalid location - stop parsing
                            break
                    else:
                        locations.append(combined)
                        i += 2
                        continue
                else:
                    # Standalone directional, keep as is (unusual but possible)
                    if not self.valid_locations or self.is_valid_location(part):
                        locations.append(part)
                    else:
                        break  # Invalid location - stop
                    i += 1
                    continue
            
            # Check if next part is a directional suffix that should be combined with current part
            if i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                if next_part in directional_suffixes:
                    # Combine current location with directional suffix
                    combined = f"{part} {next_part}"
                    
                    # Validate location
                    if self.valid_locations:
                        if self.is_valid_location(combined):
                            locations.append(combined)
                            i += 2
                            continue
                        else:
                            break  # Invalid location - stop
                    else:
                        locations.append(combined)
                        i += 2
                        continue
            
            # Regular location - validate and add it
            if self.valid_locations:
                if self.is_valid_location(part):
                    locations.append(part)
                else:
                    # Invalid location - stop parsing
                    break
            else:
                locations.append(part)
            i += 1
        
        return locations
    
    # ==================== PDF EXTRACTION METHODS ====================
    
    def extract_rainfall_tables_from_pdf(self, pdf_path: str) -> List[List[List]]:
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
                    print("[INFO] Falling back to HTML extraction")
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
    
    def extract_rainfall_warnings_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extract rainfall warnings from PDF tables
        
        Returns:
            Dict with structure:
            {
                'red': [...],
                'orange': [...],
                'yellow': [...]
            }
        """
        tables = self.extract_rainfall_tables_from_pdf(pdf_path)
        
        if not tables:
            print("[WARNING] No rainfall tables found in PDF or PDF is image-based")
            return None  # Return None to indicate PDF extraction failed
        
        print(f"[INFO] Processing {len(tables)} PDF table(s)")
        
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
                
                # Extract locations from "Today" column ONLY (2nd column, index 1)
                today_locs = self.parse_locations_text(row[1] if len(row) > 1 else '')
                
                if today_locs:
                    # Add locations directly to warning level
                    warnings[warning_level].extend(today_locs)
        
        # Remove duplicates and sort
        for level in warnings:
            warnings[level] = sorted(list(set(warnings[level])))
        
        return warnings
    
    # ==================== HTML EXTRACTION METHODS ====================

    def extract_html_text_from_url(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL or local file and extract advisory text"""
        print(f"[INFO] Fetching page from: {url}")
        
        try:
            # Check if it's a local file path
            if os.path.exists(url):
                print(f"[INFO] Reading from local file: {url}")
                with open(url, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return self.extract_advisory_text_from_html(html_content)
            
            # Otherwise, treat as URL
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            html_content = response.text
            
            return self.extract_advisory_text_from_html(html_content)
        except requests.RequestException as e:
            print(f"[ERROR] Failed to fetch page: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to read file: {e}")
            return None
    
    def extract_advisory_text_from_html(self, html_content: str) -> Optional[str]:
        """Extract rainfall advisory text from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the weekly-content-adv div
        advisory_div = soup.find('div', class_='weekly-content-adv')
        
        if not advisory_div:
            print("[WARNING] Could not find weekly-content-adv div")
            return None
        
        # Look for commented content first
        comments = advisory_div.find_all(string=lambda text: isinstance(text, Comment))
        
        for comment in comments:
            comment_text = str(comment).strip()
            # Check if this comment contains rainfall data
            if 'rainfall' in comment_text.lower() or 'mm)' in comment_text.lower():
                print("[INFO] Found rainfall data in HTML comment")
                # Decode HTML entities (e.g., &gt; to >, &nbsp; to space)
                return html.unescape(comment_text)
        
        # If no comments found, try to extract from paragraph tags
        paragraphs = advisory_div.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if 'rainfall' in text.lower() or 'mm)' in text.lower():
                print("[INFO] Found rainfall data in paragraph tag")
                return text
        
        print("[WARNING] No rainfall advisory text found in HTML")
        return None
    
    def parse_rainfall_text(self, text: str) -> Dict[str, List[str]]:
        """
        Parse rainfall advisory text to extract locations by warning level.
        
        Text format example:
        (>200 mm) Location1, Location2, Location3 (100-200 mm) Location4, ...
        
        Returns dict with keys: red, orange, yellow
        """
        warnings = self._empty_warnings()
        
        if not text:
            return warnings
        
        # Patterns for rainfall indicators
        # Red warning: MUST have '>' symbol for values greater than 200mm
        # Matches: (>200 mm), (> 200 mm), >200 mm, > 200 mm
        red_pattern = r'\(?\s*>\s*200\s*mm\s*\)?'
        # Orange warning: 100-200mm range
        # Matches: (100 - 200 mm), (100 – 200 mm), 100-200 mm
        orange_pattern = r'\(?\s*100\s*[-–]\s*200\s*mm\s*\)?'
        # Yellow warning: 50-100mm range
        # Matches: (50 - 100 mm), (50 – 100 mm), 50-100 mm
        yellow_pattern = r'\(?\s*50\s*[-–]\s*100\s*mm\s*\)?'
        
        # Find all rainfall indicators and their positions
        indicators = []
        
        for match in re.finditer(red_pattern, text, re.IGNORECASE):
            indicators.append(('red', match.end()))
        
        for match in re.finditer(orange_pattern, text, re.IGNORECASE):
            indicators.append(('orange', match.end()))
        
        for match in re.finditer(yellow_pattern, text, re.IGNORECASE):
            indicators.append(('yellow', match.end()))
        
        # Sort by position
        indicators.sort(key=lambda x: x[1])
        
        print(f"[INFO] Found {len(indicators)} rainfall indicators")
        
        # Extract locations for each indicator
        for i, (level, start_pos) in enumerate(indicators):
            # Determine end position (next indicator or end of text)
            if i + 1 < len(indicators):
                # Find the start of the next indicator pattern
                next_indicator_pos = indicators[i + 1][1]
                # Back up to the opening parenthesis of the next pattern
                search_start = max(0, next_indicator_pos - PATTERN_SEARCH_WINDOW)
                text_before_next = text[search_start:next_indicator_pos]
                opening_paren_pos = text_before_next.rfind('(')
                if opening_paren_pos >= 0:
                    end_pos = search_start + opening_paren_pos
                else:
                    end_pos = next_indicator_pos
            else:
                end_pos = len(text)
            
            # Extract text segment for this warning level
            segment = text[start_pos:end_pos].strip()
            
            # Extract only the "Today" column (first column of locations)
            # The "Today" column ends when we find "and Location" followed by 
            # another location without a comma (indicating start of "Tomorrow" column)
            today_locations = self.extract_today_column_locations(segment)
            
            # Remove duplicates and add to warnings
            unique_locations = list(dict.fromkeys(today_locations))  # Preserves order
            warnings[level].extend(unique_locations)
            
            print(f"[INFO] Extracted {len(unique_locations)} locations for {level} warning")
        
        # Final deduplication across all levels
        for level in warnings:
            warnings[level] = list(dict.fromkeys(warnings[level]))
        
        return warnings
    
    def extract_today_column_locations(self, text: str) -> List[str]:
        """
        Extract locations only from the "Today" column.
        
        The "Today" column ends when we find a location preceded by "and" followed by
        another location that starts without a comma (indicating column break).
        
        Example: "Location1, Location2, and Location3 Location4" 
                 -> Extract: Location1, Location2, Location3
                 -> Stop at: Location4 (starts Tomorrow column)
        
        If the Today column is empty (starts with "-" or double spaces), returns empty list.
        """
        if not text or text.strip() == '-' or text.strip() == '':
            return []
        
        # Check if Today column is empty BEFORE normalization
        # Pattern 1: starts with dash (may be followed by Tomorrow column content)
        # Example: "- Northern Samar" means Today is empty (dash), Tomorrow has "Northern Samar"
        if text.strip().startswith('-'):
            return []
        
        # Pattern 2: starts with double (or more) spaces - indicates empty Today column
        # Check the raw text before normalization
        if re.match(r'^\s{2,}', text):
            return []
        
        # Clean up the text
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Stop at "Potential Impacts" or similar text
        if re.search(r'potential\s+impacts', text, re.IGNORECASE):
            text = re.split(r'potential\s+impacts', text, flags=re.IGNORECASE)[0]
        
        # Find the first occurrence of column break pattern: ", and Location NextLocation"
        # where NextLocation has no comma before it (indicates start of Tomorrow column)
        # Pattern breakdown:
        #   ,\s+and\s+     - comma, spaces, "and", spaces
        #   (LOCATION)     - capture group 1: location name after "and"
        #   \s+            - spaces between columns
        #   (LOCATION)     - capture group 2: next location (Tomorrow column start)
        pattern = rf',\s+and\s+({LOCATION_NAME_PATTERN})\s+({LOCATION_NAME_PATTERN})'
        match = re.search(pattern, text)
        
        if match:
            # Found column break - extract up to (but not including) the Tomorrow column
            # match.start(2) is where the next location (Tomorrow column) starts
            end_pos = match.start(2)
            today_text = text[:end_pos].strip()
        else:
            # No clear column break found, try fallback: ", and Location" followed by dash/spaces
            # This handles cases where there's no Tomorrow column or different formatting
            simple_pattern = rf',\s+and\s+({LOCATION_NAME_PATTERN})\s*[-\s]{{2,}}'
            simple_match = re.search(simple_pattern, text)
            if simple_match:
                today_text = text[:simple_match.end(1)].strip()
            else:
                # Final fallback: split by double spaces or dash
                if '  ' in text:
                    today_text = text.split('  ')[0].strip()
                elif ' - ' in text:
                    today_text = text.split(' - ')[0].strip()
                else:
                    today_text = text.strip()
        
        # Parse the locations from the "Today" column text
        return self.parse_locations_text(today_text)
    
    def extract_rainfall_warnings_from_html(self, url: str) -> Dict:
        """
        Extract rainfall warnings from HTML URL
        
        Returns:
            Dict with structure:
            {
                'red': [...],
                'orange': [...],
                'yellow': [...]
            }
        """
        advisory_text = self.extract_html_text_from_url(url)
        
        if not advisory_text:
            print("[WARNING] No advisory text found")
            return self._empty_warnings()
        
        print(f"[INFO] Parsing advisory text ({len(advisory_text)} characters)")
        
        return self.parse_rainfall_text(advisory_text)
    
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


def download_pdf(pdf_url, output_dir):
    """Download a PDF file to temporary location"""
    try:
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Always use advisory_ prefix for temporary files
        filename = f"advisory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = output_dir / filename
        
        print(f"[INFO] Downloading PDF to temporary location: {filename}")
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[INFO] Downloaded PDF temporarily: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Failed to download PDF: {e}")
        return None


def extract_pdf_url_from_page(page_url):
    """Extract PDF URL from PAGASA weather advisory page"""
    try:
        print(f"[INFO] Fetching page to find PDF URL: {page_url}")
        response = requests.get(page_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for PDF link in iframe or direct link
        iframe = soup.find('iframe', {'id': 'blockrandom'})
        if iframe and iframe.get('src'):
            pdf_url = iframe['src']
            # Remove PDF viewer parameters
            pdf_url = re.sub(r'#.*$', '', pdf_url)
            
            # Handle web archive URLs - use urlparse to properly check domain
            from urllib.parse import urlparse as url_parse
            page_parsed = url_parse(page_url)
            pdf_parsed = url_parse(pdf_url)
            
            if page_parsed.netloc == 'web.archive.org' and pdf_parsed.netloc == 'web.archive.org':
                # Extract the actual PDF URL from web archive
                match = re.search(r'web\.archive\.org/web/\d+/(.*)', pdf_url)
                if match:
                    actual_url = match.group(1)
                    print(f"[INFO] Found PDF URL (via web archive): {actual_url}")
                    return actual_url
            
            print(f"[INFO] Found PDF URL: {pdf_url}")
            return pdf_url
        
        # Look for direct PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_links:
            pdf_url = urljoin(page_url, pdf_links[0]['href'])
            print(f"[INFO] Found PDF URL: {pdf_url}")
            return pdf_url
        
        print("[WARNING] No PDF URL found on page")
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to extract PDF URL: {e}")
        return None


def extract_from_url(url: str) -> Dict:
    """
    Extract rainfall warnings using hybrid PDF/HTML approach.
    
    Workflow:
    1. Try to extract PDF URL from page
    2. Download PDF
    3. Check if PDF has text content
    4. If PDF has text, use PDF extraction
    5. If PDF is image-based or extraction fails, fall back to HTML extraction
    """
    print("="*70)
    print("PAGASA WEATHER ADVISORY EXTRACTOR (Hybrid PDF/HTML)")
    print("="*70)
    
    extractor = RainfallAdvisoryExtractor()
    warnings = None
    source_type = None
    
    # Check if URL is a direct PDF file
    if url.lower().endswith('.pdf') and os.path.exists(url):
        # Local PDF file
        print("[INFO] Detected local PDF file")
        warnings = extractor.extract_rainfall_warnings_from_pdf(url)
        source_type = "PDF (local)"
        
        if warnings is None:
            print("[INFO] PDF extraction failed, falling back to HTML extraction")
            # Can't fall back for local PDF
            warnings = extractor._empty_warnings()
    
    elif url.lower().endswith('.pdf'):
        # URL to PDF file
        print("[INFO] Detected PDF URL")
        pdf_path = download_pdf(url, OUTPUT_DIR)
        
        if pdf_path:
            try:
                warnings = extractor.extract_rainfall_warnings_from_pdf(str(pdf_path))
                source_type = "PDF (downloaded)"
                
                if warnings is None:
                    print("[INFO] PDF is image-based, cannot fall back to HTML for direct PDF URL")
                    warnings = extractor._empty_warnings()
                    source_type = "PDF (image-based, no HTML fallback)"
            finally:
                # Clean up: delete temporary PDF file
                try:
                    pdf_path.unlink()
                    print(f"[INFO] Deleted temporary PDF: {pdf_path.name}")
                except Exception as e:
                    print(f"[WARNING] Failed to delete temporary PDF: {e}")
        else:
            warnings = extractor._empty_warnings()
            source_type = "Failed"
    
    else:
        # HTML page URL - try hybrid approach
        print("[INFO] Attempting PDF extraction from page")
        
        # Step 1: Try to extract PDF URL from page
        pdf_url = extract_pdf_url_from_page(url)
        
        if pdf_url:
            # Step 2: Download PDF
            pdf_path = download_pdf(pdf_url, OUTPUT_DIR)
            
            if pdf_path:
                try:
                    # Step 3: Try PDF extraction
                    print("[INFO] Attempting PDF extraction")
                    warnings = extractor.extract_rainfall_warnings_from_pdf(str(pdf_path))
                    
                    if warnings is not None and any(len(v) > 0 for v in warnings.values()):
                        # PDF extraction successful
                        source_type = "PDF (text-based)"
                        print(f"[SUCCESS] Extracted from PDF: {sum(len(v) for v in warnings.values())} total locations")
                    else:
                        # PDF extraction failed or returned empty results
                        print("[INFO] PDF extraction unsuccessful, falling back to HTML")
                        warnings = None
                finally:
                    # Clean up: delete temporary PDF file
                    try:
                        pdf_path.unlink()
                        print(f"[INFO] Deleted temporary PDF: {pdf_path.name}")
                    except Exception as e:
                        print(f"[WARNING] Failed to delete temporary PDF: {e}")
        
        # Step 4: Fall back to HTML extraction if PDF failed
        if warnings is None:
            print("[INFO] Using HTML extraction")
            warnings = extractor.extract_rainfall_warnings_from_html(url)
            source_type = "HTML (DOM parsing)"
    
    # Format output
    if warnings:
        formatted = extractor.format_for_output(warnings)
    else:
        formatted = extractor._empty_warnings()
    
    result = {
        'source_url': url,
        'extraction_method': source_type or "Unknown",
        'rainfall_warnings': formatted
    }
    
    return result


def scrape_and_extract():
    """Scrape and extract from live URL"""
    print("="*70)
    print("PAGASA WEATHER ADVISORY SCRAPER & EXTRACTOR")
    print("="*70)
    
    return extract_from_url(TARGET_URL)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract rainfall warnings from PAGASA weather advisory HTML pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python advisory_scraper.py                          # Scrape from live URL
  python advisory_scraper.py --archive                # Use web archive URL (with timestamp)
  python advisory_scraper.py "http://..."             # Extract from custom URL
        """
    )
    
    parser.add_argument('source', nargs='?', help='Custom URL to extract from')
    parser.add_argument('--archive', action='store_true', help='Use web archive URL with timestamp')
    parser.add_argument('--timestamp', default='20251108223833', help='Web archive timestamp (default: 20251108223833)')
    parser.add_argument('--json', action='store_true', help='Output only JSON (no progress messages)')
    
    args = parser.parse_args()
    
    result = None
    
    try:
        if args.source:
            # Extract from custom URL
            result = extract_from_url(args.source)
        elif args.archive:
            # Use web archive URL
            archive_url = WEB_ARCHIVE_URL_TEMPLATE.format(timestamp=args.timestamp)
            result = extract_from_url(archive_url)
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
