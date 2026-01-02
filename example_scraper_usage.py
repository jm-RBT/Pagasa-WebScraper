#!/usr/bin/env python
"""
Example: Using the PAGASA bulletin scraper programmatically

This example shows how to integrate scrape_bulletin.py into your own scripts.
"""

from scrape_bulletin import scrape_bulletin

# Example 1: Scrape the default HTML file
print("Example 1: Using default HTML file")
print("-" * 60)
pdf_links = scrape_bulletin("bin/PAGASA.html")

# The result is a 2D array where each sub-array represents one typhoon
for typhoon_index, typhoon_pdfs in enumerate(pdf_links, 1):
    print(f"\nTyphoon {typhoon_index}: {len(typhoon_pdfs)} bulletins")
    for pdf_index, pdf_url in enumerate(typhoon_pdfs, 1):
        print(f"  {pdf_index}. {pdf_url}")

# Example 2: Process the data
print("\n" + "=" * 60)
print("Example 2: Processing the extracted data")
print("-" * 60)
total_pdfs = sum(len(typhoon) for typhoon in pdf_links)
print(f"Total typhoons: {len(pdf_links)}")
print(f"Total PDF bulletins: {total_pdfs}")

# Example 3: Download PDFs (pseudo-code)
print("\n" + "=" * 60)
print("Example 3: Pseudo-code for downloading PDFs")
print("-" * 60)
print("""
import requests

for typhoon_index, typhoon_pdfs in enumerate(pdf_links, 1):
    for pdf_url in typhoon_pdfs:
        filename = pdf_url.split('/')[-1]
        # Download logic here
        # response = requests.get(pdf_url)
        # with open(f'typhoon_{typhoon_index}_{filename}', 'wb') as f:
        #     f.write(response.content)
        print(f"Would download: {filename} for typhoon {typhoon_index}")
""")
