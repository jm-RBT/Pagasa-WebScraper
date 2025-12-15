"""
Script to add typhoon_name field to all extracted JSON files.
Extracts the typhoon name from the filename pattern.
"""

import json
import os
import re
from pathlib import Path

def extract_typhoon_name(filename: str) -> str:
    """
    Extracts typhoon name from filename.
    Pattern examples:
    - PAGASA_20-19W_Pepito_SWB#01.pdf -> Pepito
    - PAGASA_21-TC01_Auring_SWB#01.pdf -> Auring
    - TCB_1.json -> (from context, needs to check meta data)
    """
    # Try pattern: PAGASA_YY-CCXX_NAME_SWB#NN
    match = re.search(r'PAGASA_\d+-[A-Z0-9]+_([A-Za-z]+)_', filename)
    if match:
        return match.group(1).upper()
    
    # Try pattern with spaces: PAGASA_YY-CCXX_NAME SWB
    match = re.search(r'PAGASA_\d+-[A-Z0-9]+\s+([A-Za-z]+)\s+', filename)
    if match:
        return match.group(1).upper()
    
    return "UNKNOWN"

def add_typhoon_name_to_json(json_path: str) -> bool:
    """
    Adds typhoon_name field to a JSON file.
    Returns True if successful, False otherwise.
    """
    try:
        # Extract typhoon name from filename
        filename = os.path.basename(json_path)
        typhoon_name = extract_typhoon_name(filename)
        
        # Read JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add typhoon_name field at the top level
        data['typhoon_name'] = typhoon_name
        
        # Write back to JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        return True
    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        return False

def process_all_json_files(base_dir: str):
    """
    Recursively processes all JSON files in a directory.
    """
    json_files = list(Path(base_dir).rglob("*.json"))
    json_files.sort()
    
    print(f"Found {len(json_files)} JSON files")
    print(f"Processing directory: {base_dir}\n")
    
    successful = 0
    failed = 0
    
    for json_path in json_files:
        if add_typhoon_name_to_json(str(json_path)):
            successful += 1
            print(f"[OK] {json_path.relative_to(base_dir)}")
        else:
            failed += 1
            print(f"[FAIL] {json_path.relative_to(base_dir)}")
    
    print(f"\n{'='*60}")
    print(f"Processing Complete")
    print(f"{'='*60}")
    print(f"Successful: {successful}/{len(json_files)}")
    print(f"Failed: {failed}/{len(json_files)}")
    
    return successful, failed

if __name__ == "__main__":
    import sys
    
    base_path = "dataset/extracted_labels"
    
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    
    if not os.path.exists(base_path):
        print(f"Error: Directory not found: {base_path}")
        sys.exit(1)
    
    process_all_json_files(base_path)
