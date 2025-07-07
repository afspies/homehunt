#!/usr/bin/env python3
"""
Extract structured property data from Fire Crawl response
"""

from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import os
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import json
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()
console = Console()

class PropertyListing(BaseModel):
    """Extracted property data"""
    property_id: Optional[str] = Field(default=None, description="Rightmove property ID")
    url: Optional[str] = Field(default=None, description="Property URL")
    price: Optional[str] = Field(default=None, description="Rental price")
    bedrooms: Optional[int] = Field(default=None, description="Number of bedrooms")
    address: Optional[str] = Field(default=None, description="Property address")
    description: Optional[str] = Field(default=None, description="Property description")
    images: List[str] = Field(default_factory=list, description="Image URLs")

def extract_property_ids(markdown_content: str) -> List[str]:
    """Extract property IDs from markdown content"""
    # Look for Rightmove property URLs
    pattern = r'rightmove\.co\.uk/properties/(\d+)'
    matches = re.findall(pattern, markdown_content)
    return list(set(matches))  # Remove duplicates

def extract_property_details(markdown_content: str) -> List[PropertyListing]:
    """Extract property details from markdown"""
    properties = []
    
    # Split content into potential property sections
    # Look for property IDs as section markers
    property_sections = re.split(r'(?=rightmove\.co\.uk/properties/\d+)', markdown_content)
    
    for section in property_sections:
        if 'rightmove.co.uk/properties/' in section:
            property_data = PropertyListing()
            
            # Extract property ID
            id_match = re.search(r'rightmove\.co\.uk/properties/(\d+)', section)
            if id_match:
                property_data.property_id = id_match.group(1)
                property_data.url = f"https://www.rightmove.co.uk/properties/{property_data.property_id}"
            
            # Extract images
            image_matches = re.findall(r'!\[.*?\]\((https://media\.rightmove\.co\.uk/[^)]+)\)', section)
            property_data.images = image_matches
            
            # Look for price information
            price_match = re.search(r'£[\d,]+\s*(?:pcm|per month|pw|per week)', section, re.IGNORECASE)
            if price_match:
                property_data.price = price_match.group(0)
            
            # Look for bedroom count
            bed_match = re.search(r'(\d+)\s*bed(?:room)?s?', section, re.IGNORECASE)
            if bed_match:
                property_data.bedrooms = int(bed_match.group(1))
            
            properties.append(property_data)
    
    return properties

def test_property_extraction():
    """Test Fire Crawl with property extraction"""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        console.print("[red]FIRECRAWL_API_KEY not found[/red]")
        return
    
    app = FirecrawlApp(api_key=api_key)
    
    # The comprehensive URL
    comprehensive_url = "https://www.rightmove.co.uk/property-to-rent/find.html?useLocationIdentifier=true&locationIdentifier=STATION%5E9491&rent=To+rent&radius=1.0&_includeLetAgreed=on&dontShow=houseShare,retirement,student&sortType=6&channel=RENT&transactionType=LETTING&displayLocationIdentifier=undefined&index=0&moveInByDate=2025-09-28&minBedrooms=0&maxBedrooms=2&furnishTypes=partFurnished,furnished&propertyTypes=flat,semi-detached,detached&maxPrice=3500&minPrice=2250"
    
    console.print(Panel.fit(
        "[bold blue]Fire Crawl Property Extraction Test[/bold blue]",
        title="HomeHunt Analysis"
    ))
    
    try:
        # 1. Test basic scraping
        console.print("\n[bold]1. Scraping search results...[/bold]")
        result = app.scrape_url(comprehensive_url)
        
        if result.success and result.markdown:
            console.print(f"✅ Scraped {len(result.markdown)} characters")
            
            # Save full markdown for analysis
            with open("full_rightmove_results.md", 'w', encoding='utf-8') as f:
                f.write(result.markdown)
            console.print("📄 Full results saved to full_rightmove_results.md")
            
            # Extract property IDs
            property_ids = extract_property_ids(result.markdown)
            console.print(f"🏠 Found {len(property_ids)} property IDs: {property_ids[:5]}...")
            
            # Extract property details
            properties = extract_property_details(result.markdown)
            valid_properties = [p for p in properties if p.property_id]
            
            console.print(f"✅ Extracted {len(valid_properties)} properties with details")
            
            # Display results table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Property ID", style="dim", width=12)
            table.add_column("Price", width=15)
            table.add_column("Bedrooms", justify="center", width=8)
            table.add_column("Images", justify="center", width=8)
            
            for prop in valid_properties[:10]:  # Show first 10
                table.add_row(
                    prop.property_id or "N/A",
                    prop.price or "N/A",
                    str(prop.bedrooms) if prop.bedrooms else "N/A",
                    str(len(prop.images))
                )
            
            console.print("\n[bold]Property Summary:[/bold]")
            console.print(table)
            
            # Save extracted data
            properties_data = [prop.dict() for prop in valid_properties]
            with open("extracted_properties.json", 'w') as f:
                json.dump(properties_data, f, indent=2)
            console.print(f"\n💾 Saved {len(properties_data)} properties to extracted_properties.json")
            
        else:
            console.print("❌ Failed to scrape content")
            
        # 2. Test individual property scraping
        if property_ids:
            console.print(f"\n[bold]2. Testing individual property scraping...[/bold]")
            individual_url = f"https://www.rightmove.co.uk/properties/{property_ids[0]}"
            
            individual_result = app.scrape_url(individual_url)
            if individual_result.success and individual_result.markdown:
                console.print(f"✅ Individual property: {len(individual_result.markdown)} characters")
                
                # Save individual property sample
                with open(f"individual_property_{property_ids[0]}.md", 'w', encoding='utf-8') as f:
                    f.write(individual_result.markdown)
                console.print(f"📄 Individual property saved to individual_property_{property_ids[0]}.md")
                
                # Look for detailed info
                price_matches = re.findall(r'£[\d,]+\s*(?:pcm|per month|pw|per week)', individual_result.markdown, re.IGNORECASE)
                bed_matches = re.findall(r'(\d+)\s*bed(?:room)?s?', individual_result.markdown, re.IGNORECASE)
                
                console.print(f"💰 Prices found: {price_matches[:3]}")
                console.print(f"🛏️  Bedrooms found: {bed_matches[:3]}")
                
        # 3. Test crawl for multiple pages
        console.print(f"\n[bold]3. Testing crawl for pagination...[/bold]")
        crawl_result = app.crawl_url(comprehensive_url, limit=3)
        
        if crawl_result.success and crawl_result.data:
            console.print(f"✅ Crawled {len(crawl_result.data)} pages")
            
            all_property_ids = []
            for page in crawl_result.data:
                if page.markdown:
                    page_ids = extract_property_ids(page.markdown)
                    all_property_ids.extend(page_ids)
            
            unique_ids = list(set(all_property_ids))
            console.print(f"🏠 Total unique properties across all pages: {len(unique_ids)}")
            
            # Save crawl results
            crawl_data = {
                'total_pages': len(crawl_result.data),
                'unique_properties': len(unique_ids),
                'property_ids': unique_ids
            }
            
            with open("crawl_results.json", 'w') as f:
                json.dump(crawl_data, f, indent=2)
            
        console.print(f"\n[green]✅ Fire Crawl integration test complete![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print_exception()

if __name__ == "__main__":
    test_property_extraction()