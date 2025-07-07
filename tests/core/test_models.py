"""
Tests for core data models
"""

from datetime import datetime

from homehunt.core.models import (
    ExtractionMethod,
    Portal,
    PropertyListing,
    PropertyType,
    ScrapingResult,
    SearchConfig,
)


class TestPropertyListing:
    """Test PropertyListing model"""

    def test_create_minimal_listing(self):
        """Test creating a minimal property listing"""
        listing = PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="164209706",
            url="https://www.rightmove.co.uk/properties/164209706",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )

        assert listing.portal == Portal.RIGHTMOVE
        assert listing.property_id == "164209706"
        assert listing.uid == "rightmove:164209706"
        assert listing.extraction_method == ExtractionMethod.DIRECT_HTTP
        assert isinstance(listing.first_seen, datetime)
        assert isinstance(listing.last_scraped, datetime)
        assert listing.scrape_count == 1

    def test_create_full_listing(self):
        """Test creating a full property listing with all fields"""
        listing = PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="164209706",
            url="https://www.rightmove.co.uk/properties/164209706",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
            address="Grosvenor Road, London, SW1V",
            postcode="SW1V 3SA",
            area="Victoria",
            price="£2,385 pcm",
            bedrooms=1,
            bathrooms=1,
            property_type=PropertyType.APARTMENT,
            furnished="Furnished",
            available_date="2024-01-01",
            description="Beautiful apartment in Victoria",
            features=["Balcony", "Parking", "Garden"],
            agent_name="Premium Properties",
            agent_phone="020 7123 4567",
            title="1 bedroom apartment for rent in Grosvenor Road, London, SW1V",
            images=["https://media.rightmove.co.uk/image1.jpg"],
            commute_public_transport=25,
            commute_cycling=15,
        )

        assert listing.address == "Grosvenor Road, London, SW1V"
        assert listing.postcode == "SW1V 3SA"
        assert listing.price_numeric == 238500  # £2,385 in pence
        assert listing.bedrooms == 1
        assert listing.property_type == PropertyType.APARTMENT
        assert len(listing.features) == 3
        assert listing.commute_public_transport == 25

    def test_uid_generation(self):
        """Test UID generation from portal and property_id"""
        listing = PropertyListing(
            portal=Portal.ZOOPLA,
            property_id="70186875",
            url="https://www.zoopla.co.uk/to-rent/details/70186875",
            extraction_method=ExtractionMethod.FIRECRAWL,
        )

        assert listing.uid == "zoopla:70186875"

    def test_price_parsing(self):
        """Test price parsing from various formats"""
        test_cases = [
            ("£2,385 pcm", 238500),
            ("£1,500 per month", 150000),
            ("£999 pcm", 99900),
            ("£10,000 pcm", 1000000),
            ("No price available", None),
            ("", None),
        ]

        for price_str, expected_pence in test_cases:
            listing = PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="test",
                url="https://example.com",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                price=price_str if price_str else None,
            )

            assert listing.price_numeric == expected_pence

    def test_property_type_normalization(self):
        """Test property type normalization"""
        test_cases = [
            ("flat", PropertyType.FLAT),
            ("Apartment", PropertyType.APARTMENT),
            ("House", PropertyType.HOUSE),
            ("Studio", PropertyType.STUDIO),
            ("Semi-detached house", PropertyType.HOUSE),
            ("Detached house", PropertyType.HOUSE),
            ("Unknown type", PropertyType.UNKNOWN),
        ]

        for input_type, expected_type in test_cases:
            listing = PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="test",
                url="https://example.com",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                property_type=input_type,
            )

            assert listing.property_type == expected_type

    def test_postcode_validation(self):
        """Test postcode validation"""
        test_cases = [
            ("SW1V 3SA", "SW1V 3SA"),
            ("sw1v 3sa", "SW1V 3SA"),
            ("W1A 0AX", "W1A 0AX"),
            ("Invalid postcode", "Invalid postcode"),  # Return as-is if invalid
            (None, None),
        ]

        for input_postcode, expected_postcode in test_cases:
            listing = PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="test",
                url="https://example.com",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                postcode=input_postcode,
            )

            assert listing.postcode == expected_postcode

    def test_from_extraction_result(self):
        """Test creating PropertyListing from extraction result"""
        extraction_result = {
            "address": "123 Test Street, London",
            "price": "£1,500 pcm",
            "bedrooms": 2,
            "property_type": "flat",
            "title": "2 bedroom flat for rent in Test Street, London",
        }

        listing = PropertyListing.from_extraction_result(
            portal="rightmove",
            property_id="123456",
            url="https://www.rightmove.co.uk/properties/123456",
            extraction_result=extraction_result,
            extraction_method="direct_http",
        )

        assert listing.portal == Portal.RIGHTMOVE
        assert listing.property_id == "123456"
        assert listing.uid == "rightmove:123456"
        assert listing.address == "123 Test Street, London"
        assert listing.price_numeric == 150000
        assert listing.bedrooms == 2
        assert listing.property_type == PropertyType.FLAT
        assert listing.extraction_method == ExtractionMethod.DIRECT_HTTP

    def test_to_dict(self):
        """Test converting to dictionary"""
        listing = PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="test",
            url="https://example.com",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
            address="Test Address",
            price="£1,000 pcm",
        )

        data = listing.to_dict()

        assert isinstance(data, dict)
        assert data["portal"] == "rightmove"
        assert data["property_id"] == "test"
        assert data["address"] == "Test Address"
        assert data["price"] == "£1,000 pcm"
        assert "first_seen" in data
        assert "last_scraped" in data


class TestSearchConfig:
    """Test SearchConfig model"""

    def test_create_basic_config(self):
        """Test creating basic search configuration"""
        config = SearchConfig(
            location="Victoria, London",
            min_price=1000,
            max_price=3000,
            min_bedrooms=1,
            max_bedrooms=2,
        )

        assert config.location == "Victoria, London"
        assert config.min_price == 1000
        assert config.max_price == 3000
        assert config.min_bedrooms == 1
        assert config.max_bedrooms == 2
        assert config.portals == [Portal.RIGHTMOVE, Portal.ZOOPLA]
        assert config.max_pages == 20

    def test_build_rightmove_url(self):
        """Test building Rightmove search URL"""
        config = SearchConfig(
            location="STATION^9491",
            radius=1.0,
            min_price=2250,
            max_price=3500,
            min_bedrooms=0,
            max_bedrooms=2,
            property_types=["flat", "house"],
            furnished="furnished",
        )

        url = config.build_rightmove_url()

        assert "rightmove.co.uk/property-to-rent/find.html" in url
        assert "locationIdentifier=STATION^9491" in url
        assert "radius=1.0" in url
        assert "minPrice=2250" in url
        assert "maxPrice=3500" in url
        assert "minBedrooms=0" in url
        assert "maxBedrooms=2" in url
        assert "propertyTypes=flat,house" in url
        assert "furnishTypes=furnished" in url

    def test_build_zoopla_url(self):
        """Test building Zoopla search URL"""
        config = SearchConfig(
            location="Victoria, London",
            radius=0.5,
            min_price=2000,
            max_price=4000,
            min_bedrooms=1,
            max_bedrooms=3,
            property_types=["flats"],
            furnished="unfurnished",
        )

        url = config.build_zoopla_url()

        assert "zoopla.co.uk/to-rent/property" in url
        assert "q=Victoria, London" in url
        assert "radius=0.5" in url
        assert "price_min=2000" in url
        assert "price_max=4000" in url
        assert "beds_min=1" in url
        assert "beds_max=3" in url
        assert "property_type=flats" in url
        assert "furnished_state=unfurnished" in url


class TestScrapingResult:
    """Test ScrapingResult model"""

    def test_create_successful_result(self):
        """Test creating successful scraping result"""
        result = ScrapingResult(
            url="https://www.rightmove.co.uk/properties/164209706",
            success=True,
            portal=Portal.RIGHTMOVE,
            property_id="164209706",
            response_time=0.17,
            content_length=327486,
            data={"price": "£2,385 pcm", "bedrooms": 1},
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )

        assert result.success is True
        assert result.portal == Portal.RIGHTMOVE
        assert result.property_id == "164209706"
        assert result.response_time == 0.17
        assert result.data["price"] == "£2,385 pcm"
        assert result.error is None

    def test_create_failed_result(self):
        """Test creating failed scraping result"""
        result = ScrapingResult(
            url="https://www.zoopla.co.uk/to-rent/details/70186875",
            success=False,
            portal=Portal.ZOOPLA,
            error="All URL patterns failed",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )

        assert result.success is False
        assert result.portal == Portal.ZOOPLA
        assert result.error == "All URL patterns failed"
        assert result.data is None
        assert result.property_id is None


# Example test data for integration tests
SAMPLE_PROPERTY_DATA = {
    "rightmove_property": {
        "portal": "rightmove",
        "property_id": "164209706",
        "url": "https://www.rightmove.co.uk/properties/164209706",
        "extraction_method": "direct_http",
        "address": "Grosvenor Road, London, SW1V",
        "postcode": "SW1V 3SA",
        "price": "£2,385 pcm",
        "bedrooms": 1,
        "property_type": "apartment",
        "title": "1 bedroom apartment for rent in Grosvenor Road, London, SW1V",
        "content_length": 327486,
        "images": ["https://media.rightmove.co.uk/image1.jpg"],
    },
    "zoopla_property": {
        "portal": "zoopla",
        "property_id": "70186875",
        "url": "https://www.zoopla.co.uk/to-rent/details/70186875",
        "extraction_method": "firecrawl",
        "address": "Test Road, London, E1",
        "postcode": "E1 6AN",
        "price": "£1,800 pcm",
        "bedrooms": 2,
        "property_type": "flat",
        "title": "2 bedroom flat to rent in Test Road, London",
        "content_length": 0,
        "images": [],
    },
}
