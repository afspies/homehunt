"""
Tests for TravelTime API client
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from homehunt.traveltime.client import TravelTimeClient
from homehunt.traveltime.models import CommuteResult, GeocodingResult


class TestTravelTimeClient:
    """Test TravelTime API client"""
    
    def test_client_initialization(self):
        """Test client initialization with credentials"""
        client = TravelTimeClient(app_id="test_app_id", api_key="test_api_key")
        
        assert client.app_id == "test_app_id"
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.traveltimeapp.com"
        assert client.timeout == 30
    
    def test_client_initialization_from_env(self):
        """Test client initialization from environment variables"""
        with patch.dict(os.environ, {
            "TRAVELTIME_APP_ID": "env_app_id",
            "TRAVELTIME_API_KEY": "env_api_key"
        }):
            client = TravelTimeClient()
            assert client.app_id == "env_app_id"
            assert client.api_key == "env_api_key"
    
    def test_client_missing_credentials(self):
        """Test client initialization without credentials"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TravelTime API credentials required"):
                TravelTimeClient()
    
    def test_headers_property(self):
        """Test HTTP headers generation"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        headers = client.headers
        
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Application-Id"] == "test_app"
        assert headers["X-Api-Key"] == "test_key"
    
    @pytest.mark.asyncio
    async def test_geocode_success(self):
        """Test successful geocoding"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        mock_response = {
            "features": [{
                "geometry": {
                    "coordinates": [-0.1278, 51.5074]  # [lng, lat]
                },
                "properties": {
                    "label": "London, United Kingdom",
                    "confidence": 0.95
                }
            }]
        }
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            result = await client.geocode("London, UK")
            
            assert isinstance(result, GeocodingResult)
            assert result.address == "London, UK"
            assert result.lat == 51.5074
            assert result.lng == -0.1278
            assert result.formatted_address == "London, United Kingdom"
            assert result.confidence == 0.95
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "/v4/geocoding/search" in call_args[0][0]
            assert call_args[1]["params"]["query"] == "London, UK"
    
    @pytest.mark.asyncio
    async def test_geocode_no_results(self):
        """Test geocoding with no results"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        mock_response = {"features": []}
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            result = await client.geocode("Invalid Address")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_geocode_http_error(self):
        """Test geocoding with HTTP error"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("API Error")
            
            result = await client.geocode("Test Address")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_calculate_commute_times_success(self):
        """Test successful commute time calculation"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        origins = [("prop1", 51.5074, -0.1278), ("prop2", 51.5155, -0.0922)]
        destination = ("dest", 51.5033, -0.1195)
        
        mock_response = {
            "results": [{
                "search_id": "commute_public_transport",
                "locations": [
                    {
                        "id": "prop1",
                        "properties": [{"travel_time": 1800}]  # 30 minutes
                    },
                    {
                        "id": "prop2", 
                        "properties": [{"travel_time": 2400}]  # 40 minutes
                    }
                ]
            }, {
                "search_id": "commute_cycling",
                "locations": [
                    {
                        "id": "prop1",
                        "properties": [{"travel_time": 1500}]  # 25 minutes
                    },
                    {
                        "id": "prop2",
                        "properties": [{"travel_time": 1800}]  # 30 minutes
                    }
                ]
            }]
        }
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_post.return_value = mock_response_obj
            
            results = await client.calculate_commute_times(
                origins=origins,
                destination=destination,
                transport_modes=["public_transport", "cycling"]
            )
            
            assert len(results) == 2
            
            # Check first property
            result1 = results[0]
            assert result1.property_id == "prop1"
            assert result1.destination == "dest"
            assert result1.public_transport == 30  # 1800 seconds / 60
            assert result1.cycling == 25  # 1500 seconds / 60
            assert result1.success is True
            
            # Check second property
            result2 = results[1]
            assert result2.property_id == "prop2"
            assert result2.public_transport == 40
            assert result2.cycling == 30
            assert result2.success is True
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "/v4/time-filter" in call_args[0][0]
            
            # Check request body structure
            request_body = call_args[1]["json"]
            assert "locations" in request_body
            assert "departure_searches" in request_body
            assert len(request_body["locations"]) == 3  # 2 origins + 1 destination
    
    @pytest.mark.asyncio
    async def test_calculate_commute_times_empty_origins(self):
        """Test commute calculation with empty origins"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        results = await client.calculate_commute_times(
            origins=[],
            destination=("dest", 51.5033, -0.1195)
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_calculate_commute_times_http_error(self):
        """Test commute calculation with HTTP error"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        origins = [("prop1", 51.5074, -0.1278)]
        destination = ("dest", 51.5033, -0.1195)
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.HTTPError("API Error")
            
            results = await client.calculate_commute_times(
                origins=origins,
                destination=destination
            )
            
            assert len(results) == 1
            assert results[0].success is False
            assert "API Error" in results[0].error_message
    
    @pytest.mark.asyncio
    async def test_get_property_commute_success(self):
        """Test single property commute calculation"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        # Mock geocoding responses
        geocode_responses = [
            # Property geocoding
            {
                "features": [{
                    "geometry": {"coordinates": [-0.1278, 51.5074]},
                    "properties": {"label": "Property Address"}
                }]
            },
            # Destination geocoding
            {
                "features": [{
                    "geometry": {"coordinates": [-0.1195, 51.5033]},
                    "properties": {"label": "Destination Address"}
                }]
            }
        ]
        
        # Mock commute calculation response
        commute_response = {
            "results": [{
                "search_id": "commute_public_transport",
                "locations": [{
                    "id": "Property Address",
                    "properties": [{"travel_time": 1800}]
                }]
            }]
        }
        
        with patch("httpx.AsyncClient.get") as mock_get, \
             patch("httpx.AsyncClient.post") as mock_post:
            
            # Setup geocoding mocks
            mock_get_responses = []
            for response_data in geocode_responses:
                mock_response = Mock()
                mock_response.json.return_value = response_data
                mock_response.raise_for_status.return_value = None
                mock_get_responses.append(mock_response)
            
            mock_get.side_effect = mock_get_responses
            
            # Setup commute calculation mock
            mock_post_response = Mock()
            mock_post_response.json.return_value = commute_response
            mock_post_response.raise_for_status.return_value = None
            mock_post.return_value = mock_post_response
            
            result = await client.get_property_commute(
                property_address="Property Address",
                destination_address="Destination Address",
                transport_modes=["public_transport"]
            )
            
            assert isinstance(result, CommuteResult)
            assert result.property_id == "Property Address"
            assert result.destination == "Destination Address"
            assert result.public_transport == 30  # 1800 / 60
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_get_property_commute_geocoding_failure(self):
        """Test property commute with geocoding failure"""
        client = TravelTimeClient(app_id="test_app", api_key="test_key")
        
        # Mock failed geocoding (no features)
        mock_response = {"features": []}
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response_obj = Mock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_get.return_value = mock_response_obj
            
            result = await client.get_property_commute(
                property_address="Invalid Address",
                destination_address="Valid Destination"
            )
            
            assert result.success is False
            assert "Failed to geocode addresses" in result.error_message