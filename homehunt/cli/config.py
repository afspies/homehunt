"""
Search configuration models for CLI commands
Defines all available search parameters and filters
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from homehunt.core.models import Portal, PropertyType


class SortOrder(str, Enum):
    """Sort order options for search results"""
    
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    DATE_DESC = "date_desc"  # Most recent first
    DATE_ASC = "date_asc"    # Oldest first


class FurnishedType(str, Enum):
    """Furnished status options"""
    
    FURNISHED = "furnished"
    UNFURNISHED = "unfurnished"
    PART_FURNISHED = "part_furnished"
    ANY = "any"


class LetType(str, Enum):
    """Let type options"""
    
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    ANY = "any"


class SearchRadius(float, Enum):
    """Search radius options in miles"""
    
    QUARTER_MILE = 0.25
    HALF_MILE = 0.5
    ONE_MILE = 1.0
    THREE_MILES = 3.0
    FIVE_MILES = 5.0
    TEN_MILES = 10.0
    FIFTEEN_MILES = 15.0
    TWENTY_MILES = 20.0
    THIRTY_MILES = 30.0
    FORTY_MILES = 40.0


class SearchConfig(BaseModel):
    """
    Comprehensive search configuration for property searches
    Supports both Rightmove and Zoopla parameters
    """
    
    # Portal selection
    portals: List[Portal] = Field(
        default=[Portal.RIGHTMOVE, Portal.ZOOPLA],
        description="Property portals to search"
    )
    
    # Location parameters
    location: str = Field(
        ...,
        description="Search location (postcode, area, or city)",
        min_length=2
    )
    radius: Optional[SearchRadius] = Field(
        SearchRadius.QUARTER_MILE,
        description="Search radius from location"
    )
    
    # Price filters
    min_price: Optional[int] = Field(
        None,
        description="Minimum monthly rent in pounds",
        ge=0
    )
    max_price: Optional[int] = Field(
        None,
        description="Maximum monthly rent in pounds",
        ge=0
    )
    
    # Property characteristics
    min_bedrooms: Optional[int] = Field(
        None,
        description="Minimum number of bedrooms",
        ge=0
    )
    max_bedrooms: Optional[int] = Field(
        None,
        description="Maximum number of bedrooms",
        ge=0
    )
    property_types: Optional[List[PropertyType]] = Field(
        None,
        description="Property types to include"
    )
    
    # Additional filters
    furnished: FurnishedType = Field(
        FurnishedType.ANY,
        description="Furnished status"
    )
    let_type: LetType = Field(
        LetType.LONG_TERM,
        description="Let type preference"
    )
    pets_allowed: Optional[bool] = Field(
        None,
        description="Must allow pets"
    )
    parking: Optional[bool] = Field(
        None,
        description="Must have parking"
    )
    garden: Optional[bool] = Field(
        None,
        description="Must have garden"
    )
    bills_included: Optional[bool] = Field(
        None,
        description="Bills included in rent"
    )
    student_friendly: Optional[bool] = Field(
        None,
        description="Suitable for students"
    )
    dss_accepted: Optional[bool] = Field(
        None,
        description="DSS/Housing benefit accepted"
    )
    
    # Availability filters
    available_from: Optional[date] = Field(
        None,
        description="Available from date"
    )
    include_let_agreed: bool = Field(
        False,
        description="Include properties marked as let agreed"
    )
    
    # Search behavior
    sort_order: SortOrder = Field(
        SortOrder.DATE_DESC,
        description="Sort order for results"
    )
    max_results: Optional[int] = Field(
        100,
        description="Maximum number of results to return",
        ge=1,
        le=1000
    )
    
    # Advanced options
    keywords: Optional[List[str]] = Field(
        None,
        description="Keywords to search in descriptions"
    )
    exclude_keywords: Optional[List[str]] = Field(
        None,
        description="Keywords to exclude from results"
    )
    
    # Shared ownership and retirement
    exclude_shared: bool = Field(
        True,
        description="Exclude shared ownership properties"
    )
    exclude_retirement: bool = Field(
        True,
        description="Exclude retirement properties"
    )
    
    # Geographic filtering
    exclude_areas: Optional[List[str]] = Field(
        None,
        description="Areas to exclude from search results"
    )
    
    # Property age and new build preferences
    new_build_preferred: bool = Field(
        False,
        description="Prefer new build properties"
    )
    preferred_features: Optional[List[str]] = Field(
        None,
        description="Preferred property features (new build, modern, etc.)"
    )
    
    @field_validator('max_price')
    def validate_price_range(cls, v, info):
        """Ensure max_price is greater than min_price"""
        if v is not None and info.data.get('min_price') is not None:
            if v < info.data['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v
    
    @field_validator('max_bedrooms')
    def validate_bedroom_range(cls, v, info):
        """Ensure max_bedrooms is greater than min_bedrooms"""
        if v is not None and info.data.get('min_bedrooms') is not None:
            if v < info.data['min_bedrooms']:
                raise ValueError('max_bedrooms must be greater than min_bedrooms')
        return v
    
    def to_dict(self) -> dict:
        """Convert to dictionary for URL building"""
        data = self.model_dump(exclude_none=True)
        
        # Convert enums to strings
        if 'portals' in data:
            data['portals'] = [p.value for p in data['portals']]
        if 'property_types' in data:
            data['property_types'] = [pt.value for pt in data['property_types']]
        if 'furnished' in data:
            data['furnished'] = data['furnished'].value
        if 'let_type' in data:
            data['let_type'] = data['let_type'].value
        if 'sort_order' in data:
            data['sort_order'] = data['sort_order'].value
        if 'radius' in data:
            data['radius'] = float(data['radius'])
        
        # Convert date to string
        if 'available_from' in data:
            data['available_from'] = data['available_from'].isoformat()
            
        return data


class CommuteConfig(BaseModel):
    """
    Commute filtering configuration
    Used after property search to filter by commute times
    """
    
    destination: str = Field(
        ...,
        description="Commute destination (address or postcode)",
        min_length=2
    )
    
    max_commute_time: int = Field(
        ...,
        description="Maximum commute time in minutes",
        ge=1,
        le=180
    )
    
    transport_modes: List[str] = Field(
        default=["public_transport", "cycling"],
        description="Transport modes to consider"
    )
    
    departure_time: Optional[str] = Field(
        "08:00",
        description="Departure time for commute calculation (HH:MM format)"
    )
    
    @field_validator('transport_modes')
    def validate_transport_modes(cls, v):
        """Validate transport modes"""
        valid_modes = {"public_transport", "cycling", "walking", "driving"}
        for mode in v:
            if mode not in valid_modes:
                raise ValueError(f"Invalid transport mode: {mode}. Must be one of {valid_modes}")
        return v
    
    @field_validator('departure_time')
    def validate_departure_time(cls, v):
        """Validate departure time format"""
        if v:
            try:
                hours, minutes = v.split(':')
                hour = int(hours)
                minute = int(minutes)
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValueError("Departure time must be in HH:MM format (e.g., 08:00)")
        return v