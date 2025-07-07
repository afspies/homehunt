"""
Tests for hybrid scraper functionality
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homehunt.core.db import Database
from homehunt.core.models import (
    ExtractionMethod,
    Portal,
    PropertyListing,
    ScrapingResult,
    SearchConfig,
)
from homehunt.scrapers.hybrid import HybridScraper


class TestHybridScraper:
    """Test HybridScraper functionality"""
    
    @pytest.fixture
    async def mock_database(self):
        """Create mock database for testing"""
        db = Mock(spec=Database)
        db.create_tables_async = AsyncMock()
        db.get_property = AsyncMock(return_value=None)
        db.save_property = AsyncMock(return_value=True)
        db.close = AsyncMock()
        return db
    
    @pytest.fixture
    def sample_search_config(self):
        """Create sample search configuration"""
        return SearchConfig(
            location="Victoria, London",
            min_price=2000,
            max_price=3000,
            min_bedrooms=1,
            max_bedrooms=2,
            portals=[Portal.RIGHTMOVE, Portal.ZOOPLA],
            max_pages=2,
        )
    
    @pytest.fixture
    def mock_property_urls(self):
        """Mock property URLs for testing"""
        return [
            "https://www.rightmove.co.uk/properties/123456",
            "https://www.rightmove.co.uk/properties/789012",
            "https://www.zoopla.co.uk/to-rent/details/345678",
            "https://www.zoopla.co.uk/to-rent/details/901234",
        ]
    
    @pytest.fixture
    def mock_scraping_results(self):
        """Mock scraping results for testing"""
        return [
            ScrapingResult(
                url="https://www.rightmove.co.uk/properties/123456",
                success=True,
                portal=Portal.RIGHTMOVE,
                property_id="123456",
                data={
                    "title": "1 bedroom flat in Victoria",
                    "price": "£2,500 pcm",
                    "bedrooms": 1,
                    "property_type": "flat",
                },
                extraction_method=ExtractionMethod.DIRECT_HTTP,
            ),
            ScrapingResult(
                url="https://www.zoopla.co.uk/to-rent/details/345678",
                success=True,
                portal=Portal.ZOOPLA,
                property_id="345678",
                data={
                    "title": "2 bedroom apartment in London",
                    "price": "£2,800 pcm",
                    "bedrooms": 2,
                    "property_type": "apartment",
                },
                extraction_method=ExtractionMethod.FIRECRAWL,
            ),
        ]
    
    @pytest.mark.asyncio
    async def test_hybrid_scraper_initialization(self, mock_database):
        """Test HybridScraper initialization"""
        scraper = HybridScraper(
            firecrawl_api_key="test_key",
            database=mock_database,
            dedupe_hours=12,
            max_concurrent=3,
        )
        
        assert scraper.database == mock_database
        assert scraper.dedupe_hours == 12
        assert scraper.rate_limiter.max_concurrent == 3
        assert scraper.firecrawl_scraper is not None
        assert scraper.direct_http_scraper is not None
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_database):
        """Test HybridScraper as context manager"""
        async with HybridScraper(database=mock_database, firecrawl_api_key="test") as scraper:
            assert scraper.database == mock_database
        
        # Database should be closed
        mock_database.close.assert_called_once()
    
    def test_detect_portal(self, mock_database):
        """Test portal detection from URLs"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        assert scraper._detect_portal("https://www.rightmove.co.uk/properties/123") == Portal.RIGHTMOVE
        assert scraper._detect_portal("https://www.zoopla.co.uk/to-rent/details/456") == Portal.ZOOPLA
        
        with pytest.raises(Exception):
            scraper._detect_portal("https://example.com/unknown")
    
    @pytest.mark.asyncio
    async def test_deduplicate_urls_no_existing(self, mock_database, mock_property_urls):
        """Test URL deduplication with no existing properties"""
        mock_database.get_property = AsyncMock(return_value=None)
        
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock property ID extraction
        with patch.object(scraper.direct_http_scraper, 'extract_property_id', return_value="123"):
            with patch.object(scraper.firecrawl_scraper, 'extract_property_id', return_value="456"):
                result = await scraper._deduplicate_urls(mock_property_urls)
        
        # All URLs should remain since no existing properties
        assert len(result) == len(mock_property_urls)
    
    @pytest.mark.asyncio
    async def test_deduplicate_urls_with_existing(self, mock_database, mock_property_urls):
        """Test URL deduplication with existing recent properties"""
        # Mock existing property that was recently scraped
        existing_property = Mock()
        existing_property.last_scraped = datetime.utcnow() - timedelta(hours=1)
        
        mock_database.get_property = AsyncMock(return_value=existing_property)
        
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test", dedupe_hours=2)
        
        # Mock property ID extraction
        with patch.object(scraper.direct_http_scraper, 'extract_property_id', return_value="123"):
            with patch.object(scraper.firecrawl_scraper, 'extract_property_id', return_value="456"):
                result = await scraper._deduplicate_urls(mock_property_urls)
        
        # URLs should be filtered out due to recent scraping
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_scrape_properties_hybrid(self, mock_database, mock_property_urls, mock_scraping_results):
        """Test hybrid property scraping"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock scraper batch methods
        with patch.object(scraper.direct_http_scraper, 'scrape_properties_batch') as mock_direct:
            with patch.object(scraper.firecrawl_scraper, 'scrape_properties_batch') as mock_firecrawl:
                
                # Return appropriate results for each scraper
                mock_direct.return_value = [mock_scraping_results[0]]  # Rightmove result
                mock_firecrawl.return_value = [mock_scraping_results[1]]  # Zoopla result
                
                # Mock progress
                mock_progress = Mock()
                mock_task_id = 1
                
                properties = await scraper._scrape_properties_hybrid(
                    mock_property_urls, mock_progress, mock_task_id
                )
        
        # Should return PropertyListing objects
        assert len(properties) == 2
        assert all(isinstance(prop, PropertyListing) for prop in properties)
        
        # Check that both scrapers were called
        mock_direct.assert_called_once()
        mock_firecrawl.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_properties(self, mock_database):
        """Test saving properties to database"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Create test properties
        properties = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="123",
                url="https://example.com/123",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
            ),
            PropertyListing(
                portal=Portal.ZOOPLA,
                property_id="456",
                url="https://example.com/456",
                extraction_method=ExtractionMethod.FIRECRAWL,
            ),
        ]
        
        # Mock progress
        mock_progress = Mock()
        mock_task_id = 1
        
        await scraper._save_properties(properties, mock_progress, mock_task_id)
        
        # Check that all properties were saved
        assert mock_database.save_property.call_count == 2
        assert scraper.stats["properties_saved"] == 2
    
    @pytest.mark.asyncio
    async def test_scrape_single_property_rightmove(self, mock_database):
        """Test scraping single Rightmove property"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock direct HTTP scraper result
        mock_result = ScrapingResult(
            url="https://www.rightmove.co.uk/properties/123456",
            success=True,
            portal=Portal.RIGHTMOVE,
            property_id="123456",
            data={"title": "Test Property", "price": "£2,000 pcm"},
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )
        
        with patch.object(scraper.direct_http_scraper, 'scrape_property', return_value=mock_result):
            property_listing = await scraper.scrape_single_property(
                "https://www.rightmove.co.uk/properties/123456"
            )
        
        assert property_listing is not None
        assert property_listing.portal == Portal.RIGHTMOVE
        assert property_listing.property_id == "123456"
        assert scraper.stats["direct_http_requests"] == 1
        
        # Check that property was saved
        mock_database.save_property.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_single_property_zoopla(self, mock_database):
        """Test scraping single Zoopla property"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock Fire Crawl scraper result
        mock_result = ScrapingResult(
            url="https://www.zoopla.co.uk/to-rent/details/345678",
            success=True,
            portal=Portal.ZOOPLA,
            property_id="345678",
            data={"title": "Test Property", "price": "£2,500 pcm"},
            extraction_method=ExtractionMethod.FIRECRAWL,
        )
        
        with patch.object(scraper.firecrawl_scraper, 'scrape_property', return_value=mock_result):
            property_listing = await scraper.scrape_single_property(
                "https://www.zoopla.co.uk/to-rent/details/345678"
            )
        
        assert property_listing is not None
        assert property_listing.portal == Portal.ZOOPLA
        assert property_listing.property_id == "345678"
        assert scraper.stats["firecrawl_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_single_property_failure(self, mock_database):
        """Test handling scraping failure for single property"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock failed result
        mock_result = ScrapingResult(
            url="https://www.rightmove.co.uk/properties/123456",
            success=False,
            portal=Portal.RIGHTMOVE,
            property_id="123456",
            error="Scraping failed",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )
        
        with patch.object(scraper.direct_http_scraper, 'scrape_property', return_value=mock_result):
            property_listing = await scraper.scrape_single_property(
                "https://www.rightmove.co.uk/properties/123456"
            )
        
        assert property_listing is None
    
    def test_get_stats(self, mock_database):
        """Test getting scraping statistics"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Modify some stats
        scraper.stats["total_urls_discovered"] = 100
        scraper.stats["properties_scraped"] = 50
        scraper.stats["firecrawl_requests"] = 10
        scraper.stats["direct_http_requests"] = 40
        
        stats = scraper.get_stats()
        
        assert stats["total_urls_discovered"] == 100
        assert stats["properties_scraped"] == 50
        assert stats["firecrawl_requests"] == 10
        assert stats["direct_http_requests"] == 40
        
        # Ensure it's a copy, not the original
        stats["test"] = "value"
        assert "test" not in scraper.stats
    
    @pytest.mark.asyncio
    async def test_search_properties_integration(
        self, mock_database, sample_search_config, mock_property_urls, mock_scraping_results
    ):
        """Test full search properties integration"""
        scraper = HybridScraper(database=mock_database, firecrawl_api_key="test")
        
        # Mock the discovery phase
        with patch.object(scraper, '_discover_property_urls', return_value=mock_property_urls):
            with patch.object(scraper, '_deduplicate_urls', return_value=mock_property_urls):
                with patch.object(scraper.direct_http_scraper, 'scrape_properties_batch') as mock_direct:
                    with patch.object(scraper.firecrawl_scraper, 'scrape_properties_batch') as mock_firecrawl:
                        
                        # Return appropriate results
                        mock_direct.return_value = [mock_scraping_results[0]]
                        mock_firecrawl.return_value = [mock_scraping_results[1]]
                        
                        properties = await scraper.search_properties(
                            sample_search_config, show_progress=False
                        )
        
        # Verify results
        assert len(properties) == 2
        assert scraper.stats["total_urls_discovered"] == 4
        assert scraper.stats["urls_after_deduplication"] == 4
        assert scraper.stats["properties_scraped"] == 2
        assert scraper.stats["properties_saved"] == 2