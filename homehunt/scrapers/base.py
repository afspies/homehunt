"""
Base scraper class with rate limiting and error handling
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.progress import Progress

from homehunt.core.models import Portal, PropertyListing, ScrapingResult


class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass


class RateLimiter:
    """Rate limiter for API calls with concurrent request management"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60, max_concurrent: int = 5):
        self.max_requests = max_requests
        self.time_window = time_window
        self.max_concurrent = max_concurrent
        self.requests = []
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)
    
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self.semaphore:
            now = time.time()
            
            # Remove old requests outside time window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # Check if we can make a request
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    self.logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                    await asyncio.sleep(sleep_time)
                    # Re-check after sleeping
                    now = time.time()
                    self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # Record this request
            self.requests.append(now)
            
            return True


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality"""
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self.console = Console()
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            follow_redirects=True,
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self):
        """Close HTTP client and cleanup resources"""
        if hasattr(self, 'client'):
            await self.client.aclose()
    
    @abstractmethod
    async def scrape_search_page(self, url: str) -> List[str]:
        """
        Scrape a search page and return property URLs
        
        Args:
            url: Search page URL
            
        Returns:
            List of property URLs found
        """
        pass
    
    @abstractmethod
    async def scrape_property(self, url: str) -> ScrapingResult:
        """
        Scrape a single property page
        
        Args:
            url: Property URL
            
        Returns:
            ScrapingResult with property data
        """
        pass
    
    @abstractmethod
    def get_portal(self) -> Portal:
        """Get the portal this scraper handles"""
        pass
    
    def extract_property_id(self, url: str) -> Optional[str]:
        """Extract property ID from URL"""
        try:
            # Generic ID extraction - override in subclasses for specific patterns
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # Look for numeric ID in path
            for part in reversed(path_parts):
                if part.isdigit():
                    return part
            
            # Look for ID in query parameters
            if parsed.query:
                from urllib.parse import parse_qs
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    if 'id' in key.lower() and values and values[0].isdigit():
                        return values[0]
            
            return None
        except Exception as e:
            self.logger.error(f"Error extracting property ID from {url}: {e}")
            return None
    
    async def make_request(self, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """
        Make HTTP request with rate limiting and retries
        
        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            ScraperError: If request fails after retries
        """
        await self.rate_limiter.acquire()
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except httpx.TimeoutException:
                self.logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
            except httpx.RequestError as e:
                self.logger.warning(f"Request error for {url}: {e} (attempt {attempt + 1})")
            
            if attempt < self.max_retries:
                wait_time = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(wait_time)
        
        raise ScraperError(f"Failed to fetch {url} after {self.max_retries + 1} attempts")
    
    async def scrape_properties_batch(
        self,
        urls: List[str],
        progress: Optional[Progress] = None,
        task_id: Optional[int] = None,
    ) -> List[ScrapingResult]:
        """
        Scrape multiple properties concurrently
        
        Args:
            urls: List of property URLs to scrape
            progress: Optional progress tracker
            task_id: Optional task ID for progress tracking
            
        Returns:
            List of ScrapingResult objects
        """
        results = []
        
        async def scrape_single(url: str) -> ScrapingResult:
            try:
                result = await self.scrape_property(url)
                if progress and task_id:
                    progress.update(task_id, advance=1)
                return result
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                return ScrapingResult(
                    url=url,
                    success=False,
                    portal=self.get_portal(),
                    error=str(e),
                    extraction_method=self.get_extraction_method(),
                )
        
        # Process URLs in batches to avoid overwhelming the server
        batch_size = min(self.rate_limiter.max_concurrent, 10)
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[scrape_single(url) for url in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch scraping error: {result}")
                else:
                    results.append(result)
        
        return results
    
    @abstractmethod
    def get_extraction_method(self):
        """Get the extraction method used by this scraper"""
        pass
    
    def log_scraping_stats(self, results: List[ScrapingResult]):
        """Log scraping statistics"""
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        self.logger.info(
            f"Scraping completed: {successful} successful, {failed} failed "
            f"({successful/len(results)*100:.1f}% success rate)"
        )
        
        if failed > 0:
            # Log common error types
            error_types = {}
            for result in results:
                if not result.success and result.error:
                    error_type = result.error.split(':')[0]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            self.logger.info(f"Error breakdown: {error_types}")