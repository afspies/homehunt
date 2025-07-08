"""
CLI commands for export and sync operations
Handles exporting property data to various formats including Google Sheets
"""

import asyncio
from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from homehunt.core.db import Database
from homehunt.exports.models import ExportConfig, ExportFormat, GoogleSheetsConfig
from homehunt.exports.service import ExportService, ExportServiceError

console = Console()


async def run_export_operation(
    format: ExportFormat,
    output: Optional[Path] = None,
    spreadsheet_id: Optional[str] = None,
    service_account: Optional[Path] = None,
    sheet_name: str = "Properties",
    include_fields: Optional[List[str]] = None,
    exclude_fields: Optional[List[str]] = None,
    portal_filter: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    clear_existing: bool = False,
    share_emails: Optional[List[str]] = None,
) -> None:
    """Execute export operation"""
    
    db = Database()
    export_service = ExportService(db)
    
    try:
        # Build export configuration
        config_kwargs = {
            "format": format,
            "include_fields": include_fields,
            "exclude_fields": exclude_fields,
            "portal_filter": portal_filter,
        }
        
        # Add price range if specified
        if min_price is not None or max_price is not None:
            price_range = {}
            if min_price is not None:
                price_range["min"] = min_price
            if max_price is not None:
                price_range["max"] = max_price
            config_kwargs["price_range"] = price_range
        
        # Format-specific configuration
        if format in [ExportFormat.CSV, ExportFormat.JSON]:
            if not output:
                # Generate default filename
                timestamp = "properties"
                extension = format.value
                output = Path(f"./exports/{timestamp}.{extension}")
            
            config_kwargs["output_path"] = output
            
        elif format == ExportFormat.GOOGLE_SHEETS:
            if not service_account and not spreadsheet_id:
                console.print("[red]Error: Either --service-account or --spreadsheet-id is required for Google Sheets export[/red]")
                return
            
            # Build Google Sheets config
            sheets_config_kwargs = {
                "sheet_name": sheet_name,
                "include_headers": True,
                "clear_existing": clear_existing,
                "append_mode": not clear_existing,
            }
            
            if service_account:
                sheets_config_kwargs["service_account_file"] = service_account
            
            if spreadsheet_id:
                sheets_config_kwargs["spreadsheet_id"] = spreadsheet_id
            
            if share_emails:
                sheets_config_kwargs["share_with_emails"] = share_emails
                sheets_config_kwargs["share_type"] = "reader"
            
            config_kwargs["google_sheets"] = GoogleSheetsConfig(**sheets_config_kwargs)
        
        # Create export configuration
        export_config = ExportConfig(**config_kwargs)
        
        # Execute export
        console.print(f"[cyan]Starting {format.value} export...[/cyan]")
        
        result = await export_service.export_properties(export_config)
        
        if result.success:
            console.print(f"[green]✓ Export completed successfully![/green]")
            console.print(f"  Properties exported: {result.properties_exported}")
            if result.output_location:
                console.print(f"  Output location: {result.output_location}")
            if result.duration_seconds:
                console.print(f"  Duration: {result.duration_seconds:.2f} seconds")
            if result.file_size_bytes:
                console.print(f"  File size: {result.file_size_bytes:,} bytes")
        else:
            console.print(f"[red]✗ Export failed: {result.error_message}[/red]")
            
    except ExportServiceError as e:
        console.print(f"[red]Export error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
    finally:
        await db.close()


def export_csv(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output CSV file path"),
    include_fields: Optional[List[str]] = typer.Option(None, "--include", help="Fields to include"),
    exclude_fields: Optional[List[str]] = typer.Option(None, "--exclude", help="Fields to exclude"),
    portal: Optional[List[str]] = typer.Option(None, "--portal", help="Filter by portal(s)"),
    min_price: Optional[float] = typer.Option(None, "--min-price", help="Minimum price filter"),
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Maximum price filter"),
):
    """
    Export properties to CSV file
    
    Examples:
        homehunt export-csv --output properties.csv
        homehunt export-csv --include title,price,bedrooms,area
        homehunt export-csv --portal rightmove --min-price 1000 --max-price 3000
    """
    asyncio.run(run_export_operation(
        format=ExportFormat.CSV,
        output=output,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        portal_filter=portal,
        min_price=min_price,
        max_price=max_price,
    ))


def export_json(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON file path"),
    include_fields: Optional[List[str]] = typer.Option(None, "--include", help="Fields to include"),
    exclude_fields: Optional[List[str]] = typer.Option(None, "--exclude", help="Fields to exclude"),
    portal: Optional[List[str]] = typer.Option(None, "--portal", help="Filter by portal(s)"),
    min_price: Optional[float] = typer.Option(None, "--min-price", help="Minimum price filter"),
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Maximum price filter"),
):
    """
    Export properties to JSON file
    
    Examples:
        homehunt export-json --output properties.json
        homehunt export-json --include title,price,bedrooms --portal zoopla
    """
    asyncio.run(run_export_operation(
        format=ExportFormat.JSON,
        output=output,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        portal_filter=portal,
        min_price=min_price,
        max_price=max_price,
    ))


def export_sheets(
    spreadsheet_id: Optional[str] = typer.Option(None, "--spreadsheet-id", help="Google Sheets spreadsheet ID"),
    service_account: Optional[Path] = typer.Option(None, "--service-account", help="Service account JSON file"),
    sheet_name: str = typer.Option("Properties", "--sheet-name", help="Name of the sheet"),
    include_fields: Optional[List[str]] = typer.Option(None, "--include", help="Fields to include"),
    exclude_fields: Optional[List[str]] = typer.Option(None, "--exclude", help="Fields to exclude"),
    portal: Optional[List[str]] = typer.Option(None, "--portal", help="Filter by portal(s)"),
    min_price: Optional[float] = typer.Option(None, "--min-price", help="Minimum price filter"),
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Maximum price filter"),
    clear_existing: bool = typer.Option(False, "--clear", help="Clear existing data before writing"),
    share_with: Optional[List[str]] = typer.Option(None, "--share", help="Email addresses to share with"),
):
    """
    Export properties to Google Sheets
    
    Examples:
        homehunt export-sheets --service-account credentials.json
        homehunt export-sheets --spreadsheet-id 1ABC... --sheet-name "New Properties"
        homehunt export-sheets --service-account creds.json --share user@example.com --clear
    """
    asyncio.run(run_export_operation(
        format=ExportFormat.GOOGLE_SHEETS,
        spreadsheet_id=spreadsheet_id,
        service_account=service_account,
        sheet_name=sheet_name,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
        portal_filter=portal,
        min_price=min_price,
        max_price=max_price,
        clear_existing=clear_existing,
        share_emails=share_with,
    ))


def list_export_templates():
    """List available export templates"""
    async def show_templates():
        db = Database()
        export_service = ExportService(db)
        
        try:
            templates = await export_service.get_export_templates()
            
            if not templates:
                console.print("[yellow]No export templates available[/yellow]")
                return
            
            console.print(f"\\n[cyan]Available Export Templates ({len(templates)}):[/cyan]\\n")
            
            for name, config in templates.items():
                console.print(f"[bold]{name}[/bold]")
                console.print(f"  Format: {config.format.value}")
                
                if config.output_path:
                    console.print(f"  Output: {config.output_path}")
                
                if config.include_fields:
                    fields = ", ".join(config.include_fields[:5])
                    if len(config.include_fields) > 5:
                        fields += f" ... ({len(config.include_fields)} total)"
                    console.print(f"  Fields: {fields}")
                
                if config.google_sheets:
                    console.print(f"  Sheet: {config.google_sheets.sheet_name}")
                
                console.print()
                
        except Exception as e:
            console.print(f"[red]Error listing templates: {e}[/red]")
        finally:
            await db.close()
    
    asyncio.run(show_templates())


def export_status():
    """Show export and database status"""
    async def show_status():
        db = Database()
        
        try:
            # Get database statistics
            stats = await db.get_statistics()
            
            console.print("\\n[bold cyan]HomeHunt Export Status[/bold cyan]\\n")
            
            # Database stats table
            stats_table = Table(title="Database Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="white")
            
            total_properties = sum(portal_stat.get('total', 0) for portal_stat in stats.get('portal_stats', []))
            stats_table.add_row("Total Properties", str(total_properties))
            stats_table.add_row("Last Updated", stats.get('last_updated', 'Never'))
            stats_table.add_row("Recent Activity (24h)", str(stats.get('recent_activity', 0)))
            
            console.print(stats_table)
            
            # Portal breakdown
            if stats.get('portal_stats'):
                portal_table = Table(title="\\nPortal Breakdown")
                portal_table.add_column("Portal", style="cyan")
                portal_table.add_column("Properties", justify="right")
                portal_table.add_column("With Price", justify="right")
                
                for portal_stat in stats['portal_stats']:
                    portal_table.add_row(
                        portal_stat['portal'].title(),
                        str(portal_stat['total']),
                        str(portal_stat['with_price'])
                    )
                
                console.print(portal_table)
            
            # Export recommendations
            console.print("\\n[bold]Export Recommendations:[/bold]")
            if total_properties > 0:
                console.print("  • Use 'homehunt export-csv' for spreadsheet analysis")
                console.print("  • Use 'homehunt export-sheets' for live collaboration")
                console.print("  • Use 'homehunt export-json' for programmatic access")
            else:
                console.print("  • Run some searches first to populate the database")
                console.print("  • Example: homehunt search 'London' --max-price 2000")
                
        except Exception as e:
            console.print(f"[red]Error getting status: {e}[/red]")
        finally:
            await db.close()
    
    asyncio.run(show_status())


def test_sheets_connection(
    service_account: Optional[Path] = typer.Argument(None, help="Service account JSON file path (optional if using gcloud auth)"),
):
    """
    Test Google Sheets API connection
    
    Examples:
        homehunt test-sheets credentials.json
        homehunt test-sheets  # Uses gcloud application default credentials
    """
    async def test_connection():
        try:
            from homehunt.exports.client import GoogleSheetsClient
            from homehunt.exports.models import GoogleSheetsConfig
            
            # Create test configuration
            config_kwargs = {"sheet_name": "Test"}
            if service_account:
                config_kwargs["service_account_file"] = service_account
            
            config = GoogleSheetsConfig(**config_kwargs)
            
            client = GoogleSheetsClient(config)
            
            console.print("[cyan]Testing Google Sheets connection...[/cyan]")
            
            # Test by creating a temporary spreadsheet
            test_title = f"HomeHunt Connection Test {console._get_datetime().strftime('%Y%m%d_%H%M%S')}"
            spreadsheet_id = await client.create_spreadsheet(test_title)
            
            console.print(f"[green]✓ Connection successful![/green]")
            console.print(f"  Created test spreadsheet: {test_title}")
            console.print(f"  Spreadsheet ID: {spreadsheet_id}")
            console.print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            
            # Test writing data
            test_data = [
                ["Test", "Data"],
                ["Connection", "Successful"],
            ]
            
            await client.write_data(
                spreadsheet_id=spreadsheet_id,
                sheet_name="Sheet1",
                data=test_data,
                include_headers=True
            )
            
            console.print("[green]✓ Data writing test successful![/green]")
            console.print("\\n[blue]You can now use this service account for HomeHunt exports[/blue]")
            
        except Exception as e:
            console.print(f"[red]✗ Connection test failed: {e}[/red]")
            console.print("\\n[yellow]Please check:[/yellow]")
            console.print("  • Service account file path is correct")
            console.print("  • Service account has Google Sheets API enabled")
            console.print("  • Service account has Google Drive API enabled")
            console.print("  • Credentials file contains valid JSON")
    
    asyncio.run(test_connection())