#!/usr/bin/env python3
"""
Test script for Fire Crawl API integration with property sites
Tests both crawl and scrape endpoints on Zoopla and Rightmove
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

# Load environment variables
load_dotenv()

console = Console()

class PropertyExtraction(BaseModel):
    """Test schema for property data extraction"""
    address: str = Field(description="Property address")
    price: str = Field(description="Rental price (e.g., £2,500 pcm)")
    bedrooms: int = Field(description="Number of bedrooms")
    property_type: str = Field(description="Type of property (flat, house, etc.)")
    postcode: str = Field(None, description="Postcode if available")
    description: str = Field(None, description="Property description")
    agent: str = Field(None, description="Estate agent name")
    url: str = Field(description="Property URL")

class FireCrawlTester:
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in environment")
        
        self.app = FirecrawlApp(api_key=api_key)
        self.results = {}
        
    async def test_search_pages(self):
        """Test scraping search result pages"""
        console.print("\n[bold blue]Testing Search Pages[/bold blue]")
        
        # Test URLs - using the ones you provided plus similar Rightmove
        test_urls = {
            "zoopla_victoria_2bed": "https://www.zoopla.co.uk/to-rent/property/london/victoria/?beds_min=2&price_frequency=per_month&price_max=3000&price_min=2000&q=Victoria%2C%20London&radius=0.25&search_source=to-rent",
            "zoopla_victoria_flats": "https://www.zoopla.co.uk/to-rent/flats/london/victoria/?beds_max=2&beds_min=0&price_frequency=per_month&price_max=3000&price_min=2000&q=Victoria,+London&radius=0&search_source=to-rent",
            "rightmove_london_rent": "https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E87490&minBedrooms=2&maxPrice=3000&radius=0.25&propertyTypes=&includeLetAgreed=false&mustHave=&dontShow=&furnishTypes=&keywords="
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            for name, url in test_urls.items():
                task = progress.add_task(f"Scraping {name}...", total=None)
                
                try:
                    # Test basic scrape endpoint - simplified call
                    result = self.app.scrape_url(url)
                    
                    self.results[f"{name}_scrape"] = {
                        'url': url,
                        'success': result.success,
                        'content_length': len(result.content or ''),
                        'markdown_length': len(result.markdown or ''),
                        'has_links': 'http' in (result.content or '').lower(),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    progress.update(task, description=f"✅ {name} - {len(result.content or '')} chars")
                    
                except Exception as e:
                    self.results[f"{name}_scrape"] = {
                        'url': url,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    progress.update(task, description=f"❌ {name} - Error: {str(e)[:50]}")
                
                await asyncio.sleep(1)  # Be respectful with timing
    
    async def test_crawl_functionality(self):
        """Test crawl endpoint for pagination discovery"""
        console.print("\n[bold blue]Testing Crawl Functionality[/bold blue]")
        
        # Test crawl on a simpler search to avoid overwhelming the API
        crawl_test_url = "https://www.rightmove.co.uk/property-to-rent/find.html?locationIdentifier=REGION%5E87490&minBedrooms=2&maxPrice=3000&radius=0.25"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Starting crawl...", total=None)
            
            try:
                # Start crawl with limited scope - simplified call
                crawl_result = self.app.crawl_url(crawl_test_url, limit=5)
                
                progress.update(task, description="✅ Crawl completed")
                
                # Check if we got crawl results
                if crawl_result.success:
                    data = crawl_result.data or []
                    self.results['crawl_test'] = {
                        'url': crawl_test_url,
                        'success': True,
                        'pages_found': len(data),
                        'sample_urls': [item.url for item in data[:3]] if data else [],
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    self.results['crawl_test'] = {
                        'url': crawl_test_url,
                        'success': False,
                        'error': 'Crawl returned success=False',
                        'timestamp': datetime.now().isoformat()
                    }
                    
            except Exception as e:
                self.results['crawl_test'] = {
                    'url': crawl_test_url,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                progress.update(task, description=f"❌ Crawl failed: {str(e)[:50]}")
    
    async def test_individual_property_extraction(self):
        """Test structured data extraction from individual property pages"""
        console.print("\n[bold blue]Testing Individual Property Extraction[/bold blue]")
        
        # Sample property URLs (these would typically be discovered from crawl)
        # Using some common patterns - these may or may not work
        test_property_urls = [
            "https://www.rightmove.co.uk/properties/147537623",
            "https://www.zoopla.co.uk/to-rent/details/70186875"
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            for i, url in enumerate(test_property_urls):
                task = progress.add_task(f"Extracting property {i+1}...", total=None)
                
                try:
                    # Test basic scraping first (we'll add extraction later)
                    result = self.app.scrape_url(url)
                    
                    if result.success:
                        content = result.content or ''
                        self.results[f'property_extract_{i}'] = {
                            'url': url,
                            'success': True,
                            'content_length': len(content),
                            'has_price': '£' in content,
                            'has_bedrooms': 'bedroom' in content.lower(),
                            'timestamp': datetime.now().isoformat()
                        }
                        progress.update(task, description=f"✅ Property {i+1} scraped")
                    else:
                        self.results[f'property_extract_{i}'] = {
                            'url': url,
                            'success': False,
                            'error': 'Scrape returned success=False',
                            'timestamp': datetime.now().isoformat()
                        }
                        progress.update(task, description=f"❌ Property {i+1} failed")
                        
                except Exception as e:
                    self.results[f'property_extract_{i}'] = {
                        'url': url,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    progress.update(task, description=f"❌ Property {i+1} error: {str(e)[:30]}")
                
                await asyncio.sleep(2)  # Be respectful between requests
    
    def display_results(self):
        """Display test results in a formatted table"""
        console.print("\n[bold green]Test Results Summary[/bold green]")
        
        # Create results table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="dim", width=25)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Details", width=50)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result.get('success') else "❌ FAIL"
            
            if result.get('success'):
                if 'content_length' in result:
                    details = f"Content: {result['content_length']} chars"
                elif 'pages_found' in result:
                    details = f"Pages found: {result['pages_found']}"
                elif 'extracted_data' in result:
                    details = f"Data extracted: {len(result['extracted_data'])} fields"
                else:
                    details = "Success"
            else:
                details = f"Error: {result.get('error', 'Unknown')[:45]}"
            
            table.add_row(test_name, status, details)
        
        console.print(table)
        
        # Show sample extracted data if available
        for test_name, result in self.results.items():
            if 'extracted_data' in result and result['extracted_data']:
                console.print(f"\n[bold cyan]Sample extracted data from {test_name}:[/bold cyan]")
                console.print(Panel(json.dumps(result['extracted_data'], indent=2)))
    
    def save_results(self):
        """Save results to JSON file for analysis"""
        results_file = Path("firecrawl_test_results.json")
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        console.print(f"\n[dim]Results saved to {results_file}[/dim]")

async def main():
    """Main test runner"""
    console.print(Panel.fit(
        "[bold blue]Fire Crawl API Test Suite[/bold blue]\n"
        "Testing scraping capabilities on Zoopla and Rightmove",
        title="HomeHunt Fire Crawl Integration Test"
    ))
    
    tester = FireCrawlTester()
    
    try:
        # Run tests sequentially to avoid overwhelming the API
        await tester.test_search_pages()
        await asyncio.sleep(5)  # Brief pause between test suites
        
        await tester.test_crawl_functionality()
        await asyncio.sleep(5)
        
        await tester.test_individual_property_extraction()
        
        # Display and save results
        tester.display_results()
        tester.save_results()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Test suite failed: {e}[/red]")
        console.print_exception()

if __name__ == "__main__":
    asyncio.run(main())