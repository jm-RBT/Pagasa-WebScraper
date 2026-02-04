#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Main script: Combines web scraping and HTML/PDF analysis for PAGASA bulletins.

Copyright (c) 2026 JMontero, Adotac
Licensed under the MIT License. See LICENSE file in the project root for details.

This script:
1. Uses scrape_bulletin.py to detect typhoon names and extract PDF links
2. Extracts typhoon data from HTML content (primary method)
3. Falls back to PDF analysis if HTML extraction fails
4. Returns data for ALL typhoons found in the bulletin page

By default, outputs raw JSON data to stdout (for easy piping/parsing).
Use --verbose flag to see progress messages (sent to stderr).

Usage:
    python main.py                      # Uses default bin/PAGASA.html, outputs JSON for all typhoons
    python main.py <html_file_path>     # Uses specified HTML file, outputs JSON for all typhoons
    python main.py <url>                # Scrapes from URL, outputs JSON for all typhoons
    python main.py --help               # Show help message

Options:
    --verbose                           # Show progress messages (to stderr)
    --low-cpu                           # Limit CPU usage to ~30%
    --metrics                           # Show performance metrics (to stderr)
    --extract-image                     # Extract typhoon track images (requires --stream or --save-image)
    --stream                            # Return images as base64 stream with JSON (use with --extract-image)
    --save-image                        # Save images to files (use with --extract-image)

Examples:
    python main.py                                      # Pure JSON output for all typhoons
    python main.py --verbose                            # JSON + progress messages
    python main.py > output.json                        # Save JSON to file
    python main.py --verbose 2>/dev/null                # JSON only (suppress logs)
    python main.py | jq '.typhoons[0].data.typhoon_windspeed'  # Parse with jq
    python main.py --extract-image --stream             # Extract images as base64 streams
    python main.py --extract-image --save-image         # Extract and save images to files
"""

import sys
import json
import time
import psutil
import os
from pathlib import Path
from scrape_bulletin import scrape_bulletin
from typhoon_extraction import TyphoonBulletinExtractor
from typhoon_image_extractor import TyphoonImageExtractor
from html_bulletin_extractor import HTMLBulletinExtractor
import requests
import tempfile
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from contextlib import contextmanager
from advisory_scraper import scrape_and_extract
from concurrent.futures import ThreadPoolExecutor
import base64


@contextmanager
def suppress_stdout():
    """Context manager to suppress stdout output."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def get_typhoon_names_and_pdfs(source, verbose=False):
    """
    Extract typhoon names and PDF links from PAGASA bulletin page.
    
    This function extends the scrape_bulletin functionality to also
    capture typhoon names from the HTML tabs.
    
    Args:
        source: File path or URL to HTML content
        verbose: If True, show loading messages
        
    Returns:
        List of tuples: [(typhoon_name, [pdf_urls]), ...]
        If no names available, returns [("Unknown", [pdf_urls]), ...]
    """
    # Load HTML content
    if source.startswith('http://') or source.startswith('https://'):
        if verbose:
            print(f"Loading HTML from URL: {source}", file=sys.stderr)
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        html_content = response.text
    else:
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"HTML file not found: {source}")
        if verbose:
            print(f"Loading HTML from file: {source}", file=sys.stderr)
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
    
    # Get PDF links using the existing scraper (suppress its output if not verbose)
    if verbose:
        pdf_links_by_typhoon = scrape_bulletin(source)
    else:
        with suppress_stdout():
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
    
    Assumes PDFs are ordered chronologically, with the latest last.
    
    Args:
        pdf_urls: List of PDF URLs
        
    Returns:
        Latest PDF URL, or None if list is empty
    """
    if not pdf_urls:
        return None
    return pdf_urls[-1]


def fetch_live_advisory_data(verbose=False):
    """
    Fetch live rainfall advisory data from PAGASA.
    Returns dict with keys: red, orange, yellow (each containing list of locations)
    Returns None if fetch fails.
    """
    try:
        if verbose:
            print("[INFO] Fetching live rainfall advisory from PAGASA...", file=sys.stderr)
        
        # Suppress advisory_scraper output when not verbose
        if not verbose:
            # Redirect stdout to devnull to suppress advisory_scraper prints
            import os
            old_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            try:
                result = scrape_and_extract()
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
        else:
            result = scrape_and_extract()
        
        if result and 'rainfall_warnings' in result:
            warnings = result['rainfall_warnings']
            if verbose:
                print(f"[INFO] Successfully fetched advisory data:", file=sys.stderr)
                print(f"  - Red warnings: {len(warnings.get('red', []))} locations", file=sys.stderr)
                print(f"  - Orange warnings: {len(warnings.get('orange', []))} locations", file=sys.stderr)
                print(f"  - Yellow warnings: {len(warnings.get('yellow', []))} locations", file=sys.stderr)
            return warnings
        else:
            if verbose:
                print("[WARNING] Advisory data fetch returned no warnings", file=sys.stderr)
            return None
    except Exception as e:
        if verbose:
            print(f"[WARNING] Failed to fetch advisory data: {e}", file=sys.stderr)
        return None





def analyze_html_with_pdf_fallback(html_source, typhoon_index, pdf_url_or_path=None, low_cpu_mode=False, verbose=False):
    """
    Analyze typhoon data with HTML as primary method and PDF as fallback.
    
    Args:
        html_source: File path or URL to HTML content
        typhoon_index: Index of typhoon tab (0-based)
        pdf_url_or_path: Optional PDF URL or path for fallback
        low_cpu_mode: Whether to limit CPU usage
        verbose: Whether to show progress
        
    Returns:
        Dictionary of extracted data, or None on failure
    """
    # Try HTML extraction first
    if verbose:
        print(f"  Attempting HTML extraction...", file=sys.stderr)
    
    try:
        extractor = HTMLBulletinExtractor()
        data = extractor.extract_from_html(html_source, typhoon_index=typhoon_index)
        
        if data:
            if verbose:
                print(f"  Successfully extracted data from HTML", file=sys.stderr)
            return data
        else:
            if verbose:
                print(f"  HTML extraction returned no data", file=sys.stderr)
    except Exception as e:
        if verbose:
            print(f"  HTML extraction failed: {e}", file=sys.stderr)
    
    # Fallback to PDF extraction if HTML fails or PDF is provided
    if pdf_url_or_path:
        if verbose:
            print(f"  Falling back to PDF extraction...", file=sys.stderr)
        return analyze_pdf(pdf_url_or_path, low_cpu_mode=low_cpu_mode, verbose=verbose)
    else:
        if verbose:
            print(f"  No PDF provided for fallback", file=sys.stderr)
        return None


def analyze_html_and_advisory_parallel(html_source, typhoon_index, pdf_url_or_path=None, low_cpu_mode=False, verbose=False):
    """
    Run HTML/PDF analysis and advisory scraping in parallel for better performance.
    
    Args:
        html_source: File path or URL to HTML content
        typhoon_index: Index of typhoon tab (0-based)
        pdf_url_or_path: Optional PDF URL or path for fallback
        low_cpu_mode: Whether to limit CPU usage
        verbose: Whether to show progress
        
    Returns:
        Dictionary of extracted data with merged rainfall warnings, or None on failure
    """
    if verbose:
        print("[INFO] Starting parallel execution of HTML/PDF analysis and advisory scraping...", file=sys.stderr)
    
    html_data = None
    advisory_data = None
    
    # Use ThreadPoolExecutor for I/O bound operations
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        html_future = executor.submit(analyze_html_with_pdf_fallback, html_source, typhoon_index, pdf_url_or_path, low_cpu_mode, verbose)
        advisory_future = executor.submit(fetch_live_advisory_data, verbose)
        
        # Wait for both to complete (blocks until both are done)
        html_data = html_future.result()
        advisory_data = advisory_future.result()
        
        if verbose:
            print("[INFO] Both tasks completed", file=sys.stderr)
    
    # Check if HTML/PDF analysis succeeded
    if not html_data:
        if verbose:
            print("[ERROR] HTML/PDF analysis failed", file=sys.stderr)
        return None
    
    # Merge advisory data with extraction results
    if advisory_data and any(advisory_data.get(level, []) for level in ['red', 'orange', 'yellow']):
        # Add rainfall warnings from live advisory data
        # Map: red -> rainfall_warning_tags1, orange -> rainfall_warning_tags2, yellow -> rainfall_warning_tags3
        html_data['rainfall_warning_tags1'] = advisory_data.get('red', [])
        html_data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
        html_data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
        if verbose:
            print("[INFO] Added live advisory data to extraction", file=sys.stderr)
    else:
        # If advisory fetch fails or returns empty data, set empty rainfall warnings
        if verbose:
            print("[INFO] No advisory data available, rainfall warnings will be empty", file=sys.stderr)
        html_data['rainfall_warning_tags1'] = []
        html_data['rainfall_warning_tags2'] = []
        html_data['rainfall_warning_tags3'] = []
    
    return html_data


def analyze_pdf(pdf_url_or_path, low_cpu_mode=False, verbose=False):
    """
    Analyze a PDF using the TyphoonBulletinExtractor.
    
    Args:
        pdf_url_or_path: URL or local path to PDF file
        low_cpu_mode: Whether to limit CPU usage
        verbose: Whether to show download progress
        
    Returns:
        Dictionary of extracted data, or None on failure
    """
    # Download PDF if it's a URL (TyphoonBulletinExtractor requires local files)
    temp_file = None
    pdf_path = pdf_url_or_path
    
    if pdf_url_or_path.startswith('http://') or pdf_url_or_path.startswith('https://'):
        if verbose:
            print(f"  Downloading PDF from: {pdf_url_or_path}", file=sys.stderr)
        try:
            response = requests.get(pdf_url_or_path, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                temp_file = tmp.name
                pdf_path = temp_file
            
            if verbose:
                print(f"  Saved to temporary file: {temp_file}", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"  Error downloading PDF: {e}", file=sys.stderr)
            return None
    else:
        # Verify local file exists
        if not Path(pdf_url_or_path).exists():
            if verbose:
                print(f"  Error: Local file not found: {pdf_url_or_path}", file=sys.stderr)
            return None
    
    # Analyze the PDF
    extractor = TyphoonBulletinExtractor()
    process = psutil.Process(os.getpid())
    
    try:
        # Apply continuous CPU throttling if enabled
        if low_cpu_mode:
            from analyze_pdf import continuous_cpu_throttle
            with continuous_cpu_throttle(process, target_cpu_percent=30):
                data = extractor.extract_from_pdf(pdf_path)
        else:
            data = extractor.extract_from_pdf(pdf_path)
        
        return data
    except Exception as e:
        if verbose:
            print(f"  Error analyzing PDF: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        return None
    finally:
        del extractor
        # Clean up temporary file if we created one
        if temp_file:
            try:
                Path(temp_file).unlink()
                if verbose:
                    print(f"  Cleaned up temporary file: {temp_file}", file=sys.stderr)
            except Exception as e:
                if verbose:
                    print(f"  Warning: Could not delete temp file: {e}", file=sys.stderr)


def analyze_pdf_and_advisory_parallel(pdf_url_or_path, low_cpu_mode=False, verbose=False):
    """
    Run PDF analysis and advisory scraping in parallel for better performance.
    
    Args:
        pdf_url_or_path: URL or local path to PDF file
        low_cpu_mode: Whether to limit CPU usage
        verbose: Whether to show progress
        
    Returns:
        Dictionary of extracted data with merged rainfall warnings, or None on failure
    """
    if verbose:
        print("[INFO] Starting parallel execution of PDF analysis and advisory scraping...", file=sys.stderr)
    
    pdf_data = None
    advisory_data = None
    
    # Use ThreadPoolExecutor for I/O bound operations
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        pdf_future = executor.submit(analyze_pdf, pdf_url_or_path, low_cpu_mode, verbose)
        advisory_future = executor.submit(fetch_live_advisory_data, verbose)
        
        # Wait for both to complete (blocks until both are done)
        pdf_data = pdf_future.result()
        advisory_data = advisory_future.result()
        
        if verbose:
            print("[INFO] Both tasks completed", file=sys.stderr)
    
    # Check if PDF analysis succeeded
    if not pdf_data:
        if verbose:
            print("[ERROR] PDF analysis failed", file=sys.stderr)
        return None
    
    # Merge advisory data with PDF extraction results
    if advisory_data and any(advisory_data.get(level, []) for level in ['red', 'orange', 'yellow']):
        # Add rainfall warnings from live advisory data
        # Map: red -> rainfall_warning_tags1, orange -> rainfall_warning_tags2, yellow -> rainfall_warning_tags3
        pdf_data['rainfall_warning_tags1'] = advisory_data.get('red', [])
        pdf_data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
        pdf_data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
        if verbose:
            print("[INFO] Added live advisory data to PDF extraction", file=sys.stderr)
    else:
        # If advisory fetch fails or returns empty data, set empty rainfall warnings
        if verbose:
            print("[INFO] No advisory data available, rainfall warnings will be empty", file=sys.stderr)
        pdf_data['rainfall_warning_tags1'] = []
        pdf_data['rainfall_warning_tags2'] = []
        pdf_data['rainfall_warning_tags3'] = []
    
    return pdf_data


def display_results(typhoon_name, data):
    """Display extraction results in a readable format."""
    print("\n" + "=" * 80)
    print(f"PAGASA BULLETIN ANALYSIS - {typhoon_name}")
    print("=" * 80)
    
    # Basic Info
    print("\n[BASIC INFORMATION]")
    print(f"  Issued:       {data.get('updated_datetime', 'N/A')}")
    print(f"  Location:     {data.get('typhoon_location_text', 'N/A')}")
    print(f"  Wind Speed:   {data.get('typhoon_windspeed', 'N/A')}")
    print(f"  Movement:     {data.get('typhoon_movement', 'N/A')}")
    
    # Signal Warnings
    print("\n[SIGNAL WARNINGS (TCWS)]")
    signal_found = False
    for level in range(1, 6):
        tag_key = f'signal_warning_tags{level}'
        tag = data.get(tag_key, {})
        
        # Check if any island group has locations
        has_locations = any(tag.get(ig) for ig in ['Luzon', 'Visayas', 'Mindanao', 'Other'])
        
        if has_locations:
            signal_found = True
            print(f"\n  Signal {level}:")
            for island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                locations = tag.get(island_group)
                if locations:
                    print(f"    {island_group:12} -> {locations}")
    
    if not signal_found:
        print("  [OK] No tropical cyclone wind signals in effect")
    
    # Rainfall Warnings
    print("\n[RAINFALL WARNINGS]")
    rainfall_found = False
    
    rainfall_levels = {
        1: "Red Warning - Intense Rainfall (>200mm/24hr)",
        2: "Orange Warning - Heavy Rainfall (100-200mm/24hr)",
        3: "Yellow Warning - Moderate Rainfall (50-100mm/24hr)"
    }
    
    for level in range(1, 4):
        tag_key = f'rainfall_warning_tags{level}'
        locations = data.get(tag_key, [])
        
        # Check if there are any locations (new format is a list)
        if locations and len(locations) > 0:
            rainfall_found = True
            print(f"\n  {rainfall_levels[level]}:")
            print(f"    Locations: {', '.join(locations)}")
        else:
            print(f"\n  {rainfall_levels[level]}: No warnings")
    
    if not rainfall_found:
        print("  [OK] No rainfall warnings issued")
    
    print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point."""
    # Parse arguments
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    low_cpu_mode = '--low-cpu' in sys.argv
    show_metrics = '--metrics' in sys.argv
    verbose = '--verbose' in sys.argv
    extract_image = '--extract-image' in sys.argv
    stream_image = '--stream' in sys.argv
    save_image_flag = '--save-image' in sys.argv
    
    # Validate image extraction flags
    if extract_image and not (stream_image or save_image_flag):
        if verbose:
            print("Error: --extract-image requires either --stream or --save-image", file=sys.stderr)
        sys.exit(1)
    
    if extract_image and stream_image and save_image_flag:
        if verbose:
            print("Error: Cannot use both --stream and --save-image", file=sys.stderr)
        sys.exit(1)
    
    # Filter out flags to get source
    args = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    
    # Determine source
    if args:
        source = args[0]
    else:
        default_html = Path(__file__).parent / "bin" / "PAGASA BULLETIN PAGE" / "PAGASA.html"
        if not default_html.exists():
            # Try old path for backward compatibility
            default_html = Path(__file__).parent / "bin" / "PAGASA.html"
        if not default_html.exists():
            if verbose:
                print("Error: Default HTML file not found at bin/PAGASA.html", file=sys.stderr)
                print(f"Usage: python {sys.argv[0]} <html_file_or_url>", file=sys.stderr)
            sys.exit(1)
        source = str(default_html)
        if verbose:
            print(f"No source provided, using default: {source}", file=sys.stderr)
    
    start_time = time.time()
    process = psutil.Process(os.getpid())
    process.cpu_percent(interval=None)  # Initialize CPU monitoring
    time.sleep(0.1)
    
    if low_cpu_mode and verbose:
        print("[*] Low CPU mode enabled - limiting to ~30% CPU usage\n", file=sys.stderr)
    
    try:
        # Step 1: Extract typhoon names and PDF links
        if verbose:
            print("\n[STEP 1] Scraping PAGASA bulletin page...", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
        typhoons_data = get_typhoon_names_and_pdfs(source, verbose=verbose)
        
        if not typhoons_data:
            if verbose:
                print("Error: No typhoons found in the bulletin page.", file=sys.stderr)
            sys.exit(1)
        
        if verbose:
            print(f"\nFound {len(typhoons_data)} typhoon(s):", file=sys.stderr)
            for name, pdfs in typhoons_data:
                print(f"  - {name}: {len(pdfs)} bulletin(s)", file=sys.stderr)
        
        # Step 2: Process all typhoons
        if verbose:
            print("\n[STEP 2] Processing all typhoons...", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
        
        all_typhoon_results = []
        
        for idx, (typhoon_name, pdf_urls) in enumerate(typhoons_data, 1):
            if verbose:
                print(f"\n  Processing Typhoon {idx}/{len(typhoons_data)}: {typhoon_name}", file=sys.stderr)
            
            latest_pdf = get_latest_pdf(pdf_urls)
            
            if verbose:
                if latest_pdf:
                    print(f"    Latest bulletin: {latest_pdf}", file=sys.stderr)
                else:
                    print(f"    No PDF available, using HTML extraction only", file=sys.stderr)
            
            # Step 3: Analyze using HTML first, then PDF as fallback
            # (fetch advisory data in parallel only for first typhoon)
            if verbose:
                print(f"    Analyzing HTML (with PDF fallback){' and fetching advisory data' if idx == 1 else ''}...", file=sys.stderr)
            
            # Only fetch advisory data once for the first typhoon (it's the same for all typhoons)
            if idx == 1:
                data = analyze_html_and_advisory_parallel(
                    source, 
                    typhoon_index=idx-1,  # 0-based index
                    pdf_url_or_path=latest_pdf, 
                    low_cpu_mode=low_cpu_mode, 
                    verbose=verbose
                )
            else:
                data = analyze_html_with_pdf_fallback(
                    source, 
                    typhoon_index=idx-1,  # 0-based index
                    pdf_url_or_path=latest_pdf, 
                    low_cpu_mode=low_cpu_mode, 
                    verbose=verbose
                )
                # Copy rainfall warnings from first typhoon if available
                if all_typhoon_results and data:
                    first_data = all_typhoon_results[0]['data']
                    data['rainfall_warning_tags1'] = first_data.get('rainfall_warning_tags1', [])
                    data['rainfall_warning_tags2'] = first_data.get('rainfall_warning_tags2', [])
                    data['rainfall_warning_tags3'] = first_data.get('rainfall_warning_tags3', [])
            
            if not data:
                if verbose:
                    print(f"    Warning: Failed to extract data for {typhoon_name}, skipping...", file=sys.stderr)
                continue
            
            if verbose:
                print(f"    Successfully extracted data for {typhoon_name}", file=sys.stderr)
            
            all_typhoon_results.append({
                'typhoon_name': typhoon_name,
                'pdf_url': latest_pdf if latest_pdf else 'N/A',
                'data': data
            })
        
        if not all_typhoon_results:
            if verbose:
                print("\nError: Failed to extract data from any typhoon sources", file=sys.stderr)
            sys.exit(1)
        
        # Step 4: Extract images if requested
        if extract_image:
            if verbose:
                print("\n[STEP 4] Extracting typhoon track images...", file=sys.stderr)
                print("-" * 80, file=sys.stderr)
            
            img_extractor = TyphoonImageExtractor()
            
            for idx, typhoon_result in enumerate(all_typhoon_results, 1):
                typhoon_name = typhoon_result['typhoon_name']
                latest_pdf = typhoon_result['pdf_url']
                data = typhoon_result['data']
                
                if verbose:
                    print(f"\n  Extracting image for Typhoon {idx}/{len(all_typhoon_results)}: {typhoon_name}", file=sys.stderr)
                
                # Determine the tab index (1-based indexing)
                tab_index = idx
                
                img_stream = None
                img_path = None
                
                if save_image_flag:
                    # Generate filename based on typhoon name and datetime
                    safe_typhoon_name = typhoon_name.replace(' ', '_').replace('"', '')
                    datetime_str = data.get('updated_datetime', '').replace(':', '-').replace(' ', '_')
                    if not datetime_str:
                        datetime_str = time.strftime('%Y%m%d_%H%M%S')
                    img_filename = f"typhoon_track_{safe_typhoon_name}_{datetime_str}.png"
                    img_path = str(Path.cwd() / img_filename)
                    
                    # Try to extract from HTML first, fallback to PDF
                    if source.startswith('http') or Path(source).suffix.lower() in ['.html', '.htm']:
                        result = img_extractor.extract_image(source, tab_index, img_path)
                    else:
                        # If source is not HTML, extract from PDF
                        result = img_extractor.extract_image(latest_pdf, tab_index, img_path)
                    
                    if result:
                        img_stream, img_path = result
                        typhoon_result['image_path'] = img_path
                        if verbose:
                            print(f"    Image saved to: {img_path}", file=sys.stderr)
                            print(f"    Image size: {len(img_stream.getvalue())} bytes", file=sys.stderr)
                    else:
                        if verbose:
                            print(f"    Failed to extract image", file=sys.stderr)
                else:
                    # Stream mode
                    # Try to extract from HTML first, fallback to PDF
                    if source.startswith('http') or Path(source).suffix.lower() in ['.html', '.htm']:
                        img_stream = img_extractor.extract_image(source, tab_index)
                    else:
                        # If source is not HTML, extract from PDF
                        img_stream = img_extractor.extract_image(latest_pdf, tab_index)
                    
                    if img_stream:
                        typhoon_result['image_stream'] = base64.b64encode(img_stream.getvalue()).decode('utf-8')
                        if verbose:
                            print(f"    Image extracted to memory stream", file=sys.stderr)
                            print(f"    Image size: {len(img_stream.getvalue())} bytes", file=sys.stderr)
                    else:
                        if verbose:
                            print(f"    Failed to extract image", file=sys.stderr)
        
        # Step 5: Display results - always output JSON by default
        output = {
            'total_typhoons': len(all_typhoon_results),
            'typhoons': all_typhoon_results
        }
        
        # Output the results
        print(json.dumps(output, indent=2))
        
        # Performance metrics
        elapsed = time.time() - start_time
        
        if show_metrics:
            cpu_percent = process.cpu_percent(interval=None)
            memory_info = process.memory_info()
            
            print(f"\n{'='*80}", file=sys.stderr)
            print("[PERFORMANCE METRICS]", file=sys.stderr)
            print(f"  Total execution time: {elapsed:.2f}s", file=sys.stderr)
            print(f"  Average CPU usage:    {cpu_percent:.1f}%", file=sys.stderr)
            print(f"  Memory used:          {memory_info.rss / 1024 / 1024:.2f} MB", file=sys.stderr)
            if low_cpu_mode:
                print(f"  Low CPU mode:         Enabled", file=sys.stderr)
            print(f"{'='*80}\n", file=sys.stderr)
        
        if verbose:
            print(f"\n[SUCCESS] Analysis completed in {elapsed:.2f}s", file=sys.stderr)
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Process stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
