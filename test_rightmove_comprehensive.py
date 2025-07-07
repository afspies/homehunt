#!/usr/bin/env python3
"""
Test Fire Crawl with comprehensive Rightmove URL
"""

from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.panel import Panel
import json

load_dotenv()
console = Console()

def test_comprehensive_rightmove():
    """Test Fire Crawl with the comprehensive Rightmove URL"""
    
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        console.print("[red]FIRECRAWL_API_KEY not found[/red]")
        return
    
    app = FirecrawlApp(api_key=api_key)
    
    # The comprehensive URL you provided
    comprehensive_url = "https://www.rightmove.co.uk/property-to-rent/find.html?useLocationIdentifier=true&locationIdentifier=STATION%5E9491&rent=To+rent&radius=1.0&_includeLetAgreed=on&dontShow=houseShare,retirement,student&sortType=6&channel=RENT&transactionType=LETTING&displayLocationIdentifier=undefined&index=0&moveInByDate=2025-09-28&minBedrooms=0&maxBedrooms=2&furnishTypes=partFurnished,furnished&propertyTypes=flat,semi-detached,detached&maxPrice=3500&minPrice=2250"
    
    console.print(Panel.fit(
        "[bold blue]Testing Comprehensive Rightmove Search[/bold blue]\n"
        f"URL: {comprehensive_url[:80]}...",
        title="Fire Crawl Test"
    ))
    
    try:
        # First, let's inspect the response object
        console.print("\n[bold]1. Testing basic scrape...[/bold]")
        result = app.scrape_url(comprehensive_url)
        
        console.print(f"Response type: {type(result)}")
        console.print("Available attributes:")
        
        # Check what attributes are available
        for attr in dir(result):
            if not attr.startswith('_'):
                try:
                    value = getattr(result, attr)
                    if not callable(value):
                        value_preview = str(value)[:50] if value else "None"
                        console.print(f"  • {attr}: {value_preview}")
                except:
                    pass
        
        # Try different ways to access content
        console.print(f"\n[bold]2. Checking content access methods...[/bold]")
        
        content_methods = ['content', 'data', 'text', 'html', 'markdown']
        for method in content_methods:
            try:
                value = getattr(result, method, None)
                if value:
                    console.print(f"✅ {method}: {len(str(value))} characters")
                    
                    # Save a sample to file for inspection
                    with open(f"sample_{method}.txt", 'w') as f:
                        f.write(str(value)[:5000])  # First 5000 chars
                    console.print(f"   Sample saved to sample_{method}.txt")
                else:
                    console.print(f"❌ {method}: None or empty")
            except Exception as e:
                console.print(f"❌ {method}: Error - {e}")
        
        # Test crawl functionality
        console.print(f"\n[bold]3. Testing crawl functionality...[/bold]")
        
        try:
            crawl_result = app.crawl_url(comprehensive_url, limit=3)
            console.print(f"Crawl result type: {type(crawl_result)}")
            
            # Check crawl response attributes
            for attr in dir(crawl_result):
                if not attr.startswith('_'):
                    try:
                        value = getattr(crawl_result, attr)
                        if not callable(value) and value is not None:
                            console.print(f"  • {attr}: {str(value)[:50]}")
                    except:
                        pass
                        
        except Exception as e:
            console.print(f"Crawl error: {e}")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print_exception()

if __name__ == "__main__":
    test_comprehensive_rightmove()