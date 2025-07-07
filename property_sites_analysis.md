# Property Sites Analysis - Zoopla & Rightmove

## Overview
This document analyzes the HTML structure and data availability on UK property websites to inform our scraping strategy and data models.

## Zoopla Analysis

### Initial Findings
- **Anti-scraping measures detected**: 403 Forbidden errors when accessing URLs directly
- **Potential bot detection**: The site likely uses various techniques to block automated requests
- **User-Agent requirements**: May need to mimic real browser behavior
- **Rate limiting**: Aggressive blocking of rapid requests

### URLs Analyzed (Failed Access)
1. **Victoria London Search (2+ beds, £2000-3000)**: 
   - `https://www.zoopla.co.uk/to-rent/property/london/victoria/?beds_min=2&price_frequency=per_month&price_max=3000&price_min=2000&q=Victoria%2C%20London&radius=0.25&search_source=to-rent`
   - Status: 403 Forbidden

2. **Victoria London Flats (0-2 beds, £2000-3000)**:
   - `https://www.zoopla.co.uk/to-rent/flats/london/victoria/?beds_max=2&beds_min=0&price_frequency=per_month&price_max=3000&price_min=2000&q=Victoria,+London&radius=0&search_source=to-rent`
   - Status: 403 Forbidden

### Scraping Strategy for Zoopla
Based on the 403 errors, we'll need to implement:

1. **Proper Headers**: 
   - User-Agent rotation
   - Accept headers mimicking real browsers
   - Referer headers
   - Accept-Language, Accept-Encoding

2. **Request Patterns**:
   - Randomized delays between requests
   - Session management with cookies
   - IP rotation (if necessary)

3. **Alternative Approaches**:
   - Consider using a headless browser (Playwright/Selenium)
   - Implement CAPTCHA handling if required
   - Use proxy rotation for IP diversity

## Rightmove Analysis

### Initial Findings
- **Partial access achieved**: Search pages accessible initially
- **Rate limiting detected**: 429 Too Many Requests after multiple calls
- **Less aggressive than Zoopla**: Initial requests succeed
- **JavaScript-heavy**: Extensive dynamic content loading

### URLs Analyzed

1. **Search Results Page**: 
   - **Status**: ✅ Accessible (initially)
   - **Rate Limit**: 429 after multiple requests
   - **Structure**: Responsive grid layout with property cards

### Property Listing Structure (From Search Results)
```html
<!-- Rightmove property card structure -->
<div class="property-card">
    <div class="property-image">
        <!-- Image carousel with multiple photos -->
        <img src="..." alt="Property photo">
    </div>
    <div class="property-details">
        <div class="property-price">£2,500 pcm</div>
        <div class="property-address">Street Address</div>
        <div class="property-type">2 bedroom flat</div>
        <div class="property-description">Brief description...</div>
        <div class="property-agent">Agent details</div>
    </div>
    <a href="/properties/163713287" class="property-link">View Details</a>
</div>
```

### Available Data Fields (Search Results)
- **Price**: Monthly (PCM) and weekly rates
- **Address**: Street address (not full postcode typically)
- **Property Type**: Flat, house, apartment, etc.
- **Bedrooms**: Number of bedrooms
- **Bathrooms**: Number of bathrooms
- **Description**: Brief property description
- **Agent**: Estate agent name and logo
- **Date Added**: When listing was added/reduced
- **Property ID**: Unique identifier in URL
- **Features**: Floorplan/virtual tour indicators

### Individual Property Pages
- **Status**: ❌ Rate limited (429 Too Many Requests)
- **Expected Data**: Full postcode, detailed description, comprehensive features
- **Access Strategy**: Need careful rate limiting and headers

## Expected Data Structure (Based on Typical Property Sites)

### Search Results Page Structure
```html
<!-- Typical structure we expect to find -->
<div class="search-results">
    <div class="property-listing" data-property-id="123456">
        <div class="property-image">
            <img src="..." alt="Property photo">
        </div>
        <div class="property-details">
            <h3 class="property-title">Property Address</h3>
            <div class="property-price">£2,500 pcm</div>
            <div class="property-beds">2 bedrooms</div>
            <div class="property-type">Flat</div>
            <div class="property-location">Victoria, London</div>
        </div>
        <a href="/property/details/123456" class="property-link">View Details</a>
    </div>
</div>
```

### Individual Property Page Structure
```html
<!-- Expected individual property structure -->
<div class="property-details-page">
    <div class="property-header">
        <h1 class="property-address">Full Address</h1>
        <div class="property-price">£2,500 per month</div>
    </div>
    <div class="property-features">
        <span class="bedrooms">2 bedrooms</span>
        <span class="bathrooms">1 bathroom</span>
        <span class="property-type">Flat</span>
    </div>
    <div class="property-description">
        <p>Property description text...</p>
    </div>
    <div class="property-contact">
        <div class="agent-info">Estate Agent Details</div>
    </div>
</div>
```

## Data Fields to Extract

### Primary Fields (Expected to be available)
- **Property ID**: Unique identifier for each listing
- **URL**: Direct link to property page
- **Address**: Full or partial address
- **Price**: Rental price (format varies: "£2,500 pcm", "£2500 per month")
- **Bedrooms**: Number of bedrooms
- **Property Type**: Flat, House, Studio, etc.
- **Location/Area**: District, postcode area

### Secondary Fields (May be available)
- **Bathrooms**: Number of bathrooms
- **Postcode**: Full postcode (crucial for commute calculations)
- **Property Size**: Square footage/meters
- **Furnished Status**: Furnished, Unfurnished, Part-furnished
- **Available Date**: When property becomes available
- **Description**: Property description text
- **Features**: Garden, parking, balcony, etc.
- **Agent Details**: Estate agent information
- **Images**: Property photos
- **Council Tax Band**: Tax information
- **EPC Rating**: Energy performance certificate

### Metadata Fields
- **Portal**: "zoopla" or "rightmove"
- **Listing ID**: Platform-specific ID
- **Scraped Date**: When we extracted the data
- **Last Updated**: When listing was last updated on site

## Technical Challenges Identified

### 1. Anti-Scraping Measures
- **403 Forbidden responses** from Zoopla
- **Likely bot detection** systems in place
- **Need for sophisticated request handling**

### 2. Dynamic Content Loading
- **JavaScript-rendered content** possible
- **AJAX-loaded listings** on scroll/pagination
- **React/Vue components** for property cards

### 3. Rate Limiting
- **Aggressive blocking** of rapid requests
- **Need for careful request timing**
- **Session management** requirements

## Recommended Implementation Strategy

### Phase 1: Basic HTTP Scraping
```python
# Sophisticated request handling
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Rate limiting with exponential backoff
import asyncio
import random

async def rate_limited_request(session, url):
    delay = random.uniform(1, 3)  # Random delay 1-3 seconds
    await asyncio.sleep(delay)
    
    try:
        response = await session.get(url, headers=headers)
        if response.status_code == 403:
            # Implement backoff strategy
            await asyncio.sleep(random.uniform(5, 15))
            # Retry with different headers or approach
        return response
    except Exception as e:
        # Handle and log errors
        pass
```

### Phase 2: Headless Browser (If Needed)
```python
# Playwright for JavaScript-heavy sites
from playwright.async_api import async_playwright

async def scrape_with_browser(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        # Wait for dynamic content to load
        await page.wait_for_selector('.property-listing')
        content = await page.content()
        await browser.close()
        return content
```

## Next Steps

1. **Try Rightmove URLs** - Test if they have similar blocking
2. **Implement robust HTTP client** with proper headers and rate limiting
3. **Create HTML parsing utilities** using selectolax
4. **Test with individual property pages** once we can access search results
5. **Design data models** based on actual extracted data
6. **Implement fallback strategies** for blocked requests

## Notes
- Both sites likely have Terms of Service restrictions on scraping
- Consider respecting robots.txt files
- Implement ethical scraping practices (reasonable delays, respect rate limits)
- Monitor for IP blocking and implement rotation if needed
- Consider legal implications of scraping real estate data