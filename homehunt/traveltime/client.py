"""
TravelTime API client for commute analysis
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import httpx
from pydantic import ValidationError

from .models import CommuteResult, GeocodingResult, Location


class TravelTimeClient:
    """
    Async client for TravelTime API
    Handles geocoding and commute time calculations
    """
    
    def __init__(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.app_id = app_id or os.getenv("TRAVELTIME_APP_ID")
        self.api_key = api_key or os.getenv("TRAVELTIME_API_KEY")
        self.base_url = "https://api.traveltimeapp.com"
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        if not self.app_id or not self.api_key:
            raise ValueError(
                "TravelTime API credentials required. Set TRAVELTIME_APP_ID and TRAVELTIME_API_KEY"
            )
    
    @property
    def headers(self) -> Dict[str, str]:
        """HTTP headers for API requests"""
        return {
            "Content-Type": "application/json",
            "X-Application-Id": self.app_id,
            "X-Api-Key": self.api_key,
        }
    
    async def geocode(self, address: str) -> Optional[GeocodingResult]:
        """
        Geocode an address to get coordinates
        
        Args:
            address: Address to geocode
            
        Returns:
            GeocodingResult with coordinates or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/v4/geocoding/search",
                    headers=self.headers,
                    params={"query": address, "limit": 1}
                )
                response.raise_for_status()
                
                data = response.json()
                if not data.get("features"):
                    self.logger.warning(f"No geocoding results for address: {address}")
                    return None
                
                feature = data["features"][0]
                geometry = feature["geometry"]
                properties = feature.get("properties", {})
                
                return GeocodingResult(
                    address=address,
                    lat=geometry["coordinates"][1],  # TravelTime returns [lng, lat]
                    lng=geometry["coordinates"][0],
                    formatted_address=properties.get("label"),
                    confidence=properties.get("confidence")
                )
                
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error geocoding address {address}: {e}")
            return None
        except (KeyError, ValidationError) as e:
            self.logger.error(f"Error parsing geocoding response for {address}: {e}")
            return None
    
    async def calculate_commute_times(
        self,
        origins: List[Tuple[str, float, float]],  # (id, lat, lng)
        destination: Tuple[str, float, float],     # (id, lat, lng)
        transport_modes: List[str] = None,
        departure_time: str = "08:00",
        max_travel_time: int = 3600  # 1 hour in seconds
    ) -> List[CommuteResult]:
        """
        Calculate commute times from multiple origins to a destination
        
        Args:
            origins: List of (property_id, lat, lng) tuples
            destination: (destination_id, lat, lng) tuple
            transport_modes: List of transport modes to calculate
            departure_time: Departure time in HH:MM format
            max_travel_time: Maximum travel time in seconds
            
        Returns:
            List of CommuteResult objects
        """
        if not origins:
            return []
        
        if transport_modes is None:
            transport_modes = ["public_transport", "driving", "cycling", "walking"]
        
        try:
            # Build locations list
            locations = []
            
            # Add destination
            dest_id, dest_lat, dest_lng = destination
            locations.append({
                "id": dest_id,
                "coords": {"lat": dest_lat, "lng": dest_lng}
            })
            
            # Add origins
            for origin_id, origin_lat, origin_lng in origins:
                locations.append({
                    "id": origin_id,
                    "coords": {"lat": origin_lat, "lng": origin_lng}
                })
            
            # Build departure searches for each transport mode
            departure_searches = []
            
            for mode in transport_modes:
                search_config = {
                    "id": f"commute_{mode}",
                    "coords": {"lat": dest_lat, "lng": dest_lng},
                    "transportation": {"type": mode},
                    "departure_time": departure_time,
                    "travel_time": max_travel_time,
                    "properties": ["travel_time"]
                }
                
                # Add mode-specific parameters
                if mode == "public_transport":
                    search_config["transportation"]["walking_time"] = 900  # 15 min walking
                elif mode == "driving":
                    search_config["transportation"]["disable_border_crossing"] = False
                
                departure_searches.append(search_config)
            
            # Make API request
            request_body = {
                "locations": locations,
                "departure_searches": departure_searches
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v4/time-filter",
                    headers=self.headers,
                    json=request_body
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_commute_results(data, origins, dest_id, transport_modes)
                
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error calculating commutes: {e}")
            return self._create_error_results(origins, dest_id, str(e))
        except Exception as e:
            self.logger.error(f"Error calculating commutes: {e}")
            return self._create_error_results(origins, dest_id, str(e))
    
    def _parse_commute_results(
        self,
        api_response: Dict,
        origins: List[Tuple[str, float, float]],
        destination_id: str,
        transport_modes: List[str]
    ) -> List[CommuteResult]:
        """Parse API response into CommuteResult objects"""
        results = []
        
        # Create a result for each origin
        for origin_id, _, _ in origins:
            result_data = {
                "property_id": origin_id,
                "destination": destination_id,
                "success": True
            }
            
            # Extract travel times for each mode
            for search in api_response.get("results", []):
                mode = search["search_id"].replace("commute_", "")
                if mode not in transport_modes:
                    continue
                
                # Find this origin in the results
                for location in search.get("locations", []):
                    if location["id"] == origin_id:
                        travel_time_seconds = location["properties"][0]["travel_time"]
                        travel_time_minutes = travel_time_seconds // 60
                        
                        if mode == "public_transport":
                            result_data["public_transport"] = travel_time_minutes
                        elif mode == "driving":
                            result_data["driving"] = travel_time_minutes
                        elif mode == "cycling":
                            result_data["cycling"] = travel_time_minutes
                        elif mode == "walking":
                            result_data["walking"] = travel_time_minutes
                        break
            
            try:
                results.append(CommuteResult(**result_data))
            except ValidationError as e:
                self.logger.error(f"Error creating CommuteResult for {origin_id}: {e}")
                results.append(CommuteResult(
                    property_id=origin_id,
                    destination=destination_id,
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    def _create_error_results(
        self,
        origins: List[Tuple[str, float, float]],
        destination_id: str,
        error_message: str
    ) -> List[CommuteResult]:
        """Create error results for failed API calls"""
        return [
            CommuteResult(
                property_id=origin_id,
                destination=destination_id,
                success=False,
                error_message=error_message
            )
            for origin_id, _, _ in origins
        ]
    
    async def get_property_commute(
        self,
        property_address: str,
        destination_address: str,
        transport_modes: List[str] = None,
        departure_time: str = "08:00"
    ) -> Optional[CommuteResult]:
        """
        Calculate commute time for a single property
        
        Args:
            property_address: Property address
            destination_address: Destination address  
            transport_modes: Transport modes to calculate
            departure_time: Departure time in HH:MM format
            
        Returns:
            CommuteResult or None if geocoding failed
        """
        # Geocode both addresses
        property_geo = await self.geocode(property_address)
        destination_geo = await self.geocode(destination_address)
        
        if not property_geo or not destination_geo:
            return CommuteResult(
                property_id=property_address,
                destination=destination_address,
                success=False,
                error_message="Failed to geocode addresses"
            )
        
        # Calculate commute times
        origins = [(property_address, property_geo.lat, property_geo.lng)]
        destination = (destination_address, destination_geo.lat, destination_geo.lng)
        
        results = await self.calculate_commute_times(
            origins=origins,
            destination=destination,
            transport_modes=transport_modes,
            departure_time=departure_time
        )
        
        return results[0] if results else None