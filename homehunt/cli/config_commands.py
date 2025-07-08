"""
CLI commands for configuration-driven searches
Handles running searches from YAML/JSON config files
"""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from homehunt.config.executor import ConfigExecutor, ConfigExecutorError
from homehunt.config.manager import ConfigManager, ConfigManagerError
from homehunt.config.models import AdvancedSearchConfig, SavedSearchProfile
from homehunt.config.parser import ConfigParser, ConfigParserError
from homehunt.core.db import Database
from homehunt.core.models import PropertyListing

from .search_command import search_properties

console = Console()


async def run_config_search(
    config: AdvancedSearchConfig,
    profile_names: Optional[List[str]] = None,
    dry_run: bool = False
) -> None:
    """
    Execute searches based on configuration
    
    Args:
        config: Advanced search configuration
        profile_names: Specific profile names to run (all if None)
        dry_run: If True, show what would be done without executing
    """
    console.print(f"\\n[cyan]Executing configuration: {config.name or 'Unnamed'}[/cyan]")
    
    try:
        executor = ConfigExecutor(config)
        properties = await executor.execute(profile_names, dry_run)
        
        if not dry_run and properties:
            console.print(f"\\n[bold green]Search completed: {len(properties)} total properties[/bold green]")
            show_search_summary(properties, config.profiles)
        
    except ConfigExecutorError as e:
        console.print(f"[red]Execution error: {e}[/red]")
        raise


def show_search_summary(properties: List[PropertyListing], profiles: List[SavedSearchProfile]) -> None:
    """Show summary of search results"""
    # Profile summary
    table = Table(title="Search Results Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Profiles executed", str(len(profiles)))
    table.add_row("Total properties", str(len(properties)))
    
    # Property breakdown by portal
    portal_counts = {}
    for prop in properties:
        portal = prop.portal.value
        portal_counts[portal] = portal_counts.get(portal, 0) + 1
    
    for portal, count in portal_counts.items():
        table.add_row(f"{portal.title()} properties", str(count))
    
    # Price statistics
    prices = []
    for prop in properties:
        if prop.price:
            try:
                price_value = float(prop.price.replace('£', '').replace(',', '').replace(' pcm', ''))
                prices.append(price_value)
            except (ValueError, AttributeError):
                pass
    
    if prices:
        table.add_row("Average price", f"£{sum(prices) / len(prices):,.0f}")
        table.add_row("Price range", f"£{min(prices):,.0f} - £{max(prices):,.0f}")
    
    console.print(table)


# CLI command functions
def run_config(
    config_file: Path = typer.Argument(..., help="Path to configuration file"),
    profiles: Optional[List[str]] = typer.Option(None, "--profile", "-p", help="Specific profiles to run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without executing"),
    validate_only: bool = typer.Option(False, "--validate", help="Only validate configuration"),
):
    """
    Run property searches from configuration file
    
    Examples:
        homehunt run-config config.yaml
        homehunt run-config config.yaml --profile family_homes --profile budget_flats
        homehunt run-config config.yaml --dry-run
    """
    try:
        # Validate configuration
        config_manager = ConfigManager()
        errors = config_manager.validate_config(config_file)
        
        if errors:
            console.print(f"[red]Configuration validation failed:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            raise typer.Exit(1)
        
        if validate_only:
            console.print("[green]✓ Configuration is valid[/green]")
            return
        
        # Load and execute configuration
        config = ConfigParser.parse_config(config_file)
        
        asyncio.run(run_config_search(config, profiles, dry_run))
        
    except (ConfigParserError, ConfigManagerError) as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print(f"[red]Configuration file not found: {config_file}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\\n[yellow]Search cancelled by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error executing configuration: {e}[/red]")
        raise typer.Exit(1)


def init_config(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing file"),
):
    """
    Create a template configuration file
    
    Examples:
        homehunt init-config
        homehunt init-config --output my-config.yaml
    """
    try:
        config_manager = ConfigManager()
        
        if output is None:
            # Use default location
            output = config_manager.default_config_file
        
        if output.exists() and not overwrite:
            console.print(f"[red]Configuration file already exists: {output}[/red]")
            console.print("Use --overwrite to replace it")
            raise typer.Exit(1)
        
        # Create template
        template_config = ConfigParser.create_template_config()
        ConfigParser.save_file(template_config, output)
        
        console.print(f"[green]✓ Template configuration created: {output}[/green]")
        console.print("\\nEdit the file to customize your search criteria:")
        console.print(f"  {output}")
        
    except Exception as e:
        console.print(f"[red]Error creating configuration: {e}[/red]")
        raise typer.Exit(1)


def list_configs():
    """List available configuration files"""
    try:
        config_manager = ConfigManager()
        config_files = config_manager.list_config_files()
        
        if not config_files:
            console.print("[yellow]No configuration files found[/yellow]")
            console.print("Create one with: homehunt init-config")
            return
        
        console.print(f"\\n[cyan]Found {len(config_files)} configuration file(s):[/cyan]")
        
        for config_file in config_files:
            console.print(f"  • {config_file}")
            
            # Try to show basic info
            try:
                config = ConfigParser.parse_config(config_file)
                console.print(f"    {len(config.profiles)} profile(s): {', '.join(p.name for p in config.profiles[:3])}")
                if len(config.profiles) > 3:
                    console.print(f"    ... and {len(config.profiles) - 3} more")
            except Exception:
                console.print("    [red](Invalid configuration)[/red]")
        
    except Exception as e:
        console.print(f"[red]Error listing configurations: {e}[/red]")
        raise typer.Exit(1)


def show_config(
    config_file: Optional[Path] = typer.Argument(None, help="Configuration file to show"),
):
    """
    Show configuration summary
    
    Examples:
        homehunt show-config
        homehunt show-config my-config.yaml
    """
    try:
        config_manager = ConfigManager()
        
        if config_file is None:
            config_file = config_manager.default_config_file
            if not config_file.exists():
                console.print("[red]No default configuration found[/red]")
                console.print("Create one with: homehunt init-config")
                raise typer.Exit(1)
        
        config_manager.show_config_summary(config_file)
        
    except (ConfigParserError, ConfigManagerError) as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error showing configuration: {e}[/red]")
        raise typer.Exit(1)