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
            'let_type': FeatureExtractor.extract_let_type(combined_text)
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
    
    # Zoopla map patterns
    zoopla_patterns = [
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
    
    # Try patterns in order of reliability (Rightmove maps are most accurate)
    all_patterns = rightmove_patterns + zoopla_patterns + google_patterns + script_patterns
    
    for pattern in all_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            try:
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