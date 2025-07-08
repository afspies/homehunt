#!/usr/bin/env python3
"""
Test direct HTTP scraping on Zoopla properties
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

class ZooplaDirectScraper:
    """Test direct HTTP scraping on Zoopla"""
    
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
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.zoopla.co.uk/'
        }
        
    async def test_zoopla_property(self, property_id: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Test scraping individual Zoopla property page"""
        # Common Zoopla URL patterns
        url_patterns = [
            f"https://www.zoopla.co.uk/to-rent/details/{property_id}",
            f"https://www.zoopla.co.uk/rental/{property_id}",
            f"https://www.zoopla.co.uk/property/{property_id}"
        ]
        
        for url in url_patterns:
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
                        'error': None,
                        'portal': 'zoopla'
                    }
                    
                    if response.status == 200:
                        content = await response.text()
                        result['content_length'] = len(content)
                        
                        # Quick data extraction test for Zoopla
                        parser = HTMLParser(content)
                        
                        # Zoopla-specific selectors
                        price_elem = None
                        price_selectors = [
                            '[data-testid="price"]',
                            '.ui-pricing__main-price',
                            '.dp-price-text',
                            'h2[data-testid="price"]',
                            'span[data-testid="price"]'
                        ]
                        
                        for selector in price_selectors:
                            price_elem = parser.css_first(selector)
                            if price_elem:
                                break
                        
                        # Fallback to regex for price
                        price_text = None
                        if not price_elem:
                            price_match = re.search(r'£[\d,]+\s*(?:pcm|per month|pw|per week)', content, re.IGNORECASE)
                            if price_match:
                                price_text = price_match.group(0)
                        
                        # Look for bedrooms in Zoopla
                        bed_elem = None
                        bed_selectors = [
                            '[data-testid="beds-bathrooms"]',
                            '.dp-features-list',
                            'h1',
                            'title'
                        ]
                        
                        for selector in bed_selectors:
                            bed_elem = parser.css_first(selector)
                            if bed_elem and ('bed' in bed_elem.text().lower()):
                                break
                            bed_elem = None
                        
                        # Look for address in Zoopla
                        address_elem = None
                        address_selectors = [
                            '[data-testid="address-label"]',
                            'h1[data-testid="address"]',
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
                        
                        return result  # Success, return immediately
                    elif response.status == 403:
                        result['error'] = f"HTTP 403 Forbidden (Anti-bot)"
                    elif response.status == 404:
                        continue  # Try next URL pattern
                    else:
                        result['error'] = f"HTTP {response.status}"
                        
            except asyncio.TimeoutError:
                result = {
                    'property_id': property_id,
                    'url': url,
                    'success': False,
                    'error': 'Timeout',
                    'response_time': 30.0,
                    'portal': 'zoopla'
                }
            except Exception as e:
                result = {
                    'property_id': property_id,
                    'url': url,
                    'success': False,
                    'error': str(e),
                    'response_time': 0,
                    'portal': 'zoopla'
                }
        
        # If we get here, all URL patterns failed
        return {
            'property_id': property_id,
            'url': url_patterns[0],  # Return first URL as default
            'success': False,
            'error': 'All URL patterns failed',
            'portal': 'zoopla'
        }

async def test_zoopla_vs_rightmove():
    """Compare Zoopla and Rightmove direct scraping"""
    
    console.print(Panel.fit(
        "[bold blue]Zoopla vs Rightmove Direct Scraping Test[/bold blue]",
        title="Portal Comparison"
    ))
    
    # Test with some sample property IDs
    # Note: These might not be current/valid, but we can test the anti-bot response
    rightmove_ids = ['164209706', '164244281', '164223689']
    zoopla_ids = ['70186875', '70000000', '69999999']  # Sample IDs
    
    scraper = ZooplaDirectScraper()
    
    connector = aiohttp.TCPConnector(limit=3, limit_per_host=1)
    timeout = aiohttp.ClientTimeout(total=30)
    
    results = {'rightmove': [], 'zoopla': []}
    
    async with aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout
    ) as session:
        
        # Test Rightmove (we know this works)
        console.print("\n[bold]1. Testing Rightmove Direct Scraping[/bold]")
        
        for property_id in rightmove_ids:
            url = f"https://www.rightmove.co.uk/properties/{property_id}"
            try:
                start_time = time.time()
                async with session.get(url, headers=scraper.headers) as response:
                    elapsed = time.time() - start_time
                    result = {
                        'property_id': property_id,
                        'portal': 'rightmove',
                        'status_code': response.status,
                        'success': response.status == 200,
                        'response_time': elapsed,
                        'content_length': len(await response.text()) if response.status == 200 else 0
                    }
                    results['rightmove'].append(result)
                    console.print(f"  • RM {property_id}: {result['status_code']} ({result['response_time']:.2f}s)")
                    
            except Exception as e:
                results['rightmove'].append({
                    'property_id': property_id,
                    'portal': 'rightmove',
                    'success': False,
                    'error': str(e)
                })
                console.print(f"  • RM {property_id}: Error - {str(e)[:50]}")
            
            await asyncio.sleep(2)  # Be respectful
        
        # Test Zoopla
        console.print("\n[bold]2. Testing Zoopla Direct Scraping[/bold]")
        
        for property_id in zoopla_ids:
            result = await scraper.test_zoopla_property(property_id, session)
            results['zoopla'].append(result)
            
            if result['success']:
                console.print(f"  • ZP {property_id}: {result['status_code']} ({result['response_time']:.2f}s)")
            else:
                console.print(f"  • ZP {property_id}: {result.get('error', 'Failed')}")
            
            await asyncio.sleep(3)  # Be extra respectful with Zoopla
        
        # Analysis
        console.print(f"\n[bold]Results Analysis:[/bold]")
        
        rm_success = len([r for r in results['rightmove'] if r.get('success')])
        zp_success = len([r for r in results['zoopla'] if r.get('success')])
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Portal", style="bold")
        table.add_column("Success Rate", justify="center")
        table.add_column("Avg Response Time", justify="center")
        table.add_column("Anti-Bot Protection", justify="center")
        table.add_column("Recommendation", width=40)
        
        rm_avg_time = sum(r.get('response_time', 0) for r in results['rightmove'] if r.get('success')) / max(rm_success, 1)
        zp_avg_time = sum(r.get('response_time', 0) for r in results['zoopla'] if r.get('success')) / max(zp_success, 1)
        
        # Check for specific error patterns
        rm_403_count = len([r for r in results['rightmove'] if r.get('status_code') == 403])
        zp_403_count = len([r for r in results['zoopla'] if r.get('status_code') == 403])
        
        table.add_row(
            "Rightmove",
            f"{rm_success}/{len(rightmove_ids)}",
            f"{rm_avg_time:.2f}s" if rm_success > 0 else "N/A",
            "Low" if rm_403_count == 0 else "High",
            "✅ Use direct HTTP for individual properties"
        )
        
        table.add_row(
            "Zoopla",
            f"{zp_success}/{len(zoopla_ids)}",
            f"{zp_avg_time:.2f}s" if zp_success > 0 else "N/A",
            "Low" if zp_403_count == 0 else "High",
            "🔥 Use Fire Crawl" if zp_success == 0 else "✅ Direct HTTP viable"
        )
        
        console.print(table)
        
        # Save results
        comparison_data = {
            'test_timestamp': time.time(),
            'results': results,
            'summary': {
                'rightmove_success_rate': rm_success / len(rightmove_ids),
                'zoopla_success_rate': zp_success / len(zoopla_ids),
                'rightmove_403_errors': rm_403_count,
                'zoopla_403_errors': zp_403_count
            },
            'recommendations': {
                'rightmove': 'Direct HTTP scraping viable',
                'zoopla': 'Fire Crawl recommended' if zp_success == 0 else 'Direct HTTP viable with caution',
                'overall_strategy': 'Hybrid approach - Fire Crawl for discovery, direct HTTP where possible'
            }
        }
        
        with open('portal_comparison.json', 'w') as f:
            json.dump(comparison_data, f, indent=2)
        
        console.print(f"\n💾 Results saved to portal_comparison.json")
        
        # Strategic recommendations
        console.print(f"\n[bold cyan]Strategic Recommendations:[/bold cyan]")
        
        if rm_success > 0 and zp_success > 0:
            console.print("[green]✅ Both portals support direct HTTP scraping[/green]")
            console.print("  • Use hybrid approach for maximum efficiency")
            console.print("  • Fire Crawl for search page discovery")
            console.print("  • Direct HTTP for individual property pages")
            console.print("  • Implement portal-specific retry logic")
        elif rm_success > 0:
            console.print("[yellow]⚠️ Mixed results - Rightmove works, Zoopla may need Fire Crawl[/yellow]")
            console.print("  • Use direct HTTP for Rightmove properties")
            console.print("  • Use Fire Crawl for Zoopla properties")
            console.print("  • Monitor success rates and adjust strategy")
        else:
            console.print("[red]❌ High anti-bot protection detected[/red]")
            console.print("  • Stick with Fire Crawl for reliability")
            console.print("  • Consider proxy rotation for direct scraping")
            console.print("  • Implement sophisticated request patterns")

if __name__ == "__main__":
    asyncio.run(test_zoopla_vs_rightmove())