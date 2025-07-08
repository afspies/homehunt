"""
Tests for export models
"""

import pytest
from pathlib import Path
from datetime import datetime

from homehunt.exports.models import (
    ExportConfig,
    ExportFormat,
    ExportResult,
    GoogleSheetsConfig,
    SyncConfig,
    SyncResult,
)


class TestExportModels:
    """Test export model validation and functionality"""
    
    def test_export_config_csv(self):
        """Test CSV export configuration"""
        config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("test.csv")
        )
        
        assert config.format == ExportFormat.CSV
        assert config.output_path == Path("test.csv")
        assert config.include_urls is True
        assert config.include_metadata is True
    
    def test_export_config_json(self):
        """Test JSON export configuration"""
        config = ExportConfig(
            format=ExportFormat.JSON,
            output_path=Path("test.json"),
            include_fields=["title", "price", "bedrooms"]
        )
        
        assert config.format == ExportFormat.JSON
        assert config.include_fields == ["title", "price", "bedrooms"]
    
    def test_google_sheets_config_with_file(self):
        """Test Google Sheets config with service account file"""
        sheets_config = GoogleSheetsConfig(
            service_account_file=Path("credentials.json"),
            sheet_name="Properties"
        )
        
        assert sheets_config.service_account_file == Path("credentials.json")
        assert sheets_config.sheet_name == "Properties"
        assert sheets_config.include_headers is True
    
    def test_google_sheets_config_with_info(self):
        """Test Google Sheets config with service account info dict"""
        service_info = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "client_email": "test@test.iam.gserviceaccount.com"
        }
        
        sheets_config = GoogleSheetsConfig(
            service_account_info=service_info,
            sheet_name="Test Sheet"
        )
        
        assert sheets_config.service_account_info == service_info
        assert sheets_config.sheet_name == "Test Sheet"
    
    def test_google_sheets_config_validation_error(self):
        """Test that GoogleSheetsConfig requires either file or info"""
        with pytest.raises(ValueError, match="Either service_account_file or service_account_info must be provided"):
            GoogleSheetsConfig(sheet_name="Test")
    
    def test_export_config_google_sheets(self):
        """Test export config for Google Sheets"""
        sheets_config = GoogleSheetsConfig(
            service_account_file=Path("creds.json"),
            sheet_name="Properties"
        )
        
        config = ExportConfig(
            format=ExportFormat.GOOGLE_SHEETS,
            google_sheets=sheets_config
        )
        
        assert config.format == ExportFormat.GOOGLE_SHEETS
        assert config.google_sheets is not None
        assert config.google_sheets.sheet_name == "Properties"
    
    def test_export_config_validation_google_sheets_missing(self):
        """Test that Google Sheets export requires sheets config"""
        with pytest.raises(ValueError, match="google_sheets configuration required"):
            ExportConfig(format=ExportFormat.GOOGLE_SHEETS)
    
    def test_export_config_validation_csv_missing_path(self):
        """Test that CSV export requires output path"""
        with pytest.raises(ValueError, match="output_path required"):
            ExportConfig(format=ExportFormat.CSV)
    
    def test_export_result_success(self):
        """Test successful export result"""
        started = datetime.utcnow()
        completed = datetime.utcnow()
        
        result = ExportResult(
            success=True,
            format=ExportFormat.CSV,
            output_location="test.csv",
            properties_exported=100,
            started_at=started,
            completed_at=completed
        )
        
        assert result.success is True
        assert result.properties_exported == 100
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
    
    def test_export_result_failure(self):
        """Test failed export result"""
        result = ExportResult(
            success=False,
            format=ExportFormat.CSV,
            properties_exported=0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            error_message="Export failed"
        )
        
        assert result.success is False
        assert result.properties_exported == 0
        assert result.error_message == "Export failed"
    
    def test_sync_config_validation(self):
        """Test sync configuration validation"""
        export_config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("test.csv")
        )
        
        sync_config = SyncConfig(
            exports=[export_config],
            interval_minutes=30
        )
        
        assert len(sync_config.exports) == 1
        assert sync_config.interval_minutes == 30
        assert sync_config.enabled is False
    
    def test_sync_config_validation_no_exports(self):
        """Test that sync config requires at least one export"""
        with pytest.raises(ValueError, match="At least one export configuration is required"):
            SyncConfig(exports=[])
    
    def test_sync_config_validation_interval_too_short(self):
        """Test that sync interval must be at least 5 minutes"""
        export_config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("test.csv")
        )
        
        with pytest.raises(ValueError, match="Sync interval must be at least 5 minutes"):
            SyncConfig(
                exports=[export_config],
                interval_minutes=2
            )
    
    def test_sync_result(self):
        """Test sync result with multiple exports"""
        export_result1 = ExportResult(
            success=True,
            format=ExportFormat.CSV,
            properties_exported=50,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        export_result2 = ExportResult(
            success=False,
            format=ExportFormat.JSON,
            properties_exported=0,
            started_at=datetime.utcnow(),
            error_message="Failed"
        )
        
        sync_result = SyncResult(
            success=True,
            sync_id="test-sync-123",
            export_results=[export_result1, export_result2],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        assert sync_result.successful_exports == 1
        assert sync_result.failed_exports == 1
        assert sync_result.properties_processed == 50  # Max from all exports
        assert sync_result.success is True  # At least one successful export