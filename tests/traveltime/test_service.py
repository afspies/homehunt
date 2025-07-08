"""
Tests for TravelTime service
"""

from unittest.mock import AsyncMock, Mock

import pytest

from homehunt.core.models import ExtractionMethod, Portal, PropertyListing, PropertyType
from homehunt.traveltime.client import TravelTimeClient
from homehunt.traveltime.models import CommuteResult, GeocodingResult
from homehunt.traveltime.service import TravelTimeService


@pytest.fixture
def mock_db():
    """Mock database"""
    db = Mock()
    # Create a proper async context manager mock
    async_session_mock = AsyncMock()
    async_session_mock.__aenter__ = AsyncMock(return_value=async_session_mock)
    async_session_mock.__aexit__ = AsyncMock(return_value=None)
    db.async_session.return_value = async_session_mock
    db.get_property = AsyncMock()
    db.save_property = AsyncMock()
    return db


@pytest.fixture
def mock_traveltime_client():
    """Mock TravelTime client"""
    client = Mock(spec=TravelTimeClient)
    client.geocode = AsyncMock()
    client.calculate_commute_times = AsyncMock()
    return client


@pytest.fixture
def sample_properties():
    """Sample property listings for testing"""
    return [
        PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="prop1",
            url="https://example.com/prop1",
            uid="rightmove:prop1",
            address="123 Test Street, London E1 4AB",
            price="£2,000 pcm",
            price_numeric=200000,
            bedrooms=2,
            property_type=PropertyType.FLAT,
            extraction_method=ExtractionMethod.DIRECT_HTTP
        ),
        PropertyListing(
            portal=Portal.ZOOPLA,
            property_id="prop2", 
            url="https://example.com/prop2",
            uid="zoopla:prop2",
            address="456 Example Road, London E2 8CD",
            price="£1,800 pcm",
            price_numeric=180000,
            bedrooms=1,
            property_type=PropertyType.STUDIO,
            extraction_method=ExtractionMethod.FIRECRAWL
        ),
        PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="prop3",
            url="https://example.com/prop3", 
            uid="rightmove:prop3",
            address=None,  # No address - should be filtered out
            price="£2,500 pcm",
            price_numeric=250000,
            bedrooms=3,
            property_type=PropertyType.HOUSE,
            extraction_method=ExtractionMethod.DIRECT_HTTP
        )
    ]


class TestTravelTimeService:
    """Test TravelTime service"""
    
    def test_service_initialization(self, mock_db, mock_traveltime_client):
        """Test service initialization"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        assert service.db == mock_db
        assert service.client == mock_traveltime_client
    
    @pytest.mark.asyncio
    async def test_analyze_property_commutes_success(
        self, mock_db, mock_traveltime_client, sample_properties
    ):
        """Test successful property commute analysis"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        # Mock geocoding for destination and properties
        def mock_geocode(address):
            if address == "Canary Wharf":
                return GeocodingResult(
                    address="Canary Wharf",
                    lat=51.5055,
                    lng=-0.0235
                )
            elif address == "123 Test Street, London E1 4AB":
                return GeocodingResult(
                    address=address,
                    lat=51.5074,
                    lng=-0.1278
                )
            elif address == "456 Example Road, London E2 8CD":
                return GeocodingResult(
                    address=address,
                    lat=51.5155,
                    lng=-0.0922
                )
            return None
        
        mock_traveltime_client.geocode.side_effect = mock_geocode
        
        # Mock commute calculation - this will be called for each property batch
        def mock_calculate_commute_times(origins, destination, **kwargs):
            results = []
            for origin_id, _, _ in origins:
                if origin_id == "rightmove:prop1":
                    results.append(CommuteResult(
                        property_id=origin_id,
                        destination="Canary Wharf",
                        public_transport=25,
                        cycling=30,
                        success=True
                    ))
                elif origin_id == "zoopla:prop2":
                    results.append(CommuteResult(
                        property_id=origin_id,
                        destination="Canary Wharf", 
                        public_transport=35,
                        cycling=40,
                        success=True
                    ))
            return results
        
        mock_traveltime_client.calculate_commute_times.side_effect = mock_calculate_commute_times
        
        # Mock database updates
        mock_db.get_property.side_effect = sample_properties[:2]  # Return first 2 properties
        mock_db.save_property.return_value = True
        
        results = await service.analyze_property_commutes(
            properties=sample_properties,
            destination_address="Canary Wharf",
            transport_modes=["public_transport", "cycling"]
        )
        
        # Verify results
        assert len(results) == 2  # Only properties with addresses
        assert all(result.success for result in results)
        
        # Check that we got results for both properties (order may vary)
        property_ids = [result.property_id for result in results]
        assert "rightmove:prop1" in property_ids
        assert "zoopla:prop2" in property_ids
        
        # Verify API calls
        assert mock_traveltime_client.geocode.call_count == 3  # Destination + 2 properties
        mock_traveltime_client.calculate_commute_times.assert_called()
        
        # Verify database updates
        assert mock_db.get_property.call_count == 2
        assert mock_db.save_property.call_count == 2
    
    @pytest.mark.asyncio
    async def test_analyze_property_commutes_empty_properties(
        self, mock_db, mock_traveltime_client
    ):
        """Test commute analysis with empty property list"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        results = await service.analyze_property_commutes(
            properties=[],
            destination_address="Test Destination"
        )
        
        assert results == []
        mock_traveltime_client.geocode.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_property_commutes_no_addresses(
        self, mock_db, mock_traveltime_client
    ):
        """Test commute analysis with properties having no addresses"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        # Properties without addresses
        properties_no_address = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop1",
                url="https://example.com/prop1",
                uid="rightmove:prop1",
                address=None,  # No address
                price="£2,000 pcm",
                extraction_method=ExtractionMethod.DIRECT_HTTP
            )
        ]
        
        results = await service.analyze_property_commutes(
            properties=properties_no_address,
            destination_address="Test Destination"
        )
        
        assert results == []
        mock_traveltime_client.geocode.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_property_commutes_geocoding_failure(
        self, mock_db, mock_traveltime_client, sample_properties
    ):
        """Test commute analysis with geocoding failure"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        # Mock failed destination geocoding
        mock_traveltime_client.geocode.return_value = None
        
        results = await service.analyze_property_commutes(
            properties=sample_properties,
            destination_address="Invalid Destination"
        )
        
        assert results == []
        mock_traveltime_client.calculate_commute_times.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_filter_by_commute(self, mock_db, mock_traveltime_client):
        """Test filtering properties by commute time"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        # Properties with commute times
        properties_with_commutes = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop1",
                url="https://example.com/prop1",
                uid="rightmove:prop1",
                address="Test Address 1",
                commute_public_transport=20,
                commute_cycling=25,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            ),
            PropertyListing(
                portal=Portal.ZOOPLA,
                property_id="prop2",
                url="https://example.com/prop2", 
                uid="zoopla:prop2",
                address="Test Address 2",
                commute_public_transport=45,
                commute_cycling=35,
                extraction_method=ExtractionMethod.FIRECRAWL
            ),
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop3",
                url="https://example.com/prop3",
                uid="rightmove:prop3", 
                address="Test Address 3",
                commute_public_transport=None,  # No commute data
                commute_cycling=None,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            )
        ]
        
        # Filter by public transport (max 30 minutes)
        filtered = await service.filter_by_commute(
            properties=properties_with_commutes,
            max_commute_time=30,
            transport_mode="public_transport"
        )
        
        assert len(filtered) == 1
        assert filtered[0].property_id == "prop1"
        
        # Filter by cycling (max 40 minutes)
        filtered_cycling = await service.filter_by_commute(
            properties=properties_with_commutes,
            max_commute_time=40,
            transport_mode="cycling"
        )
        
        assert len(filtered_cycling) == 2
        assert filtered_cycling[0].property_id == "prop1"
        assert filtered_cycling[1].property_id == "prop2"
        
        # Filter with high limit (all properties with data)
        filtered_high = await service.filter_by_commute(
            properties=properties_with_commutes,
            max_commute_time=60,
            transport_mode="public_transport"
        )
        
        assert len(filtered_high) == 2  # Excludes property with no commute data
    
    @pytest.mark.asyncio
    async def test_get_commute_statistics(self, mock_db, mock_traveltime_client):
        """Test commute statistics calculation"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        properties_with_commutes = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop1",
                url="https://example.com/prop1",
                uid="rightmove:prop1",
                commute_public_transport=20,
                commute_cycling=15,
                commute_walking=60,
                commute_driving=25,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            ),
            PropertyListing(
                portal=Portal.ZOOPLA,
                property_id="prop2",
                url="https://example.com/prop2",
                uid="zoopla:prop2",
                commute_public_transport=30,
                commute_cycling=25,
                commute_walking=80,
                commute_driving=35,
                extraction_method=ExtractionMethod.FIRECRAWL
            ),
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop3",
                url="https://example.com/prop3",
                uid="rightmove:prop3",
                commute_public_transport=40,
                commute_cycling=None,  # Missing cycling data
                commute_walking=None,  # Missing walking data
                commute_driving=None,  # Missing driving data
                extraction_method=ExtractionMethod.DIRECT_HTTP
            )
        ]
        
        stats = await service.get_commute_statistics(
            properties=properties_with_commutes,
            transport_modes=["public_transport", "cycling", "walking", "driving"]
        )
        
        # Public transport stats (all 3 properties have data)
        assert stats["public_transport"]["count"] == 3
        assert stats["public_transport"]["min"] == 20
        assert stats["public_transport"]["max"] == 40
        assert stats["public_transport"]["avg"] == 30.0
        
        # Cycling stats (only 2 properties have data)
        assert stats["cycling"]["count"] == 2
        assert stats["cycling"]["min"] == 15
        assert stats["cycling"]["max"] == 25
        assert stats["cycling"]["avg"] == 20.0
        
        # Walking stats (only 2 properties have data)
        assert stats["walking"]["count"] == 2
        assert stats["walking"]["min"] == 60
        assert stats["walking"]["max"] == 80
        assert stats["walking"]["avg"] == 70.0
        
        # Driving stats (only 2 properties have data)
        assert stats["driving"]["count"] == 2
        assert stats["driving"]["min"] == 25
        assert stats["driving"]["max"] == 35
        assert stats["driving"]["avg"] == 30.0
    
    @pytest.mark.asyncio
    async def test_get_commute_statistics_no_data(self, mock_db, mock_traveltime_client):
        """Test commute statistics with no data"""
        service = TravelTimeService(mock_db, mock_traveltime_client)
        
        properties_no_commutes = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="prop1",
                url="https://example.com/prop1",
                uid="rightmove:prop1",
                commute_public_transport=None,
                commute_cycling=None,
                extraction_method=ExtractionMethod.DIRECT_HTTP
            )
        ]
        
        stats = await service.get_commute_statistics(
            properties=properties_no_commutes,
            transport_modes=["public_transport", "cycling"]
        )
        
        assert stats["public_transport"]["count"] == 0
        assert stats["public_transport"]["min"] is None
        assert stats["public_transport"]["max"] is None
        assert stats["public_transport"]["avg"] is None
        
        assert stats["cycling"]["count"] == 0
        assert stats["cycling"]["min"] is None
        assert stats["cycling"]["max"] is None
        assert stats["cycling"]["avg"] is None