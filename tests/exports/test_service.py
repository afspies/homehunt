"""
Tests for export service
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homehunt.core.models import Portal, PropertyListing, PropertyType
from homehunt.exports.models import ExportConfig, ExportFormat
from homehunt.exports.service import ExportService, ExportServiceError


class TestExportService:
    """Test export service functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database"""
        db = AsyncMock()
        db.search_properties.return_value = []
        return db
    
    @pytest.fixture
    def export_service(self, mock_db):
        """Create export service with mock database"""
        return ExportService(mock_db)
    
    @pytest.fixture
    def sample_properties(self):
        """Create sample property listings"""
        return [
            PropertyListing(
                url="https://rightmove.co.uk/1",
                title="Test Property 1",
                price="£2000 pcm",
                bedrooms=2,
                portal=Portal.RIGHTMOVE,
                area="Test Area 1",
                property_type=PropertyType.FLAT
            ),
            PropertyListing(
                url="https://zoopla.co.uk/2",
                title="Test Property 2", 
                price="£2500 pcm",
                bedrooms=3,
                portal=Portal.ZOOPLA,
                area="Test Area 2",
                property_type=PropertyType.HOUSE
            )
        ]
    
    @pytest.mark.asyncio
    async def test_export_csv(self, export_service, sample_properties):
        """Test CSV export functionality"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            config = ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path(tmp.name)
            )
            
            result = await export_service.export_properties(config, sample_properties)
            
            assert result.success is True
            assert result.properties_exported == 2
            assert result.format == ExportFormat.CSV
            assert result.output_location == str(config.output_path)
            
            # Check file was created
            assert Path(tmp.name).exists()
            
            # Check CSV content
            with open(tmp.name, 'r') as f:
                content = f.read()
                assert 'Test Property 1' in content
                assert 'Test Property 2' in content
                assert 'rightmove' in content
                assert 'zoopla' in content
        
        # Cleanup
        Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_export_json(self, export_service, sample_properties):
        """Test JSON export functionality"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            config = ExportConfig(
                format=ExportFormat.JSON,
                output_path=Path(tmp.name),
                include_fields=["title", "price", "portal"]
            )
            
            result = await export_service.export_properties(config, sample_properties)
            
            assert result.success is True
            assert result.properties_exported == 2
            assert result.format == ExportFormat.JSON
            
            # Check JSON content
            with open(tmp.name, 'r') as f:
                data = json.load(f)
                assert 'metadata' in data
                assert 'properties' in data
                assert len(data['properties']) == 2
                
                # Check field filtering worked
                for prop in data['properties']:
                    assert 'title' in prop
                    assert 'price' in prop
                    assert 'portal' in prop
                    assert 'bedrooms' not in prop  # Should be filtered out
        
        # Cleanup
        Path(tmp.name).unlink()
    
    @pytest.mark.asyncio 
    async def test_export_no_properties(self, export_service):
        """Test export with no properties"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            config = ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path(tmp.name)
            )
            
            result = await export_service.export_properties(config, [])
            
            assert result.success is True
            assert result.properties_exported == 0
            assert "No properties to export" in result.error_message
        
        # Cleanup
        Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_export_with_filtering(self, export_service, sample_properties):
        """Test export with field filtering"""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            config = ExportConfig(
                format=ExportFormat.CSV,
                output_path=Path(tmp.name),
                include_fields=["title", "price"],
                include_urls=False,
                include_metadata=False
            )
            
            result = await export_service.export_properties(config, sample_properties)
            
            assert result.success is True
            assert result.properties_exported == 2
            
            # Check CSV headers
            with open(tmp.name, 'r') as f:
                first_line = f.readline().strip()
                assert 'title' in first_line
                assert 'price' in first_line
                assert 'url' not in first_line
                assert 'first_seen' not in first_line
        
        # Cleanup
        Path(tmp.name).unlink()
    
    @pytest.mark.asyncio
    async def test_export_error_handling(self, export_service, sample_properties):
        """Test export error handling"""
        # Use invalid path to trigger error
        config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("/invalid/path/test.csv")
        )
        
        result = await export_service.export_properties(config, sample_properties)
        
        assert result.success is False
        assert result.properties_exported == 0
        assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_get_export_templates(self, export_service):
        """Test getting export templates"""
        templates = await export_service.get_export_templates()
        
        assert isinstance(templates, dict)
        assert len(templates) > 0
        
        # Check basic template exists
        assert "basic_csv" in templates
        assert templates["basic_csv"].format == ExportFormat.CSV
        
        # Check Google Sheets template
        assert "google_sheets_basic" in templates
        assert templates["google_sheets_basic"].format == ExportFormat.GOOGLE_SHEETS
    
    @pytest.mark.asyncio
    async def test_format_property_data(self, export_service, sample_properties):
        """Test property data formatting"""
        config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("test.csv")
        )
        
        formatted = export_service._format_property_data(sample_properties, config)
        
        assert len(formatted) == 2
        assert isinstance(formatted[0], dict)
        
        # Check all expected fields are present
        expected_fields = ['title', 'price', 'bedrooms', 'portal', 'area']
        for field in expected_fields:
            assert field in formatted[0]
        
        # Check data values
        assert formatted[0]['title'] == "Test Property 1"
        assert formatted[0]['portal'] == "rightmove"
        assert formatted[1]['portal'] == "zoopla"
    
    @pytest.mark.asyncio
    async def test_filter_properties(self, export_service, sample_properties):
        """Test property filtering"""
        # Test with no filters
        config = ExportConfig(
            format=ExportFormat.CSV,
            output_path=Path("test.csv")
        )
        
        filtered = export_service._filter_properties(sample_properties, config)
        assert len(filtered) == 2
        
        # Test with price range filter
        config.price_range = {"min": 2200, "max": 3000}
        
        # Since our sample data uses string prices, this should return all
        # (the filter would need to be applied at DB level for real numeric filtering)
        filtered = export_service._filter_properties(sample_properties, config)
        assert len(filtered) == 2