#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML Bulletin Extractor - Extracts typhoon data from PAGASA HTML bulletins.

Copyright (c) 2026 JMontero, Adotac
Licensed under the MIT License. See LICENSE file in the project root for details.

This module provides HTML-based extraction as the primary method for extracting
typhoon bulletin data, with PDF extraction as a fallback.
"""

import re
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from pathlib import Path
import requests
from typhoon_extraction import LocationMatcher, DateTimeExtractor


class HTMLBulletinExtractor:
    """Extracts typhoon data from PAGASA HTML bulletin pages"""
    
    def __init__(self, consolidated_csv_path: str = "bin/consolidated_locations.csv"):
        """Initialize the extractor with location matcher"""
        self.location_matcher = LocationMatcher(consolidated_csv_path)
        self.datetime_extractor = DateTimeExtractor()
    
    def extract_from_html(self, html_source: str, typhoon_index: int = 0) -> Optional[Dict]:
        """
        Extract typhoon data from HTML content.
        
        Args:
            html_source: File path or URL to HTML content
            typhoon_index: Index of typhoon tab (0-based) to extract from
            
        Returns:
            Dictionary with extracted data or None on failure
        """
        # Load HTML content
        if html_source.startswith('http://') or html_source.startswith('https://'):
            try:
                response = requests.get(html_source, timeout=30)
                response.raise_for_status()
                html_content = response.text
            except Exception as e:
                print(f"Error loading HTML from URL: {e}")
                return None
        else:
            filepath = Path(html_source)
            if not filepath.exists():
                print(f"Error: HTML file not found: {html_source}")
                return None
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all typhoon tabs
        tab_content_divs = soup.find_all('div', class_='tab-pane')
        
        if not tab_content_divs or typhoon_index >= len(tab_content_divs):
            print(f"Error: Typhoon tab {typhoon_index} not found")
            return None
        
        # Get the specific typhoon's content
        typhoon_div = tab_content_divs[typhoon_index]
        
        # Extract data
        data = {
            'typhoon_name': None,
            'updated_datetime': None,
            'typhoon_location_text': None,
            'typhoon_movement': None,
            'typhoon_windspeed': None,
            'signal_warning_tags1': {},
            'signal_warning_tags2': {},
            'signal_warning_tags3': {},
            'signal_warning_tags4': {},
            'signal_warning_tags5': {},
            'rainfall_warning_tags1': [],
            'rainfall_warning_tags2': [],
            'rainfall_warning_tags3': []
        }
        
        # Extract typhoon name from heading
        name_heading = typhoon_div.find('h3')
        if name_heading:
            data['typhoon_name'] = self._extract_typhoon_name(name_heading.get_text())
        
        # Extract issued datetime
        datetime_heading = typhoon_div.find('h5')
        if datetime_heading:
            datetime_text = datetime_heading.get_text()
            data['updated_datetime'] = self._extract_datetime(datetime_text)
        
        # Extract location, movement, and strength from panels
        panels = typhoon_div.find_all('div', class_='panel')
        for panel in panels:
            panel_heading = panel.find('div', class_='panel-heading')
            if not panel_heading:
                continue
            
            heading_text = panel_heading.get_text(strip=True)
            panel_body = panel.find('div', class_='panel-body')
            
            if not panel_body:
                continue
            
            body_text = panel_body.get_text(strip=True)
            
            if 'Location' in heading_text or 'Eye/center' in heading_text:
                data['typhoon_location_text'] = body_text
            elif 'Movement' in heading_text:
                data['typhoon_movement'] = body_text
            elif 'Strength' in heading_text:
                data['typhoon_windspeed'] = self._extract_windspeed(body_text)
        
        # Extract signal warnings from table
        signal_warnings = self._extract_signal_warnings(typhoon_div)
        for signal_level, locations in signal_warnings.items():
            data[f'signal_warning_tags{signal_level}'] = locations
        
        return data
    
    def _extract_typhoon_name(self, text: str) -> Optional[str]:
        """Extract typhoon name from heading text"""
        # Pattern: Tropical Storm "Name" or similar
        match = re.search(r'"([^"]+)"', text)
        if match:
            return match.group(1)
        return text.strip()
    
    def _extract_datetime(self, text: str) -> Optional[str]:
        """Extract and normalize datetime from text"""
        # Pattern: "Issued at HH:MM AM/PM, DD Month YYYY"
        raw_datetime = self.datetime_extractor.extract_issue_datetime(text)
        if raw_datetime:
            normalized = self.datetime_extractor.normalize_datetime(raw_datetime)
            return normalized
        return None
    
    def _extract_windspeed(self, text: str) -> Optional[str]:
        """
        Extract wind speed from strength text.
        
        Returns the wind speed value if found, otherwise returns None.
        """
        # Pattern: "Maximum sustained winds of XX km/h"
        match = re.search(r'(\d+\s*km/h)', text, re.IGNORECASE)
        if match:
            return match.group(1)
        # If no pattern matches, return None to indicate no wind speed found
        return None
    
    def _extract_signal_warnings(self, typhoon_div) -> Dict[int, Dict[str, Optional[str]]]:
        """
        Extract signal warnings from the HTML table.
        
        Signal levels are indicated by class names like 'signalno1', 'signalno2', etc.
        Affected areas are organized by island groups (Luzon, Visayas, Mindanao).
        
        Returns: {signal_level: {island_group: location_string}}
        """
        result = {}
        for level in range(1, 6):
            result[level] = {
                'Luzon': None,
                'Visayas': None,
                'Mindanao': None,
                'Other': None
            }
        
        # Check for "No signal" message in panel body
        wind_signal_panel = typhoon_div.find('div', class_='panel-heading', string=re.compile('Wind Signal', re.IGNORECASE))
        if wind_signal_panel:
            # Check if there's a panel-body (no table present, just text)
            parent_panel = wind_signal_panel.find_parent('div', class_='panel')
            if parent_panel:
                panel_body = parent_panel.find('div', class_='panel-body')
                if panel_body:
                    body_text = panel_body.get_text(strip=True).lower()
                    if 'no' in body_text and 'signal' in body_text:
                        return result
        
        # Find all tables in the typhoon div
        tables = typhoon_div.find_all('table')
        
        for table in tables:
            # Find signal level headers with class like "signalno1", "signalno2", etc.
            signal_headers = table.find_all('th', class_=re.compile(r'signalno\d'))
            
            for signal_header in signal_headers:
                # Extract signal number from class
                class_list = signal_header.get('class', [])
                signal_level = None
                
                for cls in class_list:
                    match = re.match(r'signalno(\d)', cls)
                    if match:
                        signal_level = int(match.group(1))
                        break
                
                if not signal_level or signal_level not in range(1, 6):
                    continue
                
                # Find the tbody that follows this signal header
                parent_thead = signal_header.find_parent('thead')
                if not parent_thead:
                    continue
                
                # Get the next tbody after this thead
                tbody = parent_thead.find_next_sibling('tbody')
                if not tbody:
                    continue
                
                # Look for the affected areas row in this tbody
                rows = tbody.find_all('tr', recursive=False)
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        first_cell_text = cells[0].get_text(strip=True).lower()
                        if 'affected areas' in first_cell_text:
                            # Found the affected areas row
                            locations_cell = cells[1]
                            self._parse_affected_areas(locations_cell, result[signal_level])
                            break
        
        return result
    
    def _parse_affected_areas(self, locations_cell, island_dict: Dict[str, Optional[str]]):
        """
        Parse affected areas cell and organize by island groupings.
        
        Note: This method modifies the island_dict parameter in place.
        
        Args:
            locations_cell: BeautifulSoup element containing the locations
            island_dict: Dictionary to populate with island group locations (modified in place)
        
        The structure is typically:
        <ul>
            <li><strong>Luzon</strong>
                <ul>
                    <li>Location details</li>
                </ul>
            </li>
            <li><strong>Visayas</strong>
                <ul>
                    <li>Location details</li>
                </ul>
            </li>
        </ul>
        """
        # Find all list items with island group headers
        list_items = locations_cell.find_all('li', recursive=True)
        
        current_island = None
        
        for li in list_items:
            # Check if this li contains an island group name
            strong_tag = li.find('strong', recursive=False)
            
            if strong_tag:
                # This is an island group header
                island_text = strong_tag.get_text(strip=True)
                
                if 'Luzon' in island_text:
                    current_island = 'Luzon'
                elif 'Visayas' in island_text:
                    current_island = 'Visayas'
                elif 'Mindanao' in island_text:
                    current_island = 'Mindanao'
                else:
                    current_island = 'Other'
                
                # Find nested ul with locations
                nested_ul = li.find('ul')
                if nested_ul and current_island:
                    # Get all nested li elements
                    location_items = nested_ul.find_all('li', recursive=False)
                    location_texts = [loc.get_text(strip=True) for loc in location_items]
                    
                    if location_texts:
                        # Join all location texts with commas
                        island_dict[current_island] = ', '.join(location_texts)
    
    def extract_all_typhoons(self, html_source: str) -> List[Dict]:
        """
        Extract data for all typhoons in the HTML page.
        
        Args:
            html_source: File path or URL to HTML content
            
        Returns:
            List of dictionaries with extracted data
        """
        # Load HTML content
        if html_source.startswith('http://') or html_source.startswith('https://'):
            try:
                response = requests.get(html_source, timeout=30)
                response.raise_for_status()
                html_content = response.text
            except Exception as e:
                print(f"Error loading HTML from URL: {e}")
                return []
        else:
            filepath = Path(html_source)
            if not filepath.exists():
                print(f"Error: HTML file not found: {html_source}")
                return []
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find typhoon names from tabs
        tab_list = soup.find('ul', class_='nav nav-tabs')
        typhoon_names = []
        
        if tab_list:
            tabs = tab_list.find_all('li', role='presentation')
            for tab in tabs:
                tab_link = tab.find('a')
                if tab_link:
                    typhoon_name = tab_link.get_text(strip=True)
                    typhoon_names.append(typhoon_name)
        
        # Extract data for each typhoon
        results = []
        for idx in range(len(typhoon_names)):
            data = self.extract_from_html(html_source, typhoon_index=idx)
            if data:
                # Ensure typhoon name is set from tab if not in heading
                if not data['typhoon_name'] and idx < len(typhoon_names):
                    data['typhoon_name'] = typhoon_names[idx]
                results.append(data)
        
        return results


def main():
    """Test the HTML extractor"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python html_bulletin_extractor.py <html_file_or_url>")
        print("Example: python html_bulletin_extractor.py 'bin/PAGASA BULLETIN PAGE/PAGASA.html'")
        sys.exit(1)
    
    html_source = sys.argv[1]
    
    extractor = HTMLBulletinExtractor()
    typhoons_data = extractor.extract_all_typhoons(html_source)
    
    if not typhoons_data:
        print("No typhoon data extracted")
        sys.exit(1)
    
    # Display results
    import json
    print(json.dumps({'typhoons': typhoons_data}, indent=2))


if __name__ == "__main__":
    main()
