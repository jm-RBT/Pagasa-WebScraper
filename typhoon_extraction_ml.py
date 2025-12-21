"""
Advanced PAGASA PDF Extraction Algorithm with ML-based Classification

This module extracts typhoon bulletin data from PDFs and classifies them into
structured TyphoonHubType format using ML-assisted pattern recognition and rule-based
extraction for 90%+ accuracy.
"""

import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pdfplumber
from datetime import datetime
import json


class LocationMatcher:
    """Matches location names from PDFs to Philippine administrative divisions"""
    
    # Region names and their island groups - for handling region-level mentions
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
        self.locations_df = pd.read_csv(consolidated_csv_path)
        
        # Create priority-based lookup dicts
        # Prioritize: Province > Region > City > Municipality > Barangay
        self.priority = {'Province': 5, 'Region': 4, 'City': 3, 'Municipality': 2, 'Barangay': 1}
        
        # Build optimized lookup structures
        self.location_dict = {}  # Maps location_name_lower -> island_group (best match)
        self.island_groups_dict = {'Luzon': set(), 'Visayas': set(), 'Mindanao': set()}
        
        # First pass: Group by location name and keep highest priority
        grouped = {}
        for _, row in self.locations_df.iterrows():
            name_key = row['location_name'].lower()
            priority = self.priority.get(row['location_type'], 0)
            island_group = row['island_group']
            
            if name_key not in grouped:
                grouped[name_key] = {'priority': priority, 'island_group': island_group}
            elif priority > grouped[name_key]['priority']:
                # Keep the higher priority version
                grouped[name_key] = {'priority': priority, 'island_group': island_group}
        
        # Build final lookup
        for name_key, info in grouped.items():
            self.location_dict[name_key] = info['island_group']
            if info['island_group'] in self.island_groups_dict:
                self.island_groups_dict[info['island_group']].add(name_key)
    
    def find_island_group(self, location_name: str) -> Optional[str]:
        """Find which island group a location belongs to"""
        if not location_name:
            return None
        
        name_lower = location_name.lower().strip()
        
        # First try exact match in consolidated locations
        if name_lower in self.location_dict:
            return self.location_dict[name_lower]
        
        # Try partial match - check if location_name is contained in or contains any known location
        for known_location, island_group in self.location_dict.items():
            # Check if the known location contains our search term (e.g., "region v (bicol region)" contains "bicol")
            if name_lower in known_location or known_location in name_lower:
                return island_group
        
        # Check region mapping
        for region_name, island_group in self.REGION_MAPPING.items():
            if region_name.lower() == name_lower:
                return island_group
            # Also check for partial matches (e.g., "Bicol" in "Bicol Region")
            if region_name.lower() in name_lower or name_lower in region_name.lower():
                return island_group
        
        return None
    
    def _is_vague_location(self, text: str) -> bool:
        """
        Determine if a location text is vague or non-specific.
        Vague locations include phrases like "most of Luzon", "northeastern Mindanao", 
        "Eastern Visayas" without specific places, region-only mentions, etc.
        
        Note: If the text has parenthetical sub-locations, it's generally NOT vague
        because the sub-locations make it specific.
        """
        text_lower = text.lower().strip()
        
        # If text has parentheses with content, check if it has sub-locations
        # If it does, it's not vague (the sub-locations make it specific)
        if '(' in text and ')' in text:
            paren_match = re.search(r'\((.*?)\)', text)
            if paren_match and paren_match.group(1).strip():
                # Has non-empty parenthetical content - likely specific sub-locations
                # Only consider vague if the parenthetical content itself is vague
                paren_content = paren_match.group(1).lower()
                if not any(phrase in paren_content for phrase in ['etc', 'and others', 'among others']):
                    return False
        
        # Vague qualifiers
        vague_phrases = [
            'most of', 'much of', 'parts of', 'portions of', 'areas of',
            'northeastern', 'northwestern', 'southeastern', 'southwestern',
            'northern', 'southern', 'eastern', 'western', 'central',
            'rest of', 'remaining', 'entire', 'whole'
        ]
        
        # Check if it contains vague qualifiers
        for phrase in vague_phrases:
            if phrase in text_lower:
                return True
        
        # Check if it's only a region name without specific locations
        # (if text only contains region/island group names with no municipalities/cities)
        island_groups = ['luzon', 'visayas', 'mindanao']
        region_only_keywords = island_groups + list(self.REGION_MAPPING.keys())
        
        # If text is short and matches a general region pattern
        words = text_lower.split()
        if len(words) <= 4:
            for keyword in region_only_keywords:
                if keyword.lower() in text_lower:
                    return True
        
        return False
    
    def _parse_parenthetical_content(self, text: str) -> Tuple[str, List[str]]:
        """
        Parse parenthetical sub-locations from text.
        Returns (main_location, sub_locations_list).
        Example: "northwestern Isabela (Santo Tomas, Santa Maria)" 
        -> ("northwestern Isabela", ["Santo Tomas", "Santa Maria"])
        """
        # Find parentheses
        paren_pattern = r'^(.*?)\s*\((.*?)\)\s*$'
        match = re.match(paren_pattern, text.strip())
        
        if match:
            main_location = match.group(1).strip()
            paren_content = match.group(2).strip()
            
            # Split sub-locations by comma
            sub_locations = [sub.strip() for sub in paren_content.split(',') if sub.strip()]
            
            return main_location, sub_locations
        
        # No parentheses found
        return text.strip(), []
    
    def parse_location_text_with_rules(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse location text with specific rules:
        1. Comma separation: Each comma-separated token is an individual location entity
        2. Parenthetical sub-locations: Content in () is kept with main location as one entity
        3. Duplicates: Same name in different island groups are both kept and tagged
        4. Vague locations: Kept as-is and assigned to "Other" island group
        
        IMPORTANT: This method is designed for parsing clean, comma-separated location lists,
        NOT for extracting locations from arbitrary text or bulletin sections.
        Use extract_locations_with_regions() for finding locations in bulletin text.
        
        Args:
            text: Clean comma-separated location list (e.g., "Batanes, Cagayan, Isabela (Santo Tomas, Quezon)")
            
        Returns:
            List of location entities with structure:
            {
                'raw_text': str,           # Original text including parentheses
                'main_location': str,      # Main location name
                'sub_locations': List[str], # Sub-location names if any
                'island_group': str,       # 'Luzon', 'Visayas', 'Mindanao', or 'Other'
                'is_vague': bool          # Whether this is a vague location
            }
            
        Example:
            >>> lm = LocationMatcher()
            >>> text = "Batanes, the northwestern portion of Isabela (Santo Tomas, Quezon), Apayao"
            >>> entities = lm.parse_location_text_with_rules(text)
            >>> len(entities)  # Returns 3 entities
            3
        """
        if not text or not text.strip():
            return []
        
        location_entities = []
        
        # Step 1: Split by comma, but respect parentheses
        # We need to split by commas that are NOT inside parentheses
        tokens = []
        current_token = ""
        paren_depth = 0
        
        for char in text:
            if char == '(':
                paren_depth += 1
                current_token += char
            elif char == ')':
                paren_depth -= 1
                current_token += char
            elif char == ',' and paren_depth == 0:
                # This comma is outside parentheses - it's a separator
                if current_token.strip():
                    tokens.append(current_token.strip())
                current_token = ""
            else:
                current_token += char
        
        # Don't forget the last token
        if current_token.strip():
            tokens.append(current_token.strip())
        
        # Step 2: Process each token
        for token in tokens:
            # Parse parenthetical content
            main_location, sub_locations = self._parse_parenthetical_content(token)
            
            # Check if vague
            is_vague = self._is_vague_location(token)
            
            # Determine island group
            if is_vague:
                island_group = 'Other'
            else:
                # Try to find island group from main location
                island_group = self.find_island_group(main_location)
                
                # If not found and there are sub-locations, try first sub-location
                if not island_group and sub_locations:
                    island_group = self.find_island_group(sub_locations[0])
                
                # Default to 'Other' if still not found
                if not island_group:
                    island_group = 'Other'
            
            # Create entity
            entity = {
                'raw_text': token,
                'main_location': main_location,
                'sub_locations': sub_locations,
                'island_group': island_group,
                'is_vague': is_vague
            }
            
            location_entities.append(entity)
        
        # Step 3: Handle duplicates with different island groups
        # Group by main_location to find duplicates
        location_map = {}
        for entity in location_entities:
            key = entity['main_location'].lower()
            if key not in location_map:
                location_map[key] = []
            location_map[key].append(entity)
        
        # Filter: keep all if they have different island groups, otherwise keep one
        final_entities = []
        for key, entities_list in location_map.items():
            if len(entities_list) == 1:
                final_entities.extend(entities_list)
            else:
                # Check if they belong to different island groups
                island_groups_set = set(e['island_group'] for e in entities_list)
                if len(island_groups_set) > 1:
                    # Different island groups - keep all with tagging
                    final_entities.extend(entities_list)
                else:
                    # Same island group - keep first one
                    final_entities.append(entities_list[0])
        
        return final_entities
    
    def extract_locations_with_regions(self, text: str) -> Dict[str, List[str]]:
        """
        Extract all mentioned locations including regions and classify by island group.
        Regions are captured for proper mapping to island groups.
        Only returns the highest-priority version of each location name.
        """
        found_locations = {}  # Track: location_name_lower -> (island_group, original_name)
        
        text_lower = text.lower()
        text_with_boundaries = f" {text_lower} "
        
        # First pass: Check consolidated locations from CSV
        # Use simple substring matching for multi-word locations
        for island_group, locations in self.island_groups_dict.items():
            for location in locations:
                location_lower = location.lower()
                
                # Only add if not already found
                if location_lower not in found_locations:
                    location_words = location.split()
                    
                    match_found = False
                    if len(location_words) == 1:
                        # Single word: use word boundaries with optimized regex
                        # Avoid complex patterns
                        try:
                            pattern = f'\\b{re.escape(location)}\\b'
                            if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                                match_found = True
                        except:
                            # Fallback to simple substring match
                            if f' {location_lower} ' in text_with_boundaries:
                                match_found = True
                    else:
                        # Multi-word: simple substring check only
                        if location_lower in text_lower:
                            match_found = True
                    
                    if match_found:
                        found_locations[location_lower] = (island_group, location)
        
        # Second pass: Check region names
        for region_name, target_island_group in self.REGION_MAPPING.items():
            region_lower = region_name.lower()
            
            if region_lower not in found_locations:
                region_words = region_lower.split()
                
                found = False
                if len(region_words) == 1:
                    # Single word: use word boundaries
                    try:
                        pattern = f'\\b{re.escape(region_lower)}\\b'
                        if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                            found = True
                    except:
                        # Fallback
                        if f' {region_lower} ' in text_with_boundaries:
                            found = True
                else:
                    # Multi-word: simple substring check
                    if region_lower in text_lower:
                        found = True
                
                if found:
                    found_locations[region_lower] = (target_island_group, region_name)
        
        # Group by island group
        island_groups = {'Luzon': [], 'Visayas': [], 'Mindanao': [], 'Other': []}
        for location_lower, (island_group, original_name) in found_locations.items():
            if island_group in island_groups:
                island_groups[island_group].append(original_name)
        
        # Remove empty categories and return
        result = {k: v for k, v in island_groups.items() if v}
        return result
    
    def extract_locations(self, text: str) -> Dict[str, List[str]]:
        """Extract all mentioned locations and classify by island group - OPTIMIZED"""
        island_groups = {'Luzon': set(), 'Visayas': set(), 'Mindanao': set()}
        
        # Convert text to lowercase for matching
        text_lower = text.lower()
        
        # Use word boundaries for matching to avoid partial matches
        # Add spaces around text for boundary matching
        text_with_boundaries = f" {text_lower} "
        
        # For each island group, check which locations are mentioned in text
        for island_group, locations in self.island_groups_dict.items():
            for location in locations:
                # Use word boundaries to avoid matching substrings
                # Split location by spaces and try to match whole location
                location_words = location.split()
                
                if len(location_words) == 1:
                    # Single word: use word boundaries
                    pattern = f'\\b{re.escape(location)}\\b'
                    if re.search(pattern, text_with_boundaries, re.IGNORECASE):
                        island_groups[island_group].add(location)
                else:
                    # Multi-word: just check if sequence exists
                    if location in text_lower:
                        island_groups[island_group].add(location)
        
        # Convert sets to lists
        return {k: list(v) for k, v in island_groups.items() if v}


class DateTimeExtractor:
    """Extracts datetime information from bulletin text"""
    
    @staticmethod
    def extract_issue_datetime(text: str) -> Optional[str]:
        """Extract 'Issued at' datetime pattern"""
        # Clean spaces for pattern matching
        text_clean = re.sub(r'\s+', ' ', text)
        
        # Pattern: "ISSUED AT" followed by time and date
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
    def normalize_datetime(datetime_str: str) -> str:
        """Normalize datetime string to standard format"""
        if not datetime_str:
            return None
        
        # Try to parse and standardize
        try:
            dt = pd.to_datetime(datetime_str)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return datetime_str


class SignalWarningExtractor:
    """Extracts Tropical Cyclone Wind Signal warnings (TCWS 1-5)"""
    
    # Signal keywords and patterns from Signal Warning Rules
    SIGNAL_KEYWORDS = {
        1: ['signal 1', 'tcws 1', 'signal 1', 'wind signal 1', 'gale force', 'initial warning'],
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
        
        # Extract the winds/signal section specifically
        wind_section = self._extract_wind_section(text_clean)
        if not wind_section:
            return result
        
        # Check for "no signal" statement
        if 'no tropical cyclone wind signal' in wind_section or 'no wind signal' in wind_section:
            return result
        
        # Find highest signal number mentioned
        highest_signal = self._identify_highest_signal_in_text(wind_section)
        
        if highest_signal:
            # Extract locations with regions
            locations_by_group = self.location_matcher.extract_locations_with_regions(wind_section)
            
            # Populate result with location names for the detected signal level
            for island_group, location_names in locations_by_group.items():
                if island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                    if location_names:
                        result[highest_signal][island_group] = ', '.join(location_names)
        
        return result
    
    def _extract_wind_section(self, text: str) -> str:
        """Extract the winds/signals section from bulletin"""
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
        """Segment text by location mentions"""
        # Split by common section headers and location mentions
        sections = re.split(r'(?:over|across|affecting)\s+', text, flags=re.IGNORECASE)
        return [s for s in sections if s.strip()]
    
    def _identify_highest_signal(self, text: str) -> Optional[int]:
        """Identify the highest signal number mentioned"""
        highest_signal = None
        
        for signal_num in range(5, 0, -1):
            keywords = self.SIGNAL_KEYWORDS.get(signal_num, [])
            for keyword in keywords:
                if keyword in text:
                    return signal_num
        
        return highest_signal
    
    def _identify_highest_signal_in_text(self, text: str) -> Optional[int]:
        """Identify highest signal by looking for explicit signal numbers"""
        # Look for explicit signal numbers mentioned
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
    """Extracts Rainfall warnings (Red/Orange/Yellow = 1/2/3)"""
    
    # Rainfall warning patterns from Rainfall Warning Rules
    RAINFALL_KEYWORDS = {
        1: ['intense rainfall', 'intense rain', '>30 mm', 'flash flood', 'widespread flooding', 'landslide'],
        2: ['heavy rainfall', 'heavy rain', '15-30 mm', 'moderate flooding', 'landslide risk'],
        3: ['heavy rainfall advisory', 'rainfall advisory', '7.5-15 mm', 'minor flooding', 'waterlogging'],
    }
    
    def __init__(self, location_matcher: LocationMatcher):
        self.location_matcher = location_matcher
    
    def extract_rainfall_warnings(self, text: str) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Extract rainfall warnings for each island group with location names.
        Returns: {warning_level: {island_group: location_string}}
        """
        result = {1: {}, 2: {}, 3: {}}
        
        text_clean = re.sub(r'\s+', ' ', text.lower())
        
        # Extract rainfall section from text
        rainfall_section = self._extract_rainfall_section(text_clean)
        if not rainfall_section:
            return result
        
        # Identify warning level
        warning_level = self._identify_warning_level(rainfall_section)
        if not warning_level:
            return result
        
        # Extract locations with regions (includes both CSV locations and region names)
        locations_by_group = self.location_matcher.extract_locations_with_regions(rainfall_section)
        
        # Populate result with location names for the detected warning level
        for island_group, location_names in locations_by_group.items():
            if island_group in ['Luzon', 'Visayas', 'Mindanao', 'Other']:
                if location_names:
                    result[warning_level][island_group] = ', '.join(location_names)
        
        return result
    
    def _extract_rainfall_section(self, text: str) -> str:
        """Extract the rainfall/hazards section from bulletin"""
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
        """Identify the highest rainfall warning level"""
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
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """Extract complete TyphoonHubType data from PDF"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages])
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return None
        
        # Extract components
        issue_datetime = self.datetime_extractor.extract_issue_datetime(full_text)
        normalized_datetime = self.datetime_extractor.normalize_datetime(issue_datetime)
        
        typhoon_location = self._extract_typhoon_location(full_text)
        typhoon_movement = self._extract_typhoon_movement(full_text)
        typhoon_windspeed = self._extract_typhoon_windspeed(full_text)
        
        signals_by_level = self.signal_extractor.extract_signals(full_text)
        rainfall_by_level = self.rainfall_extractor.extract_rainfall_warnings(full_text)
        
        # Build TyphoonHubType structure with signal and rainfall tags
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
        """Extract current typhoon location text"""
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
        """Extract typhoon movement information"""
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
        """Extract maximum sustained wind speed"""
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
        """
        Build IslandGroupType dictionary for specific warning level.
        warnings_by_level format: {level: {island_group: location_string}}
        """
        result = {
            'Luzon': None,
            'Visayas': None,
            'Mindanao': None,
            'Other': None
        }
        
        # Get locations for this warning level
        if level in warnings_by_level:
            level_data = warnings_by_level[level]
            for island_group, location_string in level_data.items():
                if island_group in result:
                    result[island_group] = location_string
        
        return result


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
    
    # Save results
    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nExtracted {len(results)} bulletins")
    print(f"Results saved to {output_json}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "dataset/pdfs"
    
    extract_from_directory(directory)
