#!/usr/bin/env python
"""
Wayback Machine Weather Advisory PDF Scraper

Uses the Wayback Machine API to find snapshots of PAGASA weather advisory page
and extracts PDF files from elements with class "col-md-12 article-content weather-advisory".

Usage:
    python wayback_advisory_scraper.py
    python wayback_advisory_scraper.py --limit 10
    python wayback_advisory_scraper.py --year 2024
    
Downloads PDFs to: dataset/pdfs_advisory/
"""

import requests
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import argparse


# Configuration
TARGET_URL = "https://www.pagasa.dost.gov.ph/weather/weather-advisory"
WAYBACK_API_URL = "http://archive.org/wayback/available"
WAYBACK_CDX_API = "http://web.archive.org/cdx/search/cdx"
OUTPUT_DIR = Path(__file__).parent / "dataset" / "pdfs_advisory"


def setup_output_directory():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Output directory: {OUTPUT_DIR}")


def get_latest_snapshot(url):
    """
    Query Wayback Machine API for the latest snapshot of a URL.
    
    Args:
        url: Target URL to check
        
    Returns:
        Dictionary with snapshot info, or None if not available
    """
    print(f"[STEP 1] Querying Wayback Machine API for: {url}")
    
    try:
        params = {'url': url}
        response = requests.get(WAYBACK_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'archived_snapshots' in data and 'closest' in data['archived_snapshots']:
            snapshot = data['archived_snapshots']['closest']
            if snapshot.get('available'):
                print(f"[SUCCESS] Found snapshot from {snapshot.get('timestamp')}")
                print(f"[INFO] Snapshot URL: {snapshot.get('url')}")
                return snapshot
        
        print("[WARNING] No snapshots available for this URL")
        return None
        
    except requests.RequestException as e:
        print(f"[ERROR] Failed to query Wayback Machine API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse API response: {e}")
        return None


def get_all_snapshots(url, limit=None, year=None):
    """
    Query Wayback Machine CDX API for all snapshots of a URL.
    
    Args:
        url: Target URL to check
        limit: Maximum number of snapshots to retrieve
        year: Filter snapshots by year (e.g., 2024)
        
    Returns:
        List of snapshot URLs
    """
    print(f"[STEP 1] Querying Wayback Machine CDX API for all snapshots: {url}")
    
    try:
        params = {
            'url': url,
            'output': 'json',
            'fl': 'timestamp,original,statuscode,mimetype',
            'filter': 'statuscode:200',
            'collapse': 'timestamp:8'  # One snapshot per day
        }
        
        if year:
            params['from'] = f"{year}0101"
            params['to'] = f"{year}1231"
        
        if limit:
            params['limit'] = limit
        
        response = requests.get(WAYBACK_CDX_API, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # First row is header
        if len(data) <= 1:
            print("[WARNING] No snapshots found")
            return []
        
        snapshots = []
        headers = data[0]
        
        for row in data[1:]:
            snapshot_data = dict(zip(headers, row))
            timestamp = snapshot_data.get('timestamp')
            if timestamp:
                snapshot_url = f"http://web.archive.org/web/{timestamp}/{url}"
                snapshots.append({
                    'url': snapshot_url,
                    'timestamp': timestamp,
                    'original': snapshot_data.get('original'),
                    'statuscode': snapshot_data.get('statuscode')
                })
        
        print(f"[SUCCESS] Found {len(snapshots)} snapshot(s)")
        return snapshots
        
    except requests.RequestException as e:
        print(f"[ERROR] Failed to query Wayback Machine CDX API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse CDX API response: {e}")
        return []


def fetch_snapshot_html(snapshot_url):
    """
    Fetch HTML content from a Wayback Machine snapshot.
    
    Args:
        snapshot_url: URL of the archived snapshot
        
    Returns:
        HTML content as string, or None if failed
    """
    print(f"[STEP 2] Fetching snapshot HTML...")
    
    try:
        response = requests.get(snapshot_url, timeout=30)
        response.raise_for_status()
        print("[SUCCESS] Snapshot HTML retrieved")
        return response.text
        
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch snapshot: {e}")
        return None


def extract_pdfs_from_advisory_elements(html_content, base_url):
    """
    Extract PDF links from elements with class "col-md-12 article-content weather-advisory".
    
    Args:
        html_content: HTML content to parse
        base_url: Base URL for resolving relative links
        
    Returns:
        List of PDF URLs found
    """
    print("[STEP 3] Parsing HTML and extracting PDFs...")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_urls = []
    
    # Find all elements with the specified classes
    advisory_elements = soup.find_all('div', class_=lambda x: x and 'col-md-12' in x and 'article-content' in x and 'weather-advisory' in x)
    
    if not advisory_elements:
        print("[WARNING] No elements found with class 'col-md-12 article-content weather-advisory'")
        # Try alternative search strategies
        advisory_elements = soup.find_all('div', class_='article-content weather-advisory')
        if not advisory_elements:
            advisory_elements = soup.find_all('div', class_='weather-advisory')
        
        if advisory_elements:
            print(f"[INFO] Found {len(advisory_elements)} element(s) using alternative search")
    else:
        print(f"[INFO] Found {len(advisory_elements)} advisory element(s)")
    
    # Extract PDF links from found elements
    for element in advisory_elements:
        links = element.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            # Remove Wayback Machine wrapper if present
            if 'web.archive.org' in href and '/http' in href:
                parts = href.split('/http')
                if len(parts) > 1:
                    href = 'http' + parts[-1]
            
            # Check if it's a PDF link
            if href.endswith('.pdf') or '.pdf' in href.lower():
                # Resolve relative URLs
                if not href.startswith('http'):
                    href = urljoin(base_url, href)
                
                if href not in pdf_urls:
                    pdf_urls.append(href)
                    print(f"[FOUND] PDF: {href}")
    
    print(f"[SUCCESS] Found {len(pdf_urls)} PDF(s)")
    return pdf_urls


def download_pdf(pdf_url, output_dir, timestamp=None):
    """
    Download a PDF file.
    
    Args:
        pdf_url: URL of the PDF to download
        output_dir: Directory to save the PDF
        timestamp: Optional timestamp for filename
        
    Returns:
        Path to downloaded file, or None if failed
    """
    try:
        # Generate filename
        parsed_url = urlparse(pdf_url)
        filename = os.path.basename(parsed_url.path)
        
        # Clean filename
        if not filename or filename == '' or not filename.endswith('.pdf'):
            filename = f"advisory_{timestamp or datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        # Add timestamp prefix if provided
        if timestamp:
            filename = f"{timestamp}_{filename}"
        
        output_path = output_dir / filename
        
        # Check if file already exists
        if output_path.exists():
            print(f"[SKIP] File already exists: {filename}")
            return output_path
        
        # Download PDF
        print(f"[DOWNLOAD] Downloading: {filename}")
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"[SUCCESS] Saved: {output_path}")
        return output_path
        
    except requests.RequestException as e:
        print(f"[ERROR] Failed to download PDF: {e}")
        return None
    except IOError as e:
        print(f"[ERROR] Failed to save PDF: {e}")
        return None


def scrape_snapshot(snapshot_url, timestamp=None):
    """
    Scrape a single Wayback Machine snapshot for PDFs.
    
    Args:
        snapshot_url: URL of the snapshot
        timestamp: Timestamp of the snapshot
        
    Returns:
        List of downloaded file paths
    """
    print(f"\n{'='*70}")
    print(f"[SNAPSHOT] Processing: {timestamp or 'unknown'}")
    print(f"{'='*70}")
    
    # Fetch HTML
    html_content = fetch_snapshot_html(snapshot_url)
    if not html_content:
        return []
    
    # Extract PDFs
    base_url = TARGET_URL
    pdf_urls = extract_pdfs_from_advisory_elements(html_content, base_url)
    
    if not pdf_urls:
        print("[INFO] No PDFs found in this snapshot")
        return []
    
    # Download PDFs
    print(f"\n[STEP 4] Downloading {len(pdf_urls)} PDF(s)...")
    downloaded_files = []
    
    for i, pdf_url in enumerate(pdf_urls, 1):
        print(f"\n[{i}/{len(pdf_urls)}] Processing: {pdf_url}")
        
        output_path = download_pdf(pdf_url, OUTPUT_DIR, timestamp)
        if output_path:
            downloaded_files.append(output_path)
        
        # Be nice to the server
        if i < len(pdf_urls):
            time.sleep(1)
    
    return downloaded_files


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scrape weather advisory PDFs from Wayback Machine snapshots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wayback_advisory_scraper.py                    # Latest snapshot only
  python wayback_advisory_scraper.py --all              # All available snapshots
  python wayback_advisory_scraper.py --all --limit 10   # Latest 10 snapshots
  python wayback_advisory_scraper.py --all --year 2024  # All snapshots from 2024
        """
    )
    
    parser.add_argument('--all', action='store_true',
                        help='Process all available snapshots (not just latest)')
    parser.add_argument('--limit', type=int,
                        help='Maximum number of snapshots to process')
    parser.add_argument('--year', type=int,
                        help='Filter snapshots by year (e.g., 2024)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("WAYBACK MACHINE WEATHER ADVISORY PDF SCRAPER")
    print("="*70)
    print(f"Target URL: {TARGET_URL}")
    print()
    
    # Setup
    setup_output_directory()
    
    all_downloaded_files = []
    
    if args.all:
        # Get all snapshots
        snapshots = get_all_snapshots(TARGET_URL, limit=args.limit, year=args.year)
        
        if not snapshots:
            print("\n[ERROR] No snapshots found")
            return 1
        
        print(f"\n[INFO] Processing {len(snapshots)} snapshot(s)...")
        
        # Process each snapshot
        for i, snapshot in enumerate(snapshots, 1):
            print(f"\n{'='*70}")
            print(f"[PROGRESS] Snapshot {i}/{len(snapshots)}")
            print(f"{'='*70}")
            
            downloaded = scrape_snapshot(snapshot['url'], snapshot['timestamp'])
            all_downloaded_files.extend(downloaded)
            
            # Be nice to the server
            if i < len(snapshots):
                print("\n[WAIT] Pausing before next snapshot...")
                time.sleep(2)
    
    else:
        # Get latest snapshot only
        snapshot = get_latest_snapshot(TARGET_URL)
        
        if not snapshot:
            print("\n[ERROR] No snapshot available")
            return 1
        
        downloaded = scrape_snapshot(snapshot['url'], snapshot.get('timestamp'))
        all_downloaded_files.extend(downloaded)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total PDFs downloaded: {len(all_downloaded_files)}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    if all_downloaded_files:
        print("\nDownloaded files:")
        for filepath in all_downloaded_files:
            print(f"  - {filepath.name}")
    
    print("\n[COMPLETE] Scraping finished successfully")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Scraping cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
