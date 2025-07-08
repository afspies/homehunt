"""
Tests for TravelTime models
"""

from datetime import datetime

import pytest

from homehunt.traveltime.models import CommuteResult, GeocodingResult, Location, TravelTimeRequest


class TestLocation:
    """Test Location model"""
    
    def test_location_creation(self):
        """Test creating a location"""
        location = Location(
            id="test_location",
            lat=51.5074,
            lng=-0.1278
        )
        
        assert location.id == "test_location"
        assert location.lat == 51.5074
        assert location.lng == -0.1278
    
    def test_location_validation(self):
        """Test location validation"""
        # Pydantic v2 ValidationError instead of ValueError
        from pydantic import ValidationError
        # Test missing required field
        with pytest.raises(ValidationError):
            Location(lat=51.5074, lng=-0.1278)  # Missing id field


class TestCommuteResult:
    """Test CommuteResult model"""
    
    def test_commute_result_creation(self):
        """Test creating a commute result"""
        result = CommuteResult(
            property_id="test_property",
            destination="Canary Wharf",
            public_transport=30,
            cycling=25,
            walking=90,
            driving=20
        )
        
        assert result.property_id == "test_property"
        assert result.destination == "Canary Wharf"
        assert result.public_transport == 30
        assert result.cycling == 25
        assert result.walking == 90
        assert result.driving == 20
        assert result.success is True
        assert result.error_message is None
        assert isinstance(result.calculated_at, datetime)
    
    def test_commute_result_with_error(self):
        """Test creating a commute result with error"""
        result = CommuteResult(
            property_id="test_property",
            destination="Invalid Location",
            success=False,
            error_message="Failed to geocode destination"
        )
        
        assert result.success is False
        assert result.error_message == "Failed to geocode destination"
        assert result.public_transport is None
        assert result.cycling is None
    
    def test_commute_result_partial_data(self):
        """Test commute result with partial transport data"""
        result = CommuteResult(
            property_id="test_property",
            destination="Test Destination",
            public_transport=45,
            cycling=None,  # Not available
            walking=120,
            driving=None   # Not available
        )
        
        assert result.public_transport == 45
        assert result.cycling is None
        assert result.walking == 120
        assert result.driving is None


class TestGeocodingResult:
    """Test GeocodingResult model"""
    
    def test_geocoding_result_creation(self):
        """Test creating a geocoding result"""
        result = GeocodingResult(
            address="London, UK",
            lat=51.5074,
            lng=-0.1278,
            formatted_address="London, United Kingdom",
            confidence=0.95
        )
        
        assert result.address == "London, UK"
        assert result.lat == 51.5074
        assert result.lng == -0.1278
        assert result.formatted_address == "London, United Kingdom"
        assert result.confidence == 0.95
    
    def test_geocoding_result_minimal(self):
        """Test geocoding result with minimal data"""
        result = GeocodingResult(
            address="Test Address",
            lat=50.0,
            lng=0.0
        )
        
        assert result.address == "Test Address"
        assert result.lat == 50.0
        assert result.lng == 0.0
        assert result.formatted_address is None
        assert result.confidence is None


class TestTravelTimeRequest:
    """Test TravelTimeRequest model"""
    
    def test_request_creation(self):
        """Test creating a TravelTime API request"""
        locations = [
            Location(id="origin", lat=51.5074, lng=-0.1278),
            Location(id="destination", lat=51.5155, lng=-0.0922)
        ]
        
        departure_searches = [{
            "id": "test_search",
            "coords": {"lat": 51.5074, "lng": -0.1278},
            "transportation": {"type": "public_transport"},
            "departure_time": "08:00",
            "travel_time": 3600
        }]
        
        request = TravelTimeRequest(
            locations=locations,
            departure_searches=departure_searches
        )
        
        assert len(request.locations) == 2
        assert request.locations[0].id == "origin"
        assert request.departure_searches == departure_searches
        assert request.arrival_searches is None
    
    def test_request_with_arrivals(self):
        """Test request with arrival searches"""
        locations = [Location(id="test", lat=51.5074, lng=-0.1278)]
        
        arrival_searches = [{
            "id": "arrival_search",
            "coords": {"lat": 51.5155, "lng": -0.0922},
            "transportation": {"type": "cycling"},
            "arrival_time": "09:00",
            "travel_time": 1800
        }]
        
        request = TravelTimeRequest(
            locations=locations,
            arrival_searches=arrival_searches
        )
        
        assert request.arrival_searches == arrival_searches
        assert request.departure_searches is None