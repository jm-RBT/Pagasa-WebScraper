#!/usr/bin/env python
"""
PAGASA Weather Advisory HTML Extractor

Extracts rainfall warning data from PAGASA weather advisory HTML pages.
Parses HTML DOM to extract locations affected by different rainfall warning levels.

Usage:
    python advisory_scraper.py                    # Scrape from live URL
    python advisory_scraper.py --archive          # Test with web archive URL
    python advisory_scraper.py "http://..."       # Extract from URL
    
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



# Configuration
TARGET_URL = "https://www.pagasa.dost.gov.ph/weather/weather-advisory"
WEB_ARCHIVE_URL_TEMPLATE = "https://web.archive.org/web/{timestamp}/https://www.pagasa.dost.gov.ph/weather/weather-advisory"
CONSOLIDATED_LOCATIONS_PATH = Path(__file__).parent / "bin" / "consolidated_locations.csv"

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
        # Pattern 1: starts with dash (after optional whitespace)
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
    
    def extract_rainfall_warnings(self, url: str) -> Dict:
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


def extract_from_url(url: str) -> Dict:
    """Extract rainfall warnings from HTML URL"""
    print("="*70)
    print("EXTRACTING FROM URL")
    print("="*70)
    
    extractor = RainfallAdvisoryExtractor()
    warnings = extractor.extract_rainfall_warnings(url)
    formatted = extractor.format_for_output(warnings)
    
    result = {
        'source_url': url,
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
