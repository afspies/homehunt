"""
Async search command implementation with progress tracking
Coordinates hybrid scraping and database storage
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from rich.table import Table

from homehunt.core.db import Database
from homehunt.core.models import Portal, PropertyListing
from homehunt.scrapers.hybrid import HybridScraper

from .config import SearchConfig
from .url_builder import build_search_urls

console = Console()


async def search_properties(
    config: SearchConfig,
    save_to_db: bool = True,
    output_file: Optional[Path] = None,
) -> List[PropertyListing]:
    """
    Execute property search with progress tracking
    
    Args:
        config: Search configuration
        save_to_db: Whether to save results to database
        output_file: Optional file path to export results
        
    Returns:
        List of PropertyListing objects
    """
    # Initialize database if saving
    db = None
    if save_to_db:
        db = Database()
        await db.create_tables_async()
    
    # Build search URLs
    console.print("\n[cyan]Building search URLs...[/cyan]")
    search_urls = build_search_urls(config)
    
    # Display search parameters
    _display_search_config(config, search_urls)
    
    # Initialize scraper
    scraper = HybridScraper(
        rate_limit_per_minute=30,
        max_concurrent_requests=5,
    )
    
    all_properties = []
    
    try:
        # Create progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            # Search each portal
            for portal, urls in search_urls.items():
                portal_task = progress.add_task(
                    f"[cyan]Searching {portal.value.title()}...[/cyan]",
                    total=None
                )
                
                for url in urls:
                    # Run search
                    properties = await scraper.search_and_scrape(
                        search_url=url,
                        portal=portal,
                        max_results=config.max_results,
                    )
                    
                    console.print(
                        f"\n[green]✓[/green] Found {len(properties)} properties on {portal.value.title()}"
                    )
                    
                    # Save to database if enabled
                    if save_to_db and db:
                        saved_count = 0
                        for prop in properties:
                            if await db.save_property(prop):
                                saved_count += 1
                        
                        console.print(
                            f"[green]✓[/green] Saved {saved_count} properties to database"
                        )
                    
                    all_properties.extend(properties)
                
                progress.update(portal_task, completed=True)
        
        # Display results summary
        _display_results_summary(all_properties)
        
        # Export if requested
        if output_file:
            await _export_results(all_properties, output_file)
        
        # Show sample properties
        if all_properties:
            _display_sample_properties(all_properties[:5])
        
    finally:
        # Cleanup
        await scraper.close()
        if db:
            await db.close()
    
    return all_properties


def _display_search_config(config: SearchConfig, search_urls: dict):
    """Display search configuration in a nice panel"""
    lines = []
    
    lines.append(f"[bold]Location:[/bold] {config.location}")
    lines.append(f"[bold]Radius:[/bold] {config.radius.value} miles")
    
    if config.min_price or config.max_price:
        price_range = []
        if config.min_price:
            price_range.append(f"£{config.min_price}")
        else:
            price_range.append("Any")
        price_range.append(" - ")
        if config.max_price:
            price_range.append(f"£{config.max_price}")
        else:
            price_range.append("Any")
        lines.append(f"[bold]Price Range:[/bold] {''.join(price_range)}/month")
    
    if config.min_bedrooms or config.max_bedrooms:
        bed_range = []
        if config.min_bedrooms:
            bed_range.append(str(config.min_bedrooms))
        else:
            bed_range.append("Any")
        bed_range.append(" - ")
        if config.max_bedrooms:
            bed_range.append(str(config.max_bedrooms))
        else:
            bed_range.append("Any")
        lines.append(f"[bold]Bedrooms:[/bold] {''.join(bed_range)}")
    
    if config.property_types:
        types = ", ".join(pt.value for pt in config.property_types)
        lines.append(f"[bold]Property Types:[/bold] {types}")
    
    if config.furnished.value != "any":
        lines.append(f"[bold]Furnished:[/bold] {config.furnished.value}")
    
    # Additional filters
    filters = []
    if config.parking:
        filters.append("Parking")
    if config.garden:
        filters.append("Garden")
    if config.pets_allowed:
        filters.append("Pets Allowed")
    if filters:
        lines.append(f"[bold]Must Have:[/bold] {', '.join(filters)}")
    
    lines.append(f"[bold]Portals:[/bold] {', '.join(p.value.title() for p in config.portals)}")
    lines.append(f"[bold]Max Results:[/bold] {config.max_results}")
    
    panel = Panel(
        "\n".join(lines),
        title="[bold cyan]Search Configuration[/bold cyan]",
        border_style="cyan"
    )
    console.print(panel)


def _display_results_summary(properties: List[PropertyListing]):
    """Display summary of search results"""
    if not properties:
        console.print("\n[yellow]No properties found matching your criteria[/yellow]")
        return
    
    # Calculate statistics
    total = len(properties)
    by_portal = {}
    by_type = {}
    prices = []
    
    for prop in properties:
        # Count by portal
        by_portal[prop.portal.value] = by_portal.get(prop.portal.value, 0) + 1
        
        # Count by type
        if prop.property_type:
            by_type[prop.property_type.value] = by_type.get(prop.property_type.value, 0) + 1
        
        # Collect prices
        if prop.price_numeric:
            prices.append(prop.price_numeric / 100)  # Convert to pounds
    
    # Create summary
    lines = []
    lines.append(f"[bold]Total Properties Found:[/bold] {total}")
    lines.append("")
    
    lines.append("[bold]By Portal:[/bold]")
    for portal, count in sorted(by_portal.items()):
        lines.append(f"  • {portal.title()}: {count}")
    
    if by_type:
        lines.append("")
        lines.append("[bold]By Type:[/bold]")
        for prop_type, count in sorted(by_type.items()):
            lines.append(f"  • {prop_type.title()}: {count}")
    
    if prices:
        lines.append("")
        lines.append("[bold]Price Range:[/bold]")
        lines.append(f"  • Min: £{int(min(prices)):,}/month")
        lines.append(f"  • Max: £{int(max(prices)):,}/month")
        lines.append(f"  • Avg: £{int(sum(prices) / len(prices)):,}/month")
    
    panel = Panel(
        "\n".join(lines),
        title="[bold green]Search Results Summary[/bold green]",
        border_style="green"
    )
    console.print("\n")
    console.print(panel)


def _display_sample_properties(properties: List[PropertyListing]):
    """Display a sample of found properties"""
    if not properties:
        return
    
    console.print("\n[bold cyan]Sample Properties:[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Portal", width=10)
    table.add_column("Price", justify="right", width=12)
    table.add_column("Beds", justify="center", width=5)
    table.add_column("Type", width=12)
    table.add_column("Area", width=20)
    table.add_column("Features", width=30)
    
    for prop in properties:
        # Format features
        features = []
        if prop.furnished:
            features.append(prop.furnished)
        if prop.features:
            # Add first few features
            features.extend(prop.features[:2])
        features_str = ", ".join(features) if features else "-"
        
        table.add_row(
            prop.portal.value.title(),
            prop.price or "N/A",
            str(prop.bedrooms or "-"),
            prop.property_type.value if prop.property_type else "-",
            prop.area or "-",
            features_str
        )
    
    console.print(table)
    console.print(f"\n[dim]Showing {len(properties)} of {len(properties)} properties[/dim]")


async def _export_results(properties: List[PropertyListing], output_file: Path):
    """Export results to file"""
    console.print(f"\n[cyan]Exporting results to {output_file}...[/cyan]")
    
    try:
        if output_file.suffix.lower() == '.json':
            # Export as JSON
            data = [prop.to_dict() for prop in properties]
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        elif output_file.suffix.lower() == '.csv':
            # Export as CSV
            import csv
            
            # Define CSV fields
            fields = [
                'portal', 'property_id', 'url', 'price', 'bedrooms', 'bathrooms',
                'property_type', 'area', 'postcode', 'address', 'furnished',
                'agent_name', 'agent_phone', 'description'
            ]
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                
                for prop in properties:
                    row = {
                        'portal': prop.portal.value,
                        'property_id': prop.property_id,
                        'url': prop.url,
                        'price': prop.price,
                        'bedrooms': prop.bedrooms,
                        'bathrooms': prop.bathrooms,
                        'property_type': prop.property_type.value if prop.property_type else '',
                        'area': prop.area or '',
                        'postcode': prop.postcode or '',
                        'address': prop.address or '',
                        'furnished': prop.furnished or '',
                        'agent_name': prop.agent_name or '',
                        'agent_phone': prop.agent_phone or '',
                        'description': (prop.description or '')[:200],  # Truncate long descriptions
                    }
                    writer.writerow(row)
        
        else:
            console.print(f"[red]Unsupported file format: {output_file.suffix}[/red]")
            return
        
        console.print(f"[green]✓ Exported {len(properties)} properties to {output_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error exporting results: {e}[/red]")