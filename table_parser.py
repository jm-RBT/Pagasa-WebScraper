import json
import logging
import unicodedata
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

# Configuration
CONFIG = {
    "HEADER_ALIASES": {
        "location": ["Location of Center", "Location", "Centre at", "Estimated center"],
        "movement": ["Present Movement", "Movement", "Direction and speed"],
        "windspeed": ["Intensity", "Maximum sustained winds", "Winds", "MSW", "Sustained winds"],
        "updated_datetime": ["Issued at", "Issued:", "Issued as of", "Date/Time", "Date and Time", "Issued"],
        "tcws": ["TROPICAL CYCLONE WIND SIGNALS", "TCWS", "WIND SIGNALS"],
        "rainfall": ["Heavy Rainfall Outlook", "HEAVY RAINFALL", "Rainfall Warning", "Rainfall"]
    },
    "REGIONS": ["Luzon", "Visayas", "Mindanao"],
    "RAINFALL_MAP": {
        "Red": 1,
        "Orange": 2,
        "Yellow": 3
    },
    "DEFAULT_TIMEZONE_OFFSET": 8  # UTC+8
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class HeaderMatcher:
    @staticmethod
    def normalize(text: str) -> str:
        if not text: return ""
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    @staticmethod
    def match(text: str, aliases: List[str]) -> float:
        """Returns confidence score 0.0 to 1.0"""
        norm_text = HeaderMatcher.normalize(text)
        best_ratio = 0.0
        
        for alias in aliases:
            norm_alias = HeaderMatcher.normalize(alias)
            
            # Exact match (normalized)
            if norm_text == norm_alias:
                return 1.0
            
            # Startswith match (strong anchor)
            if norm_text.startswith(norm_alias):
                return 0.9

            # Substring match (alias in text or text in alias)
            if norm_alias in norm_text or norm_text in norm_alias:
                # Penalize length diff
                len_ratio = min(len(norm_alias), len(norm_text)) / max(len(norm_alias), len(norm_text))
                return 0.8 * len_ratio

            # Fuzzy match
            ratio = SequenceMatcher(None, norm_text, norm_alias).ratio()
            best_ratio = max(best_ratio, ratio)
            
        return best_ratio if best_ratio > 0.6 else 0.0

class TableParser:
    def __init__(self, raw_data: List[Dict[str, Any]], config: Dict = None):
        """
        raw_data: List of pages as returned by pdf_parser_prototype.py
                  [{ "page_number": 1, "tables": [ [ [row1_col1, ...] ... ] ... ] }, ...]
        """
        self.raw_data = raw_data
        self.config = config or CONFIG
        self.flattened_tables = self._flatten_tables()
        self.full_text = self._get_full_text()

    def _flatten_tables(self) -> List[List[str]]:
        """Flatten all pages -> tables -> rows into a single list of rows."""
        all_rows = []
        for page in self.raw_data:
            if "tables" in page and page["tables"]:
                for table in page["tables"]:
                    for row in table:
                        # Clean cell content
                        cleaned_row = [HeaderMatcher.normalize(str(cell)) if cell else "" for cell in row]
                        all_rows.append((row, cleaned_row)) # Store (Original, Cleaned) tuple
        return all_rows

    def _get_full_text(self) -> str:
        """Concatenates all text for fallback extraction."""
        text = []
        for row_tuple in self.flattened_tables:
            original_row = row_tuple[0]
            text.append(" ".join([str(c) for c in original_row if c]))
        return "\n".join(text)

    def parse(self) -> Dict[str, Any]:
        result = {
            "typhoon_location_text": {"value": None, "confidence": 0.0},
            "typhoon_movement": {"value": None, "confidence": 0.0},
            "typhoon_windspeed": {"value": None, "confidence": 0.0},
            "updated_datetime": {"value": None, "confidence": 0.0},
            "signal_warning_tags1": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "signal_warning_tags2": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "signal_warning_tags3": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "signal_warning_tags4": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "signal_warning_tags5": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "rainfall_warning_tags1": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "rainfall_warning_tags2": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "rainfall_warning_tags3": {"value": {"Luzon": None, "Visayas": None, "Mindanao": None}, "confidence": 0.0},
            "meta": {
                "raw_tables": self.raw_data
            }
        }

        # 1. Parsing Key-Values
        result["typhoon_location_text"] = self._extract_simple_field("location")
        result["typhoon_movement"] = self._extract_simple_field("movement")
        result["typhoon_windspeed"] = self._extract_simple_field("windspeed")
        result["updated_datetime"] = self._extract_datetime()

        # 2. Parsing Signals
        signals = self._extract_signals()
        for i in range(1, 6):
            key = f"signal_warning_tags{i}"
            if i in signals:
                result[key] = signals[i]

        # 3. Parsing Rainfall
        rainfall = self._extract_rainfall()
        for i in range(1, 4):
            key = f"rainfall_warning_tags{i}"
            if i in rainfall:
                result[key] = rainfall[i]

        return result

    def parse_for_dataset(self) -> Dict[str, Any]:
        """
        Returns parsed result without confidence fields for dataset generation.
        Useful for creating training datasets.
        """
        result = self.parse()
        return self._strip_confidence(result)

    def _strip_confidence(self, obj: Any) -> Any:
        """Recursively removes 'confidence' fields from nested structures."""
        if isinstance(obj, dict):
            return {k: self._strip_confidence(v) for k, v in obj.items() if k != "confidence"}
        elif isinstance(obj, list):
            return [self._strip_confidence(item) for item in obj]
        else:
            return obj

    def _extract_simple_field(self, config_key: str) -> Dict[str, Any]:
        aliases = self.config["HEADER_ALIASES"][config_key]
        best_result = {"value": None, "confidence": 0.0}

        for i, (orig_row, clean_row) in enumerate(self.flattened_tables):
            for j, cell in enumerate(clean_row):
                if not cell: continue
                
                confidence = HeaderMatcher.match(cell, aliases)
                if confidence > 0.7:
                    # Attempt Extraction
                    value = None
                    
                    # 1. Content in same row (next cell)
                    if j + 1 < len(orig_row) and orig_row[j+1]:
                         value = str(orig_row[j+1]).strip()
                    
                    # 2. Content in next row (same column or first cell)
                    elif i + 1 < len(self.flattened_tables):
                        next_orig_row = self.flattened_tables[i+1][0]
                        # Try same column index
                        if j < len(next_orig_row) and next_orig_row[j]:
                             value = str(next_orig_row[j]).strip()
                        # Try first cell if same column is empty
                        elif next_orig_row and next_orig_row[0]:
                             value = str(next_orig_row[0]).strip()
                    
                    # 3. Content in same cell (split by :)
                    if not value and ":" in str(orig_row[j]):
                        parts = str(orig_row[j]).split(":", 1)
                        if len(parts) > 1 and parts[1].strip():
                            value = parts[1].strip()

                    if value:
                        # Clean value
                        value = re.sub(r'\s+', ' ', value).strip()
                        if confidence > best_result["confidence"]:
                            best_result = {"value": value, "confidence": confidence}

        return best_result

    def _extract_datetime(self) -> Dict[str, Any]:
        result = self._extract_simple_field("updated_datetime")
        raw_val = result["value"]
        if raw_val:
            # Attempt to parse datetime
            # Heuristics for "11:00 AM, 04 December 2025" or similar
            try:
                # Remove "Issued at " prefix if present
                clean_val = re.sub(r"(?i)issued\s*at\s*", "", raw_val).strip()
                # Remove trailing text like "Valid ..."
                clean_val = re.split(r"(?i)Valid|Synopsis", clean_val)[0].strip()
                
                formats = [
                    "%I:%M %p, %d %B %Y",
                    "%I:%M %p %d %B %Y",
                    "%H:%M, %d %B %Y",
                    "%B %d, %Y %I:%M %p"
                ]
                
                dt = None
                for fmt in formats:
                    try:
                        dt = datetime.strptime(clean_val, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt:
                    # Add TZ
                    tz = timezone(timedelta(hours=self.config["DEFAULT_TIMEZONE_OFFSET"]))
                    dt = dt.replace(tzinfo=tz)
                    result["value"] = dt.isoformat()
                else:
                    # Keep raw as fallback but lower confidence slightly
                    result["value"] = clean_val
                    result["confidence"] *= 0.8
            except Exception:
                pass
        return result

    def _extract_signals(self) -> Dict[int, Dict[str, Any]]:
        extracted = {}
        
        # 1. Find the Signals Table Header
        header_idx = -1
        col_map = {"Luzon": -1, "Visayas": -1, "Mindanao": -1}
        
        found_header = False
        
        for i, (orig_row, clean_row) in enumerate(self.flattened_tables):
            # Check for main anchor first
            for cell in clean_row:
                if HeaderMatcher.match(cell, self.config["HEADER_ALIASES"]["tcws"]) > 0.8:
                    # Look for region headers in this row or next few rows
                    for check_idx in range(i, min(i+5, len(self.flattened_tables))):
                        check_row = self.flattened_tables[check_idx][1] # clean
                        for r_idx, r_cell in enumerate(check_row):
                            for region in self.config["REGIONS"]:
                                if region.lower() in r_cell and col_map[region] == -1:
                                    col_map[region] = r_idx
                        
                        if all(v != -1 for v in col_map.values()):
                            header_idx = check_idx
                            found_header = True
                            break
                    if found_header: break
            if found_header: break
            
        if not found_header:
            return extracted

        # 2. Iterate rows below header
        for i in range(header_idx + 1, len(self.flattened_tables)):
            row = self.flattened_tables[i][0] # use original row for content
            clean_row = self.flattened_tables[i][1]
            
            # Stop if we hit another section header (all caps, likely) or end of table structure
            # Heuristic: if row is empty or completely different structure
            if not any(row): continue
            if any("HAZARDS" in str(c) for c in row if c): break
            
            # Detect Signal Number
            # Usually column 0 or 1
            sig_num = 0
            first_cell = str(row[0]).strip() if row and row[0] else ""
            
            # regex for "1", "TCWS No. 1", "Signal #1"
            match = re.search(r'\b([1-5])\b', first_cell)
            if match:
                sig_num = int(match.group(1))
            
            if sig_num > 0:
                # Extract regions
                region_data = {"Luzon": None, "Visayas": None, "Mindanao": None}
                has_content = False
                
                for region, col_idx in col_map.items():
                    if col_idx < len(row) and row[col_idx]:
                        val = str(row[col_idx]).strip()
                        if val and val != "-" and val.lower() != "none":
                            # Normalize delimiters
                            val = re.sub(r'[\n\r]+', '; ', val)
                            region_data[region] = val
                            has_content = True
                
                extracted[sig_num] = {
                    "value": region_data,
                    "confidence": 0.9 if has_content else 0.5
                }

        return extracted

    def _extract_rainfall(self) -> Dict[int, Dict[str, Any]]:
        extracted = {}
        # Simple heuristic: Look for lines containing "Red"/"Orange"/"Yellow" and try to find regions in them
        # Limitations: PDF extraction often mangles this into a paragraph.
        # We will scan the full text for these sections.
        
        # Locate Rainfall Section in Full Text
        # This is strictly searching normalized text for simplicity
        
        # Better: Iterate flattened rows to find the "Heavy Rainfall" section
        start_idx = -1
        for i, (orig_row, clean_row) in enumerate(self.flattened_tables):
            for cell in clean_row:
                 if HeaderMatcher.match(cell, self.config["HEADER_ALIASES"]["rainfall"]) > 0.8:
                     start_idx = i
                     break
            if start_idx != -1: break
            
        if start_idx == -1: return extracted

        # Aggregate text from this section until next header
        text_block = ""
        for i in range(start_idx, len(self.flattened_tables)):
            row = self.flattened_tables[i][0]
            row_text = " ".join([str(c) for c in row if c])
            if "SEVERE WINDS" in row_text.upper() or "HAZARDS" in row_text.upper():
                break
            text_block += row_text + "\n"

        # Parse text block for colors
        for color, level in self.config["RAINFALL_MAP"].items():
            # Regex to find "Red ... Luzon: ... Visayas: ..."
            # This is hard because formatting varies.
            # We look for the Color keyword.
            if color.lower() in text_block.lower():
                # Naive Region Extraction for now:
                # If we find "Luzon" after the color and before the next color...
                # For this specific PDF structure, complex parsing is needed. 
                # Adhering to the prompt: attempt categorization.
                
                item = {"Luzon": None, "Visayas": None, "Mindanao": None}
                # TODO: Implement robust regex for unstructured text if needed.
                # For now, if the color exists, we might just put the whole snippet in "Luzon" if unambiguous, or leave generic.
                # User prompted "Expect three major regions".
                # Let's try to split the text block by Region keywords.
                
                # ... implementation simplified for prototype ...
                confidence = 0.5
                
                # Check for explicit region mentions near the color
                # (Complex NLP normally required here without strict table cols)
                
                # Placeholder: If color found, set confidence.
                # In strict table mode, we'd look for columns like Signals.
                extracted[level] = {
                    "value": item, 
                    "confidence": 0.3 # Low confidence on text blob parsing
                }
                
        return extracted


if __name__ == "__main__":
    # Test Driver
    import sys
    import os
    
    # Check if a file is provided
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        if os.path.exists(target_file):
            print(f"Parsing {target_file}...")
            # Load the text file (which contains the JSON array)
            # Use utf-8-sig to handle potential BOM from PowerShell Out-File
            with open(target_file, 'r', encoding='utf-8-sig') as f:
                raw_json = json.load(f)
            
            # Since the text file contains the list of tables directly [ {page...}, ... ]
            # And parser expects that structure.
            
            parser = TableParser(raw_json)
            result = parser.parse()
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"File not found: {target_file}")
    else:
        print("Usage: python table_parser.py <path_to_TCB_tables.txt>")
