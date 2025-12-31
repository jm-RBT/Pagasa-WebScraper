#!/usr/bin/env python
"""
Web scraper for PAGASA Severe Weather Bulletin page.
Extracts PDF links from the bulletin archive, organized by typhoon.

Usage: 
    python scrape_bulletin.py <html_file_path>
    python scrape_bulletin.py <url>
    python scrape_bulletin.py  # Uses default bin/PAGASA.html

Returns:
    2D array where each sub-array contains PDF links for one typhoon
"""

from bs4 import BeautifulSoup
import requests
import sys
import os
from pathlib import Path
from urllib.parse import urlparse, urljoin
import json


def scrape_bulletin_from_html(html_content, base_url="https://www.pagasa.dost.gov.ph"):
    """
    Parse HTML content and extract PDF links organized by typhoon tabs.
    
    Args:
        html_content: HTML string to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        List of lists, where each sub-list contains PDF links for one typhoon
        Example: [["url1.pdf", "url2.pdf"], ["url3.pdf", "url4.pdf"]]
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the tab navigation to identify typhoons
    tab_list = soup.find('ul', class_='nav nav-tabs')
    if not tab_list:
        print("Warning: No tab navigation found")
        return []
    
    # Get all typhoon tabs
    tabs = tab_list.find_all('li', role='presentation')
    if not tabs:
        print("Warning: No typhoon tabs found")
        return []
    
    typhoon_pdfs = []
    
    # Process each typhoon tab
    for tab in tabs:
        tab_link = tab.find('a')
        if not tab_link:
            continue
            
        # Extract typhoon name from tab text
        typhoon_name = tab_link.get_text(strip=True)
        
        # Get the tab panel ID (e.g., #tcwb-1)
        tab_href = tab_link.get('href', '')
        tab_id = tab_href.split('#')[-1] if '#' in tab_href else None
        
        if not tab_id:
            continue
        
        # Find the corresponding tab panel content
        tab_panel = soup.find('div', id=tab_id)
        if not tab_panel:
            continue
        
        # Find the "Tropical Cyclone Bulletin Archive" section
        archive_section = tab_panel.find('div', class_='panel-heading', string='Tropical Cyclone Bulletin Archive')
        if not archive_section:
            # Try alternative search
            archive_section = tab_panel.find(string='Tropical Cyclone Bulletin Archive')
        
        pdf_links = []
        
        if archive_section:
            # Get the panel body containing the PDF links
            panel = archive_section.find_parent('div', class_='panel')
            if panel:
                panel_body = panel.find('div', class_='panel-body')
                if panel_body:
                    # Extract all PDF links from the list
                    links = panel_body.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        # Clean wayback machine URLs
                        if 'web.archive.org' in href:
                            # Extract the original URL from wayback machine URL
                            parts = href.split('/http')
                            if len(parts) > 1:
                                href = 'http' + parts[-1]
                        
                        # Only include PDF links
                        if href.endswith('.pdf') or '.pdf' in href:
                            pdf_links.append(href)
        
        # Add this typhoon's PDFs to the result
        if pdf_links:
            typhoon_pdfs.append(pdf_links)
            print(f"Found {len(pdf_links)} PDF(s) for {typhoon_name}")
        else:
            print(f"Warning: No PDFs found for {typhoon_name}")
    
    return typhoon_pdfs


def load_html_from_file(filepath):
    """Load HTML content from a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def load_html_from_url(url):
    """Load HTML content from a URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def scrape_bulletin(source):
    """
    Main function to scrape bulletin from file or URL.
    
    Args:
        source: File path or URL to HTML content
        
    Returns:
        2D list of PDF links organized by typhoon
    """
    # Determine if source is URL or file
    if source.startswith('http://') or source.startswith('https://'):
        print(f"Loading HTML from URL: {source}")
        html_content = load_html_from_url(source)
    else:
        # Treat as file path
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"HTML file not found: {source}")
        print(f"Loading HTML from file: {source}")
        html_content = load_html_from_file(filepath)
    
    # Parse and extract PDF links
    print("Parsing HTML and extracting PDF links...")
    pdf_links = scrape_bulletin_from_html(html_content)
    
    return pdf_links


def main():
    """Command-line interface."""
    # Default to the provided HTML file
    default_html = Path(__file__).parent / "bin" / "PAGASA.html"
    
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        if not default_html.exists():
            print("Error: Default HTML file not found at bin/PAGASA.html")
            print(f"Usage: python {sys.argv[0]} <html_file_or_url>")
            sys.exit(1)
        source = str(default_html)
        print(f"No source provided, using default: {source}")
    
    try:
        # Scrape the bulletin
        pdf_links = scrape_bulletin(source)
        
        # Display results
        print("\n" + "="*60)
        print("EXTRACTION RESULTS")
        print("="*60)
        print(f"Total typhoons found: {len(pdf_links)}")
        print()
        
        for i, typhoon_pdfs in enumerate(pdf_links, 1):
            print(f"Typhoon {i}: {len(typhoon_pdfs)} PDF(s)")
            for j, pdf_url in enumerate(typhoon_pdfs, 1):
                print(f"  [{j}] {pdf_url}")
            print()
        
        # Output as JSON for programmatic use
        print("="*60)
        print("JSON OUTPUT")
        print("="*60)
        print(json.dumps(pdf_links, indent=2))
        
        return pdf_links
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
