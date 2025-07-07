"""
Core data models for HomeHunt property scraping and analysis
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Portal(str, Enum):
    """Supported property portals"""

    RIGHTMOVE = "rightmove"
    ZOOPLA = "zoopla"


class PropertyType(str, Enum):
    """Property types"""

    FLAT = "flat"
    APARTMENT = "apartment"
    HOUSE = "house"
    STUDIO = "studio"
    MAISONETTE = "maisonette"
    BUNGALOW = "bungalow"
    UNKNOWN = "unknown"


class ExtractionMethod(str, Enum):
    """Method used to extract property data"""

    FIRECRAWL = "firecrawl"
    DIRECT_HTTP = "direct_http"
    HYBRID = "hybrid"


class PropertyListing(BaseModel):
    """
    Property listing data model optimized for hybrid scraping approach
    Based on comprehensive testing of Rightmove and Zoopla extraction
    """

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    # Core identification
    portal: Portal = Field(..., description="Property portal (rightmove/zoopla)")
    property_id: str = Field(..., description="Unique property ID from URL")
    url: str = Field(..., description="Direct property URL")
    uid: Optional[str] = Field(
        None, description="Unique identifier: portal:property_id"
    )

    # Location data (extracted from validation tests)
    address: Optional[str] = Field(None, description="Property address from title/h1")
    postcode: Optional[str] = Field(None, description="Full postcode if available")
    area: Optional[str] = Field(None, description="Area/district")

    # Property details (validated extractable fields)
    price: Optional[str] = Field(None, description="Raw price text (£2,385 pcm)")
    price_numeric: Optional[int] = Field(
        None, description="Parsed monthly rent in pence"
    )
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms from title")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    property_type: Optional[PropertyType] = Field(
        None, description="Property type from title"
    )

    # Additional property details
    furnished: Optional[str] = Field(None, description="Furnished status")
    available_date: Optional[str] = Field(None, description="Available from date")
    description: Optional[str] = Field(None, description="Property description")
    features: List[str] = Field(default_factory=list, description="Property features")

    # Agent and contact info
    agent_name: Optional[str] = Field(None, description="Estate agent name")
    agent_phone: Optional[str] = Field(None, description="Agent contact number")

    # Extraction method tracking
    extraction_method: ExtractionMethod = Field(
        ..., description="Method used for extraction"
    )
    content_length: Optional[int] = Field(None, description="Raw content size in bytes")

    # Metadata
    title: Optional[str] = Field(None, description="Page title (rich source of data)")
    images: List[str] = Field(default_factory=list, description="Property image URLs")

    # Tracking fields
    first_seen: datetime = Field(
        default_factory=datetime.utcnow, description="First discovery timestamp"
    )
    last_scraped: datetime = Field(
        default_factory=datetime.utcnow, description="Last successful scrape"
    )
    scrape_count: int = Field(default=1, description="Number of times scraped")

    # Commute analysis (filled by TravelTime integration)
    commute_public_transport: Optional[int] = Field(
        None, description="Public transport time in minutes"
    )
    commute_cycling: Optional[int] = Field(None, description="Cycling time in minutes")
    commute_walking: Optional[int] = Field(None, description="Walking time in minutes")
    commute_driving: Optional[int] = Field(None, description="Driving time in minutes")

    @model_validator(mode="after")
    def generate_uid(self):
        """Generate unique identifier from portal and property_id"""
        if not self.uid and self.portal and self.property_id:
            portal_str = (
                self.portal.value if hasattr(self.portal, "value") else str(self.portal)
            )
            self.uid = f"{portal_str}:{self.property_id}"
        return self

    @model_validator(mode="after")
    def parse_price_numeric(self):
        """Parse numeric price from price string"""
        if self.price_numeric is None and self.price:
            # Extract numeric value from "£2,385 pcm" format
            match = re.search(r"£([\d,]+)", self.price)
            if match:
                numeric_str = match.group(1).replace(",", "")
                try:
                    self.price_numeric = int(numeric_str) * 100  # Convert to pence
                except ValueError:
                    pass
        return self

    @field_validator("property_type", mode="before")
    @classmethod
    def normalize_property_type(cls, v):
        """Normalize property type from extracted text"""
        if v is None:
            return None

        v_lower = str(v).lower()

        # Map common variations
        type_mapping = {
            "flat": PropertyType.FLAT,
            "apartment": PropertyType.APARTMENT,
            "house": PropertyType.HOUSE,
            "studio": PropertyType.STUDIO,
            "maisonette": PropertyType.MAISONETTE,
            "bungalow": PropertyType.BUNGALOW,
            "semi-detached": PropertyType.HOUSE,
            "detached": PropertyType.HOUSE,
            "terraced": PropertyType.HOUSE,
            "end terrace": PropertyType.HOUSE,
        }

        for key, property_type in type_mapping.items():
            if key in v_lower:
                return property_type

        return PropertyType.UNKNOWN

    @field_validator("postcode", mode="before")
    @classmethod
    def validate_postcode(cls, v):
        """Validate UK postcode format"""
        if v is None or v == "":
            return None if v is None else ""

        # UK postcode regex pattern
        postcode_pattern = r"^[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$"
        if re.match(postcode_pattern, v.upper()):
            return v.upper()
        return v  # Return as-is if not valid postcode format

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_extraction_result(
        cls,
        portal: str,
        property_id: str,
        url: str,
        extraction_result: Dict[str, Any],
        extraction_method: str,
    ) -> "PropertyListing":
        """
        Create PropertyListing from extraction result

        Args:
            portal: Property portal name
            property_id: Unique property ID
            url: Property URL
            extraction_result: Raw extraction data
            extraction_method: Method used for extraction

        Returns:
            PropertyListing instance
        """
        return cls(
            portal=Portal(portal),
            property_id=property_id,
            url=url,
            extraction_method=ExtractionMethod(extraction_method),
            **extraction_result,
        )


class SearchConfig(BaseModel):
    """Configuration for property search"""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    # Location parameters
    location: str = Field(..., description="Search location (area, postcode, station)")
    radius: Optional[float] = Field(None, description="Search radius in miles")

    # Property criteria
    min_price: Optional[int] = Field(None, description="Minimum rent in pounds")
    max_price: Optional[int] = Field(None, description="Maximum rent in pounds")
    min_bedrooms: Optional[int] = Field(None, description="Minimum bedrooms")
    max_bedrooms: Optional[int] = Field(None, description="Maximum bedrooms")
    property_types: List[str] = Field(
        default_factory=list, description="Property types to include"
    )

    # Additional filters
    furnished: Optional[str] = Field(None, description="Furnished status filter")
    available_from: Optional[str] = Field(None, description="Available from date")

    # Search parameters
    portals: List[Portal] = Field(
        default_factory=lambda: [Portal.RIGHTMOVE, Portal.ZOOPLA]
    )
    max_pages: int = Field(default=20, description="Maximum pages to scrape")

    # Commute analysis
    commute_destinations: List[str] = Field(
        default_factory=list, description="Commute destinations"
    )
    max_commute_time: Optional[int] = Field(
        None, description="Maximum commute time in minutes"
    )

    def build_rightmove_url(self) -> str:
        """Build Rightmove search URL"""
        params = {
            "locationIdentifier": self.location,
            "radius": self.radius or 1.0,
            "propertyTypes": (
                ",".join(self.property_types) if self.property_types else "flat,house"
            ),
            "includeLetAgreed": "false",
            "mustHave": "",
            "dontShow": "",
            "furnishTypes": self.furnished or "",
            "keywords": "",
        }

        if self.min_price:
            params["minPrice"] = self.min_price
        if self.max_price:
            params["maxPrice"] = self.max_price
        if self.min_bedrooms is not None:
            params["minBedrooms"] = self.min_bedrooms
        if self.max_bedrooms is not None:
            params["maxBedrooms"] = self.max_bedrooms

        # Build query string
        query_params = []
        for key, value in params.items():
            if value is not None and value != "" and value != 0:
                query_params.append(f"{key}={value}")
            elif key in ["minBedrooms", "maxBedrooms"] and value == 0:
                # Include 0 bedrooms for bedroom filters
                query_params.append(f"{key}={value}")

        base_url = "https://www.rightmove.co.uk/property-to-rent/find.html"
        return f"{base_url}?{'&'.join(query_params)}"

    def build_zoopla_url(self) -> str:
        """Build Zoopla search URL"""
        params = {
            "q": self.location,
            "radius": self.radius or 1.0,
            "price_frequency": "per_month",
            "property_type": (
                ",".join(self.property_types) if self.property_types else "flats,houses"
            ),
            "furnished_state": self.furnished or "",
            "search_source": "to-rent",
        }

        if self.min_price:
            params["price_min"] = self.min_price
        if self.max_price:
            params["price_max"] = self.max_price
        if self.min_bedrooms is not None:
            params["beds_min"] = self.min_bedrooms
        if self.max_bedrooms is not None:
            params["beds_max"] = self.max_bedrooms

        # Build query string
        query_params = []
        for key, value in params.items():
            if value is not None and value != "" and value != 0:
                query_params.append(f"{key}={value}")
            elif key in ["beds_min", "beds_max"] and value == 0:
                # Include 0 bedrooms for bedroom filters
                query_params.append(f"{key}={value}")

        base_url = "https://www.zoopla.co.uk/to-rent/property"
        return f"{base_url}?{'&'.join(query_params)}"


class ScrapingResult(BaseModel):
    """Result of a scraping operation"""

    model_config = ConfigDict(validate_assignment=True)

    url: str = Field(..., description="Scraped URL")
    success: bool = Field(..., description="Whether scraping was successful")
    portal: Portal = Field(..., description="Property portal")
    property_id: Optional[str] = Field(None, description="Extracted property ID")

    # Timing and performance
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    content_length: Optional[int] = Field(None, description="Content length in bytes")

    # Result data
    data: Optional[Dict[str, Any]] = Field(None, description="Extracted property data")
    error: Optional[str] = Field(None, description="Error message if failed")

    # Metadata
    extraction_method: ExtractionMethod = Field(
        ..., description="Method used for extraction"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Scraping timestamp"
    )
