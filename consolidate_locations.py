"""
Location Extraction and Consolidation Script
Extracts locations mentioned in PDFs and consolidates them into a CSV 
organized by island group (Luzon, Visayas, Mindanao).
"""

import json
import csv
import os
from pathlib import Path
from collections import defaultdict
from location_mapper import PhilippinesLocationMapper
from warning_extractor import WarningExtractor

class LocationConsolidator:
    """Extracts and consolidates locations from PDFs by island group."""
    
    def __init__(self, psgc_csv_dir: str = "dataset/psgc_csv"):
        """Initialize with location mapper and warning extractor."""
        self.location_mapper = PhilippinesLocationMapper(psgc_csv_dir)
        self.warning_extractor = WarningExtractor(self.location_mapper)
        self.consolidated_locations = {
            "Luzon": set(),
            "Visayas": set(),
            "Mindanao": set()
        }
    
    def extract_from_text(self, text: str) -> dict:
        """Extract and categorize locations from text."""
        if not text:
            return {"Luzon": [], "Visayas": [], "Mindanao": []}
        
        # Find matching locations
        matches = self.location_mapper.find_matching_locations(text)
        
        result = {"Luzon": [], "Visayas": [], "Mindanao": []}
        
        for location, island_group in matches.items():
            # Clean location name
            clean_location = location.replace("_", " ").title()
            
            if island_group in result:
                result[island_group].append(clean_location)
                self.consolidated_locations[island_group].add(clean_location)
        
        return result
    
    def extract_from_pdf_json(self, json_data: dict) -> dict:
        """Extract locations from parsed PDF JSON."""
        extracted = {
            "Luzon": [],
            "Visayas": [],
            "Mindanao": []
        }
        
        # Extract from meta raw_tables if available
        if "meta" in json_data and "raw_tables" in json_data["meta"]:
            raw_tables = json_data["meta"]["raw_tables"]
            
            # Concatenate all text from tables
            all_text = []
            for page in raw_tables:
                if "tables" in page:
                    for table in page["tables"]:
                        for row in table:
                            for cell in row:
                                if cell:
                                    all_text.append(str(cell))
            
            full_text = " ".join(all_text)
            extracted = self.extract_from_text(full_text)
        
        return extracted
    
    def process_extracted_labels(self, labels_dir: str) -> dict:
        """Process all JSON files in extracted_labels directory."""
        json_files = list(Path(labels_dir).rglob("*.json"))
        json_files.sort()
        
        results = defaultdict(lambda: {
            "Luzon": set(),
            "Visayas": set(),
            "Mindanao": set()
        })
        
        print(f"Processing {len(json_files)} JSON files...")
        
        for idx, json_path in enumerate(json_files):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract from text
                full_text = ""
                
                # Get location text
                if "typhoon_location_text" in data and data["typhoon_location_text"]:
                    full_text += str(data["typhoon_location_text"]) + " "
                
                # Get movement
                if "typhoon_movement" in data and data["typhoon_movement"]:
                    full_text += str(data["typhoon_movement"]) + " "
                
                # Get meta raw_tables
                if "meta" in data and "raw_tables" in data["meta"]:
                    for page in data["meta"]["raw_tables"]:
                        if "tables" in page:
                            for table in page["tables"]:
                                for row in table:
                                    for cell in row:
                                        if cell:
                                            full_text += str(cell) + " "
                
                # Extract locations
                extracted = self.extract_from_text(full_text)
                
                # Get typhoon name
                typhoon_name = data.get("typhoon_name", "UNKNOWN")
                
                for island, locations in extracted.items():
                    for location in locations:
                        results[typhoon_name][island].add(location)
                
                if (idx + 1) % 100 == 0:
                    print(f"  Processed {idx + 1}/{len(json_files)} files...")
                
            except Exception as e:
                print(f"  Error processing {json_path}: {str(e)}")
        
        return results
    
    def save_to_csv(self, results: dict, output_file: str):
        """Save consolidated locations to CSV with 3 columns (Luzon, Visayas, Mindanao)."""
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        # Consolidate all locations regardless of typhoon
        all_locations = {
            "Luzon": set(),
            "Visayas": set(),
            "Mindanao": set()
        }
        
        for typhoon_name in results.keys():
            typhoon_data = results[typhoon_name]
            for island, locations in typhoon_data.items():
                all_locations[island].update(locations)
        
        # Sort locations
        luzon_locs = sorted(list(all_locations["Luzon"]))
        visayas_locs = sorted(list(all_locations["Visayas"]))
        mindanao_locs = sorted(list(all_locations["Mindanao"]))
        
        # Find max length
        max_len = max(len(luzon_locs), len(visayas_locs), len(mindanao_locs))
        
        # Prepare rows with padding
        rows = []
        for i in range(max_len):
            row = {
                "Luzon": luzon_locs[i] if i < len(luzon_locs) else "",
                "Visayas": visayas_locs[i] if i < len(visayas_locs) else "",
                "Mindanao": mindanao_locs[i] if i < len(mindanao_locs) else ""
            }
            rows.append(row)
        
        # Write CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Luzon", "Visayas", "Mindanao"])
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"\nConsolidated locations saved to: {output_file}")
        print(f"Total locations by island:")
        print(f"  Luzon: {len(all_locations['Luzon'])}")
        print(f"  Visayas: {len(all_locations['Visayas'])}")
        print(f"  Mindanao: {len(all_locations['Mindanao'])}")
        
        return output_file


if __name__ == "__main__":
    import sys
    
    labels_dir = "dataset/extracted_labels"
    output_file = "dataset/locations_consolidated.csv"
    
    if len(sys.argv) > 1:
        labels_dir = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    if not os.path.exists(labels_dir):
        print(f"Error: Labels directory not found: {labels_dir}")
        sys.exit(1)
    
    consolidator = LocationConsolidator("dataset/psgc_csv")
    results = consolidator.process_extracted_labels(labels_dir)
    consolidator.save_to_csv(results, output_file)
