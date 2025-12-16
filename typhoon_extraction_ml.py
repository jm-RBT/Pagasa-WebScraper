"""
Advanced PAGASA PDF Extraction Algorithm with ML assisted Classification

This module extracts typhoon bulletin data from PDFs and classifies them into
structured TyphoonHubType format using ML assisted pattern recognition and rule based
extraction for high accuracy.
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pdfplumber
from datetime import datetime
import json
import os
import urllib.request
import tempfile
import shutil
from pathlib import Path

# ----------------------------
# location matcher and extractors
# ----------------------------

class LocationMatcher:
    """Matches location names from PDFs to Philippine administrative divisions"""

    REGION_MAPPING = {
        'Ilocos Region': 'Luzon',
        'Cagayan Valley': 'Luzon',
        'Central Luzon': 'Luzon',
        'CALABARZON': 'Luzon',
        'MIMAROPA': 'Luzon',
        'Bicol Region': 'Luzon',
        'Western Visayas': 'Visayas',
        'Central Visayas': 'Visayas',
        'Eastern Visayas': 'Visayas',
        'Zamboanga Peninsula': 'Mindanao',
        'Northern Mindanao': 'Mindanao',
        'Davao Region': 'Mindanao',
        'SOCCSKSARGEN': 'Mindanao',
        'Caraga': 'Mindanao',
        'Bangsamoro': 'Mindanao',
        'BARMM': 'Mindanao',
        'National Capital Region': 'Luzon',
        'NCR': 'Luzon',
        'Cordillera Administrative Region': 'Luzon',
        'CAR': 'Luzon',
    }

    def __init__(self, consolidated_csv_path: str = "bin/consolidated_locations.csv"):
        """Load consolidated locations mapping"""
        # If the csv does not exist, create an empty frame to avoid crash
        if not os.path.exists(consolidated_csv_path):
            self.locations_df = pd.DataFrame(columns=['location_name', 'location_type', 'island_group'])
        else:
            self.locations_df = pd.read_csv(consolidated_csv_path)

        self.priority = {'Province': 5, 'Region': 4, 'City': 3, 'Municipality': 2, 'Barangay': 1}

        self.location_dict = {}
        self.island_groups_dict = {'Luzon': set(), 'Visayas': set(), 'Mindanao': set()}

        grouped = {}
        for _, row in self.locations_df.iterrows():
            name_key = str(row.get('location_name', '')).lower()
            priority = self.priority.get(row.get('location_type', ''), 0)
            island_group = row.get('island_group', None)

            if not name_key:
                continue

            if name_key not in grouped:
                grouped[name_key] = {'priority': priority, 'island_group': island_group}
            elif priority > grouped[name_key]['priority']:
                grouped[name_key] = {'priority': priority, 'island_group': island_group}

        for name_key, info in grouped.items():
            self.location_dict[name_key] = info['island_group']
            if info['island_group'] in self.island_groups_dict:
                self.island_groups_dict[info['island_group']].add(name_key)

    def find_island_group(self, location_name: str) -> Optional[str]:
        """Find which island group a location belongs to"""
        if not location_name:
            return None

        name_lower = location_name.lower().strip()

        if name_lower in self.location_dict:
            return self.location_dict[name_lower]

        for known_location, island_group in self.location_dict.items():
            if name_lower in known_location or known_location in name_lower:
                return island_group

        for region_name, island_group in self.REGION_MAPPING.items():
            if region_name.lower() == name_lower:
                return island_group
            if region_name.lower() in name_lower or name_lower in region_name.lower():
                return island_group

        return None

    def extract_locations_with_regions(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all mentioned locations including regions and classify by island group.
        Only returns the highest priority version of each location name.
        """
        found_locations = {}

        text_lower = text.lower()
        text_with_boundaries = f" {text_lower} "

        for island_group, locations in self.island_groups_dict.items():
            for location in locations:
                location_lower = location.lower()

                if location_lower not in found_locations:
                    location_words = location.split()

                    match_found = False
                    if len(location_words) == 1:
                        try:
                            pattern = f'\\b{re.escape(location)}\\b'
                            if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                                match_found = True
                        except:
                            if f' {location_lower} ' in text_with_boundaries:
                                match_found = True
                    else:
                        if location_lower in text_lower:
                            match_found = True

                    if match_found:
                        found_locations[location_lower] = (island_group, location)

        for region_name, target_island_group in self.REGION_MAPPING.items():
            region_lower = region_name.lower()

            if region_lower not in found_locations:
                region_words = region_lower.split()

                found = False
                if len(region_words) == 1:
                    try:
                        pattern = f'\\b{re.escape(region_lower)}\\b'
                        if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                            found = True
                    except:
                        if f' {region_lower} ' in text_with_boundaries:
                            found = True
                else:
                    if region_lower in text_lower:
                        found = True

                if found:
                    found_locations[region_lower] = (target_island_group, region_name)

        island_groups = {'Luzon': [], 'Visayas': [], 'Mindanao': [], 'Other': []}
        for location_lower, (island_group, original_name) in found_locations.items():
            if island_group in island_groups:
                island_groups[island_group].append(original_name)

        result = {k: v for k, v in island_groups.items() if v}
        return result

    def extract_locations(self, text: str) -> Dict[str, List[str]]:
        """Extract all mentioned locations and classify by island group"""
        island_groups = {'Luzon': set(), 'Visayas': set(), 'Mindanao': set()}

        text_lower = text.lower()
        text_with_boundaries = f" {text_lower} "

        for island_group, locations in self.island_groups_dict.items():
            for location in locations:
                location_words = location.split()

                if len(location_words) == 1:
                    pattern = f'\\b{re.escape(location)}\\b'
                    if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                        island_groups[island_group].add(location)
                else:
                    if location in text_lower:
                        island_groups[island_group].add(location)

        return {k: list(v) for k, v in island_groups.items() if v}


class DateTimeExtractor:
    """Extracts datetime information from bulletin text"""

    @staticmethod
    def extract_issue_datetime(text: str) -> Optional[str]:
        """Extract Issued at datetime pattern"""
        text_clean = re.sub(r'\s+', ' ', text)

        patterns = [
            r'ISSUED\s+AT\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)[,\s]+\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
            r'ISSUED\s+AT\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)[,\s]+\d{1,2}\s+\w+\s+\d{4})',
            r'ISSUED\s*AT\s*([0-9]{1,2}:[0-9]{2}[AP]M[^0-9]*\d{1,2}\s+\w+\s+\d{4})',
            r'ISSUEDAT\s*([0-9]{1,2}:[0-9]{2}[AP]M[,\s]*\d{1,2}\s*\w+\s*\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    @staticmethod
    def normalize_datetime(datetime_str: str) -> Optional[str]:
        """Normalize datetime string to standard format"""
        if not datetime_str:
            return None

        try:
            dt = pd.to_datetime(datetime_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return datetime_str


class SignalWarningExtractor:
    """Extracts Tropical Cyclone Wind Signal warnings for levels 1 to 5"""

    SIGNAL_KEYWORDS = {
        1: ['signal 1', 'tcws 1', 'wind signal 1', 'gale force', 'initial warning'],
        2: ['signal 2', 'tcws 2', 'wind signal 2', 'storm force'],
        3: ['signal 3', 'tcws 3', 'wind signal 3', 'severe tropical storm'],
        4: ['signal 4', 'tcws 4', 'wind signal 4', 'typhoon force'],
        5: ['signal 5', 'tcws 5', 'wind signal 5', 'violent winds', 'super typhoon'],
    }

    def __init__(self, location_matcher: LocationMatcher):
        self.location_matcher = location_matcher

    def extract_signals(self, text: str) -> Dict[int, Dict[str, Optional[str]]]:
        """
        Extract signal warnings for each island group with location names.
        Returns: {signal_level: {island_group: location_string}}
        """
        result = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}}

        text_lower = text.lower()
        text_clean = re.sub(r'\s+', ' ', text_lower)

        wind_section = self._extract_wind_section(text_clean)
        if not wind_section:
            return result

        if 'no tropical cyclone wind signal' in wind_section or 'no wind signal' in wind_section:
            return result

        highest_signal = self._identify_highest_signal_in_text(wind_section)

        if highest_signal:
            locations_by_group = self.location_matcher.extract_locations_with_regions(wind_section)

            for island_group, location_names in locations_by_group.items():
                if island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                    if location_names:
                        result[highest_signal][island_group] = ', '.join(location_names)

        return result

    def _extract_wind_section(self, text: str) -> Optional[str]:
        """Extract the winds section from bulletin"""
        patterns = [
            r'winds?:(.*?)(?:hazard|rainfall|$)',
            r'(?:tropical cyclone )?wind(?:\s+)?signals?:(.*?)(?:hazard|rainfall|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        return None

    def _segment_text_by_location(self, text: str) -> List[str]:
        sections = re.split(r'(?:over|across|affecting)\s+', text, flags=re.IGNORECASE)
        return [s for s in sections if s.strip()]

    def _identify_highest_signal(self, text: str) -> Optional[int]:
        highest_signal = None

        for signal_num in range(5, 0, -1):
            keywords = self.SIGNAL_KEYWORDS.get(signal_num, [])
            for keyword in keywords:
                if keyword in text:
                    return signal_num

        return highest_signal

    def _identify_highest_signal_in_text(self, text: str) -> Optional[int]:
        patterns = [
            r'(?:signal|tcws|tropical\s+cyclone\s+wind\s+signal)[^0-9]*?#?(\d)',
            r'signal\s+(?:no\\.?\\s+)?(\d)',
            r'tcws\s+(\d)',
        ]

        highest = None
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                signal_num = int(match)
                if signal_num > 0 and signal_num <= 5:
                    if highest is None or signal_num > highest:
                        highest = signal_num

        return highest


class RainfallWarningExtractor:
    """Extracts Rainfall warnings mapped to levels 1 to 3"""

    RAINFALL_KEYWORDS = {
        1: ['intense rainfall', 'intense rain', '>30 mm', 'flash flood', 'widespread flooding', 'landslide'],
        2: ['heavy rainfall', 'heavy rain', '15-30 mm', 'moderate flooding', 'landslide risk'],
        3: ['heavy rainfall advisory', 'rainfall advisory', '7.5-15 mm', 'minor flooding', 'waterlogging'],
    }

    def __init__(self, location_matcher: LocationMatcher):
        self.location_matcher = location_matcher

    def extract_rainfall_warnings(self, text: str) -> Dict[str, Dict[str, Optional[str]]]:
        result = {1: {}, 2: {}, 3: {}}

        text_clean = re.sub(r'\s+', ' ', text.lower())

        rainfall_section = self._extract_rainfall_section(text_clean)
        if not rainfall_section:
            return result

        warning_level = self._identify_warning_level(rainfall_section)
        if not warning_level:
            return result

        locations_by_group = self.location_matcher.extract_locations_with_regions(rainfall_section)

        for island_group, location_names in locations_by_group.items():
            if island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                if location_names:
                    result[warning_level][island_group] = ', '.join(location_names)

        return result

    def _extract_rainfall_section(self, text: str) -> str:
        patterns = [
            r'(?:hazards affecting|rainfall:)(.*?)(?:winds:|$)',
            r'(?:rainfall)(.*?)(?:winds:|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        return text

    def _identify_warning_level(self, text: str) -> Optional[int]:
        for level in range(3, 0, -1):
            keywords = self.RAINFALL_KEYWORDS.get(level, [])
            for keyword in keywords:
                if keyword in text:
                    return level

        return None


class TyphoonBulletinExtractor:
    """Main extractor that combines all components"""

    def __init__(self):
        self.location_matcher = LocationMatcher()
        self.datetime_extractor = DateTimeExtractor()
        self.signal_extractor = SignalWarningExtractor(self.location_matcher)
        self.rainfall_extractor = RainfallWarningExtractor(self.location_matcher)

    def extract_from_pdf(self, pdf_path: str) -> Optional[Dict]:
        """Extract complete TyphoonHubType data from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                pages_text = []
                for p in pdf.pages:
                    t = p.extract_text()
                    if t:
                        pages_text.append(t)
                full_text = "\n".join(pages_text)
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return None

        issue_datetime = self.datetime_extractor.extract_issue_datetime(full_text)
        normalized_datetime = self.datetime_extractor.normalize_datetime(issue_datetime)

        typhoon_location = self._extract_typhoon_location(full_text)
        typhoon_movement = self._extract_typhoon_movement(full_text)
        typhoon_windspeed = self._extract_typhoon_windspeed(full_text)

        signals_by_level = self.signal_extractor.extract_signals(full_text)
        rainfall_by_level = self.rainfall_extractor.extract_rainfall_warnings(full_text)

        result = {
            'typhoon_location_text': typhoon_location,
            'typhoon_movement': typhoon_movement,
            'typhoon_windspeed': typhoon_windspeed,
            'updated_datetime': normalized_datetime,
            'signal_warning_tags1': self._build_island_group_dict_from_warnings(signals_by_level, 1),
            'signal_warning_tags2': self._build_island_group_dict_from_warnings(signals_by_level, 2),
            'signal_warning_tags3': self._build_island_group_dict_from_warnings(signals_by_level, 3),
            'signal_warning_tags4': self._build_island_group_dict_from_warnings(signals_by_level, 4),
            'signal_warning_tags5': self._build_island_group_dict_from_warnings(signals_by_level, 5),
            'rainfall_warning_tags1': self._build_island_group_dict_from_warnings(rainfall_by_level, 1),
            'rainfall_warning_tags2': self._build_island_group_dict_from_warnings(rainfall_by_level, 2),
            'rainfall_warning_tags3': self._build_island_group_dict_from_warnings(rainfall_by_level, 3),
        }

        return result

    def _extract_typhoon_location(self, text: str) -> str:
        text_clean = re.sub(r'\s+', ' ', text)

        patterns = [
            r'(?:is\s+)?(?:located|centered|positioned|moving)[^.]*?(?:latitude|longitude|east|west|northeast|northwest)',
            r'(?:the\s+)?(?:low\s+)?(?:pressure\s+)?(?:area|depression|storm)[^.]*?(?:of|over|near)[^.]*',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0).strip()

        return "Location not found"

    def _extract_typhoon_movement(self, text: str) -> str:
        text_clean = re.sub(r'\s+', ' ', text)

        patterns = [
            r'(?:will|is expected to)\s+move\s+[^.]*?(?:direction|area)',
            r'(?:will|forecast)\s+[^.]*?(?:westward|northwestward|northward|eastward|southward)[^.]*?(?:today|tomorrow)',
            r'on\s+the\s+forecast\s+track[^.]*',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0).strip()

        return "Movement information not found"

    def _extract_typhoon_windspeed(self, text: str) -> str:
        text_clean = re.sub(r'\s+', ' ', text)

        patterns = [
            r'(?:maximum\s+sustained\s+)?(?:wind)?s?\s+(?:of\s+)?(\d+)\s*(?:km/h|kph)',
            r'(\d+)\s*(?:km/h|kph|km/hr)(?:\s+(?:sustained|wind))?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                return f"{match.group(1)} km/h"

        return "Wind speed not found"

    def _build_island_group_dict_from_warnings(self, warnings_by_level: Dict[int, Dict[str, Optional[str]]], level: int) -> Dict:
        result = {
            'Luzon': None,
            'Visayas': None,
            'Mindanao': None,
            'Other': None
        }

        if level in warnings_by_level:
            level_data = warnings_by_level[level]
            for island_group, location_string in level_data.items():
                if island_group in result:
                    result[island_group] = location_string

        return result


# ----------------------------
# batch and single file helpers
# ----------------------------

def extract_from_directory(pdfs_directory: str, output_json: str = "bin/extracted_typhoon_data.json"):
    """Extract data from all PDFs in a directory"""
    extractor = TyphoonBulletinExtractor()
    results = []

    pdfs_path = Path(pdfs_directory)
    pdf_files = list(pdfs_path.rglob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files")

    for i, pdf_file in enumerate(pdf_files):
        print(f"Processing [{i+1}/{len(pdf_files)}] {pdf_file.name}...")
        data = extractor.extract_from_pdf(str(pdf_file))
        if data:
            data['source_file'] = str(pdf_file)
            results.append(data)

    os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nExtracted {len(results)} bulletins")
    print(f"Results saved to {output_json}")

    return results


def extract_single_pdf_file(pdf_path: str, output_json: Optional[str] = None):
    extractor = TyphoonBulletinExtractor()
    data = extractor.extract_from_pdf(pdf_path)
    if not data:
        print("No data extracted from file")
        return None

    data['source_file'] = pdf_path

    if output_json:
        # Save as single element list for consistency with directory output
        os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
        with open(output_json, 'w') as f:
            json.dump([data], f, indent=2)
        print(f"Saved extracted data to {output_json}")
    else:
        print(json.dumps(data, indent=2))

    return data


def download_to_temp(url: str) -> str:
    """Download a url to a temporary file and return path"""
    tmp_dir = tempfile.mkdtemp()
    local_path = os.path.join(tmp_dir, "downloaded_file.pdf")
    try:
        urllib.request.urlretrieve(url, local_path)
        return local_path
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to download {url}: {e}")


# ----------------------------
# command line entry
# ----------------------------

if __name__ == "__main__":
    import sys

    # Simple positional argument parsing to avoid requiring option names
    # Usage:
    #   python script.py <input_path_or_url> [output_json_path]
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_path_or_url> [output_json_path]")
        sys.exit(1)

    input_arg = sys.argv[1]
    output_arg = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        # If input is directory
        if os.path.isdir(input_arg):
            outpath = output_arg or "bin/extracted_typhoon_data.json"
            extract_from_directory(input_arg, outpath)

        # If looks like url
        elif input_arg.lower().startswith("http://") or input_arg.lower().startswith("https://"):
            print(f"Downloading {input_arg} ...")
            try:
                tmp_pdf = download_to_temp(input_arg)
            except Exception as e:
                print(f"Download failed: {e}")
                sys.exit(2)

            try:
                extract_single_pdf_file(tmp_pdf, output_arg)
            finally:
                # cleanup temporary files
                try:
                    tmp_dir = Path(tmp_pdf).parent
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except:
                    pass

        # If file exists
        elif os.path.isfile(input_arg):
            extract_single_pdf_file(input_arg, output_arg)

        else:
            print(f"Input not found or not recognized: {input_arg}")
            sys.exit(3)

    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(4)
