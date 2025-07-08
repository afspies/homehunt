"""
Tests for CLI configuration models
"""

from datetime import date

import pytest
from pydantic import ValidationError

from homehunt.cli.config import (
    CommuteConfig,
    FurnishedType,
    LetType,
    SearchConfig,
    SearchRadius,
    SortOrder,
)
from homehunt.core.models import Portal, PropertyType


class TestSearchConfig:
    """Test SearchConfig model"""
    
    def test_minimal_config(self):
        """Test creating config with minimal parameters"""
        config = SearchConfig(location="SW1A 1AA")
        
        assert config.location == "SW1A 1AA"
        assert config.portals == [Portal.RIGHTMOVE, Portal.ZOOPLA]
        assert config.radius == SearchRadius.QUARTER_MILE
        assert config.furnished == FurnishedType.ANY
        assert config.sort_order == SortOrder.DATE_DESC
        assert config.max_results == 100
    
    def test_full_config(self):
        """Test creating config with all parameters"""
        config = SearchConfig(
            location="London",
            portals=[Portal.RIGHTMOVE],
            radius=SearchRadius.FIVE_MILES,
            min_price=1000,
            max_price=2000,
            min_bedrooms=1,
            max_bedrooms=3,
            property_types=[PropertyType.FLAT, PropertyType.HOUSE],
            furnished=FurnishedType.FURNISHED,
            let_type=LetType.LONG_TERM,
            pets_allowed=True,
            parking=True,
            garden=False,
            bills_included=True,
            student_friendly=False,
            dss_accepted=False,
            available_from=date(2024, 1, 1),
            include_let_agreed=True,
            sort_order=SortOrder.PRICE_ASC,
            max_results=200,
            keywords=["balcony", "modern"],
            exclude_keywords=["studio"],
            exclude_shared=False,
            exclude_retirement=True,
        )
        
        assert config.location == "London"
        assert config.portals == [Portal.RIGHTMOVE]
        assert config.min_price == 1000
        assert config.max_price == 2000
        assert config.pets_allowed is True
        assert config.keywords == ["balcony", "modern"]
    
    def test_price_validation(self):
        """Test price range validation"""
        # Valid price range
        config = SearchConfig(location="London", min_price=1000, max_price=2000)
        assert config.min_price == 1000
        assert config.max_price == 2000
        
        # Invalid price range
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(location="London", min_price=2000, max_price=1000)
        assert "max_price must be greater than min_price" in str(exc_info.value)
    
    def test_bedroom_validation(self):
        """Test bedroom range validation"""
        # Valid bedroom range
        config = SearchConfig(location="London", min_bedrooms=1, max_bedrooms=3)
        assert config.min_bedrooms == 1
        assert config.max_bedrooms == 3
        
        # Invalid bedroom range
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(location="London", min_bedrooms=3, max_bedrooms=1)
        assert "max_bedrooms must be greater than min_bedrooms" in str(exc_info.value)
    
    def test_location_validation(self):
        """Test location validation"""
        # Valid locations
        SearchConfig(location="SW1")
        SearchConfig(location="London")
        SearchConfig(location="E14 9RH")
        
        # Invalid location (too short)
        with pytest.raises(ValidationError):
            SearchConfig(location="A")
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary"""
        config = SearchConfig(
            location="London",
            portals=[Portal.RIGHTMOVE],
            property_types=[PropertyType.FLAT],
            furnished=FurnishedType.FURNISHED,
            radius=SearchRadius.ONE_MILE,
            available_from=date(2024, 1, 1),
        )
        
        data = config.to_dict()
        
        assert data["location"] == "London"
        assert data["portals"] == ["rightmove"]
        assert data["property_types"] == ["flat"]
        assert data["furnished"] == "furnished"
        assert data["radius"] == 1.0
        assert data["available_from"] == "2024-01-01"


class TestCommuteConfig:
    """Test CommuteConfig model"""
    
    def test_minimal_config(self):
        """Test creating config with minimal parameters"""
        config = CommuteConfig(
            destination="King's Cross Station",
            max_commute_time=45
        )
        
        assert config.destination == "King's Cross Station"
        assert config.max_commute_time == 45
        assert config.transport_modes == ["public_transport", "cycling"]
        assert config.departure_time == "08:00"
    
    def test_custom_transport_modes(self):
        """Test custom transport modes"""
        config = CommuteConfig(
            destination="EC2A 4BX",
            max_commute_time=30,
            transport_modes=["walking", "driving"]
        )
        
        assert config.transport_modes == ["walking", "driving"]
    
    def test_invalid_transport_mode(self):
        """Test invalid transport mode validation"""
        with pytest.raises(ValidationError) as exc_info:
            CommuteConfig(
                destination="London",
                max_commute_time=30,
                transport_modes=["flying"]
            )
        assert "Invalid transport mode: flying" in str(exc_info.value)
    
    def test_departure_time_validation(self):
        """Test departure time format validation"""
        # Valid formats
        config = CommuteConfig(
            destination="London",
            max_commute_time=30,
            departure_time="09:30"
        )
        assert config.departure_time == "09:30"
        
        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            CommuteConfig(
                destination="London",
                max_commute_time=30,
                departure_time="25:00"
            )
        assert "Departure time must be in HH:MM format" in str(exc_info.value)
        
        # Invalid format (no colon)
        with pytest.raises(ValidationError) as exc_info:
            CommuteConfig(
                destination="London",
                max_commute_time=30,
                departure_time="0930"
            )
        assert "Departure time must be in HH:MM format" in str(exc_info.value)
    
    def test_commute_time_validation(self):
        """Test commute time range validation"""
        # Valid range
        CommuteConfig(destination="London", max_commute_time=1)
        CommuteConfig(destination="London", max_commute_time=180)
        
        # Invalid range
        with pytest.raises(ValidationError):
            CommuteConfig(destination="London", max_commute_time=0)
        
        with pytest.raises(ValidationError):
            CommuteConfig(destination="London", max_commute_time=181)