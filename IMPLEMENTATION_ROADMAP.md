# Implementation Roadmap - HomeHunt

## Overview
This roadmap outlines the validated implementation plan for HomeHunt based on comprehensive testing and analysis. We've identified an optimal hybrid scraping strategy that balances cost, performance, and reliability.

## ✅ **Completed Research & Validation**

### Phase 0: Project Setup & Research ✅
- [x] Project structure and dependencies configured
- [x] Fire Crawl API integration tested (100% success rate)
- [x] Direct HTTP scraping validated (Rightmove: 100%, Zoopla: 0%)
- [x] Property deduplication system implemented
- [x] Portal-specific anti-bot analysis completed
- [x] Hybrid strategy validated and documented

### Key Findings
- **Fire Crawl**: 382 properties discovered, 53 unique across pagination
- **Direct HTTP**: 0.17s avg response time, 327KB content, 100% Rightmove success
- **Deduplication**: 57% efficiency avoiding redundant scraping
- **Cost Analysis**: 90% savings with hybrid approach ($5 vs $50 per 1000 properties)

## 🚀 **Implementation Phases**

### Phase 1: Core Data Layer (Next Priority)
**Estimated Time**: 2-3 days

#### 1.1 Validated Property Models
```python
# homehunt/core/models.py
class PropertyListing(BaseModel):
    # Validated schema based on test extraction results
    portal: str  # "rightmove" or "zoopla"
    property_id: str  # Extracted from URL
    uid: str  # "portal:property_id"
    title: str  # Rich data source from page title
    price: Optional[str]  # "£2,385 pcm" format
    address: Optional[str]  # From title parsing
    bedrooms: Optional[int]  # From title parsing
    extraction_method: str  # "firecrawl" or "direct_http"
```

#### 1.2 SQLModel Database Schema
```python
# homehunt/core/db.py
class Listing(SQLModel, table=True):
    uid: str = Field(primary_key=True)
    portal: str
    property_id: str
    url: str
    title: Optional[str]
    address: Optional[str]
    price: Optional[str]
    price_numeric: Optional[int]  # Parsed price
    bedrooms: Optional[int]
    property_type: Optional[str]
    extraction_method: str
    
    # Deduplication fields
    first_seen: datetime
    last_scraped: datetime
    scrape_count: int = 0
    
    # TravelTime integration
    commute_public_transport: Optional[int] = None
    commute_cycling: Optional[int] = None
```

#### 1.3 Integration with Deduplication System
- Merge `PropertyDeduplicationDB` with main database
- Add price change tracking
- Implement configurable re-scrape intervals

### Phase 2: Hybrid Scraper Implementation
**Estimated Time**: 3-4 days

#### 2.1 Core Hybrid Scraper
```python
# homehunt/core/scraper/hybrid_scraper.py
class HybridPropertyScraper:
    async def scrape_search_results(self, search_url: str) -> List[str]:
        # Fire Crawl for discovery (both portals)
        
    async def scrape_individual_properties(self, urls: List[str]) -> List[PropertyListing]:
        # Deduplication filtering
        # Rightmove: Direct HTTP
        # Zoopla: Fire Crawl
```

#### 2.2 Portal-Specific Extractors
```python
# homehunt/core/scraper/extractors.py
class RightmoveExtractor:
    def extract_from_title(self, title: str) -> Dict:
        # "1 bedroom apartment for rent in Grosvenor Road, London, SW1V"
        
class ZooplaExtractor:
    def extract_from_firecrawl(self, markdown: str) -> Dict:
        # Fire Crawl response processing
```

#### 2.3 Error Handling & Fallbacks
- Direct HTTP failure → Fire Crawl fallback
- Rate limiting detection and backoff
- Retry logic with exponential delays

### Phase 3: CLI Integration
**Estimated Time**: 1-2 days

#### 3.1 Updated CLI Commands
```bash
# Use comprehensive Rightmove URL format
python -m homehunt scrape \
  --portal rightmove \
  --location "STATION^9491" \
  --radius 1.0 \
  --min-price 2250 \
  --max-price 3500 \
  --min-beds 0 \
  --max-beds 2 \
  --furnished "partFurnished,furnished" \
  --property-types "flat,semi-detached,detached"
```

#### 3.2 Progress Tracking & Statistics
- Real-time progress with Rich console
- Deduplication statistics display
- Cost tracking (Fire Crawl API usage)
- Success rate monitoring by portal

### Phase 4: TravelTime Integration
**Estimated Time**: 2-3 days

#### 4.1 Async TravelTime Client
- Batch geocoding and commute calculation
- Results caching to avoid re-calculation
- Integration with property database

#### 4.2 Commute-Based Filtering
- Properties within X minutes by public transport
- Cycling time calculations
- Combined filter scenarios

### Phase 5: Advanced Features
**Estimated Time**: 3-4 days

#### 5.1 Telegram Alerts
- New property notifications
- Price change alerts
- Filter-based targeting

#### 5.2 Export Functionality
- Google Sheets integration
- CSV export with full data
- Scheduled exports

#### 5.3 Advanced Filtering
- New listings only (date-based)
- Price change detection
- Property type combinations

## 🔧 **Technical Considerations**

### Performance Optimizations
1. **Concurrent Processing**: 
   - Fire Crawl: 2 concurrent browsers
   - Direct HTTP: 5 concurrent connections with semaphores
   
2. **Caching Strategy**:
   - Property deduplication: 24-hour default
   - TravelTime results: 7-day cache
   - Search results: 1-hour cache

3. **Rate Limiting**:
   - Rightmove direct: 2-second delays
   - Zoopla Fire Crawl: 3-second delays
   - TravelTime API: 10 concurrent requests

### Monitoring & Observability
1. **Success Rate Tracking**:
   - Portal-specific success rates
   - Extraction method performance
   - Fallback frequency monitoring

2. **Cost Monitoring**:
   - Fire Crawl API usage tracking
   - Cost per property calculations
   - Budget alerts and limits

3. **Error Handling**:
   - Graceful degradation
   - Automatic retries with backoff
   - Comprehensive logging

## 📋 **Implementation Checklist**

### Phase 1: Data Layer
- [ ] Create validated PropertyListing model
- [ ] Implement SQLModel database schema
- [ ] Integrate deduplication system
- [ ] Add price change tracking
- [ ] Write comprehensive tests

### Phase 2: Hybrid Scraper
- [ ] Implement Fire Crawl search discovery
- [ ] Build direct HTTP Rightmove scraper
- [ ] Create data extraction pipeline
- [ ] Add error handling and fallbacks
- [ ] Implement rate limiting

### Phase 3: CLI Integration
- [ ] Update CLI with comprehensive URL building
- [ ] Add progress tracking and statistics
- [ ] Implement cost monitoring
- [ ] Add filtering options

### Phase 4: TravelTime Integration
- [ ] Build async TravelTime client
- [ ] Implement geocoding and caching
- [ ] Add commute-based filtering
- [ ] Optimize batch processing

### Phase 5: Advanced Features
- [ ] Telegram notification system
- [ ] Google Sheets export
- [ ] Advanced filtering options
- [ ] Scheduling and automation

## 🎯 **Success Metrics**

### Performance Targets
- **Speed**: <2s average per property (vs 20s pure Fire Crawl)
- **Cost**: <$5 per 1000 properties (vs $50 pure Fire Crawl)
- **Success Rate**: >95% property extraction success
- **Deduplication**: >50% efficiency in avoiding redundant scraping

### Quality Targets
- **Data Completeness**: >90% properties with price, bedrooms, address
- **Accuracy**: >95% correct property type and bedroom extraction
- **Freshness**: Properties updated within 24 hours
- **Coverage**: Both Rightmove and Zoopla fully supported

This roadmap provides a clear, tested path forward based on our comprehensive analysis and validation testing.