"""
TravelTime API data models
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    """Geographic location with coordinates"""
    
    id: str = Field(description="Unique identifier for this location")
    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")


class TransportMode(BaseModel):
    """Transport mode configuration"""
    
    type: str = Field(description="Transport type (public_transport, driving, cycling, walking)")
    max_travel_time: int = Field(description="Maximum travel time in seconds")


class TravelTimeRequest(BaseModel):
    """Request model for TravelTime API"""
    
    locations: List[Location] = Field(description="List of locations")
    departure_searches: Optional[List[Dict]] = Field(None, description="Departure searches")
    arrival_searches: Optional[List[Dict]] = Field(None, description="Arrival searches")


class CommuteResult(BaseModel):
    """Result of commute time calculation"""
    
    property_id: str = Field(description="Property identifier")
    destination: str = Field(description="Destination address")
    
    # Travel times in minutes for different modes
    public_transport: Optional[int] = Field(None, description="Public transport time in minutes")
    driving: Optional[int] = Field(None, description="Driving time in minutes")
    cycling: Optional[int] = Field(None, description="Cycling time in minutes")
    walking: Optional[int] = Field(None, description="Walking time in minutes")
    
    # Additional metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="When calculated")
    success: bool = Field(True, description="Whether calculation was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class GeocodingResult(BaseModel):
    """Result of geocoding an address"""
    
    address: str = Field(description="Original address")
    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")
    formatted_address: Optional[str] = Field(None, description="Formatted address from API")
    confidence: Optional[float] = Field(None, description="Confidence score")