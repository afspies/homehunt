"""
Export service for HomeHunt
Handles property data formatting and export operations
"""

import csv
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from homehunt.core.db import Database
from homehunt.core.models import PropertyListing

from .client import GoogleSheetsClient, GoogleSheetsError
from .models import (
    ExportConfig,
    ExportFormat,
    ExportResult,
    SyncConfig,
    SyncResult,
)

console = Console()


class ExportServiceError(Exception):
    """Export service error"""
    pass


class ExportService:
    """Service for exporting property data to various formats"""
    
    def __init__(self, db: Database):
        """
        Initialize export service
        
        Args:
            db: Database instance
        """
        self.db = db
    
    async def export_properties(
        self,
        config: ExportConfig,
        properties: Optional[List[PropertyListing]] = None
    ) -> ExportResult:
        """
        Export properties based on configuration
        
        Args:
            config: Export configuration
            properties: Optional list of properties (if None, fetches from DB)
            
        Returns:
            Export result
        """
        started_at = datetime.utcnow()
        
        try:
            # Get properties if not provided
            if properties is None:
                properties = await self._fetch_properties(config)
            
            # Apply filtering
            properties = self._filter_properties(properties, config)
            
            if not properties:
                return ExportResult(
                    success=True,
                    format=config.format,
                    properties_exported=0,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error_message="No properties to export"
                )
            
            # Format data
            formatted_data = self._format_property_data(properties, config)
            
            # Export based on format
            output_location = None
            file_size = None
            
            if config.format == ExportFormat.CSV:
                output_location = await self._export_csv(formatted_data, config)
                file_size = Path(output_location).stat().st_size if output_location else None
                
            elif config.format == ExportFormat.JSON:
                output_location = await self._export_json(formatted_data, config)
                file_size = Path(output_location).stat().st_size if output_location else None
                
            elif config.format == ExportFormat.GOOGLE_SHEETS:
                output_location = await self._export_google_sheets(formatted_data, config)
            
            completed_at = datetime.utcnow()
            
            return ExportResult(
                success=True,
                format=config.format,
                output_location=output_location,
                properties_exported=len(properties),
                file_size_bytes=file_size,
                started_at=started_at,
                completed_at=completed_at
            )
            
        except Exception as e:
            return ExportResult(
                success=False,
                format=config.format,
                properties_exported=0,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_message=str(e),
                error_details={"exception_type": type(e).__name__}
            )
    
    async def sync_exports(self, sync_config: SyncConfig) -> SyncResult:
        """
        Execute multiple exports as part of sync operation
        
        Args:
            sync_config: Sync configuration
            
        Returns:
            Sync result
        """
        sync_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        console.print(f"[cyan]Starting sync operation {sync_id}[/cyan]")
        
        try:
            export_results = []
            errors = []
            
            # Fetch properties once for all exports
            properties = await self._fetch_properties_for_sync(sync_config)
            
            if not properties and sync_config.min_properties_for_sync > 0:
                return SyncResult(
                    success=True,
                    sync_id=sync_id,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    errors=["No properties found to sync"]
                )
            
            # Execute each export
            for export_config in sync_config.exports:
                try:
                    result = await self.export_properties(export_config, properties)
                    export_results.append(result)
                    
                    if not result.success:
                        errors.append(f"Export {export_config.format.value} failed: {result.error_message}")
                        
                except Exception as e:
                    errors.append(f"Export {export_config.format.value} error: {str(e)}")
            
            # Update sync metadata
            sync_config.last_sync = datetime.utcnow()
            sync_config.sync_count += 1
            
            completed_at = datetime.utcnow()
            
            result = SyncResult(
                success=True,
                sync_id=sync_id,
                export_results=export_results,
                started_at=started_at,
                completed_at=completed_at,
                errors=errors
            )
            
            console.print(f"[green]Sync {sync_id} completed: {result.successful_exports}/{len(export_results)} exports successful[/green]")
            
            return result
            
        except Exception as e:
            return SyncResult(
                success=False,
                sync_id=sync_id,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                errors=[str(e)]
            )
    
    async def _fetch_properties(self, config: ExportConfig) -> List[PropertyListing]:
        """Fetch properties from database based on config filters"""
        # Build filter parameters
        kwargs = {}
        
        if config.portal_filter:
            # Convert string to Portal enum if needed
            from homehunt.core.models import Portal
            portals = []
            for portal_str in config.portal_filter:
                try:
                    portals.append(Portal(portal_str.lower()))
                except ValueError:
                    console.print(f"[yellow]Warning: Unknown portal '{portal_str}'[/yellow]")
            if portals:
                kwargs['portal'] = portals[0]  # Database search takes single portal
        
        if config.price_range:
            if 'min' in config.price_range:
                kwargs['min_price'] = int(config.price_range['min'] * 100)  # Convert to pence
            if 'max' in config.price_range:
                kwargs['max_price'] = int(config.price_range['max'] * 100)  # Convert to pence
        
        # Fetch properties
        properties = await self.db.search_properties(limit=10000, **kwargs)
        
        return properties
    
    async def _fetch_properties_for_sync(self, sync_config: SyncConfig) -> List[PropertyListing]:
        """Fetch properties for sync operation"""
        if sync_config.only_active_properties:
            # Get only active properties (this would need to be implemented in DB)
            properties = await self.db.search_properties(limit=10000)
        else:
            properties = await self.db.search_properties(limit=10000)
        
        return properties
    
    def _filter_properties(self, properties: List[PropertyListing], config: ExportConfig) -> List[PropertyListing]:
        """Apply additional filtering to properties"""
        filtered = properties
        
        # Date range filtering
        if config.date_range:
            if 'start' in config.date_range:
                start_date = config.date_range['start']
                filtered = [p for p in filtered if p.last_scraped >= start_date]
            
            if 'end' in config.date_range:
                end_date = config.date_range['end']
                filtered = [p for p in filtered if p.last_scraped <= end_date]
        
        return filtered
    
    def _format_property_data(self, properties: List[PropertyListing], config: ExportConfig) -> List[Dict[str, Any]]:
        """Format property data for export"""
        formatted_properties = []
        
        for prop in properties:
            # Convert property to dict - only use fields that actually exist
            data = {
                'property_id': prop.property_id,
                'uid': prop.uid,
                'url': prop.url,
                'title': prop.title,
                'price': prop.price,
                'price_numeric': prop.price_numeric,
                'bedrooms': prop.bedrooms,
                'bathrooms': prop.bathrooms,
                'property_type': prop.property_type.value if prop.property_type else None,
                'portal': prop.portal.value,
                'area': prop.area,
                'address': prop.address,
                'description': prop.description,
                'features': ', '.join(prop.features) if prop.features else None,
                'furnished': prop.furnished,
                'available_date': prop.available_date,
                'agent_name': prop.agent_name,
                'agent_phone': prop.agent_phone,
                'extraction_method': prop.extraction_method.value,
                'content_length': prop.content_length,
                'images': ', '.join(prop.images) if prop.images else None,
                'first_seen': prop.first_seen.strftime(config.date_format) if prop.first_seen else None,
                'last_seen': prop.last_scraped.strftime(config.date_format) if prop.last_scraped else None,
                'scrape_count': prop.scrape_count,
            }
            
            # Add commute data if available
            commute_fields = ['commute_public_transport', 'commute_cycling', 'commute_walking', 'commute_driving']
            for field in commute_fields:
                if hasattr(prop, field):
                    data[field] = getattr(prop, field)
            
            # Add calculated score if available
            if hasattr(prop, 'calculated_score'):
                data['score'] = getattr(prop, 'calculated_score')
            
            # Apply field filtering
            if config.include_fields:
                data = {k: v for k, v in data.items() if k in config.include_fields}
            elif config.exclude_fields:
                data = {k: v for k, v in data.items() if k not in config.exclude_fields}
            
            # Handle URLs
            if not config.include_urls and 'url' in data:
                del data['url']
            
            # Remove metadata if not wanted
            if not config.include_metadata:
                metadata_fields = ['first_seen', 'last_seen', 'is_active']
                for field in metadata_fields:
                    data.pop(field, None)
            
            formatted_properties.append(data)
        
        return formatted_properties
    
    async def _export_csv(self, data: List[Dict[str, Any]], config: ExportConfig) -> str:
        """Export data to CSV file"""
        if not config.output_path:
            raise ExportServiceError("Output path required for CSV export")
        
        output_path = Path(config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not data:
            # Create empty file
            output_path.write_text("")
            return str(output_path)
        
        # Get all field names
        fieldnames = list(data[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        console.print(f"[green]Exported {len(data)} properties to {output_path}[/green]")
        return str(output_path)
    
    async def _export_json(self, data: List[Dict[str, Any]], config: ExportConfig) -> str:
        """Export data to JSON file"""
        if not config.output_path:
            raise ExportServiceError("Output path required for JSON export")
        
        output_path = Path(config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create export metadata
        export_data = {
            'metadata': {
                'exported_at': datetime.utcnow().isoformat(),
                'property_count': len(data),
                'format_version': '1.0'
            },
            'properties': data
        }
        
        with open(output_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, default=str)
        
        console.print(f"[green]Exported {len(data)} properties to {output_path}[/green]")
        return str(output_path)
    
    async def _export_google_sheets(self, data: List[Dict[str, Any]], config: ExportConfig) -> str:
        """Export data to Google Sheets"""
        if not config.google_sheets:
            raise ExportServiceError("Google Sheets configuration required")
        
        sheets_config = config.google_sheets
        
        try:
            client = GoogleSheetsClient(sheets_config)
            
            # Get or create spreadsheet
            spreadsheet_id = sheets_config.spreadsheet_id
            if not spreadsheet_id:
                # Create new spreadsheet
                title = f"HomeHunt Properties {datetime.now().strftime('%Y-%m-%d')}"
                spreadsheet_id = await client.create_spreadsheet(title)
            
            # Ensure sheet exists
            if sheets_config.create_new_sheet:
                try:
                    await client.create_sheet(spreadsheet_id, sheets_config.sheet_name)
                except GoogleSheetsError:
                    pass  # Sheet might already exist
            
            # Convert data to rows
            if data:
                # Headers
                headers = list(data[0].keys())
                rows = [headers] if sheets_config.include_headers else []
                
                # Data rows
                for item in data:
                    row = [str(item.get(field, '')) for field in headers]
                    rows.append(row)
                
                # Write data
                if sheets_config.append_mode and not sheets_config.clear_existing:
                    # Append data (skip headers if they exist)
                    data_rows = rows[1:] if sheets_config.include_headers else rows
                    if data_rows:
                        await client.append_data(spreadsheet_id, sheets_config.sheet_name, data_rows)
                else:
                    # Write/overwrite data
                    await client.write_data(
                        spreadsheet_id=spreadsheet_id,
                        sheet_name=sheets_config.sheet_name,
                        data=rows,
                        clear_existing=sheets_config.clear_existing,
                        include_headers=sheets_config.include_headers
                    )
            
            # Share if emails provided
            if sheets_config.share_with_emails:
                await client.share_spreadsheet(
                    spreadsheet_id=spreadsheet_id,
                    email_addresses=sheets_config.share_with_emails,
                    role=sheets_config.share_type
                )
            
            # Return URL
            url = await client.get_sheet_url(spreadsheet_id, sheets_config.sheet_name)
            console.print(f"[green]Exported {len(data)} properties to Google Sheets: {url}[/green]")
            
            return url
            
        except GoogleSheetsError as e:
            raise ExportServiceError(f"Google Sheets export failed: {e}")
    
    async def get_export_templates(self) -> Dict[str, ExportConfig]:
        """Get predefined export templates"""
        return {
            "basic_csv": ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path("./exports/properties_basic.csv"),
                include_fields=[
                    "title", "price", "bedrooms", "property_type", 
                    "area", "address", "url", "portal", "last_seen"
                ]
            ),
            
            "detailed_csv": ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path("./exports/properties_detailed.csv"),
                exclude_fields=["id", "description", "features"]
            ),
            
            "commute_analysis": ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path("./exports/properties_commute.csv"),
                include_fields=[
                    "title", "price", "bedrooms", "area", "address",
                    "commute_public_transport", "commute_cycling", 
                    "score", "url"
                ]
            ),
            
            "google_sheets_basic": ExportConfig(
                format=ExportFormat.GOOGLE_SHEETS,
                google_sheets=GoogleSheetsConfig(
                    service_account_file=Path("./credentials/service_account.json"),
                    sheet_name="Properties",
                    include_headers=True,
                    clear_existing=False,
                    append_mode=True
                ),
                include_fields=[
                    "title", "price", "bedrooms", "property_type",
                    "area", "address", "url", "portal", "last_seen"
                ]
            )
        }