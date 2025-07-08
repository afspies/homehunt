"""
Export configuration models for HomeHunt
Defines structures for various export formats and destinations
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ExportFormat(str, Enum):
    """Supported export formats"""
    CSV = "csv"
    JSON = "json"
    GOOGLE_SHEETS = "google_sheets"


class GoogleSheetsConfig(BaseModel):
    """Google Sheets export configuration"""
    
    # Authentication
    service_account_file: Optional[Path] = Field(
        None, 
        description="Path to Google service account JSON file"
    )
    service_account_info: Optional[Dict] = Field(
        None,
        description="Service account credentials as dict"
    )
    
    # Sheet configuration
    spreadsheet_id: Optional[str] = Field(None, description="Google Sheets spreadsheet ID")
    sheet_name: str = Field("Properties", description="Name of the sheet tab")
    create_new_sheet: bool = Field(True, description="Create new sheet if it doesn't exist")
    
    # Data configuration
    include_headers: bool = Field(True, description="Include column headers")
    clear_existing: bool = Field(False, description="Clear existing data before writing")
    append_mode: bool = Field(True, description="Append to existing data")
    
    # Sharing settings
    share_with_emails: Optional[List[str]] = Field(None, description="Email addresses to share sheet with")
    share_type: str = Field("reader", description="Share permission type (reader/writer/commenter)")
    
    @validator("service_account_file", pre=True)
    def validate_service_account_file(cls, v):
        if v and isinstance(v, str):
            return Path(v)
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate that either service_account_file or service_account_info is provided"""
        if not self.service_account_file and not self.service_account_info:
            raise ValueError("Either service_account_file or service_account_info must be provided")


class ExportConfig(BaseModel):
    """Export configuration for property data"""
    
    # Output configuration
    format: ExportFormat = Field(..., description="Export format")
    output_path: Optional[Path] = Field(None, description="Local output file path")
    
    # Google Sheets specific config
    google_sheets: Optional[GoogleSheetsConfig] = Field(None, description="Google Sheets configuration")
    
    # Data selection
    include_fields: Optional[List[str]] = Field(None, description="Specific fields to include")
    exclude_fields: Optional[List[str]] = Field(None, description="Fields to exclude") 
    
    # Filtering
    date_range: Optional[Dict[str, datetime]] = Field(None, description="Date range filter")
    portal_filter: Optional[List[str]] = Field(None, description="Filter by specific portals")
    price_range: Optional[Dict[str, float]] = Field(None, description="Price range filter")
    
    # Formatting options
    date_format: str = Field("%Y-%m-%d %H:%M:%S", description="Date format string")
    currency_symbol: str = Field("£", description="Currency symbol for prices")
    include_urls: bool = Field(True, description="Include property URLs")
    include_metadata: bool = Field(True, description="Include scraping metadata")
    
    @validator("output_path", pre=True)
    def validate_output_path(cls, v):
        if v and isinstance(v, str):
            return Path(v)
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate configuration based on format"""
        if self.format == ExportFormat.GOOGLE_SHEETS and not self.google_sheets:
            raise ValueError("google_sheets configuration required for Google Sheets export")
        
        if self.format in [ExportFormat.CSV, ExportFormat.JSON] and not self.output_path:
            raise ValueError(f"output_path required for {self.format.value} export")


class SyncConfig(BaseModel):
    """Configuration for automated sync operations"""
    
    # Sync settings
    enabled: bool = Field(False, description="Enable automatic syncing")
    interval_minutes: int = Field(60, description="Sync interval in minutes")
    
    # Export configuration
    exports: List[ExportConfig] = Field(..., description="List of export configurations")
    
    # Sync behavior
    sync_on_new_properties: bool = Field(True, description="Sync when new properties are found")
    sync_on_price_changes: bool = Field(True, description="Sync when price changes detected")
    max_retries: int = Field(3, description="Maximum retry attempts for failed syncs")
    
    # Filtering for sync
    only_active_properties: bool = Field(True, description="Only sync active properties")
    min_properties_for_sync: int = Field(1, description="Minimum properties required to trigger sync")
    
    # Metadata
    last_sync: Optional[datetime] = Field(None, description="Last successful sync timestamp")
    sync_count: int = Field(0, description="Total number of syncs performed")
    
    @validator("interval_minutes")
    def validate_interval(cls, v):
        if v < 5:
            raise ValueError("Sync interval must be at least 5 minutes")
        return v
    
    @validator("exports")
    def validate_exports(cls, v):
        if not v:
            raise ValueError("At least one export configuration is required")
        return v


class ExportResult(BaseModel):
    """Result of an export operation"""
    
    success: bool = Field(..., description="Whether export was successful")
    format: ExportFormat = Field(..., description="Export format used")
    output_location: Optional[str] = Field(None, description="Where data was exported to")
    
    # Statistics
    properties_exported: int = Field(0, description="Number of properties exported")
    file_size_bytes: Optional[int] = Field(None, description="Size of exported file")
    
    # Timing
    started_at: datetime = Field(..., description="Export start time")
    completed_at: Optional[datetime] = Field(None, description="Export completion time")
    duration_seconds: Optional[float] = Field(None, description="Export duration")
    
    # Error information
    error_message: Optional[str] = Field(None, description="Error message if export failed")
    error_details: Optional[Dict] = Field(None, description="Detailed error information")
    
    def model_post_init(self, __context) -> None:
        """Calculate duration if both timestamps are available"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()


class SyncResult(BaseModel):
    """Result of a sync operation"""
    
    success: bool = Field(..., description="Whether sync was successful")
    sync_id: str = Field(..., description="Unique sync operation ID")
    
    # Export results
    export_results: List[ExportResult] = Field(default_factory=list, description="Results of individual exports")
    
    # Statistics
    properties_processed: int = Field(0, description="Total properties processed")
    successful_exports: int = Field(0, description="Number of successful exports")
    failed_exports: int = Field(0, description="Number of failed exports")
    
    # Timing
    started_at: datetime = Field(..., description="Sync start time")
    completed_at: Optional[datetime] = Field(None, description="Sync completion time")
    duration_seconds: Optional[float] = Field(None, description="Sync duration")
    
    # Error information
    errors: List[str] = Field(default_factory=list, description="Any errors that occurred")
    
    def model_post_init(self, __context) -> None:
        """Calculate statistics and duration"""
        if self.export_results:
            self.successful_exports = sum(1 for r in self.export_results if r.success)
            self.failed_exports = len(self.export_results) - self.successful_exports
            self.properties_processed = max(r.properties_exported for r in self.export_results) if self.export_results else 0
        
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()
        
        # Overall success depends on having at least one successful export
        if self.export_results:
            self.success = self.successful_exports > 0