# Fire Crawl API Integration Plan for HomeHunt

## Overview
Fire Crawl API will replace our direct scraping approach, solving anti-scraping challenges with Zoopla and Rightmove. This document outlines our integration strategy for efficient, async property data extraction.

## API Capabilities Summary

### Core Features
- **Intelligent Crawling**: Automatically discovers and follows pagination links
- **JavaScript Handling**: Renders dynamic content (React/Vue components)
- **Structured Extraction**: AI-powered data extraction with Pydantic schemas
- **Anti-Bot Bypass**: Built-in proxy rotation and bot detection avoidance
- **Multiple Formats**: Markdown, HTML, JSON output options

### Key Advantages for Property Scraping
1. **No Rate Limiting Issues**: API handles all anti-scraping measures
2. **Automatic Pagination**: Discovers all property listing pages
3. **Structured Data**: Extract clean, validated property information
4. **Async Processing**: Handle large crawls without blocking
5. **JavaScript Support**: Works with modern property sites

## Implementation Strategy

### 1. Core Architecture Integration

```python
# homehunt/core/scraper/firecrawl_client.py
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List, Optional, AsyncIterator
import asyncio
from rich.console import Console

class FireCrawlClient:
    def __init__(self, api_key: str, console: Console):
        self.app = FirecrawlApp(api_key=api_key)
        self.console = console
    
    async def crawl_property_search(
        self, 
        search_url: str, 
        max_pages: int = 50
    ) -> AsyncIterator[dict]:
        """Crawl property search results with pagination"""
        # Implementation details below
        pass
```

### 2. Property Data Schema

```python
# homehunt/core/models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PropertyListing(BaseModel):
    """Structured property data extracted by Fire Crawl"""
    
    # Core identification
    portal: str = Field(..., description="rightmove or zoopla")
    property_id: str = Field(..., description="Unique property ID")
    url: str = Field(..., description="Direct property URL")
    
    # Location data
    address: str = Field(..., description="Property address")
    postcode: Optional[str] = Field(None, description="Full postcode")
    area: Optional[str] = Field(None, description="Area/district")
    
    # Property details
    price: Optional[int] = Field(None, description="Monthly rent in pence")
    price_frequency: Optional[str] = Field(None, description="per month/week")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    property_type: Optional[str] = Field(None, description="flat/house/studio")
    
    # Additional features
    furnished: Optional[str] = Field(None, description="furnished/unfurnished")
    description: Optional[str] = Field(None, description="Property description")
    features: Optional[List[str]] = Field(None, description="Property features")
    
    # Metadata
    agent_name: Optional[str] = Field(None, description="Estate agent")
    date_added: Optional[str] = Field(None, description="When listing was added")
    images: Optional[List[str]] = Field(None, description="Property image URLs")
    
    # Extraction metadata
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_confidence: Optional[float] = Field(None, description="AI confidence score")
```

### 3. Crawling Strategy

#### A. Search Results Crawling
```python
async def crawl_search_results(
    self,
    portal: str,
    search_params: dict,
    max_pages: int = 50
) -> List[str]:
    """Crawl search results to discover all property URLs"""
    
    # Build search URL
    search_url = self._build_search_url(portal, search_params)
    
    # Configure crawl parameters
    crawl_config = {
        'limit': max_pages,
        'crawlEntireDomain': False,  # Stay within search results
        'allowSubdomains': False,
        'scrapeFormat': 'markdown',
        'includes': [
            '*/property-*',  # Rightmove: /property-to-rent/
            '*/to-rent/*',   # Zoopla: /to-rent/
            '*/details/*'    # Individual property pages
        ],
        'excludes': [
            '*/search*',     # Avoid search pages
            '*/saved-*',     # Avoid saved searches
            '*/contact*'     # Avoid contact pages
        ]
    }
    
    # Start async crawl
    job_id = await self.app.crawl_url_async(search_url, crawl_config)
    
    # Monitor crawl progress
    with self.console.status("[bold blue]Crawling property listings..."):
        while True:
            status = await self.app.check_crawl_status(job_id)
            if status['status'] == 'completed':
                break
            elif status['status'] == 'failed':
                raise Exception(f"Crawl failed: {status.get('error')}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    # Extract property URLs
    results = await self.app.get_crawl_results(job_id)
    property_urls = [
        result['url'] for result in results 
        if self._is_property_url(result['url'])
    ]
    
    return property_urls
```

#### B. Individual Property Extraction
```python
async def extract_property_data(
    self,
    property_urls: List[str],
    batch_size: int = 20
) -> List[PropertyListing]:
    """Extract structured data from property URLs"""
    
    # Process in batches to avoid overwhelming the API
    all_properties = []
    
    for i in range(0, len(property_urls), batch_size):
        batch = property_urls[i:i + batch_size]
        
        # Use Fire Crawl's extract endpoint with our schema
        extract_config = {
            'schema': PropertyListing.model_json_schema(),
            'prompt': '''
            Extract property rental information including:
            - Full address and postcode
            - Monthly rent amount
            - Number of bedrooms and bathrooms
            - Property type (flat, house, studio)
            - Key features and description
            - Agent information
            - Date added or last updated
            ''',
            'format': 'json'
        }
        
        # Extract data for batch
        results = await self.app.extract_urls_async(batch, extract_config)
        
        # Process and validate results
        for result in results:
            try:
                property_data = PropertyListing.model_validate(result['data'])
                all_properties.append(property_data)
            except Exception as e:
                self.console.print(f"[red]Validation error for {result['url']}:[/red] {e}")
        
        # Rate limiting - be respectful
        await asyncio.sleep(1)
    
    return all_properties
```

### 4. Portal-Specific Configurations

#### Rightmove Configuration
```python
RIGHTMOVE_CONFIG = {
    'base_url': 'https://www.rightmove.co.uk',
    'search_patterns': {
        'to_rent': '/property-to-rent/find.html',
        'for_sale': '/property-for-sale/find.html'
    },
    'url_includes': [
        '*/property-to-rent/*',
        '*/properties/*'
    ],
    'url_excludes': [
        '*/find.html*',
        '*/saved-*',
        '*/contact*'
    ]
}
```

#### Zoopla Configuration
```python
ZOOPLA_CONFIG = {
    'base_url': 'https://www.zoopla.co.uk',
    'search_patterns': {
        'to_rent': '/to-rent/',
        'for_sale': '/for-sale/'
    },
    'url_includes': [
        '*/to-rent/*',
        '*/rental/*',
        '*/details/*'
    ],
    'url_excludes': [
        '*/search*',
        '*/saved-*',
        '*/contact*'
    ]
}
```

### 5. Async Implementation

```python
# homehunt/core/scraper/async_firecrawl.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import aiohttp
from rich.progress import Progress, TaskID

class AsyncFireCrawlManager:
    def __init__(self, api_key: str, max_concurrent: int = 5):
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def scrape_multiple_searches(
        self, 
        search_configs: List[Dict[str, Any]],
        progress: Progress,
        task_id: TaskID
    ) -> List[PropertyListing]:
        """Scrape multiple search configurations concurrently"""
        
        tasks = []
        for config in search_configs:
            task = self._scrape_single_search(config, progress, task_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out exceptions
        all_properties = []
        for result in results:
            if isinstance(result, Exception):
                console.print(f"[red]Search failed:[/red] {result}")
            else:
                all_properties.extend(result)
        
        return all_properties
    
    async def _scrape_single_search(
        self,
        config: Dict[str, Any],
        progress: Progress,
        task_id: TaskID
    ) -> List[PropertyListing]:
        """Scrape a single search configuration"""
        async with self.semaphore:
            # Implementation details
            pass
```

### 6. Configuration Management

```python
# homehunt/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Fire Crawl API
    firecrawl_api_key: str
    
    # Crawling limits
    max_pages_per_search: int = 50
    max_concurrent_crawls: int = 5
    crawl_timeout_minutes: int = 30
    
    # Extraction settings
    extraction_batch_size: int = 20
    extraction_confidence_threshold: float = 0.7
    
    # Other API keys
    traveltime_app_id: Optional[str] = None
    traveltime_api_key: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 7. Error Handling and Monitoring

```python
# homehunt/core/scraper/error_handling.py
import asyncio
import logging
from typing import Optional, Dict, Any
from rich.console import Console

class FireCrawlErrorHandler:
    def __init__(self, console: Console):
        self.console = console
        self.logger = logging.getLogger(__name__)
    
    async def handle_crawl_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3
    ) -> Optional[Any]:
        """Handle crawl errors with exponential backoff"""
        
        if retry_count >= max_retries:
            self.console.print(f"[red]Max retries exceeded for {context['url']}[/red]")
            return None
        
        # Log error
        self.logger.error(f"Crawl error (attempt {retry_count + 1}): {error}")
        
        # Exponential backoff
        delay = 2 ** retry_count
        await asyncio.sleep(delay)
        
        # Retry with same context
        return await self._retry_operation(context, retry_count + 1)
    
    async def validate_extraction_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[PropertyListing]:
        """Validate and clean extraction results"""
        
        valid_properties = []
        validation_errors = []
        
        for result in results:
            try:
                # Validate with Pydantic
                property_data = PropertyListing.model_validate(result)
                
                # Additional business logic validation
                if self._is_valid_property(property_data):
                    valid_properties.append(property_data)
                else:
                    validation_errors.append(f"Invalid property: {property_data.url}")
                    
            except Exception as e:
                validation_errors.append(f"Validation error: {e}")
        
        # Report validation summary
        if validation_errors:
            self.console.print(f"[yellow]Validation issues: {len(validation_errors)}[/yellow]")
            for error in validation_errors[:5]:  # Show first 5
                self.console.print(f"  • {error}")
        
        self.console.print(f"[green]Valid properties: {len(valid_properties)}[/green]")
        return valid_properties
```

## Integration Points

### 1. CLI Integration
```python
# homehunt/cli.py
@app.command()
def scrape(
    area: str = typer.Option(..., help="Search area"),
    portal: str = typer.Option("both", help="rightmove, zoopla, or both"),
    max_pages: int = typer.Option(20, help="Maximum pages to crawl"),
    # ... other options
):
    """Scrape properties using Fire Crawl API"""
    asyncio.run(scrape_properties(area, portal, max_pages))

async def scrape_properties(area: str, portal: str, max_pages: int):
    async with AsyncFireCrawlManager(settings.firecrawl_api_key) as crawl_manager:
        # Build search configurations
        search_configs = build_search_configs(area, portal, max_pages)
        
        # Execute crawls
        with Progress() as progress:
            task = progress.add_task("Scraping properties...", total=len(search_configs))
            properties = await crawl_manager.scrape_multiple_searches(
                search_configs, progress, task
            )
        
        # Process results
        console.print(f"[green]Found {len(properties)} properties[/green]")
        return properties
```

### 2. Database Integration
```python
# homehunt/core/db.py
async def save_scraped_properties(
    properties: List[PropertyListing],
    session: AsyncSession
) -> int:
    """Save scraped properties to database"""
    
    saved_count = 0
    
    for prop in properties:
        # Convert to database model
        db_property = Listing(
            uid=f"{prop.portal}:{prop.property_id}",
            portal=prop.portal,
            url=prop.url,
            address=prop.address,
            postcode=prop.postcode,
            price=prop.price,
            bedrooms=prop.bedrooms,
            property_type=prop.property_type,
            # ... other fields
        )
        
        # Upsert (update if exists, insert if new)
        await session.merge(db_property)
        saved_count += 1
    
    await session.commit()
    return saved_count
```

## Cost Optimization

### 1. Smart Crawling
- **Incremental crawls**: Only crawl new/updated listings
- **Targeted searches**: Focus on specific areas/criteria
- **Batch processing**: Group similar searches together

### 2. Caching Strategy
- **URL caching**: Cache property URLs for 24 hours
- **Data caching**: Cache extracted data for comparison
- **Search result caching**: Reuse recent search results

### 3. Rate Limiting
- **API quotas**: Monitor Fire Crawl API usage
- **Concurrent limits**: Control parallel requests
- **Retry logic**: Implement exponential backoff

## Next Steps

1. **API Key Setup**: Get Fire Crawl API key from user
2. **Basic Implementation**: Create core Fire Crawl client
3. **Schema Testing**: Test extraction with sample property URLs
4. **Async Integration**: Implement concurrent crawling
5. **Error Handling**: Add robust error handling and retries
6. **Performance Tuning**: Optimize for speed and cost

## Benefits of Fire Crawl Integration

✅ **Solves anti-scraping issues** - No more 403/429 errors
✅ **Handles JavaScript** - Works with modern property sites  
✅ **Automatic pagination** - Discovers all listing pages
✅ **Structured extraction** - Clean, validated data
✅ **Async processing** - Efficient concurrent operations
✅ **Maintenance-free** - No need to update selectors or bypass methods

This approach transforms our scraping from a complex, fragile system into a robust, scalable solution that can handle the challenges of modern property websites.