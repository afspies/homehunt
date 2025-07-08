"""
Feature extraction utilities for property data
Extracts features like parking, garden, balcony, pets from text descriptions
"""

import re
from typing import List, Optional, Set

from homehunt.core.models import LetType


class FeatureExtractor:
    """Utility class for extracting property features from text"""
    
    # Feature detection patterns
    PARKING_PATTERNS = [
        r'parking\s*(space|spot|bay)?',
        r'garage(?:d|s)?',
        r'allocated\s*parking',
        r'resident(?:s)?\s*parking',
        r'off.?street\s*parking',
        r'secure\s*parking',
        r'underground\s*parking',
        r'covered\s*parking',
        r'car\s*port',
        r'driveway',
        r'private\s*parking'
    ]
    
    GARDEN_PATTERNS = [
        r'garden(?:s)?',
        r'outdoor\s*space',
        r'private\s*(?:garden|outdoor)',
        r'rear\s*garden',
        r'front\s*garden',
        r'patio(?:s)?',
        r'terrace(?:s)?',
        r'courtyard(?:s)?',
        r'deck(?:s)?',
        r'yard(?:s)?',
        r'landscaped',
        r'communal\s*garden'
    ]
    
    BALCONY_PATTERNS = [
        r'balcon(?:y|ies)',
        r'juliet\s*balcon(?:y|ies)',
        r'roof\s*terrace',
        r'terrace(?:s)?',
        r'veranda(?:s)?',
        r'loggia(?:s)?'
    ]
    
    PETS_ALLOWED_PATTERNS = [
        r'pets?\s+(?:allowed|welcome|considered|accepted)',
        r'pets?\s*(?:are\s+)?(?:allowed|welcome|considered|accepted)',
        r'dog(?:s)?\s+(?:allowed|welcome|considered|accepted)',
        r'cat(?:s)?\s+(?:allowed|welcome|considered|accepted)',
        r'pet.?friendly',
        r'animal(?:s)?\s+(?:allowed|welcome|considered)',
        r'(?:pets?|animals?)\s*ok',
        r'(?:pets?|animals?)\s*welcome'
    ]
    
    PETS_NOT_ALLOWED_PATTERNS = [
        r'no\s+pets?',
        r'pets?\s+not\s+(?:allowed|permitted)',
        r'pets?\s+(?:not\s+)?(?:allowed|permitted)\s*not',
        r'sorry,?\s*no\s+pets?',
        r'pet.?free',
        r'animal(?:s)?\s+not\s+(?:allowed|permitted)'
    ]
    
    LET_TYPE_PATTERNS = {
        LetType.STUDENT: [
            r'student(?:s)?',
            r'university',
            r'academic\s*year',
            r'term\s*time',
            r'student\s*(?:accommodation|housing|let)',
            r'hmo',
            r'house\s*(?:in\s*)?multiple\s*occupation'
        ],
        LetType.PROFESSIONAL: [
            r'professional(?:s)?',
            r'working\s*professional(?:s)?',
            r'corporate\s*(?:let|rental)',
            r'executive',
            r'business\s*(?:let|rental)',
            r'professional\s*(?:couple|share|tenant)'
        ],
        LetType.SHORT_TERM: [
            r'short.?term',
            r'temporary',
            r'holiday\s*(?:let|rental)',
            r'vacation\s*rental',
            r'serviced\s*apartment',
            r'furnished\s*(?:weekly|monthly)',
            r'min(?:imum)?\s*(?:1|2|3)\s*(?:week|month)(?:s)?',
            r'flexible\s*(?:lease|term)'
        ],
        LetType.LONG_TERM: [
            r'long.?term',
            r'permanent',
            r'min(?:imum)?\s*(?:6|12)\s*month(?:s)?',
            r'annual\s*(?:lease|tenancy)',
            r'fixed\s*term',
            r'assured\s*shorthold'
        ]
    }
    
    NEW_BUILD_PATTERNS = [
        r'new\s*build',
        r'brand\s*new',
        r'newly\s*built',
        r'recently\s*completed',
        r'built\s*in\s*(?:2020|2021|2022|2023|2024)',
        r'completed\s*in\s*(?:2020|2021|2022|2023|2024)',
        r'modern\s*development',
        r'contemporary\s*build',
        r'luxury\s*development',
        r'high\s*specification',
        r'premium\s*development',
        r'designer\s*(?:apartment|flat)',
        r'state\s*of\s*the\s*art'
    ]
    
    SOUTH_LONDON_AREAS = [
        r'south\s*london',
        r'southwark',
        r'bermondsey',
        r'london\s*bridge',
        r'borough(?!\s*market)',  # Exclude "Borough Market" but include "Borough"
        r'elephant\s*(?:and|&)\s*castle',
        r'waterloo',
        r'lambeth',
        r'clapham',
        r'battersea',
        r'wandsworth',
        r'putney',
        r'wimbledon',
        r'tooting',
        r'streatham',
        r'brixton',
        r'camberwell',
        r'peckham',
        r'new\s*cross',
        r'greenwich',
        r'deptford',
        r'lewisham',
        r'blackheath',
        r'catford',
        r'croydon',
        r'crystal\s*palace',
        r'se\d+',  # South East London postcodes
        r'sw\d+',  # South West London postcodes (many are actually North, but some like SW8, SW9 are South)
        r'cr\d+',  # Croydon postcodes
    ]
    
    @staticmethod
    def extract_parking(text: str) -> Optional[bool]:
        """Extract parking availability from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check for parking indicators
        for pattern in FeatureExtractor.PARKING_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        # Check for explicit "no parking"
        no_parking_patterns = [
            r'no\s*parking',
            r'parking\s*not\s*(?:available|included)',
            r'street\s*parking\s*only'
        ]
        
        for pattern in no_parking_patterns:
            if re.search(pattern, text_lower):
                return False
        
        return None
    
    @staticmethod
    def extract_garden(text: str) -> Optional[bool]:
        """Extract garden availability from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check for garden indicators
        for pattern in FeatureExtractor.GARDEN_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        # Check for explicit "no garden"
        no_garden_patterns = [
            r'no\s*garden',
            r'no\s*outdoor\s*space'
        ]
        
        for pattern in no_garden_patterns:
            if re.search(pattern, text_lower):
                return False
        
        return None
    
    @staticmethod
    def extract_balcony(text: str) -> Optional[bool]:
        """Extract balcony availability from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check for balcony indicators
        for pattern in FeatureExtractor.BALCONY_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        return None
    
    @staticmethod
    def extract_pets_allowed(text: str) -> Optional[bool]:
        """Extract pets policy from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check for pets not allowed first (more specific)
        for pattern in FeatureExtractor.PETS_NOT_ALLOWED_PATTERNS:
            if re.search(pattern, text_lower):
                return False
        
        # Check for pets allowed
        for pattern in FeatureExtractor.PETS_ALLOWED_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        return None
    
    @staticmethod
    def extract_let_type(text: str) -> Optional[LetType]:
        """Extract let type from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check each let type
        for let_type, patterns in FeatureExtractor.LET_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return let_type
        
        return None
    
    @staticmethod
    def extract_new_build(text: str) -> Optional[bool]:
        """Extract new build status from text"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check for new build indicators
        for pattern in FeatureExtractor.NEW_BUILD_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        return None
    
    @staticmethod
    def is_south_london(text: str) -> bool:
        """Check if property is in South London areas"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Check for South London area indicators
        for pattern in FeatureExtractor.SOUTH_LONDON_AREAS:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    @staticmethod
    def extract_all_features(text: str, features_list: List[str] = None) -> dict:
        """
        Extract all property features from text
        
        Args:
            text: Text to extract features from (description, features, etc.)
            features_list: Optional list of feature strings to also analyze
            
        Returns:
            Dictionary with extracted features
        """
        if not text:
            text = ""
        
        # Combine text with features list
        combined_text = text
        if features_list:
            combined_text += " " + " ".join(features_list)
        
        return {
            'parking': FeatureExtractor.extract_parking(combined_text),
            'garden': FeatureExtractor.extract_garden(combined_text),
            'balcony': FeatureExtractor.extract_balcony(combined_text),
            'pets_allowed': FeatureExtractor.extract_pets_allowed(combined_text),
            'let_type': FeatureExtractor.extract_let_type(combined_text),
            'new_build': FeatureExtractor.extract_new_build(combined_text),
            'is_south_london': FeatureExtractor.is_south_london(combined_text)
        }


def extract_coordinates_from_text(text: str) -> Optional[tuple[float, float]]:
    """
    Extract GPS coordinates from text, including embedded map metadata
    
    Args:
        text: Text to search for coordinates (HTML, URLs, etc.)
        
    Returns:
        Tuple of (latitude, longitude) or None
    """
    if not text:
        return None
    
    # Pattern for decimal coordinates (lat, lng)
    coordinate_patterns = [
        # Google Maps URLs: ?q=lat,lng or @lat,lng
        r'[@?](-?\d+\.?\d*),(-?\d+\.?\d*)',
        # Explicit lat/lng in various formats
        r'lat[itude]*[:=]\s*(-?\d+\.?\d*)[,\s]+lng|lon[gitude]*[:=]\s*(-?\d+\.?\d*)',
        r'lng|lon[gitude]*[:=]\s*(-?\d+\.?\d*)[,\s]+lat[itude]*[:=]\s*(-?\d+\.?\d*)',
        # JSON-style coordinates
        r'"lat[itude]*":\s*(-?\d+\.?\d*)[,\s]*"lng|lon[gitude]*":\s*(-?\d+\.?\d*)',
        r'"lng|lon[gitude]*":\s*(-?\d+\.?\d*)[,\s]*"lat[itude]*":\s*(-?\d+\.?\d*)',
        # Coordinate pairs in parentheses or brackets
        r'[\[\(](-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)[\]\)]',
        # OpenStreetMap/other map services
        r'mlat=(-?\d+\.?\d*)&mlon=(-?\d+\.?\d*)',
        # Geographic coordinates in metadata
        r'geo:(-?\d+\.?\d*),(-?\d+\.?\d*)',
        # Common coordinate separators
        r'(-?\d{1,2}\.\d{4,})[,\s]+(-?\d{1,3}\.\d{4,})',
    ]
    
    for pattern in coordinate_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Handle different capture group arrangements
                if len(match) == 2:
                    lat_str, lng_str = match
                elif len(match) == 4:  # lat/lng patterns with both captured
                    lat_str = match[0] or match[2]
                    lng_str = match[1] or match[3]
                else:
                    continue
                
                lat = float(lat_str)
                lng = float(lng_str)
                
                # Validate coordinate ranges
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    # For UK properties, expect roughly these ranges
                    if 49.5 <= lat <= 61.0 and -8.5 <= lng <= 2.0:
                        return (lat, lng)
                    # Also accept if coordinates look reasonable globally
                    elif abs(lat) > 10 or abs(lng) > 10:  # Not (0,0) or similar
                        return (lat, lng)
                        
            except (ValueError, IndexError):
                continue
    
    return None


def extract_coordinates_from_maps_embed(html_content: str) -> Optional[tuple[float, float]]:
    """
    Extract coordinates from embedded map iframes, scripts, and image URLs
    
    Supports multiple coordinate formats:
    - Zoopla JSON: "location":{"coordinates":{"latitude":51.4933,"longitude":-0.131788}}
    - Rightmove map images: latitude=51.49681&longitude=-0.13456
    - Google Maps embeds and JavaScript patterns
    
    Args:
        html_content: HTML content containing map embeds
        
    Returns:
        Tuple of (latitude, longitude) or None
    """
    if not html_content:
        return None
    
    # Decode HTML entities first
    import html
    content = html.unescape(html_content)
    
    # Rightmove map image patterns (most reliable for Rightmove)
    rightmove_patterns = [
        r'https://media\.rightmove\.co\.uk/map/_generate[^"\']*[?&]latitude=(-?\d+\.?\d*)[^"\']*[?&]longitude=(-?\d+\.?\d*)',
        r'src=["\']https://media\.rightmove\.co\.uk/map/_generate[^"\']*[?&]latitude=(-?\d+\.?\d*)[^"\']*[?&]longitude=(-?\d+\.?\d*)',
    ]
    
    # Zoopla coordinate patterns (JSON format in page source - highest priority for Zoopla)
    zoopla_json_patterns = [
        # Primary Zoopla format: "location":{"coordinates":{"latitude":51.4933,"longitude":-0.131788}
        r'"location"\s*:\s*\{\s*"coordinates"\s*:\s*\{\s*"latitude"\s*:\s*(-?\d+\.?\d*)\s*,\s*"longitude"\s*:\s*(-?\d+\.?\d*)',
        # Nested coordinates: "coordinates":{"latitude":51.4933,"longitude":-0.131788}
        r'"coordinates"\s*:\s*\{\s*"latitude"\s*:\s*(-?\d+\.?\d*)\s*,\s*"longitude"\s*:\s*(-?\d+\.?\d*)',
        # Direct lat/lng in JSON: "latitude":51.4933,"longitude":-0.131788
        r'"latitude"\s*:\s*(-?\d+\.?\d*)\s*,\s*"longitude"\s*:\s*(-?\d+\.?\d*)',
        # Alternative order: "longitude":-0.131788,"latitude":51.4933
        r'"longitude"\s*:\s*(-?\d+\.?\d*)\s*,\s*"latitude"\s*:\s*(-?\d+\.?\d*)',
        # Compact format without quotes: latitude:51.4933,longitude:-0.131788
        r'latitude\s*:\s*(-?\d+\.?\d*)\s*,\s*longitude\s*:\s*(-?\d+\.?\d*)',
        r'longitude\s*:\s*(-?\d+\.?\d*)\s*,\s*latitude\s*:\s*(-?\d+\.?\d*)',
    ]
    
    # Zoopla map URL patterns (fallback)
    zoopla_url_patterns = [
        r'https://[^"\']*zoopla[^"\']*[?&]lat=(-?\d+\.?\d*)[^"\']*[?&]lng=(-?\d+\.?\d*)',
        r'src=["\']https://[^"\']*zoopla[^"\']*[?&]lat=(-?\d+\.?\d*)[^"\']*[?&]lng=(-?\d+\.?\d*)',
    ]
    
    # Google Maps iframe patterns
    google_patterns = [
        r'src=["\']https://www\.google\.com/maps/embed[^"\']*[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'src=["\']https://maps\.google\.com/[^"\']*[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'src=["\']https://www\.google\.com/maps/[^"\']*[@?](-?\d+\.?\d*),(-?\d+\.?\d*)',
    ]
    
    # Map script patterns (Google Maps JavaScript)
    script_patterns = [
        r'new\s+google\.maps\.LatLng\(\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)',
        r'lat\s*:\s*(-?\d+\.?\d*)\s*,\s*lng\s*:\s*(-?\d+\.?\d*)',
        r'latitude\s*:\s*(-?\d+\.?\d*)\s*,\s*longitude\s*:\s*(-?\d+\.?\d*)',
        r'center\s*:\s*\{\s*lat\s*:\s*(-?\d+\.?\d*)\s*,\s*lng\s*:\s*(-?\d+\.?\d*)\s*\}',
    ]
    
    # Try patterns in order of reliability 
    # Zoopla JSON first (most reliable for Zoopla), then Rightmove maps (most reliable for Rightmove)
    all_patterns = zoopla_json_patterns + rightmove_patterns + zoopla_url_patterns + google_patterns + script_patterns
    
    for pattern_idx, pattern in enumerate(all_patterns):
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            try:
                # Handle longitude/latitude order reversal for specific patterns
                # Check if this is a longitude-first pattern (patterns 3 and 5 in zoopla_json_patterns)
                longitude_first_patterns = {3, 5}  # Indices of patterns that capture longitude first
                if pattern_idx in longitude_first_patterns:
                    # For patterns that capture longitude first, then latitude
                    lng = float(match[0])
                    lat = float(match[1])
                else:
                    # Standard order: latitude first, then longitude
                    lat = float(match[0])
                    lng = float(match[1])
                
                # Validate coordinate ranges for UK
                if 49.5 <= lat <= 61.0 and -8.5 <= lng <= 2.0:
                    return (lat, lng)
                    
            except (ValueError, IndexError):
                continue
    
    return None


def extract_postcode(text: str) -> Optional[str]:
    """
    Extract UK postcode from text
    
    Args:
        text: Text to search for postcode
        
    Returns:
        Extracted postcode or None
    """
    if not text:
        return None
    
    # UK postcode pattern (more flexible)
    postcode_pattern = r'([A-Z]{1,2}[0-9R][0-9A-Z]?\s*[0-9][A-Z]{2})'
    
    matches = re.findall(postcode_pattern, text.upper())
    if matches:
        # Return the first match, cleaned up
        postcode = matches[0].strip()
        # Ensure proper spacing
        if len(postcode) >= 5 and postcode[-4] != ' ':
            postcode = postcode[:-3] + ' ' + postcode[-3:]
        return postcode
    
    return None


def clean_address(address: str) -> str:
    """
    Clean and normalize address text
    
    Args:
        address: Raw address text
        
    Returns:
        Cleaned address
    """
    if not address:
        return ""
    
    # Remove extra whitespace
    address = re.sub(r'\s+', ' ', address.strip())
    
    # Remove common prefixes
    prefixes_to_remove = [
        r'^(?:Property\s+)?(?:ref|reference):\s*\w+\s*[-,]?\s*',
        r'^(?:Address|Location):\s*',
        r'^Property:\s*'
    ]
    
    for prefix in prefixes_to_remove:
        address = re.sub(prefix, '', address, flags=re.IGNORECASE)
    
    return address.strip()