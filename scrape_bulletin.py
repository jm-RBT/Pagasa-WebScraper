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


def clean_pdf_url(href):
    """
    Clean a PDF URL by removing wayback machine wrapper.
    
    Args:
        href: URL string
        
    Returns:
        Cleaned URL string
    """
    # Clean wayback machine URLs
    if 'web.archive.org' in href:
        # Extract the original URL from wayback machine URL
        parts = href.split('/http')
        if len(parts) > 1:
            href = 'http' + parts[-1]
    return href


def extract_pdfs_from_container(container):
    """
    Extract PDF links from a container element.
    
    Args:
        container: BeautifulSoup element
        
    Returns:
        List of PDF URLs
    """
    pdf_links = []
    links = container.find_all('a', href=True)
    for link in links:
        href = link.get('href', '')
        # href = clean_pdf_url(href)
        
        # Only include PDF links
        if href.endswith('.pdf') or '.pdf' in href:
            pdf_links.append(href)
    
    return pdf_links


def scrape_with_tabs(soup):
    """
    Try to scrape PDFs using tab-based navigation (newer format).
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of lists of PDF links, or None if tabs not found
    """
    # Find the tab navigation to identify typhoons
    tab_list = soup.find('ul', class_='nav nav-tabs')
    if not tab_list:
        return None
    
    # Get all typhoon tabs
    tabs = tab_list.find_all('li', role='presentation')
    if not tabs:
        return None
    
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
                    pdf_links = extract_pdfs_from_container(panel_body)
        
        # If no PDFs in archive section, try finding all PDFs in tab panel
        if not pdf_links:
            pdf_links = extract_pdfs_from_container(tab_panel)
        
        # Add this typhoon's PDFs to the result
        if pdf_links:
            typhoon_pdfs.append(pdf_links)
            print(f"Found {len(pdf_links)} PDF(s) for {typhoon_name}")
        else:
            print(f"Warning: No PDFs found for {typhoon_name}")
    
    return typhoon_pdfs if typhoon_pdfs else None


def scrape_without_tabs(soup):
    """
    Try to scrape PDFs without tab navigation (older format or single typhoon).
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        List of lists of PDF links, or None if no PDFs found
    """
    pdf_links = []
    
    # Strategy 1: Look for "Tropical Cyclone Bulletin Archive" section
    archive_headings = soup.find_all(string=lambda text: text and 'Tropical Cyclone Bulletin Archive' in text)
    if archive_headings:
        for heading in archive_headings:
            parent = heading.find_parent('div', class_='panel')
            if parent:
                panel_body = parent.find('div', class_='panel-body')
                if panel_body:
                    pdfs = extract_pdfs_from_container(panel_body)
                    pdf_links.extend(pdfs)
    
    # Strategy 2: Look for any list of bulletin PDFs (pattern: TCB, bulletin, etc.)
    if not pdf_links:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # href = clean_pdf_url(href)
            
            # Check if it's a bulletin PDF
            if ('.pdf' in href.lower()) and ('bulletin' in href.lower() or 'tcb' in href.lower() or 'tca' in href.lower()):
                if href not in pdf_links:
                    pdf_links.append(href)
    
    # Strategy 3: Look for any PDF links in the main content area
    if not pdf_links:
        content_area = soup.find('div', class_='article-content')
        if content_area:
            pdf_links = extract_pdfs_from_container(content_area)
    
    # Return as 2D array (single typhoon)
    if pdf_links:
        print(f"Found {len(pdf_links)} PDF(s) (no tab structure detected)")
        return [pdf_links]
    
    return None


def scrape_bulletin_from_html(html_content, base_url="https://www.pagasa.dost.gov.ph"):
    """
    Parse HTML content and extract PDF links organized by typhoon tabs.
    
    This function tries multiple strategies to extract PDFs:
    1. Tab-based navigation (newer format with multiple typhoons)
    2. Direct search for bulletin archive sections (older format)
    3. Pattern matching for bulletin PDFs (fallback)
    
    Args:
        html_content: HTML string to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        List of lists, where each sub-list contains PDF links for one typhoon
        Example: [["url1.pdf", "url2.pdf"], ["url3.pdf", "url4.pdf"]]
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Strategy 1: Try tab-based scraping (newer format)
    result = scrape_with_tabs(soup)
    if result:
        return result
    
    print("Tab-based navigation not found, trying alternative methods...")
    
    # Strategy 2: Try without tabs (older format or single typhoon)
    result = scrape_without_tabs(soup)
    if result:
        return result
    
    print("Warning: No PDF links found with any strategy")
    return []


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
