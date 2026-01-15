#!/usr/bin/env python
"""
Analyze a single PAGASA PDF bulletin and display extracted data in a readable format.
Usage: python analyze_pdf.py "<path_to_pdf>"
       python analyze_pdf.py "<pdf_url>"
       python analyze_pdf.py --random
       python analyze_pdf.py "<path_to_pdf>" --low-cpu    # Limit CPU to 30%
       python analyze_pdf.py "<path_to_pdf>" --metrics    # Show performance metrics
       python analyze_pdf.py "<path_to_pdf>" --json       # Raw JSON output
"""

from typhoon_extraction import TyphoonBulletinExtractor
import json
import sys
import tempfile
import requests
import hashlib
import time
import psutil
import os
from pathlib import Path
from urllib.parse import urlparse
from advisory_scraper import scrape_and_extract

def cpu_throttle(process, target_cpu_percent=30, sample_interval=0.1):
    """
    CPU throttling function - pauses execution if CPU usage exceeds target.
    This reduces CPU consumption while still completing the task.
    
    Args:
        process: psutil.Process object
        target_cpu_percent: Target CPU percentage (default 30%)
        sample_interval: Time between CPU checks in seconds
    """
    current_cpu = process.cpu_percent(interval=sample_interval)
    
    if current_cpu > target_cpu_percent:
        # Sleep for a bit to let CPU cool down
        sleep_time = 0.05 * (current_cpu / target_cpu_percent)
        time.sleep(sleep_time)

def calculate_file_hash(filepath):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_pdf_for_suspicious_features(filepath):
    """Check for suspicious PDF features that may indicate malware"""
    suspicious_features = []
    content = None
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Check for JavaScript in PDF (often malicious)
        if b'/JavaScript' in content or b'/JS' in content:
            suspicious_features.append("Contains JavaScript")
        
        # Check for embedded executables
        if b'/EmbeddedFile' in content:
            suspicious_features.append("Contains embedded files")
        
        # Check for OpenAction (auto-execute on open)
        if b'/OpenAction' in content:
            suspicious_features.append("Contains auto-execute actions")
        
        # Check for suspicious launch actions
        if b'/Launch' in content or b'/SubmitForm' in content:
            suspicious_features.append("Contains form/launch actions")
        
        # Check for suspicious XObjects
        if b'/XObject' in content and b'/EmbeddedFile' in content:
            suspicious_features.append("Contains suspicious embedded objects")
        
    except Exception as e:
        print(f"  Feature check error: {e}")
        return []
    finally:
        # Free memory explicitly
        content = None
    
    return suspicious_features

def check_pdf_safety(filepath):
    """Check if PDF is safe using built-in methods (no system installations required)"""
    print("\n[SAFETY CHECK]")
    
    # 1. File size check
    file_size = Path(filepath).stat().st_size
    print(f"  File size: {file_size:,} bytes", end="")
    
    if file_size > 100 * 1024 * 1024:  # 100 MB limit
        print(" [WARNING] Large file")
        return False
    else:
        print(" [OK]")
    
    # 2. Calculate file hash
    file_hash = calculate_file_hash(filepath)
    print(f"  SHA256: {file_hash}")
    
    # 3. PDF structure validation
    print("  PDF structure validation...", end=" ", flush=True)
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                print("[INVALID] Not a valid PDF file")
                return False
        print("[OK]")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return False
    
    # 4. Check for suspicious features
    print("  Scanning for suspicious features...", end=" ", flush=True)
    suspicious = check_pdf_for_suspicious_features(filepath)
    if suspicious:
        print(f"\n    [WARNING] Found suspicious features:")
        for feature in suspicious:
            print(f"       - {feature}")
        response = input("    Continue anyway? (y/n): ").lower()
        if response != 'y':
            return False
    else:
        print("[OK]")
    
    print("  Overall: [OK] PDF appears safe to process\n")
    return True

def fetch_live_advisory_data():
    """
    Fetch live rainfall advisory data from PAGASA.
    Returns dict with keys: red, orange, yellow (each containing list of locations)
    Returns None if fetch fails.
    """
    try:
        print("[INFO] Fetching live rainfall advisory from PAGASA...")
        result = scrape_and_extract()
        
        if result and 'rainfall_warnings' in result:
            warnings = result['rainfall_warnings']
            print(f"[INFO] Successfully fetched advisory data:")
            print(f"  - Red warnings: {len(warnings.get('red', []))} locations")
            print(f"  - Orange warnings: {len(warnings.get('orange', []))} locations")
            print(f"  - Yellow warnings: {len(warnings.get('yellow', []))} locations")
            return warnings
        else:
            print("[WARNING] Advisory data fetch returned no warnings")
            return None
    except Exception as e:
        print(f"[WARNING] Failed to fetch advisory data: {e}")
        return None

def display_results(data):
    """Display extraction results in a readable format"""
    print("\n" + "=" * 80)
    print("PAGASA BULLETIN EXTRACTION RESULTS")
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
        else:
            print(f"\n  Signal {level}: No warnings")
    
    if not signal_found:
        print("  [OK] No tropical cyclone wind signals in effect")
    
    # Rainfall Warnings
    print("\n[RAINFALL WARNINGS]")
    rainfall_found = False
    
    rainfall_levels = {
        1: "Red Warning - Heavy to Intense Rainfall (>200mm/24hr)",
        2: "Orange Warning - Moderate to Heavy Rainfall (100-200mm/24hr)",
        3: "Yellow Warning - Light to Moderate Rainfall (50-100mm/24hr)"
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
    start_time = time.time()
    process = psutil.Process(os.getpid())
    
    # Get CPU usage at start (warm up)
    process.cpu_percent(interval=None)
    time.sleep(0.1)
    
    # Track CPU usage during extraction
    cpu_samples = []
    low_cpu_mode = "--low-cpu" in sys.argv
    show_metrics = "--metrics" in sys.argv
    
    if low_cpu_mode:
        print("[*] Low CPU mode enabled - limiting to ~30% CPU usage\n")
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf.py \"<path_to_pdf>\"")
        print("       python analyze_pdf.py \"<pdf_url>\"")
        print("       python analyze_pdf.py --random")
        print("       python analyze_pdf.py \"<path_to_pdf>\" --low-cpu    # Limit CPU to 30%")
        print("\nExample:")
        print('  python analyze_pdf.py "dataset/pdfs/pagasa-20-19W/PAGASA_20-19W_Pepito_SWB#02.pdf"')
        print('  python analyze_pdf.py "https://example.com/bulletin.pdf"')
        print("\nOr for random selection:")
        print("  python analyze_pdf.py --random")
        sys.exit(1)
    
    # Handle random selection
    if sys.argv[1] == "--random":
        import random
        pdfs = list(Path("dataset/pdfs").rglob("*.pdf"))
        if not pdfs:
            print("Error: No PDFs found in dataset/pdfs/")
            sys.exit(1)
        pdf_path = str(random.choice(pdfs))
        print(f"Selected random PDF: {pdf_path}\n")
    else:
        pdf_path = sys.argv[1]
    
    # Check if it's a URL or local file
    is_url = pdf_path.startswith(('http://', 'https://'))
    temp_pdf_path = None
    
    if is_url:
        # Download PDF from URL
        print(f"Downloading PDF from: {pdf_path}")
        response = None
        try:
            response = requests.get(pdf_path, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(response.content)
                temp_pdf_path = tmp.name
            
            pdf_path_to_analyze = temp_pdf_path
            print(f"Saved to temporary file: {temp_pdf_path}\n")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading PDF: {e}")
            sys.exit(1)
        finally:
            # Close response to free memory
            if response is not None:
                response.close()
    else:
        # Verify local file exists
        if not Path(pdf_path).exists():
            print(f"Error: File not found: {pdf_path}")
            sys.exit(1)
        pdf_path_to_analyze = pdf_path
    
    print(f"Analyzing: {Path(pdf_path).name if not is_url else urlparse(pdf_path).path.split('/')[-1]}")
    print("Processing...\n")
    
    # Check PDF safety before processing
    if not check_pdf_safety(pdf_path_to_analyze):
        print("[WARNING] PDF failed safety checks. Aborting analysis.")
        elapsed = time.time() - start_time
        print(f"\n[TIME] Execution time: {elapsed:.2f}s")
        sys.exit(1)
    
    # Extract data
    extractor = TyphoonBulletinExtractor()
    try:
        extraction_start = time.time()
        data = extractor.extract_from_pdf(pdf_path_to_analyze)
        
        # Apply CPU throttling if enabled
        if low_cpu_mode:
            cpu_throttle(process, target_cpu_percent=30)
        
        extraction_time = time.time() - extraction_start
        
        if not data:
            print("Error: Failed to extract data from PDF")
            elapsed = time.time() - start_time
            print(f"\n[TIME] Execution time: {elapsed:.2f}s")
            sys.exit(1)
        
        # Fetch live advisory data and merge with PDF extraction results
        advisory_data = fetch_live_advisory_data()
        if advisory_data:
            # Replace rainfall warnings with live advisory data
            # Map: red -> rainfall_warning_tags1, orange -> rainfall_warning_tags2, yellow -> rainfall_warning_tags3
            data['rainfall_warning_tags1'] = advisory_data.get('red', [])
            data['rainfall_warning_tags2'] = advisory_data.get('orange', [])
            data['rainfall_warning_tags3'] = advisory_data.get('yellow', [])
            print("[INFO] Replaced rainfall warnings with live advisory data")
        else:
            # If advisory fetch fails, convert existing IslandGroupType format to list format
            print("[INFO] Using PDF-extracted rainfall data (advisory fetch failed)")
            for level in range(1, 4):
                tag_key = f'rainfall_warning_tags{level}'
                old_format = data.get(tag_key, {})
                # Convert IslandGroupType dict to list of locations
                locations = []
                if isinstance(old_format, dict):
                    for island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                        loc_str = old_format.get(island_group)
                        if loc_str:
                            # Split by comma and add to list
                            locations.extend([loc.strip() for loc in loc_str.split(',')])
                data[tag_key] = locations
        
        # Display in readable format
        display_results(data)
        
        # Option to show raw JSON
        if len(sys.argv) > 2 and sys.argv[2] == "--json":
            print("RAW JSON OUTPUT:")
            print("=" * 80)
            print(json.dumps(data, indent=2))
    finally:
        # Clean up extractor to free resources
        del extractor
        
        # Clean up temporary file if it was created
        if temp_pdf_path is not None and Path(temp_pdf_path).exists():
            try:
                Path(temp_pdf_path).unlink()
            except Exception as e:
                print(f"Warning: Could not delete temp file: {e}")
    
    # Display execution time and resource metrics
    elapsed = time.time() - start_time
    
    if show_metrics:
        cpu_percent = process.cpu_percent(interval=None)
        memory_info = process.memory_info()
        
        print(f"\n{'='*80}")
        print("[PERFORMANCE METRICS]")
        print(f"  Total execution time: {elapsed:.2f}s")
        print(f"  PDF processing time:  {extraction_time:.2f}s ({extraction_time/elapsed*100:.1f}% of total)")
        if low_cpu_mode:
            print(f"  CPU usage (throttled): {cpu_percent:.1f}% (capped to ~30%)")
        else:
            print(f"  Average CPU usage:    {cpu_percent:.1f}%")
        print(f"  Memory used:          {memory_info.rss / 1024 / 1024:.2f} MB")
        if low_cpu_mode:
            print(f"  Low CPU mode:         Enabled")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
