"""
Main CLI application for HomeHunt
Provides commands for searching properties, managing database, and more
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from homehunt.core.db import Database, init_db
from homehunt.core.models import Portal, PropertyType
from homehunt.traveltime.client import TravelTimeClient
from homehunt.traveltime.service import TravelTimeService

from .config import FurnishedType, LetType, SearchConfig, SortOrder
from .search_command import search_properties
from .config_commands import init_config, list_configs, run_config, show_config

# Initialize Typer app
app = typer.Typer(
    name="homehunt",
    help="HomeHunt - Automated property search with commute analysis",
    add_completion=False,
)

# Console for rich output
console = Console()


@app.command()
def search(
    location: str = typer.Argument(..., help="Search location (postcode, area, or city)"),
    min_price: Optional[int] = typer.Option(None, "--min-price", help="Minimum monthly rent in pounds"),
    max_price: Optional[int] = typer.Option(None, "--max-price", help="Maximum monthly rent in pounds"),
    min_bedrooms: Optional[int] = typer.Option(None, "--min-beds", help="Minimum number of bedrooms"),
    max_bedrooms: Optional[int] = typer.Option(None, "--max-beds", help="Maximum number of bedrooms"),
    property_type: Optional[str] = typer.Option(None, "--type", help="Property type (flat/house/studio/bungalow/maisonette)"),
    furnished: str = typer.Option("any", "--furnished", help="Furnished status (furnished/unfurnished/part_furnished/any)"),
    radius: float = typer.Option(0.25, "--radius", help="Search radius in miles"),
    parking: bool = typer.Option(False, "--parking", help="Must have parking"),
    garden: bool = typer.Option(False, "--garden", help="Must have garden"),
    pets: bool = typer.Option(False, "--pets", help="Must allow pets"),
    portals: str = typer.Option("all", "--portals", help="Portals to search (rightmove/zoopla/all)"),
    max_results: int = typer.Option(100, "--max-results", help="Maximum results to return"),
    sort: str = typer.Option("date_desc", "--sort", help="Sort order (price_asc/price_desc/date_desc/date_asc)"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save results to database"),
    output: Optional[Path] = typer.Option(None, "--output", help="Export results to file (CSV/JSON)"),
):
    """
    Search for rental properties across Rightmove and Zoopla
    
    Examples:
        homehunt search "SW1A 1AA" --max-price 2000 --min-beds 1
        homehunt search "London" --type flat --furnished furnished --parking
        homehunt search "E14" --portals rightmove --radius 1.0
    """
    # Parse property type
    property_types = None
    if property_type:
        try:
            prop_type_enum = PropertyType(property_type.lower())
            property_types = [prop_type_enum]
        except ValueError:
            console.print(f"[red]Invalid property type: {property_type}[/red]")
            console.print("Valid types: flat, house, studio, bungalow, maisonette")
            raise typer.Exit(1)
    
    # Parse furnished status
    try:
        furnished_enum = FurnishedType(furnished.lower())
    except ValueError:
        console.print(f"[red]Invalid furnished status: {furnished}[/red]")
        console.print("Valid options: furnished, unfurnished, part_furnished, any")
        raise typer.Exit(1)
    
    # Parse sort order
    try:
        sort_enum = SortOrder(sort.lower())
    except ValueError:
        console.print(f"[red]Invalid sort order: {sort}[/red]")
        console.print("Valid options: price_asc, price_desc, date_desc, date_asc")
        raise typer.Exit(1)
    
    # Parse portals
    portal_list = []
    if portals.lower() == "all":
        portal_list = [Portal.RIGHTMOVE, Portal.ZOOPLA]
    elif portals.lower() == "rightmove":
        portal_list = [Portal.RIGHTMOVE]
    elif portals.lower() == "zoopla":
        portal_list = [Portal.ZOOPLA]
    else:
        console.print(f"[red]Invalid portals: {portals}[/red]")
        console.print("Valid options: rightmove, zoopla, all")
        raise typer.Exit(1)
    
    # Create search config
    config = SearchConfig(
        portals=portal_list,
        location=location,
        radius=radius,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        property_types=property_types,
        furnished=furnished_enum,
        parking=parking,
        garden=garden,
        pets_allowed=pets,
        sort_order=sort_enum,
        max_results=max_results,
    )
    
    # Run search
    try:
        asyncio.run(search_properties(config, save_to_db=save, output_file=output))
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error during search: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show database statistics"""
    async def show_stats():
        db = Database()
        stats = await db.get_statistics()
        
        # Overall stats
        console.print("\n[bold cyan]HomeHunt Database Statistics[/bold cyan]\n")
        console.print(f"Last updated: {stats.get('last_updated', 'Never')}")
        console.print(f"Properties scraped in last 24h: {stats.get('recent_activity', 0)}")
        
        # Portal breakdown
        portal_table = Table(title="\nProperties by Portal")
        portal_table.add_column("Portal", style="cyan")
        portal_table.add_column("Total", justify="right")
        portal_table.add_column("With Price", justify="right")
        portal_table.add_column("Avg Price", justify="right")
        
        for portal_stat in stats.get('portal_stats', []):
            avg_price = portal_stat.get('avg_price')
            avg_price_str = f"£{int(avg_price/100):,}" if avg_price else "N/A"
            
            portal_table.add_row(
                portal_stat['portal'],
                str(portal_stat['total']),
                str(portal_stat['with_price']),
                avg_price_str
            )
        
        console.print(portal_table)
        
        # Price statistics
        price_stats = stats.get('price_stats', {})
        if price_stats:
            console.print("\n[bold]Price Range:[/bold]")
            min_price = price_stats.get('min_price')
            max_price = price_stats.get('max_price')
            avg_price = price_stats.get('avg_price')
            
            if min_price:
                console.print(f"  Minimum: £{int(min_price/100):,}/month")
            if max_price:
                console.print(f"  Maximum: £{int(max_price/100):,}/month")
            if avg_price:
                console.print(f"  Average: £{int(avg_price/100):,}/month")
        
        await db.close()
    
    try:
        asyncio.run(show_stats())
    except Exception as e:
        console.print(f"[red]Error getting statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    limit: int = typer.Option(20, "--limit", help="Number of properties to show"),
    min_price: Optional[int] = typer.Option(None, "--min-price", help="Minimum monthly rent"),
    max_price: Optional[int] = typer.Option(None, "--max-price", help="Maximum monthly rent"),
    bedrooms: Optional[int] = typer.Option(None, "--beds", help="Number of bedrooms"),
    portal: Optional[str] = typer.Option(None, "--portal", help="Filter by portal"),
):
    """List properties from database"""
    async def list_properties():
        db = Database()
        
        # Parse portal if provided
        portal_enum = None
        if portal:
            try:
                portal_enum = Portal(portal.lower())
            except ValueError:
                console.print(f"[red]Invalid portal: {portal}[/red]")
                return
        
        # Convert prices to pence
        min_price_pence = min_price * 100 if min_price else None
        max_price_pence = max_price * 100 if max_price else None
        
        # Search properties
        properties = await db.search_properties(
            portal=portal_enum,
            min_price=min_price_pence,
            max_price=max_price_pence,
            bedrooms=bedrooms,
            limit=limit
        )
        
        if not properties:
            console.print("[yellow]No properties found matching criteria[/yellow]")
            return
        
        # Create table
        table = Table(title=f"\nShowing {len(properties)} Properties")
        table.add_column("Portal", style="cyan", width=10)
        table.add_column("Price", justify="right", width=12)
        table.add_column("Beds", justify="center", width=5)
        table.add_column("Type", width=12)
        table.add_column("Area", width=20)
        table.add_column("Address", width=40)
        table.add_column("Last Seen", width=10)
        
        for prop in properties:
            # Format price
            price_str = prop.price or "N/A"
            
            # Format date
            days_ago = (datetime.utcnow() - prop.last_scraped).days
            if days_ago == 0:
                last_seen = "Today"
            elif days_ago == 1:
                last_seen = "Yesterday"
            else:
                last_seen = f"{days_ago}d ago"
            
            table.add_row(
                prop.portal.value.title(),
                price_str,
                str(prop.bedrooms or "-"),
                prop.property_type.value if prop.property_type else "-",
                prop.area or "-",
                prop.address or "-",
                last_seen
            )
        
        console.print(table)
        
        # Show URLs if requested
        if typer.confirm("\nShow property URLs?", default=False):
            console.print("\n[bold]Property URLs:[/bold]")
            for i, prop in enumerate(properties, 1):
                console.print(f"{i}. {prop.url}")
        
        await db.close()
    
    try:
        asyncio.run(list_properties())
    except Exception as e:
        console.print(f"[red]Error listing properties: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init():
    """Initialize the database"""
    async def initialize():
        console.print("[cyan]Initializing HomeHunt database...[/cyan]")
        await init_db()
        console.print("[green]✓ Database initialized successfully![/green]")
    
    try:
        asyncio.run(initialize())
    except Exception as e:
        console.print(f"[red]Error initializing database: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cleanup(
    days: int = typer.Option(30, "--days", help="Mark properties older than N days as inactive"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clean up old properties from database"""
    if not confirm:
        confirm = typer.confirm(
            f"This will mark properties not seen in {days} days as inactive. Continue?"
        )
        if not confirm:
            console.print("[yellow]Cleanup cancelled[/yellow]")
            raise typer.Exit(0)
    
    async def run_cleanup():
        db = Database()
        console.print(f"[cyan]Marking properties older than {days} days as inactive...[/cyan]")
        await db.cleanup_old_data(days)
        console.print("[green]✓ Cleanup completed![/green]")
        await db.close()
    
    try:
        asyncio.run(run_cleanup())
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def commute(
    destination: str = typer.Argument(..., help="Commute destination (address or postcode)"),
    max_time: int = typer.Option(45, "--max-time", help="Maximum commute time in minutes"),
    transport: str = typer.Option("public_transport", "--transport", help="Transport mode (public_transport/cycling/walking/driving)"),
    departure_time: str = typer.Option("08:00", "--departure", help="Departure time (HH:MM format)"),
    limit: int = typer.Option(50, "--limit", help="Maximum properties to analyze"),
    update_all: bool = typer.Option(False, "--update-all", help="Update commute times for all properties"),
):
    """
    Analyze commute times for properties in database
    
    Examples:
        homehunt commute "Canary Wharf" --max-time 30 --transport public_transport
        homehunt commute "King's Cross Station" --transport cycling --max-time 20
        homehunt commute "EC2A 1AA" --update-all --departure 09:00
    """
    async def analyze_commutes():
        # Initialize services
        db = Database()
        
        try:
            traveltime_client = TravelTimeClient()
        except ValueError as e:
            console.print(f"[red]TravelTime API error: {e}[/red]")
            console.print("Please set TRAVELTIME_APP_ID and TRAVELTIME_API_KEY environment variables")
            return
        
        traveltime_service = TravelTimeService(db, traveltime_client)
        
        # Validate transport mode
        valid_modes = ["public_transport", "cycling", "walking", "driving"]
        if transport not in valid_modes:
            console.print(f"[red]Invalid transport mode: {transport}[/red]")
            console.print(f"Valid options: {', '.join(valid_modes)}")
            return
        
        # Get properties from database
        if update_all:
            properties = await db.search_properties(limit=1000)  # Get all properties
        else:
            properties = await db.search_properties(limit=limit)
        
        if not properties:
            console.print("[yellow]No properties found in database[/yellow]")
            console.print("Run a search first: homehunt search \"your location\"")
            return
        
        console.print(f"[cyan]Found {len(properties)} properties to analyze[/cyan]")
        
        # Analyze commute times
        transport_modes = [transport] if not update_all else ["public_transport", "cycling"]
        commute_results = await traveltime_service.analyze_property_commutes(
            properties=properties,
            destination_address=destination,
            transport_modes=transport_modes,
            departure_time=departure_time
        )
        
        # Filter properties by max commute time
        filtered_properties = await traveltime_service.filter_by_commute(
            properties=properties,
            max_commute_time=max_time,
            transport_mode=transport
        )
        
        if not filtered_properties:
            console.print(f"[yellow]No properties found within {max_time} minutes by {transport}[/yellow]")
            return
        
        # Display results
        console.print(f"\n[green]Found {len(filtered_properties)} properties within {max_time} minutes[/green]")
        
        # Create results table
        table = Table(title=f"\nProperties within {max_time}min by {transport.replace('_', ' ')}")
        table.add_column("Portal", style="cyan", width=10)
        table.add_column("Price", justify="right", width=12)
        table.add_column("Beds", justify="center", width=5)
        table.add_column("Area", width=20)
        table.add_column("Commute", justify="right", width=10)
        table.add_column("Address", width=40)
        
        # Sort by commute time
        sorted_properties = sorted(
            filtered_properties,
            key=lambda p: getattr(p, f"commute_{transport}") or 999
        )
        
        for prop in sorted_properties[:20]:  # Show top 20
            commute_time = getattr(prop, f"commute_{transport}")
            commute_str = f"{commute_time}min" if commute_time else "N/A"
            
            table.add_row(
                prop.portal.value.title(),
                prop.price or "N/A",
                str(prop.bedrooms or "-"),
                prop.area or "-",
                commute_str,
                (prop.address or "-")[:40]
            )
        
        console.print(table)
        
        # Show commute statistics
        stats = await traveltime_service.get_commute_statistics(
            filtered_properties, [transport]
        )
        
        mode_stats = stats.get(transport, {})
        if mode_stats.get("count", 0) > 0:
            console.print(f"\n[bold]Commute Statistics ({transport.replace('_', ' ')}):[/bold]")
            console.print(f"  Properties analyzed: {mode_stats['count']}")
            console.print(f"  Shortest commute: {mode_stats['min']}min")
            console.print(f"  Longest commute: {mode_stats['max']}min")
            console.print(f"  Average commute: {mode_stats['avg']:.1f}min")
        
        await db.close()
    
    try:
        asyncio.run(analyze_commutes())
    except KeyboardInterrupt:
        console.print("\n[yellow]Commute analysis cancelled by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error during commute analysis: {e}[/red]")
        raise typer.Exit(1)


# Configuration commands
app.command(name="run-config")(run_config)
app.command(name="init-config")(init_config)
app.command(name="list-configs")(list_configs)
app.command(name="show-config")(show_config)


@app.callback()
def callback():
    """
    HomeHunt - Automated property search with commute time analysis
    
    Search rental properties across multiple portals, analyze commute times,
    and get real-time alerts for new listings.
    """
    pass


def main():
    """Main entry point for CLI"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    app()


if __name__ == "__main__":
    main()