"""
Tests for URL builders
"""

from datetime import date
from urllib.parse import parse_qs, urlparse

import pytest

from homehunt.cli.config import FurnishedType, SearchConfig, SortOrder
from homehunt.cli.url_builder import RightmoveURLBuilder, ZooplaURLBuilder, build_search_urls
from homehunt.core.models import Portal, PropertyType


class TestRightmoveURLBuilder:
    """Test Rightmove URL builder"""
    
    def test_basic_url(self):
        """Test basic URL generation"""
        config = SearchConfig(location="SW1A 1AA")
        url = RightmoveURLBuilder.build_url(config)
        
        assert url.startswith("https://www.rightmove.co.uk/property-to-rent/find.html")
        assert "searchLocation=SW1A%201AA" in url
        assert "sortType=6" in url  # Default sort by date
    
    def test_price_filters(self):
        """Test price filter parameters"""
        config = SearchConfig(
            location="London",
            min_price=1000,
            max_price=2000
        )
        url = RightmoveURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["minPrice"] == ["1000"]
        assert params["maxPrice"] == ["2000"]
    
    def test_bedroom_filters(self):
        """Test bedroom filter parameters"""
        config = SearchConfig(
            location="London",
            min_bedrooms=2,
            max_bedrooms=4
        )
        url = RightmoveURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["minBedrooms"] == ["2"]
        assert params["maxBedrooms"] == ["4"]
    
    def test_property_types(self):
        """Test property type parameters"""
        config = SearchConfig(
            location="London",
            property_types=[PropertyType.FLAT, PropertyType.HOUSE]
        )
        url = RightmoveURLBuilder.build_url(config)
        
        # Rightmove uses propertyTypes[] array parameters
        assert "propertyTypes[]=flats" in url
        assert "propertyTypes[]=houses" in url
    
    def test_furnished_status(self):
        """Test furnished status parameter"""
        config = SearchConfig(
            location="London",
            furnished=FurnishedType.FURNISHED
        )
        url = RightmoveURLBuilder.build_url(config)
        
        assert "furnishTypes=furnished" in url
    
    def test_additional_features(self):
        """Test additional feature parameters"""
        config = SearchConfig(
            location="London",
            parking=True,
            garden=True,
            pets_allowed=True
        )
        url = RightmoveURLBuilder.build_url(config)
        
        assert "mustHave[]=parking" in url
        assert "mustHave[]=garden" in url
        assert "petsAllowed=true" in url
    
    def test_sort_order(self):
        """Test sort order mapping"""
        test_cases = [
            (SortOrder.PRICE_ASC, "sortType=1"),
            (SortOrder.PRICE_DESC, "sortType=2"),
            (SortOrder.DATE_DESC, "sortType=6"),
            (SortOrder.DATE_ASC, "sortType=10"),
        ]
        
        for sort_order, expected in test_cases:
            config = SearchConfig(location="London", sort_order=sort_order)
            url = RightmoveURLBuilder.build_url(config)
            assert expected in url
    
    def test_radius_conversion(self):
        """Test radius conversion from miles to km"""
        config = SearchConfig(
            location="London",
            radius=1.0  # 1 mile
        )
        url = RightmoveURLBuilder.build_url(config)
        
        # 1 mile ≈ 1.6 km, rounded to 2
        assert "radius=2" in url
    
    def test_pagination_urls(self):
        """Test pagination URL generation"""
        base_url = "https://www.rightmove.co.uk/property-to-rent/find.html?searchLocation=London"
        
        # Test with results that fit on one page
        urls = RightmoveURLBuilder.get_pagination_urls(base_url, 20, 24)
        assert len(urls) == 1
        assert urls[0] == base_url
        
        # Test with multiple pages
        urls = RightmoveURLBuilder.get_pagination_urls(base_url, 100, 24)
        assert len(urls) == 5  # 100 results / 24 per page = 5 pages
        assert urls[0] == base_url
        assert urls[1] == f"{base_url}&index=24"
        assert urls[2] == f"{base_url}&index=48"
        assert urls[3] == f"{base_url}&index=72"
        assert urls[4] == f"{base_url}&index=96"


class TestZooplaURLBuilder:
    """Test Zoopla URL builder"""
    
    def test_basic_url(self):
        """Test basic URL generation"""
        config = SearchConfig(location="SW1A 1AA")
        url = ZooplaURLBuilder.build_url(config)
        
        assert url.startswith("https://www.zoopla.co.uk/to-rent/property/sw1a-1aa/")
        assert "results_sort=most_recent" in url
    
    def test_location_cleaning(self):
        """Test location cleaning for URL"""
        config = SearchConfig(location="King's Cross, London N1C")
        url = ZooplaURLBuilder.build_url(config)
        
        # Should clean special characters and spaces
        assert "/kings-cross-london-n1c/" in url
    
    def test_property_types_in_path(self):
        """Test property types included in URL path"""
        config = SearchConfig(
            location="London",
            property_types=[PropertyType.FLAT, PropertyType.STUDIO]
        )
        url = ZooplaURLBuilder.build_url(config)
        
        assert "/flats/" in url
        assert "/studios/" in url
    
    def test_price_filters(self):
        """Test price filter parameters"""
        config = SearchConfig(
            location="London",
            min_price=1500,
            max_price=2500
        )
        url = ZooplaURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["price_min"] == ["1500"]
        assert params["price_max"] == ["2500"]
    
    def test_bedroom_filters(self):
        """Test bedroom filter parameters"""
        config = SearchConfig(
            location="London",
            min_bedrooms=1,
            max_bedrooms=2
        )
        url = ZooplaURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["beds_min"] == ["1"]
        assert params["beds_max"] == ["2"]
    
    def test_additional_filters(self):
        """Test additional filter parameters"""
        config = SearchConfig(
            location="London",
            pets_allowed=True,
            bills_included=True,
            dss_accepted=True,
            student_friendly=True
        )
        url = ZooplaURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["pets_allowed"] == ["yes"]
        assert params["bills_included"] == ["yes"]
        assert params["accept_dss"] == ["yes"]
        assert params["available_to"] == ["students"]
    
    def test_available_from_date(self):
        """Test available from date formatting"""
        config = SearchConfig(
            location="London",
            available_from=date(2024, 3, 15)
        )
        url = ZooplaURLBuilder.build_url(config)
        
        # Zoopla uses YYYYMMDD format
        assert "available_from=20240315" in url
    
    def test_keywords(self):
        """Test keyword parameters"""
        config = SearchConfig(
            location="London",
            keywords=["balcony", "modern"],
            exclude_keywords=["basement"]
        )
        url = ZooplaURLBuilder.build_url(config)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params["keywords"] == ["balcony modern"]
        assert params["exclude_keywords"] == ["basement"]
    
    def test_sort_order(self):
        """Test sort order mapping"""
        test_cases = [
            (SortOrder.PRICE_ASC, "results_sort=rental_price_ascending"),
            (SortOrder.PRICE_DESC, "results_sort=rental_price_descending"),
            (SortOrder.DATE_DESC, "results_sort=most_recent"),
            (SortOrder.DATE_ASC, "results_sort=oldest_first"),
        ]
        
        for sort_order, expected in test_cases:
            config = SearchConfig(location="London", sort_order=sort_order)
            url = ZooplaURLBuilder.build_url(config)
            assert expected in url
    
    def test_pagination_urls(self):
        """Test pagination URL generation"""
        base_url = "https://www.zoopla.co.uk/to-rent/property/london/?price_max=2000"
        
        # Test with results that fit on one page
        urls = ZooplaURLBuilder.get_pagination_urls(base_url, 20, 25)
        assert len(urls) == 1
        assert urls[0] == base_url
        
        # Test with multiple pages
        urls = ZooplaURLBuilder.get_pagination_urls(base_url, 100, 25)
        assert len(urls) == 4  # 100 results / 25 per page = 4 pages
        assert urls[0] == base_url
        assert urls[1] == f"{base_url}&pn=2"
        assert urls[2] == f"{base_url}&pn=3"
        assert urls[3] == f"{base_url}&pn=4"


class TestBuildSearchURLs:
    """Test the main build_search_urls function"""
    
    def test_all_portals(self):
        """Test building URLs for all portals"""
        config = SearchConfig(
            location="London",
            portals=[Portal.RIGHTMOVE, Portal.ZOOPLA]
        )
        urls = build_search_urls(config)
        
        assert Portal.RIGHTMOVE in urls
        assert Portal.ZOOPLA in urls
        assert len(urls[Portal.RIGHTMOVE]) == 1
        assert len(urls[Portal.ZOOPLA]) == 1
        
        assert urls[Portal.RIGHTMOVE][0].startswith("https://www.rightmove.co.uk")
        assert urls[Portal.ZOOPLA][0].startswith("https://www.zoopla.co.uk")
    
    def test_single_portal(self):
        """Test building URL for single portal"""
        config = SearchConfig(
            location="London",
            portals=[Portal.RIGHTMOVE]
        )
        urls = build_search_urls(config)
        
        assert Portal.RIGHTMOVE in urls
        assert Portal.ZOOPLA not in urls
    
    def test_consistent_parameters(self):
        """Test that parameters are consistently applied across portals"""
        config = SearchConfig(
            location="E14 9RH",
            portals=[Portal.RIGHTMOVE, Portal.ZOOPLA],
            min_price=1000,
            max_price=2000,
            min_bedrooms=2
        )
        urls = build_search_urls(config)
        
        # Check Rightmove URL
        rightmove_url = urls[Portal.RIGHTMOVE][0]
        assert "minPrice=1000" in rightmove_url
        assert "maxPrice=2000" in rightmove_url
        assert "minBedrooms=2" in rightmove_url
        
        # Check Zoopla URL
        zoopla_url = urls[Portal.ZOOPLA][0]
        assert "price_min=1000" in zoopla_url
        assert "price_max=2000" in zoopla_url
        assert "beds_min=2" in zoopla_url