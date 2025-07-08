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