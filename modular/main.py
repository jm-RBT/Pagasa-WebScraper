"""
Main script: Combines web scraping and PDF analysis for PAGASA bulletins.

This script:
1. Scrapes the PAGASA bulletin page to detect typhoons and extract PDF links
2. Selects the latest PDF for the first typhoon
3. Analyzes the latest PDF and fetches live advisory data in parallel
4. Returns the final output as a JSON object

Usage:
    from modular.main import get_pagasa_data
    
    # Get data from live PAGASA URL
    result = get_pagasa_data()
    
    # Get data from custom source
    result = get_pagasa_data(source="path/to/file.html")
    result = get_pagasa_data(source="https://example.com/bulletin")
"""

import sys
import json
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor

# Import from modular package
from .scrape_bulletin import scrape_bulletin
from .typhoon_extraction import TyphoonBulletinExtractor
from .advisory_scraper import scrape_and_extract
from .analyze_pdf import analyze_pdf


def get_typhoon_names_and_pdfs(source):
    """
    Extract typhoon names and PDF links from PAGASA bulletin page.
    
    Args:
        source: File path or URL to HTML content
        
    Returns:
        List of tuples: [(typhoon_name, [pdf_urls]), ...]
        If no names available, returns [("Unknown", [pdf_urls]), ...]
    """
    # Load HTML content
    if source.startswith('http://') or source.startswith('https://'):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        html_content = response.text
    else:
        filepath = Path(source)
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


def analyze_pdf_and_advisory_parallel(pdf_url_or_path):
    """
    Run PDF analysis and advisory scraping in parallel for better performance.
    
    Args:
        pdf_url_or_path: URL or local path to PDF file
        
    Returns:
        Dictionary of extracted data with merged rainfall warnings, or None on failure
    """
    pdf_data = None
    advisory_data = None
    
    # Use ThreadPoolExecutor for I/O bound operations
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        pdf_future = executor.submit(analyze_pdf, pdf_url_or_path)
        advisory_future = executor.submit(fetch_live_advisory_data)
        
        # Wait for both to complete
        pdf_data = pdf_future.result()
        advisory_data = advisory_future.result()
    
    # Check if PDF analysis succeeded
    if not pdf_data:
        print("[ERROR] PDF analysis failed", file=sys.stderr)
        return None
    
    # Merge advisory data with PDF extraction results
    if advisory_data and any(advisory_data.get(level, []) for level in ['red', 'orange', 'yellow']):
        # Add rainfall warnings from live advisory data
        pdf_data['rainfall_warning_tags1'] = advisory_data.get('red', [])
        pdf_data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
        pdf_data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
    else:
        # If advisory fetch fails or returns empty data, set empty rainfall warnings
        pdf_data['rainfall_warning_tags1'] = []
        pdf_data['rainfall_warning_tags2'] = []
        pdf_data['rainfall_warning_tags3'] = []
    
    return pdf_data


def get_pagasa_data(source=None):
    """
    Main function to get PAGASA typhoon bulletin data.
    
    Args:
        source: Optional file path or URL to HTML content. 
                If None, uses live PAGASA URL
        
    Returns:
        Dictionary with structure:
        {
            'typhoon_name': str,
            'pdf_url': str,
            'data': {
                # Extracted bulletin data
            }
        }
        Returns None on failure.
    """
    # Default to live PAGASA URL
    if source is None:
        source = "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"
    
    try:
        # Step 1: Extract typhoon names and PDF links
        typhoons_data = get_typhoon_names_and_pdfs(source)
        
        if not typhoons_data:
            print("[ERROR] No typhoons found in the bulletin page", file=sys.stderr)
            return None
        
        # Step 2: Select the latest PDF from the first typhoon
        typhoon_name, pdf_urls = typhoons_data[0]
        latest_pdf = get_latest_pdf(pdf_urls)
        
        if not latest_pdf:
            print(f"[ERROR] No PDFs found for {typhoon_name}", file=sys.stderr)
            return None
        
        # Step 3: Analyze the PDF and fetch advisory data in parallel
        data = analyze_pdf_and_advisory_parallel(latest_pdf)
        
        if not data:
            print("[ERROR] Failed to extract data from PDF", file=sys.stderr)
            return None
        
        # Step 4: Return result as JSON-ready dictionary
        output = {
            'typhoon_name': typhoon_name,
            'pdf_url': latest_pdf,
            'data': data
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
