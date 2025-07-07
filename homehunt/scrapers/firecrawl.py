"""
Fire Crawl scraper for search discovery and Zoopla properties
Based on validated testing showing Fire Crawl's effectiveness for these use cases
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from firecrawl import FirecrawlApp

from homehunt.core.models import ExtractionMethod, Portal, ScrapingResult

from .base import BaseScraper, ScraperError


class FireCrawlScraper(BaseScraper):
    """
    Fire Crawl scraper optimized for:
    1. Search page discovery (both Rightmove and Zoopla)
    2. Zoopla property details (anti-bot protection)
    3. Pagination handling
    """
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        
        if not self.api_key:
            raise ScraperError("Fire Crawl API key required")
        
        try:
            self.firecrawl_client = FirecrawlApp(api_key=self.api_key)
        except Exception as e:
            raise ScraperError(f"Failed to initialize Fire Crawl client: {e}")
    
    def get_portal(self) -> Portal:
        """Fire Crawl handles both portals but optimized for Zoopla"""
        return Portal.ZOOPLA
    
    def get_extraction_method(self) -> ExtractionMethod:
        return ExtractionMethod.FIRECRAWL
    
    async def close(self):
        """Close Fire Crawl client - override base class"""
        # Fire Crawl client doesn't need explicit closing
        # Just close the HTTP client from parent
        await super().close()
    
    async def scrape_search_page(self, url: str) -> List[str]:
        """
        Scrape search page to discover property URLs
        
        Args:
            url: Search page URL (Rightmove or Zoopla)
            
        Returns:
            List of property URLs found
        """
        try:
            # Determine portal from URL
            portal = self._detect_portal(url)
            
            # Fire Crawl scrape options optimized for search pages
            scrape_options = {
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
                "includeTags": ["a", "div"],
                "excludeTags": ["script", "style", "nav", "footer"],
                "waitFor": 2000,  # Wait for dynamic content
            }
            
            self.logger.info(f"Fire Crawl scraping search page: {url}")
            
            # Make Fire Crawl request
            response = self.firecrawl_client.scrape_url(
                url=url,
                params=scrape_options
            )
            
            if not response.get("success", False):
                error_msg = response.get("error", "Unknown Fire Crawl error")
                raise ScraperError(f"Fire Crawl failed: {error_msg}")
            
            # Extract property URLs from response
            property_urls = self._extract_property_urls(response, portal)
            
            self.logger.info(f"Found {len(property_urls)} property URLs on {url}")
            return property_urls
            
        except Exception as e:
            self.logger.error(f"Error scraping search page {url}: {e}")
            raise ScraperError(f"Fire Crawl search page scraping failed: {e}")
    
    async def scrape_property(self, url: str) -> ScrapingResult:
        """
        Scrape individual property page
        
        Args:
            url: Property URL
            
        Returns:
            ScrapingResult with property data
        """
        portal = self._detect_portal(url)
        property_id = self.extract_property_id(url)
        
        try:
            # Fire Crawl scrape options optimized for property details
            scrape_options = {
                "formats": ["markdown", "html"],
                "onlyMainContent": True,
                "includeTags": ["h1", "h2", "h3", "p", "span", "div", "img"],
                "excludeTags": ["script", "style", "nav", "footer", "header"],
                "waitFor": 3000,  # Wait for all content to load
            }
            
            self.logger.debug(f"Fire Crawl scraping property: {url}")
            
            # Make Fire Crawl request
            response = self.firecrawl_client.scrape_url(
                url=url,
                params=scrape_options
            )
            
            if not response.get("success", False):
                error_msg = response.get("error", "Unknown Fire Crawl error")
                return ScrapingResult(
                    url=url,
                    success=False,
                    portal=portal,
                    property_id=property_id,
                    error=f"Fire Crawl failed: {error_msg}",
                    extraction_method=self.get_extraction_method(),
                )
            
            # Extract property data from response
            property_data = self._extract_property_data(response, portal)
            
            return ScrapingResult(
                url=url,
                success=True,
                portal=portal,
                property_id=property_id,
                data=property_data,
                content_length=len(response.get("html", "")),
                extraction_method=self.get_extraction_method(),
            )
            
        except Exception as e:
            self.logger.error(f"Error scraping property {url}: {e}")
            return ScrapingResult(
                url=url,
                success=False,
                portal=portal,
                property_id=property_id,
                error=str(e),
                extraction_method=self.get_extraction_method(),
            )
    
    def _detect_portal(self, url: str) -> Portal:
        """Detect which portal the URL belongs to"""
        if "rightmove.co.uk" in url:
            return Portal.RIGHTMOVE
        elif "zoopla.co.uk" in url:
            return Portal.ZOOPLA
        else:
            raise ScraperError(f"Unknown portal for URL: {url}")
    
    def _extract_property_urls(self, response: Dict[str, Any], portal: Portal) -> List[str]:
        """Extract property URLs from search page response"""
        property_urls = []
        
        try:
            html_content = response.get("html", "")
            markdown_content = response.get("markdown", "")
            
            if portal == Portal.RIGHTMOVE:
                # Rightmove property URL patterns
                rightmove_patterns = [
                    r'href="(/properties/\d+[^"]*)"',
                    r'href="(https://www\.rightmove\.co\.uk/properties/\d+[^"]*)"',
                ]
                
                for pattern in rightmove_patterns:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if match.startswith('/'):
                            url = f"https://www.rightmove.co.uk{match}"
                        else:
                            url = match
                        
                        # Clean up URL
                        url = url.split('?')[0]  # Remove query parameters
                        if url not in property_urls:
                            property_urls.append(url)
            
            elif portal == Portal.ZOOPLA:
                # Zoopla property URL patterns
                zoopla_patterns = [
                    r'href="(/to-rent/details/\d+[^"]*)"',
                    r'href="(https://www\.zoopla\.co\.uk/to-rent/details/\d+[^"]*)"',
                ]
                
                for pattern in zoopla_patterns:
                    matches = re.findall(pattern, html_content)
                    for match in matches:
                        if match.startswith('/'):
                            url = f"https://www.zoopla.co.uk{match}"
                        else:
                            url = match
                        
                        # Clean up URL
                        url = url.split('?')[0]  # Remove query parameters
                        if url not in property_urls:
                            property_urls.append(url)
            
            # Also check markdown content for additional URLs
            markdown_urls = self._extract_urls_from_markdown(markdown_content, portal)
            property_urls.extend(markdown_urls)
            
            # Remove duplicates while preserving order
            unique_urls = []
            seen = set()
            for url in property_urls:
                if url not in seen:
                    unique_urls.append(url)
                    seen.add(url)
            
            return unique_urls
            
        except Exception as e:
            self.logger.error(f"Error extracting property URLs: {e}")
            return []
    
    def _extract_urls_from_markdown(self, markdown: str, portal: Portal) -> List[str]:
        """Extract property URLs from markdown content"""
        urls = []
        
        try:
            if portal == Portal.RIGHTMOVE:
                # Look for Rightmove links in markdown
                pattern = r'\[.*?\]\((https://www\.rightmove\.co\.uk/properties/\d+[^)]*)\)'
                matches = re.findall(pattern, markdown)
                urls.extend(matches)
            
            elif portal == Portal.ZOOPLA:
                # Look for Zoopla links in markdown
                pattern = r'\[.*?\]\((https://www\.zoopla\.co\.uk/to-rent/details/\d+[^)]*)\)'
                matches = re.findall(pattern, markdown)
                urls.extend(matches)
            
            # Clean URLs
            cleaned_urls = []
            for url in urls:
                clean_url = url.split('?')[0]  # Remove query parameters
                if clean_url not in cleaned_urls:
                    cleaned_urls.append(clean_url)
            
            return cleaned_urls
            
        except Exception as e:
            self.logger.error(f"Error extracting URLs from markdown: {e}")
            return []
    
    def _extract_property_data(self, response: Dict[str, Any], portal: Portal) -> Dict[str, Any]:
        """Extract property data from Fire Crawl response"""
        data = {}
        
        try:
            markdown = response.get("markdown", "")
            html = response.get("html", "")
            
            if portal == Portal.RIGHTMOVE:
                data = self._extract_rightmove_data(markdown, html)
            elif portal == Portal.ZOOPLA:
                data = self._extract_zoopla_data(markdown, html)
            
            # Extract common fields
            data.update({
                "title": self._extract_title(markdown, html),
                "images": self._extract_images(html),
                "content_length": len(html),
            })
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error extracting property data: {e}")
            return {}
    
    def _extract_rightmove_data(self, markdown: str, html: str) -> Dict[str, Any]:
        """Extract Rightmove-specific property data"""
        data = {}
        
        # Extract price
        price_match = re.search(r'£([\d,]+)\s*(?:pcm|per month)', markdown, re.IGNORECASE)
        if price_match:
            data["price"] = f"£{price_match.group(1)} pcm"
        
        # Extract bedrooms from title
        bed_match = re.search(r'(\d+)\s*bedroom', markdown, re.IGNORECASE)
        if bed_match:
            data["bedrooms"] = int(bed_match.group(1))
        
        # Extract property type
        type_match = re.search(r'bedroom\s+(flat|apartment|house|studio|maisonette)', markdown, re.IGNORECASE)
        if type_match:
            data["property_type"] = type_match.group(1).lower()
        
        # Extract address from title
        address_match = re.search(r'in\s+(.+?)(?:\s*\|\s*Rightmove|$)', markdown, re.IGNORECASE)
        if address_match:
            data["address"] = address_match.group(1).strip()
        
        # Extract postcode
        postcode_match = re.search(r'([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})', markdown)
        if postcode_match:
            data["postcode"] = postcode_match.group(1)
        
        return data
    
    def _extract_zoopla_data(self, markdown: str, html: str) -> Dict[str, Any]:
        """Extract Zoopla-specific property data"""
        data = {}
        
        # Extract price
        price_match = re.search(r'£([\d,]+)\s*(?:pcm|per month)', markdown, re.IGNORECASE)
        if price_match:
            data["price"] = f"£{price_match.group(1)} pcm"
        
        # Extract bedrooms
        bed_match = re.search(r'(\d+)\s*bed', markdown, re.IGNORECASE)
        if bed_match:
            data["bedrooms"] = int(bed_match.group(1))
        
        # Extract property type
        type_patterns = [
            r'(\d+)\s*bed\s+(flat|apartment|house|studio|maisonette)',
            r'(flat|apartment|house|studio|maisonette)',
        ]
        
        for pattern in type_patterns:
            type_match = re.search(pattern, markdown, re.IGNORECASE)
            if type_match:
                if type_match.lastindex == 2:  # Pattern with bedroom count
                    data["property_type"] = type_match.group(2).lower()
                else:  # Pattern without bedroom count
                    data["property_type"] = type_match.group(1).lower()
                break
        
        # Extract address
        address_match = re.search(r'to rent in\s+(.+?)(?:\s*\|\s*Zoopla|$)', markdown, re.IGNORECASE)
        if address_match:
            data["address"] = address_match.group(1).strip()
        
        # Extract postcode
        postcode_match = re.search(r'([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})', markdown)
        if postcode_match:
            data["postcode"] = postcode_match.group(1)
        
        return data
    
    def _extract_title(self, markdown: str, html: str) -> Optional[str]:
        """Extract page title"""
        # Try to find title in markdown first
        title_match = re.search(r'^#\s*(.+?)(?:\n|$)', markdown, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        # Try HTML title tag
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        return None
    
    def _extract_images(self, html: str) -> List[str]:
        """Extract image URLs from HTML"""
        images = []
        
        # Look for property images
        img_patterns = [
            r'<img[^>]+src="(https://[^"]+\.(?:jpg|jpeg|png|webp))"[^>]*>',
            r'<img[^>]+src="([^"]+\.(?:jpg|jpeg|png|webp))"[^>]*>',
        ]
        
        for pattern in img_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            images.extend(matches)
        
        # Clean and deduplicate
        unique_images = []
        seen = set()
        for img in images:
            # Convert relative URLs to absolute
            if img.startswith('/'):
                continue  # Skip relative URLs for now
            
            if img not in seen and 'logo' not in img.lower():
                unique_images.append(img)
                seen.add(img)
        
        return unique_images[:10]  # Limit to first 10 images
    
    def extract_property_id(self, url: str) -> Optional[str]:
        """Extract property ID from URL"""
        try:
            if "rightmove.co.uk" in url:
                # Rightmove: /properties/123456
                match = re.search(r'/properties/(\d+)', url)
                if match:
                    return match.group(1)
            
            elif "zoopla.co.uk" in url:
                # Zoopla: /to-rent/details/123456
                match = re.search(r'/to-rent/details/(\d+)', url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting property ID from {url}: {e}")
            return None
    
    async def get_pagination_urls(self, base_url: str, max_pages: int = 10) -> List[str]:
        """
        Get pagination URLs for search results
        
        Args:
            base_url: Base search URL
            max_pages: Maximum number of pages to generate
            
        Returns:
            List of paginated URLs
        """
        urls = [base_url]
        
        try:
            portal = self._detect_portal(base_url)
            
            if portal == Portal.RIGHTMOVE:
                # Rightmove pagination: &index=0, &index=24, &index=48, etc.
                for page in range(1, max_pages):
                    index = page * 24
                    if '&index=' in base_url:
                        # Replace existing index
                        paginated_url = re.sub(r'&index=\d+', f'&index={index}', base_url)
                    else:
                        # Add index parameter
                        paginated_url = f"{base_url}&index={index}"
                    urls.append(paginated_url)
            
            elif portal == Portal.ZOOPLA:
                # Zoopla pagination: &pn=1, &pn=2, &pn=3, etc.
                for page in range(2, max_pages + 1):
                    if '&pn=' in base_url:
                        # Replace existing page number
                        paginated_url = re.sub(r'&pn=\d+', f'&pn={page}', base_url)
                    else:
                        # Add page parameter
                        paginated_url = f"{base_url}&pn={page}"
                    urls.append(paginated_url)
            
            return urls
            
        except Exception as e:
            self.logger.error(f"Error generating pagination URLs: {e}")
            return [base_url]