#!/usr/bin/env python
"""
Example: Using the main.py pipeline programmatically

This example shows how to integrate the main pipeline into your own scripts
to automatically scrape and analyze PAGASA bulletins.
"""

import sys
import json
from pathlib import Path

# Import the functions from main.py
sys.path.insert(0, str(Path(__file__).parent))
from main import get_typhoon_names_and_pdfs, get_latest_pdf, analyze_pdf


def example1_basic_usage():
    """Example 1: Basic usage - analyze latest bulletin from default HTML"""
    print("=" * 80)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 80)
    
    # Use default HTML file
    source = "bin/PAGASA.html"
    
    # Get typhoon names and PDFs
    print(f"\n1. Scraping bulletin page: {source}")
    typhoons = get_typhoon_names_and_pdfs(source)
    
    if not typhoons:
        print("  No typhoons found!")
        return
    
    # Display what we found
    print(f"\n2. Found {len(typhoons)} typhoon(s):")
    for name, pdfs in typhoons:
        print(f"   - {name}: {len(pdfs)} bulletin(s)")
    
    # Get the latest PDF for the first typhoon
    typhoon_name, pdf_urls = typhoons[0]
    latest_pdf = get_latest_pdf(pdf_urls)
    
    print(f"\n3. Latest bulletin for '{typhoon_name}':")
    print(f"   {latest_pdf}")
    
    print("\n4. To analyze this PDF, you would call:")
    print("   data = analyze_pdf(latest_pdf)  # Handles URLs directly")
    print("   # Returns JSON data with extracted bulletin information")
    
    print("\n" + "=" * 80 + "\n")


def example2_get_all_typhoons():
    """Example 2: Get information about all typhoons"""
    print("=" * 80)
    print("EXAMPLE 2: Get All Typhoons")
    print("=" * 80)
    
    source = "bin/PAGASA.html"
    typhoons = get_typhoon_names_and_pdfs(source)
    
    print(f"\nTotal typhoons: {len(typhoons)}")
    print("-" * 80)
    
    for i, (name, pdfs) in enumerate(typhoons, 1):
        print(f"\nTyphoon {i}: {name}")
        print(f"  Number of bulletins: {len(pdfs)}")
        print(f"  Latest bulletin: {pdfs[-1] if pdfs else 'N/A'}")
        
        # Show first few bulletins as example
        if len(pdfs) > 3:
            print(f"  First 3 bulletins:")
            for j, pdf in enumerate(pdfs[:3], 1):
                print(f"    {j}. {pdf}")
            print(f"    ... and {len(pdfs) - 3} more")
        else:
            print(f"  All bulletins:")
            for j, pdf in enumerate(pdfs, 1):
                print(f"    {j}. {pdf}")
    
    print("\n" + "=" * 80 + "\n")


def example3_json_output():
    """Example 3: Get structured JSON output"""
    print("=" * 80)
    print("EXAMPLE 3: JSON Output")
    print("=" * 80)
    
    source = "bin/PAGASA.html"
    typhoons = get_typhoon_names_and_pdfs(source)
    
    # Create structured output
    output = {
        "total_typhoons": len(typhoons),
        "typhoons": []
    }
    
    for name, pdfs in typhoons:
        typhoon_data = {
            "name": name,
            "bulletin_count": len(pdfs),
            "latest_bulletin": pdfs[-1] if pdfs else None,
            "all_bulletins": pdfs
        }
        output["typhoons"].append(typhoon_data)
    
    print("\nJSON Output:")
    print(json.dumps(output, indent=2))
    
    print("\n" + "=" * 80 + "\n")


def example4_multiple_sources():
    """Example 4: Compare data from multiple sources"""
    print("=" * 80)
    print("EXAMPLE 4: Multiple Sources")
    print("=" * 80)
    
    sources = [
        "bin/PAGASA.html",
        # Add more sources as needed
        # "wayback_archive.html",
        # "https://www.pagasa.dost.gov.ph/..."
    ]
    
    for source in sources:
        print(f"\nSource: {source}")
        print("-" * 80)
        
        try:
            typhoons = get_typhoon_names_and_pdfs(source)
            print(f"  Typhoons found: {len(typhoons)}")
            for name, pdfs in typhoons:
                print(f"    - {name}: {len(pdfs)} bulletin(s)")
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 80 + "\n")


def example5_integration_pattern():
    """Example 5: Integration pattern for automated monitoring"""
    print("=" * 80)
    print("EXAMPLE 5: Integration Pattern for Automated Monitoring")
    print("=" * 80)
    
    print("""
This is a pseudo-code example showing how to integrate the pipeline
into an automated monitoring system:

```python
import time
from datetime import datetime

def monitor_typhoons(check_interval=3600):
    '''
    Monitor PAGASA bulletins and send alerts when new bulletins are detected.
    
    Args:
        check_interval: Seconds between checks (default: 1 hour)
    '''
    last_checked = {}
    
    while True:
        try:
            # Get current typhoons
            typhoons = get_typhoon_names_and_pdfs("bin/PAGASA.html")
            
            for name, pdfs in typhoons:
                latest_pdf = get_latest_pdf(pdfs)
                
                # Check if this is a new bulletin
                if name not in last_checked or last_checked[name] != latest_pdf:
                    print(f"[{datetime.now()}] New bulletin detected for {name}")
                    
                    # Analyze PDF (handles URLs directly, including download & cleanup)
                    data = analyze_pdf(latest_pdf)
                    if data:
                        # Send alert (implement your notification logic)
                        send_alert(name, data)
                    
                    # Update tracking
                    last_checked[name] = latest_pdf
            
            # Wait before next check
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)  # Wait 1 minute before retry

def send_alert(typhoon_name, data):
    '''Send notification about new bulletin'''
    # Example: Send email, SMS, push notification, etc.
    print(f"ALERT: New bulletin for {typhoon_name}")
    print(f"  Wind Speed: {data.get('typhoon_windspeed')}")
    print(f"  Location: {data.get('typhoon_location_text')}")
    # Add more notification logic here
```

To run automated monitoring:
```python
monitor_typhoons(check_interval=3600)  # Check every hour
```
    """)
    
    print("\n" + "=" * 80 + "\n")


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print("MAIN.PY PIPELINE - USAGE EXAMPLES")
    print("=" * 80)
    print("\nThese examples demonstrate how to use the main.py pipeline")
    print("programmatically in your own Python scripts.\n")
    
    # Run examples
    example1_basic_usage()
    example2_get_all_typhoons()
    example3_json_output()
    example4_multiple_sources()
    example5_integration_pattern()
    
    print("=" * 80)
    print("EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nFor more information, see:")
    print("  - main.py --help")
    print("  - README.md")
    print("\n")


if __name__ == "__main__":
    main()
