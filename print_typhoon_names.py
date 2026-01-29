#!/usr/bin/env python
"""
Print all typhoon names from PDF bulletins.

This script extracts typhoon names from PAGASA PDF bulletins in the dataset
and prints them to stdout. Useful for quick verification and debugging.

Usage: 
    python print_typhoon_names.py                    # Print names from all PDFs
    python print_typhoon_names.py --unique           # Print only unique names
    python print_typhoon_names.py --count            # Show count of unique names
    python print_typhoon_names.py --limit 150        # Limit to first 150 PDFs
    python print_typhoon_names.py --dir <path>       # Specify custom PDF directory
"""

import sys
import os
from pathlib import Path
from typhoon_extraction import TyphoonBulletinExtractor


def print_typhoon_names(pdf_directory="dataset/pdfs", limit=None, unique_only=False, show_count=False):
    """
    Extract and print typhoon names from PDF bulletins.
    
    Args:
        pdf_directory: Path to directory containing PDFs
        limit: Maximum number of PDFs to process (None for all)
        unique_only: If True, only print unique names
        show_count: If True, show count of unique names
    """
    extractor = TyphoonBulletinExtractor()
    
    # Get all PDF files
    pdf_path = Path(pdf_directory)
    pdf_files = sorted(pdf_path.rglob("*.pdf"))
    
    if limit:
        pdf_files = pdf_files[:limit]
    
    print(f"Processing {len(pdf_files)} PDF files from {pdf_directory}...")
    print("-" * 70)
    
    typhoon_names = []
    failed_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        try:
            data = extractor.extract_from_pdf(str(pdf_file))
            if data:
                typhoon_name = data.get('typhoon_name', 'N/A')
                if typhoon_name and typhoon_name != "Typhoon name not found":
                    typhoon_names.append(typhoon_name)
                    if not unique_only:
                        print(f"{i:3d}. {typhoon_name:15s} - {pdf_file.name}")
                else:
                    failed_count += 1
                    if not unique_only:
                        print(f"{i:3d}. {'NOT FOUND':15s} - {pdf_file.name}")
            else:
                failed_count += 1
                if not unique_only:
                    print(f"{i:3d}. {'EXTRACTION FAILED':15s} - {pdf_file.name}")
        except Exception as e:
            failed_count += 1
            if not unique_only:
                print(f"{i:3d}. {'ERROR':15s} - {pdf_file.name} ({str(e)[:30]})")
    
    print("-" * 70)
    
    if unique_only:
        unique_names = sorted(set(typhoon_names))
        print("\nUnique Typhoon Names:")
        for name in unique_names:
            print(f"  - {name}")
        print(f"\nTotal unique names: {len(unique_names)}")
    
    if show_count or unique_only:
        print(f"\nStatistics:")
        print(f"  Total PDFs processed: {len(pdf_files)}")
        print(f"  Successful extractions: {len(typhoon_names)}")
        print(f"  Failed extractions: {failed_count}")
        print(f"  Unique typhoon names: {len(set(typhoon_names))}")
        print(f"  Success rate: {len(typhoon_names)/len(pdf_files)*100:.1f}%")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract and print typhoon names from PAGASA PDF bulletins",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Explicitly process all PDFs (this is now the default behavior)"
    )
    parser.add_argument(
        "--unique",
        action="store_true",
        help="Print only unique typhoon names"
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show statistics and count of unique names"
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="dataset/pdfs",
        help="Path to PDF directory (default: dataset/pdfs)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of PDFs to process"
    )
    
    args = parser.parse_args()
    
    # Determine limit
    if args.limit:
        limit = args.limit
    elif args.all:
        limit = None
    else:
        limit = None  # Process all PDFs by default
    
    print_typhoon_names(
        pdf_directory=args.dir,
        limit=limit,
        unique_only=args.unique,
        show_count=args.count or args.unique
    )


if __name__ == "__main__":
    main()
