"""
Main integration module: Combines HTML/PDF extraction for PAGASA bulletins.

This module provides the main get_pagasa_data() function that Workbench calls.
It implements HTML-first extraction with PDF fallback, image extraction,
and returns data for all typhoons in the bulletin.

Usage:
    from modular import get_pagasa_data
    
    # Get data from live PAGASA URL
    result = get_pagasa_data()
    
    # Get data with image extraction (base64)
    result = get_pagasa_data(extract_image=True)
    
    # Get data with image extraction (save to temp files)
    result = get_pagasa_data(extract_image=True, save_image=True)
"""

import sys
import base64
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor

# Import from modular package
from .scrape_bulletin import scrape_bulletin
from .advisory_scraper import scrape_and_extract
from .analyze_pdf import analyze_pdf
from .html_bulletin_extractor import HTMLBulletinExtractor
from .typhoon_image_extractor import TyphoonImageExtractor


def get_number_of_typhoons(source):
    """
    Check for the number of typhoons in the HTML bulletin page.
    
    This function counts typhoon tabs and extracts their names by looking for:
    1. Tab navigation elements (ul.nav-tabs > li[role="presentation"])
    2. Tab content divs with IDs like tcwb-1, tcwb-2, etc.
    
    Args:
        source: File path or URL to HTML content
        
    Returns:
        Tuple of (count, typhoon_names_array) where:
        - count: Integer count of typhoons found
        - typhoon_names_array: List of dicts with 'full_name' and 'stripped_name' for each typhoon
        Returns (0, []) if none found
        Returns (1, []) for PDF files (name unknown)
    """
    import re
    
    # Convert to string if Path object
    source = str(source)
    
    # Load HTML content
    try:
        if source.startswith('http://') or source.startswith('https://'):
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            html_content = response.text
        else:
            filepath = Path(source)
            if filepath.suffix.lower() == '.pdf':
                # PDF files represent a single typhoon (name unknown from filename)
                return (1, [])
            if not filepath.exists():
                print(f"[WARNING] HTML file not found: {source}", file=sys.stderr)
                return (0, [])
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
    except Exception as e:
        print(f"[WARNING] Failed to load HTML: {e}", file=sys.stderr)
        return (0, [])
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Helper function to extract stripped name from full name
    def extract_stripped_name(full_name):
        """Extract stripped name from full typhoon name (same logic as html_bulletin_extractor)"""
        text_clean = full_name.strip()
        
        # Extract the name from quotes (e.g., "Dante" from 'Tropical Storm "Dante"')
        match = re.search(r'"([^"]+)"', text_clean)
        if match:
            stripped_name = match.group(1)
            # Create full name by replacing quoted name with unquoted version
            full_name_clean = text_clean.replace(f'"{stripped_name}"', stripped_name)
            # Remove any HTML tags or extra whitespace
            full_name_clean = re.sub(r'<[^>]+>', '', full_name_clean)
            full_name_clean = ' '.join(full_name_clean.split())
            return full_name_clean, stripped_name
        
        # If no quotes found, return the text as both (fallback)
        return text_clean, text_clean
    
    # Try to extract typhoon names from tabs
    tab_list = soup.find('ul', class_='nav nav-tabs')
    typhoon_names = []
    
    if tab_list:
        tabs = tab_list.find_all('li', role='presentation')
        if tabs:
            for tab in tabs:
                tab_link = tab.find('a')
                if tab_link:
                    typhoon_name = tab_link.get_text(strip=True)
                    full_name, stripped_name = extract_stripped_name(typhoon_name)
                    typhoon_names.append({
                        'full_name': full_name,
                        'stripped_name': stripped_name
                    })
            return (len(typhoon_names), typhoon_names)
    
    # Method 2: Count tab content divs with tcwb-* IDs (no names available)
    tab_content_divs = soup.find_all('div', id=re.compile(r'^tcwb-\d+$'))
    if tab_content_divs:
        return (len(tab_content_divs), [])
    
    # Method 3: Count tab-pane divs (general fallback, no names available)
    tab_panes = soup.find_all('div', class_='tab-pane')
    if tab_panes:
        return (len(tab_panes), [])
    
    # No typhoons found
    return (0, [])


def get_typhoon_names_and_pdfs(source):
    """
    Extract typhoon names and PDF links from PAGASA bulletin page.
    
    Args:
        source: File path or URL to HTML content
        
    Returns:
        List of tuples: [(typhoon_name, [pdf_urls]), ...]
        Returns 'PDF_FILE' string if source is a PDF file
    """
    # Convert to string if Path object
    source = str(source)
    
    # Load HTML content
    if source.startswith('http://') or source.startswith('https://'):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        html_content = response.text
    else:
        filepath = Path(source)
        if filepath.suffix.lower() == '.pdf':
            return 'PDF_FILE'
        if not filepath.exists():
            raise FileNotFoundError(f"HTML file not found: {source}")
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Try to extract typhoon names from tabs
    tab_list = soup.find('ul', class_='nav nav-tabs')
    typhoon_names = []
    
    if tab_list:
        tabs = tab_list.find_all('li', role='presentation')
        for tab in tabs:
            tab_link = tab.find('a')
            if tab_link:
                typhoon_name = tab_link.get_text(strip=True)
                typhoon_names.append(typhoon_name)
    
    # Get PDF links using the scraper
    pdf_links_by_typhoon = scrape_bulletin(source)
    
    # Combine names with PDF links
    result = []
    for i, pdf_links in enumerate(pdf_links_by_typhoon):
        if i < len(typhoon_names):
            name = typhoon_names[i]
        else:
            name = f"Typhoon {i+1}"
        result.append((name, pdf_links))
    
    return result


def get_latest_pdf(pdf_urls):
    """
    Select the latest PDF from a list of PDF URLs.
    
    Args:
        pdf_urls: List of PDF URLs
        
    Returns:
        Latest PDF URL, or None if list is empty
    """
    if not pdf_urls:
        return None
    return pdf_urls[-1]


def fetch_live_advisory_data():
    """
    Fetch live rainfall advisory data from PAGASA.
    Returns dict with keys: red, orange, yellow (each containing list of locations)
    Returns None if fetch fails.
    """
    try:
        result = scrape_and_extract()
        
        if result and 'rainfall_warnings' in result:
            warnings = result['rainfall_warnings']
            return warnings
        else:
            return None
    except Exception as e:
        print(f"[WARNING] Failed to fetch advisory data: {e}", file=sys.stderr)
        return None


def analyze_html_with_pdf_fallback(html_source, typhoon_index, pdf_url_or_path=None):
    """
    Analyze typhoon data with HTML as primary method and PDF as fallback.
    
    Args:
        html_source: File path or URL to HTML content
        typhoon_index: Index of typhoon tab (0-based)
        pdf_url_or_path: Optional PDF URL or path for fallback
        
    Returns:
        Dictionary of extracted data, or None on failure
    """
    # Try HTML extraction first
    try:
        extractor = HTMLBulletinExtractor()
        data = extractor.extract_from_html(html_source, typhoon_index=typhoon_index)
        
        if data:
            return data
    except Exception as e:
        print(f"[WARNING] HTML extraction failed: {e}", file=sys.stderr)
    
    # Fallback to PDF if HTML fails
    if pdf_url_or_path:
        try:
            data = analyze_pdf(pdf_url_or_path)
            if data:
                return data
        except Exception as e:
            print(f"[WARNING] PDF extraction failed: {e}", file=sys.stderr)
    
    return None


def analyze_html_and_advisory_parallel(html_source, typhoon_index, pdf_url_or_path=None):
    """
    Run HTML analysis and advisory scraping in parallel for better performance.
    
    Args:
        html_source: File path or URL to HTML content
        typhoon_index: Index of typhoon tab (0-based)
        pdf_url_or_path: Optional PDF URL or path for fallback
        
    Returns:
        Dictionary of extracted data with merged rainfall warnings, or None on failure
    """
    data = None
    advisory_data = None
    
    # Use ThreadPoolExecutor for I/O bound operations
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        data_future = executor.submit(analyze_html_with_pdf_fallback, html_source, typhoon_index, pdf_url_or_path)
        advisory_future = executor.submit(fetch_live_advisory_data)
        
        # Wait for both to complete
        data = data_future.result()
        advisory_data = advisory_future.result()
    
    # Check if data extraction succeeded
    if not data:
        print("[ERROR] Data extraction failed", file=sys.stderr)
        return None
    
    # Merge advisory data with extraction results
    if advisory_data and any(advisory_data.get(level, []) for level in ['red', 'orange', 'yellow']):
        # Add rainfall warnings from live advisory data
        data['rainfall_warning_tags1'] = advisory_data.get('red', [])
        data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
        data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
    else:
        # If advisory fetch fails or returns empty data, set empty rainfall warnings
        data['rainfall_warning_tags1'] = []
        data['rainfall_warning_tags2'] = []
        data['rainfall_warning_tags3'] = []
    
    return data


def extract_typhoon_image(source, typhoon_index, save_image=False):
    """
    Extract typhoon track image.
    
    Args:
        source: HTML source or PDF path
        typhoon_index: 0-based typhoon index
        save_image: If True, save to temp file; if False, return base64
        
    Returns:
        Tuple of (image_data, image_path) where:
        - image_data: base64 string if save_image=False, None if save_image=True
        - image_path: file path if save_image=True, None if save_image=False
        Returns (None, None) on failure
    """
    try:
        img_extractor = TyphoonImageExtractor()
        tab_index = typhoon_index + 1  # Convert to 1-based for image extractor
        
        if save_image:
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Extract and save
            result = img_extractor.extract_image(source, tab_index, temp_path)
            if result:
                return (None, temp_path)
            else:
                return (None, None)
        else:
            # Extract to stream and convert to base64
            img_stream = img_extractor.extract_image(source, tab_index)
            if img_stream:
                img_stream.seek(0)
                img_base64 = base64.b64encode(img_stream.read()).decode('utf-8')
                return (img_base64, None)
            else:
                return (None, None)
    except Exception as e:
        print(f"[WARNING] Image extraction failed: {e}", file=sys.stderr)
        return (None, None)


def get_pagasa_data(source=None, extract_image=False, save_image=False):
    """
    Main function to get PAGASA typhoon bulletin data.
    
    This is the ONLY function called by Workbench (WB).
    
    Args:
        source: Optional file path or URL to HTML content. 
                If None, uses live PAGASA URL
        extract_image: If True, extract typhoon track images
        save_image: If True (and extract_image=True), save images to temp files
                    If False (and extract_image=True), return images as base64 strings
        
    Returns:
        Dictionary with structure:
        {
            'total_typhoons': int,
            'typhoons': [
                {
                    'typhoon_name': str,
                    'pdf_url': str,
                    'data': {
                        'typhoon_name': str,
                        'typhoon_stripped_name': str,
                        'updated_datetime': str,
                        'typhoon_location_text': str,
                        'typhoon_movement': str,
                        'typhoon_windspeed': str,
                        'signal_warning_tags1': {...},
                        ...
                        'signal_warning_tags5': {...},
                        'rainfall_warning_tags1': [...],
                        'rainfall_warning_tags2': [...],
                        'rainfall_warning_tags3': [...]
                    },
                    'image_base64': str (only if extract_image=True and save_image=False),
                    'image_path': str (only if extract_image=True and save_image=True)
                },
                ...
            ]
        }
        Returns None on failure.
    """
    # Default to live PAGASA URL
    if source is None:
        source = "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
    
    try:
        # Step 1: Extract typhoon names and PDF links
        typhoons_data = get_typhoon_names_and_pdfs(source)
        
        # Check if source is a PDF file (single typhoon, PDF-only mode)
        if typhoons_data == 'PDF_FILE':
            pdf_url = source
            data = analyze_pdf(pdf_url)
            
            if not data:
                print("[ERROR] Failed to extract data from PDF", file=sys.stderr)
                return None
            
            # Fetch advisory data
            advisory_data = fetch_live_advisory_data()
            if advisory_data:
                data['rainfall_warning_tags1'] = advisory_data.get('red', [])
                data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
                data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
            else:
                data['rainfall_warning_tags1'] = []
                data['rainfall_warning_tags2'] = []
                data['rainfall_warning_tags3'] = []
            
            typhoon_name = data.get('typhoon_name', 'Typhoon')
            
            result = {
                'typhoon_name': typhoon_name,
                'pdf_url': pdf_url,
                'data': data
            }
            
            # Extract image if requested
            if extract_image:
                img_data, img_path = extract_typhoon_image(source, 0, save_image)
                if save_image and img_path:
                    result['image_path'] = img_path
                elif not save_image and img_data:
                    result['image_base64'] = img_data
            
            return {
                'total_typhoons': 1,
                'typhoons': [result]
            }
        
        # Step 2: Process HTML source with multiple typhoons
        if not typhoons_data:
            print("[ERROR] No typhoons found in the bulletin page", file=sys.stderr)
            return None
        
        all_typhoon_results = []
        
        for idx, (typhoon_name, pdf_urls) in enumerate(typhoons_data):
            latest_pdf = get_latest_pdf(pdf_urls)
            
            # Step 3: Analyze using HTML-first with PDF fallback
            # Only fetch advisory data once for the first typhoon (it's the same for all)
            if idx == 0:
                data = analyze_html_and_advisory_parallel(source, idx, latest_pdf)
            else:
                data = analyze_html_with_pdf_fallback(source, idx, latest_pdf)
                # Copy rainfall warnings from first typhoon if available
                if all_typhoon_results and data:
                    first_data = all_typhoon_results[0]['data']
                    data['rainfall_warning_tags1'] = first_data.get('rainfall_warning_tags1', [])
                    data['rainfall_warning_tags2'] = first_data.get('rainfall_warning_tags2', [])
                    data['rainfall_warning_tags3'] = first_data.get('rainfall_warning_tags3', [])
            
            if not data:
                print(f"[WARNING] Failed to extract data for {typhoon_name}, skipping...", file=sys.stderr)
                continue
            
            result = {
                'typhoon_name': typhoon_name,
                'pdf_url': latest_pdf if latest_pdf else 'N/A',
                'data': data
            }
            
            # Extract image if requested
            if extract_image:
                img_data, img_path = extract_typhoon_image(source, idx, save_image)
                if save_image and img_path:
                    result['image_path'] = img_path
                elif not save_image and img_data:
                    result['image_base64'] = img_data
            
            all_typhoon_results.append(result)
        
        if not all_typhoon_results:
            print("[ERROR] Failed to extract data from any typhoon sources", file=sys.stderr)
            return None
        
        # Step 4: Return result as JSON-ready dictionary
        output = {
            'total_typhoons': len(all_typhoon_results),
            'typhoons': all_typhoon_results
        }
        
        return output
        
    except KeyboardInterrupt:
        print("[WARNING] Process interrupted by user", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None
