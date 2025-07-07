#!/usr/bin/env python3
"""
Debug script to inspect Fire Crawl API response objects
"""

from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import os
from rich.console import Console

load_dotenv()
console = Console()

def debug_response():
    """Debug Fire Crawl response object structure"""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        console.print("[red]FIRECRAWL_API_KEY not found[/red]")
        return
    
    app = FirecrawlApp(api_key=api_key)
    
    # Test with a simple URL first
    test_url = "https://example.com"
    console.print(f"[blue]Testing with {test_url}[/blue]")
    
    try:
        result = app.scrape_url(test_url)
        
        console.print(f"[green]Response type:[/green] {type(result)}")
        console.print(f"[green]Available attributes:[/green]")
        
        for attr in dir(result):
            if not attr.startswith('_'):
                try:
                    value = getattr(result, attr)
                    if callable(value):
                        console.print(f"  {attr}() - [dim]method[/dim]")
                    else:
                        console.print(f"  {attr} - [dim]{type(value).__name__}[/dim]: {str(value)[:100]}...")
                except Exception as e:
                    console.print(f"  {attr} - [red]Error: {e}[/red]")
                    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    debug_response()