#!/usr/bin/env python3
"""
Test direct HTTP scraping vs Fire Crawl for individual property pages
"""

import asyncio
import aiohttp
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json
from typing import List, Dict, Any
from selectolax.parser import HTMLParser
import re

console = Console()

class DirectScraper:
    """Test direct HTTP scraping with proper headers"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
    async def test_individual_property(self, property_id: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test scraping individual property page"""
        url = f"https://www.rightmove.co.uk/properties/{property_id}"
        
        try:
            start_time = time.time()
            async with session.get(url, headers=self.headers) as response:
                elapsed = time.time() - start_time
                
                result = {
                    'property_id': property_id,
                    'url': url,
                    'status_code': response.status,
                    'success': response.status == 200,
                    'response_time': elapsed,
                    'content_length': 0,
                    'error': None
                }
                
                if response.status == 200:
                    content = await response.text()
                    result['content_length'] = len(content)
                    
                    # Quick data extraction test
                    parser = HTMLParser(content)
                    
                    # Look for price with multiple selectors
                    price_elem = None
                    price_selectors = [
                        'span[data-testid="price-text"]',
                        '.propertyHeaderPrice',
                        '[class*="price"]',
                        'span:contains("pcm")',
                        'span:contains("£")'
                    ]
                    
                    for selector in price_selectors:
                        if 'contains' not in selector:  # selectolax doesn't support :contains
                            price_elem = parser.css_first(selector)
                            if price_elem:
                                break
                    
                    # If no element found, search for £ in text content
                    price_text = None
                    if not price_elem:
                        import re
                        price_match = re.search(r'£[\d,]+\s*(?:pcm|per month|pw|per week)', content, re.IGNORECASE)
                        if price_match:
                            price_text = price_match.group(0)
                    
                    # Look for bedrooms  
                    bed_elem = None
                    bed_selectors = [
                        'span[data-testid="beds-label"]',
                        '.no-bed-baths',
                        '[class*="bed"]',
                        'h1'  # Often in the main heading
                    ]
                    
                    for selector in bed_selectors:
                        bed_elem = parser.css_first(selector)
                        if bed_elem and ('bed' in bed_elem.text().lower()):
                            break
                        bed_elem = None
                    
                    # Look for address
                    address_elem = None
                    address_selectors = [
                        'h1[data-testid="address-label"]',
                        '.propertyHeaderAddress',
                        'h1',
                        'title'
                    ]
                    
                    for selector in address_selectors:
                        address_elem = parser.css_first(selector)
                        if address_elem:
                            break
                    
                    result['extracted_data'] = {
                        'price': price_elem.text() if price_elem else price_text,
                        'bedrooms': bed_elem.text() if bed_elem else None,
                        'address': address_elem.text() if address_elem else None,
                        'has_price_in_content': '£' in content,
                        'has_bedroom_in_content': 'bedroom' in content.lower(),
                        'content_preview': content[:200],
                        'title': parser.css_first('title').text() if parser.css_first('title') else None
                    }
                else:
                    result['error'] = f"HTTP {response.status}"
                    
                return result
                
        except asyncio.TimeoutError:
            return {
                'property_id': property_id,
                'url': url,
                'success': False,
                'error': 'Timeout',
                'response_time': 30.0
            }
        except Exception as e:
            return {
                'property_id': property_id,
                'url': url,
                'success': False,
                'error': str(e),
                'response_time': 0
            }

async def test_direct_vs_firecrawl():
    """Compare direct scraping vs Fire Crawl"""
    
    console.print(Panel.fit(
        "[bold blue]Direct Scraping vs Fire Crawl Comparison[/bold blue]",
        title="Performance Test"
    ))
    
    # Test property IDs from our previous Fire Crawl test
    test_property_ids = [
        '164209706', '164194589', '164244281', 
        '164228585', '164236865', '164223689'
    ]
    
    scraper = DirectScraper()
    
    # Test direct HTTP scraping
    console.print("\n[bold]1. Testing Direct HTTP Scraping[/bold]")
    
    connector = aiohttp.TCPConnector(limit=5, limit_per_host=2)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout,
        headers=scraper.headers
    ) as session:
        
        start_time = time.time()
        
        # Test sequential requests first (be respectful)
        direct_results = []
        for property_id in test_property_ids:
            result = await scraper.test_individual_property(property_id, session)
            direct_results.append(result)
            console.print(f"  • {property_id}: {result['status_code']} ({result['response_time']:.2f}s)")
            
            # Be respectful - wait between requests
            await asyncio.sleep(2)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in direct_results if r['success']]
        failed_requests = [r for r in direct_results if not r['success']]
        
        console.print(f"\n[green]Direct Scraping Results:[/green]")
        console.print(f"  • Total time: {total_time:.2f}s")
        console.print(f"  • Successful: {len(successful_requests)}/{len(test_property_ids)}")
        console.print(f"  • Failed: {len(failed_requests)}")
        console.print(f"  • Average response time: {sum(r['response_time'] for r in successful_requests)/len(successful_requests):.2f}s" if successful_requests else "N/A")
        
        # Show failure details
        if failed_requests:
            console.print(f"\n[red]Failures:[/red]")
            for fail in failed_requests:
                console.print(f"  • {fail['property_id']}: {fail['error']}")
        
        # Show successful extractions
        if successful_requests:
            console.print(f"\n[green]Sample Extracted Data:[/green]")
            for success in successful_requests[:3]:
                data = success.get('extracted_data', {})
                console.print(f"  • {success['property_id']}:")
                console.print(f"    - Price: {data.get('price', 'Not found')}")
                console.print(f"    - Bedrooms: {data.get('bedrooms', 'Not found')}")
                address = data.get('address', 'Not found')
                console.print(f"    - Address: {address[:50] if address else 'Not found'}...")
                console.print(f"    - Content has £: {data.get('has_price_in_content', False)}")
        
        # Create comparison table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Method", style="bold")
        table.add_column("Speed", justify="center")
        table.add_column("Cost", justify="center") 
        table.add_column("Success Rate", justify="center")
        table.add_column("Data Quality", justify="center")
        table.add_column("Pros", width=30)
        table.add_column("Cons", width=30)
        
        # Calculate success rate
        success_rate = f"{len(successful_requests)}/{len(test_property_ids)} ({len(successful_requests)/len(test_property_ids)*100:.0f}%)"
        
        table.add_row(
            "Direct HTTP",
            f"{total_time:.1f}s",
            "Free",
            success_rate,
            "Good" if successful_requests else "Poor",
            "Fast, free, can customize parsing",
            "Anti-bot detection, rate limiting, maintenance"
        )
        
        table.add_row(
            "Fire Crawl",
            "~20s",
            "~$0.30",
            "100%",
            "Excellent", 
            "Bypasses anti-bot, reliable, handles JS",
            "Costs money, slower, API dependency"
        )
        
        console.print(f"\n[bold]Comparison Summary:[/bold]")
        console.print(table)
        
        # Save detailed results
        results_data = {
            'test_timestamp': time.time(),
            'direct_scraping': {
                'total_time': total_time,
                'success_count': len(successful_requests),
                'failure_count': len(failed_requests),
                'results': direct_results
            },
            'recommendations': {
                'use_direct_for': "Individual property pages if success rate > 80%",
                'use_firecrawl_for': "Search page discovery and problematic properties",
                'hybrid_approach': "Use Fire Crawl for discovery, direct HTTP for individual pages"
            }
        }
        
        with open('scraping_comparison.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        console.print(f"\n💾 Detailed results saved to scraping_comparison.json")
        
        # Recommendations
        console.print(f"\n[bold cyan]Recommendations:[/bold cyan]")
        
        if len(successful_requests) >= len(test_property_ids) * 0.8:
            console.print("[green]✅ Direct HTTP scraping viable for individual property pages[/green]")
            console.print("  • Use Fire Crawl for search page discovery")
            console.print("  • Use direct HTTP for individual property details")
            console.print("  • Implement proper rate limiting (2-3 second delays)")
            console.print("  • Monitor for rate limiting and fallback to Fire Crawl")
        else:
            console.print("[yellow]⚠️  Direct HTTP scraping has high failure rate[/yellow]") 
            console.print("  • Stick with Fire Crawl for reliability")
            console.print("  • Consider the cost vs reliability tradeoff")
            console.print("  • May need proxy rotation for direct scraping")

if __name__ == "__main__":
    asyncio.run(test_direct_vs_firecrawl())