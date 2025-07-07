"""
Tests for direct HTTP scraper functionality
"""

from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from homehunt.core.models import ExtractionMethod, Portal
from homehunt.scrapers.direct_http import DirectHTTPScraper


class TestDirectHTTPScraper:
    """Test DirectHTTPScraper functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create DirectHTTPScraper instance for testing"""
        return DirectHTTPScraper()
    
    @pytest.fixture
    def sample_rightmove_html(self):
        """Sample Rightmove HTML for testing"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>1 bedroom flat for rent in Victoria, London, SW1V | Rightmove</title>
        </head>
        <body>
            <h1>1 bedroom flat for rent in Victoria, London, SW1V</h1>
            <span data-testid="price">£2,385 pcm</span>
            <div class="propertyKeyFeatures">
                <span>1 bedroom</span>
                <span>1 bathroom</span>
                <span>Furnished</span>
            </div>
            <div data-testid="property-address">Grosvenor Road, London, SW1V 3SA</div>
            <div class="propertyDetailDescription">
                Beautiful one bedroom apartment in the heart of Victoria with excellent transport links.
            </div>
            <div class="propertyKeyFeatures">
                <li>Balcony</li>
                <li>Parking</li>
                <li>Garden</li>
            </div>
            <div class="contactBranchName">Premium Properties</div>
            <a href="tel:02071234567">020 7123 4567</a>
            <img src="https://media.rightmove.co.uk/image1.jpg" alt="property image">
            <img src="https://media.rightmove.co.uk/image2.jpg" alt="bedroom image">
        </body>
        </html>
        """
    
    def test_scraper_initialization(self, scraper):
        """Test scraper initialization"""
        assert scraper.get_portal() == Portal.RIGHTMOVE
        assert scraper.get_extraction_method() == ExtractionMethod.DIRECT_HTTP
        assert "Mozilla" in scraper.client.headers["User-Agent"]
    
    def test_extract_property_id(self, scraper):
        """Test property ID extraction from Rightmove URLs"""
        test_cases = [
            ("https://www.rightmove.co.uk/properties/123456", "123456"),
            ("https://www.rightmove.co.uk/properties/789012?param=value", "789012"),
            ("https://www.rightmove.co.uk/properties/", None),
            ("https://example.com/unknown", None),
        ]
        
        for url, expected_id in test_cases:
            result = scraper.extract_property_id(url)
            assert result == expected_id
    
    def test_extract_title(self, scraper, sample_rightmove_html):
        """Test title extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        title = scraper._extract_title(soup)
        
        assert title == "1 bedroom flat for rent in Victoria, London, SW1V | Rightmove"
    
    def test_parse_title_data(self, scraper):
        """Test parsing structured data from title"""
        title = "2 bedroom apartment for rent in Canary Wharf, London"
        data = scraper._parse_title_data(title)
        
        assert data["bedrooms"] == 2
        assert data["property_type"] == "apartment"
        assert "Canary Wharf, London" in data["address"]
    
    def test_extract_price(self, scraper, sample_rightmove_html):
        """Test price extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        price = scraper._extract_price(soup)
        
        assert price == "£2,385 pcm"
    
    def test_extract_property_details(self, scraper, sample_rightmove_html):
        """Test property details extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        details = scraper._extract_property_details(soup)
        
        assert details["bedrooms"] == 1
        assert details["bathrooms"] == 1
        assert details["furnished"] == "Furnished"
    
    def test_extract_address(self, scraper, sample_rightmove_html):
        """Test address extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        address = scraper._extract_address(soup)
        
        assert address == "Grosvenor Road, London, SW1V 3SA"
    
    def test_extract_postcode(self, scraper, sample_rightmove_html):
        """Test postcode extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        address = "Grosvenor Road, London, SW1V 3SA"
        postcode = scraper._extract_postcode(soup, address)
        
        assert postcode == "SW1V 3SA"
    
    def test_extract_area(self, scraper):
        """Test area extraction from address"""
        address = "Grosvenor Road, Victoria, London, SW1V 3SA"
        area = scraper._extract_area(None, address)
        
        assert area == "London"
    
    def test_extract_description(self, scraper, sample_rightmove_html):
        """Test description extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        description = scraper._extract_description(soup)
        
        assert "Beautiful one bedroom apartment" in description
        assert "Victoria" in description
    
    def test_extract_features(self, scraper, sample_rightmove_html):
        """Test features extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        features = scraper._extract_features(soup)
        
        assert "Balcony" in features
        assert "Parking" in features
        assert "Garden" in features
        assert len(features) >= 3
    
    def test_extract_agent_info(self, scraper, sample_rightmove_html):
        """Test agent information extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        agent_info = scraper._extract_agent_info(soup)
        
        assert agent_info["agent_name"] == "Premium Properties"
        assert "02071234567" in agent_info["agent_phone"]
    
    def test_extract_images(self, scraper, sample_rightmove_html):
        """Test image extraction"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        images = scraper._extract_images(soup)
        
        assert len(images) == 2
        assert "https://media.rightmove.co.uk/image1.jpg" in images
        assert "https://media.rightmove.co.uk/image2.jpg" in images
    
    def test_extract_rightmove_data_complete(self, scraper, sample_rightmove_html):
        """Test complete data extraction from Rightmove page"""
        soup = BeautifulSoup(sample_rightmove_html, 'html.parser')
        data = scraper._extract_rightmove_data(soup, "https://www.rightmove.co.uk/properties/123456")
        
        # Check all expected fields are extracted
        assert data["title"] == "1 bedroom flat for rent in Victoria, London, SW1V | Rightmove"
        assert data["price"] == "£2,385 pcm"
        assert data["bedrooms"] == 1
        assert data["bathrooms"] == 1
        assert data["property_type"] == "flat"
        assert data["address"] == "Grosvenor Road, London, SW1V 3SA"
        assert data["postcode"] == "SW1V 3SA"
        assert data["furnished"] == "Furnished"
        assert "Beautiful one bedroom apartment" in data["description"]
        assert "Balcony" in data["features"]
        assert data["agent_name"] == "Premium Properties"
        assert "02071234567" in data["agent_phone"]
        assert len(data["images"]) == 2
    
    @pytest.mark.asyncio
    async def test_scrape_property_success(self, scraper, sample_rightmove_html):
        """Test successful property scraping"""
        mock_response = Mock()
        mock_response.text = sample_rightmove_html
        mock_response.elapsed.total_seconds.return_value = 0.5
        
        with patch.object(scraper, 'make_request', return_value=mock_response):
            result = await scraper.scrape_property("https://www.rightmove.co.uk/properties/123456")
        
        assert result.success is True
        assert result.portal == Portal.RIGHTMOVE
        assert result.property_id == "123456"
        assert result.data["price"] == "£2,385 pcm"
        assert result.data["bedrooms"] == 1
        assert result.response_time == 0.5
        assert result.extraction_method == ExtractionMethod.DIRECT_HTTP
    
    @pytest.mark.asyncio
    async def test_scrape_property_failure(self, scraper):
        """Test property scraping failure"""
        with patch.object(scraper, 'make_request', side_effect=Exception("Network error")):
            result = await scraper.scrape_property("https://www.rightmove.co.uk/properties/123456")
        
        assert result.success is False
        assert result.portal == Portal.RIGHTMOVE
        assert result.property_id == "123456"
        assert "Network error" in result.error
        assert result.extraction_method == ExtractionMethod.DIRECT_HTTP
    
    @pytest.mark.asyncio
    async def test_scrape_search_page_success(self, scraper):
        """Test successful search page scraping"""
        search_html = """
        <div class="searchResults">
            <a href="/properties/123456">Property 1</a>
            <a href="/properties/789012">Property 2</a>
            <a href="/properties/345678?param=value">Property 3</a>
        </div>
        """
        
        mock_response = Mock()
        mock_response.text = search_html
        
        with patch.object(scraper, 'make_request', return_value=mock_response):
            urls = await scraper.scrape_search_page("https://www.rightmove.co.uk/property-to-rent/find.html")
        
        expected_urls = [
            "https://www.rightmove.co.uk/properties/123456",
            "https://www.rightmove.co.uk/properties/789012",
            "https://www.rightmove.co.uk/properties/345678",
        ]
        
        assert len(urls) == 3
        for expected_url in expected_urls:
            assert expected_url in urls
    
    @pytest.mark.asyncio
    async def test_scrape_search_page_failure(self, scraper):
        """Test search page scraping failure"""
        with patch.object(scraper, 'make_request', side_effect=Exception("Request failed")):
            with pytest.raises(Exception):
                await scraper.scrape_search_page("https://www.rightmove.co.uk/property-to-rent/find.html")