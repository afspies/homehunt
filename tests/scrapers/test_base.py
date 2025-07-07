"""
Tests for base scraper functionality
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from homehunt.core.models import ExtractionMethod, Portal, ScrapingResult
from homehunt.scrapers.base import BaseScraper, RateLimiter, ScraperError


class TestRateLimiter:
    """Test RateLimiter functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting functionality"""
        limiter = RateLimiter(max_requests=2, time_window=1, max_concurrent=1)
        
        # First two requests should be allowed immediately
        start_time = time.time()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1  # Should be immediate
        
        # Third request should be delayed
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        assert elapsed >= 0.9  # Should wait for time window
    
    @pytest.mark.asyncio
    async def test_concurrent_limit(self):
        """Test concurrent request limiting"""
        limiter = RateLimiter(max_requests=10, time_window=60, max_concurrent=2)
        
        # Start multiple concurrent requests
        start_time = time.time()
        tasks = [limiter.acquire() for _ in range(4)]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # With max_concurrent=2, should take at least some time to process 4 requests
        assert elapsed > 0


class MockScraper(BaseScraper):
    """Mock scraper for testing base functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mock_responses = {}
    
    async def scrape_search_page(self, url: str):
        return self.mock_responses.get(url, [])
    
    async def scrape_property(self, url: str):
        return ScrapingResult(
            url=url,
            success=True,
            portal=Portal.RIGHTMOVE,
            property_id="123",
            data={"title": "Test Property"},
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )
    
    def get_portal(self):
        return Portal.RIGHTMOVE
    
    def get_extraction_method(self):
        return ExtractionMethod.DIRECT_HTTP


class TestBaseScraper:
    """Test BaseScraper functionality"""
    
    @pytest.fixture
    def mock_scraper(self):
        """Create mock scraper for testing"""
        return MockScraper()
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self, mock_scraper):
        """Test scraper initialization"""
        assert mock_scraper.timeout == 30
        assert mock_scraper.max_retries == 3
        assert mock_scraper.retry_delay == 1.0
        assert mock_scraper.rate_limiter is not None
        assert mock_scraper.client is not None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test scraper as context manager"""
        async with MockScraper() as scraper:
            assert scraper.client is not None
        
        # Client should be closed after context
        assert scraper.client.is_closed
    
    def test_extract_property_id_numeric(self, mock_scraper):
        """Test extracting numeric property ID from URL"""
        test_cases = [
            ("https://example.com/properties/123456", "123456"),
            ("https://example.com/property/789", "789"),
            ("https://example.com/listing?id=999", "999"),
            ("https://example.com/invalid", None),
        ]
        
        for url, expected_id in test_cases:
            result = mock_scraper.extract_property_id(url)
            assert result == expected_id
    
    @pytest.mark.asyncio
    async def test_make_request_success(self, mock_scraper):
        """Test successful HTTP request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        
        with patch.object(mock_scraper.client, 'request', return_value=mock_response):
            response = await mock_scraper.make_request("https://example.com")
            assert response.status_code == 200
            assert response.text == "Success"
    
    @pytest.mark.asyncio
    async def test_make_request_retry_on_429(self, mock_scraper):
        """Test retry logic for rate limiting (429)"""
        # Mock responses: first 429, then 200
        responses = [
            Mock(status_code=429),
            Mock(status_code=200, text="Success"),
        ]
        
        with patch.object(mock_scraper.client, 'request', side_effect=responses):
            response = await mock_scraper.make_request("https://example.com")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_make_request_failure_after_retries(self, mock_scraper):
        """Test failure after max retries"""
        mock_scraper.max_retries = 1
        mock_scraper.retry_delay = 0.01  # Speed up test
        
        # All requests fail
        mock_response = Mock(status_code=500)
        
        with patch.object(mock_scraper.client, 'request', return_value=mock_response):
            with pytest.raises(ScraperError):
                await mock_scraper.make_request("https://example.com")
    
    @pytest.mark.asyncio
    async def test_make_request_timeout(self, mock_scraper):
        """Test timeout handling"""
        mock_scraper.max_retries = 1
        mock_scraper.retry_delay = 0.01
        
        with patch.object(mock_scraper.client, 'request', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(ScraperError):
                await mock_scraper.make_request("https://example.com")
    
    @pytest.mark.asyncio
    async def test_scrape_properties_batch(self, mock_scraper):
        """Test batch property scraping"""
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3",
        ]
        
        results = await mock_scraper.scrape_properties_batch(urls)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.url == urls[i]
            assert result.success is True
            assert result.property_id == "123"
    
    @pytest.mark.asyncio
    async def test_scrape_properties_batch_with_errors(self, mock_scraper):
        """Test batch scraping with some errors"""
        urls = ["https://example.com/1", "https://example.com/2"]
        
        # Mock one successful, one failed scrape
        async def mock_scrape_property(url):
            if "1" in url:
                return ScrapingResult(
                    url=url,
                    success=True,
                    portal=Portal.RIGHTMOVE,
                    property_id="123",
                    data={"title": "Success"},
                    extraction_method=ExtractionMethod.DIRECT_HTTP,
                )
            else:
                raise Exception("Scraping failed")
        
        with patch.object(mock_scraper, 'scrape_property', side_effect=mock_scrape_property):
            results = await mock_scraper.scrape_properties_batch(urls)
        
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "Scraping failed" in results[1].error
    
    def test_log_scraping_stats(self, mock_scraper, caplog):
        """Test logging scraping statistics"""
        import logging
        caplog.set_level(logging.INFO)
        
        results = [
            ScrapingResult(
                url="url1", success=True, portal=Portal.RIGHTMOVE,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            ),
            ScrapingResult(
                url="url2", success=True, portal=Portal.RIGHTMOVE,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            ),
            ScrapingResult(
                url="url3", success=False, portal=Portal.RIGHTMOVE,
                error="Failed", extraction_method=ExtractionMethod.DIRECT_HTTP
            ),
        ]
        
        mock_scraper.log_scraping_stats(results)
        
        # Check that statistics were logged
        assert "66.7% success rate" in caplog.text
        assert "2 successful, 1 failed" in caplog.text