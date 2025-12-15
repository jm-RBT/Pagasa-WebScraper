import re
import logging
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DataExtractor:
    """
    The 'Algorithm' to assign values to fields from the ML Grid.
    """
    def __init__(self):
        self.headers = {
            "location": ["Location of Center", "Location of Eye", "Center"],
            "movement": ["Present Movement", "Movement", "Direction and speed", "Moving"],
            "intensity": ["Intensity", "Maximum sustained winds", "Strength"],
            "tcws_header": ["TROPICAL CYCLONE WIND SIGNALS", "TCWS", "WIND SIGNALS"],
        }
        
    def _normalize(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip().lower()

    def _match_header(self, text: str, keys: List[str]) -> float:
        norm_text = self._normalize(text)
        best_ratio = 0.0
        for key in keys:
            norm_key = self._normalize(key)
            if norm_key in norm_text:
                return 1.0 # Strong substring match
            ratio = SequenceMatcher(None, norm_text, norm_key).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
        return best_ratio

    def extract_from_grids(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main extraction loop. Iterate over all grids from all pages.
        """
        result = {
            "typhoon_location_text": None,
            "typhoon_movement": None,
            "typhoon_windspeed": None,
            "signals": {},
            "meta": {}
        }
        
        for page in pages:
            # page['tables'] is a list of grids (List[List[str]])
            for grid in page['tables']:
                self._process_grid(grid, result)
                
        return result

    def _process_grid(self, grid: List[List[str]], result: Dict[str, Any]):
        """
        Analyzes a single grid to find key-value pairs or signal tables.
        """
        rows = len(grid)
        if rows == 0: return

        # Strategy: Iterate cells
        for r_idx, row in enumerate(grid):
            for c_idx, cell_text in enumerate(row):
                if not cell_text: continue
                
                # Check for Location
                if not result["typhoon_location_text"]: 
                    if self._match_header(cell_text, self.headers["location"]) > 0.85:
                        val = self._find_value(grid, r_idx, c_idx)
                        if val: result["typhoon_location_text"] = val
                
                # Check for Movement
                if not result["typhoon_movement"]:
                    if self._match_header(cell_text, self.headers["movement"]) > 0.85:
                        val = self._find_value(grid, r_idx, c_idx)
                        if val: result["typhoon_movement"] = val

                # Check for Intensity
                if not result["typhoon_windspeed"]:
                    if self._match_header(cell_text, self.headers["intensity"]) > 0.8: # Low thresh for "Winds"
                        val = self._find_value(grid, r_idx, c_idx)
                        if val: result["typhoon_windspeed"] = val
                     
                # Check for Signals Table
                # Usually "TCWS" is in a merged header.
                if self._match_header(cell_text, self.headers["tcws_header"]) > 0.8:
                     self._extract_signals_from_grid_part(grid, r_idx, result)

    def _find_value(self, grid: List[List[str]], r: int, c: int) -> Optional[str]:
        """
        Heuristic: Look Right, then Look Down.
        """
        row = grid[r]
        
        # 1. Look Right in same row
        # If the cell itself contains ":" split it
        if ":" in row[c]:
             parts = row[c].split(":", 1)
             if parts[1].strip(): return parts[1].strip()

        if c + 1 < len(row):
            val = row[c+1].strip()
            if val: return val
            
        # 2. Look Down (next row, same column)
        if r + 1 < len(grid):
            next_row = grid[r+1]
            if c < len(next_row):
                val = next_row[c].strip()
                if val: return val
            # Or first column of next row (sometimes layout is strictly vertical)
            if len(next_row) > 0:
                val = next_row[0].strip()
                if val: return val
                
        return None

    def _extract_signals_from_grid_part(self, grid: List[List[str]], header_row_idx: int, result: Dict[str, Any]):
        """
        Extracts TCWS signals starting from the header row.
        """
        # Iterate rows below header
        for i in range(header_row_idx + 1, len(grid)):
            row = grid[i]
            if not row: continue
            
            # Stop if we hit end of table (e.g. "Hazards")
            row_text = " ".join(row).upper()
            if "HAZARDS" in row_text or "HEAVY RAINFALL" in row_text:
                break
            
            # Check for Signal Number in first cell
            first_cell = row[0]
            sig_num = 0
            
            # Match "1", "TCWS 1", "Signal 1"
            # Strict boundary to avoid "120 km/h"
            m = re.search(r'(?:^|\s)([1-5])(?:$|\s)', first_cell)  
            if m:
                sig_num = int(m.group(1))
            
            if sig_num > 0:
                # Found a signal row
                region_data = {"Luzon": None, "Visayas": None, "Mindanao": None}
                
                # Naive: Just grep for Region keywords in the whole row
                # This works because usually the column headers align with these, 
                # OR the content explicitly says "Luzon: ... Visayas: ..."
                
                full_row_text = " ".join(row)
                
                # Simple parsing: Split by keywords? 
                # "Luzon: Cavite, ... Visayas: None ... Mindanao: ..."
                
                # Normalize spaces
                text = re.sub(r'\s+', ' ', full_row_text)
                
                patterns = {
                    "Luzon": r"Luzon:?(.*?)(?=Visayas|Mindanao|$)",
                    "Visayas": r"Visayas:?(.*?)(?=Mindanao|Luzon|$)",
                    "Mindanao": r"Mindanao:?(.*?)(?=Luzon|Visayas|$)"
                }
                
                for region, pattern in patterns.items():
                    # Check if region name exists in text
                    if region.upper() in text.upper():
                        # Try regex extract
                        m_reg = re.search(pattern, text, re.IGNORECASE)
                        if m_reg:
                            val = m_reg.group(1).strip()
                            # Clean leading separators like "- " or ":"
                            val = re.sub(r'^[:\-\s]+', '', val)
                            if val and val.lower() != "none":
                                region_data[region] = val
                        else:
                            # Fallback: if columns are distinct?
                            # Let's rely on regex for now as it handles the "Luzon: ..." format well
                            pass

                result["signals"][f"Signal {sig_num}"] = region_data
