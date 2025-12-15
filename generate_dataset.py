"""
Dataset Generation Script
Extracts information from all PDFs in the dataset/ folder using pdf_parser_prototype.py
Generates JSON files with structured metadata for training purposes.
Recursively processes all subdirectories within the dataset folder.
"""

import json
import os
import sys
from pathlib import Path
from pdf_parser_prototype import parse_pdf

def generate_dataset(dataset_dir: str, output_dir: str = None):
    """
    Recursively scans all PDF files in dataset_dir and subdirectories, 
    then generates JSON files organized by storm folder.
    
    Args:
        dataset_dir: Directory containing storm subdirectories with PDF files
        output_dir: Directory to store generated JSON files (default: dataset/extracted_labels/)
    """
    if output_dir is None:
        output_dir = os.path.join(dataset_dir, "extracted_labels")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all PDF files recursively
    pdf_files = list(Path(dataset_dir).rglob("*.pdf"))
    pdf_files.sort()
    
    print(f"Found {len(pdf_files)} PDF files in {dataset_dir}")
    print(f"Output directory: {output_dir}\n")
    
    successful = 0
    failed = 0
    failed_files = []
    
    for pdf_path in pdf_files:
        # Create a unique filename based on the storm folder and PDF name
        relative_path = pdf_path.relative_to(dataset_dir)
        storm_folder = relative_path.parent.name
        pdf_name = pdf_path.stem  # filename without extension
        
        # Create output subdirectory for each storm
        storm_output_dir = os.path.join(output_dir, storm_folder)
        os.makedirs(storm_output_dir, exist_ok=True)
        
        output_file = os.path.join(storm_output_dir, f"{pdf_name}.json")
        
        try:
            print(f"Processing: {relative_path}...", end=" ")
            
            # Parse PDF with for_dataset=True to exclude confidence fields
            result = parse_pdf(str(pdf_path), for_dataset=True)
            
            # Write to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"[OK]")
            successful += 1
            
        except Exception as e:
            print(f"[FAIL] Error: {str(e)}")
            failed += 1
            failed_files.append((str(relative_path), str(e)))
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Dataset Generation Complete")
    print(f"{'='*60}")
    print(f"Successful: {successful}/{len(pdf_files)}")
    print(f"Failed: {failed}/{len(pdf_files)}")
    
    if failed_files:
        print(f"\nFailed files:")
        for fname, error in failed_files:
            print(f"  - {fname}: {error}")
    
    print(f"\nOutput directory: {output_dir}")
    return successful, failed


if __name__ == "__main__":
    dataset_path = "dataset"
    
    # Allow custom path via command line
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset directory not found: {dataset_path}")
        sys.exit(1)
    
    generate_dataset(dataset_path)
