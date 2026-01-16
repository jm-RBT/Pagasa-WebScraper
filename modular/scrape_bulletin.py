"""
Web scraper for PAGASA Severe Weather Bulletin page.
Extracts PDF links from the bulletin archive, organized by typhoon.

Returns:
    2D array where each sub-array contains PDF links for one typhoon
"""

from bs4 import BeautifulSoup
import requests
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin


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
    
    # Strategy 2: Try without tabs (older format or single typhoon)
    result = scrape_without_tabs(soup)
    if result:
        return result
    
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
        html_content = load_html_from_url(source)
    else:
        # Treat as file path
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"HTML file not found: {source}")
        html_content = load_html_from_file(filepath)
    
    # Parse and extract PDF links
    pdf_links = scrape_bulletin_from_html(html_content)
    
    return pdf_links
