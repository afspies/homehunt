"""
TravelTime service for property commute analysis
"""

import asyncio
import logging
from typing import List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from homehunt.core.db import Database
from homehunt.core.models import PropertyListing

from .client import TravelTimeClient
from .models import CommuteResult


class TravelTimeService:
    """
    Service for analyzing property commute times
    Integrates TravelTime API with property database
    """
    
    def __init__(self, db: Database, traveltime_client: TravelTimeClient):
        self.db = db
        self.client = traveltime_client
        self.logger = logging.getLogger(__name__)
        self.console = Console()
    
    async def analyze_property_commutes(
        self,
        properties: List[PropertyListing],
        destination_address: str,
        transport_modes: List[str] = None,
        departure_time: str = "08:00",
        max_concurrent: int = 5
    ) -> List[CommuteResult]:
        """
        Analyze commute times for multiple properties
        
        Args:
            properties: List of properties to analyze
            destination_address: Destination for commute calculation
            transport_modes: Transport modes to calculate
            departure_time: Departure time in HH:MM format
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of CommmuteResult objects
        """
        if not properties:
            return []
        
        if transport_modes is None:
            transport_modes = ["public_transport", "cycling"]
        
        # Filter properties that have addresses
        valid_properties = [p for p in properties if p.address]
        
        if not valid_properties:
            self.logger.warning("No properties with addresses found for commute analysis")
            return []
        
        self.console.print(f"[blue]Analyzing commutes for {len(valid_properties)} properties...[/blue]")
        
        # Geocode destination once
        destination_geo = await self.client.geocode(destination_address)
        if not destination_geo:
            self.logger.error(f"Failed to geocode destination: {destination_address}")
            return []
        
        # Process properties in batches to respect rate limits
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Calculating commutes...", total=len(valid_properties))
            
            async def process_property(prop: PropertyListing) -> Optional[CommuteResult]:
                async with semaphore:
                    try:
                        # Geocode property address
                        property_geo = await self.client.geocode(prop.address)
                        if not property_geo:
                            self.logger.warning(f"Failed to geocode property: {prop.address}")
                            return CommuteResult(
                                property_id=prop.uid,
                                destination=destination_address,
                                success=False,
                                error_message="Failed to geocode property address"
                            )
                        
                        # Calculate commute times
                        origins = [(prop.uid, property_geo.lat, property_geo.lng)]
                        destination = (destination_address, destination_geo.lat, destination_geo.lng)
                        
                        commute_results = await self.client.calculate_commute_times(
                            origins=origins,
                            destination=destination,
                            transport_modes=transport_modes,
                            departure_time=departure_time
                        )
                        
                        progress.advance(task)
                        return commute_results[0] if commute_results else None
                        
                    except Exception as e:
                        self.logger.error(f"Error calculating commute for {prop.uid}: {e}")
                        progress.advance(task)
                        return CommuteResult(
                            property_id=prop.uid,
                            destination=destination_address,
                            success=False,
                            error_message=str(e)
                        )
            
            # Process all properties concurrently
            tasks = [process_property(prop) for prop in valid_properties]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            valid_results = []
            for result in results:
                if isinstance(result, CommuteResult):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Exception in commute calculation: {result}")
        
        # Update properties in database with commute times
        await self._update_property_commutes(valid_results)
        
        successful_results = [r for r in valid_results if r.success]
        failed_results = [r for r in valid_results if not r.success]
        
        self.console.print(f"[green]✓ Successfully calculated {len(successful_results)} commutes[/green]")
        if failed_results:
            self.console.print(f"[yellow]⚠ Failed to calculate {len(failed_results)} commutes[/yellow]")
        
        return valid_results
    
    async def _update_property_commutes(self, commute_results: List[CommuteResult]):
        """Update properties in database with commute times"""
        try:
            async with self.db.async_session() as session:
                for result in commute_results:
                    if not result.success:
                        continue
                    
                    # Get property from database
                    property_listing = await self.db.get_property(result.property_id)
                    if not property_listing:
                        continue
                    
                    # Update commute times
                    property_listing.commute_public_transport = result.public_transport
                    property_listing.commute_cycling = result.cycling
                    property_listing.commute_walking = result.walking
                    property_listing.commute_driving = result.driving
                    
                    # Save updated property
                    await self.db.save_property(property_listing)
                
                self.logger.info(f"Updated {len(commute_results)} properties with commute data")
                
        except Exception as e:
            self.logger.error(f"Error updating properties with commute data: {e}")
    
    async def filter_by_commute(
        self,
        properties: List[PropertyListing],
        max_commute_time: int,
        transport_mode: str = "public_transport"
    ) -> List[PropertyListing]:
        """
        Filter properties by maximum commute time
        
        Args:
            properties: List of properties to filter
            max_commute_time: Maximum commute time in minutes
            transport_mode: Transport mode to filter by
            
        Returns:
            Filtered list of properties
        """
        filtered = []
        
        for prop in properties:
            commute_time = None
            
            if transport_mode == "public_transport":
                commute_time = prop.commute_public_transport
            elif transport_mode == "cycling":
                commute_time = prop.commute_cycling
            elif transport_mode == "walking":
                commute_time = prop.commute_walking
            elif transport_mode == "driving":
                commute_time = prop.commute_driving
            
            if commute_time is not None and commute_time <= max_commute_time:
                filtered.append(prop)
        
        return filtered
    
    async def get_commute_statistics(
        self,
        properties: List[PropertyListing],
        transport_modes: List[str] = None
    ) -> dict:
        """
        Get commute statistics for a list of properties
        
        Args:
            properties: List of properties to analyze
            transport_modes: Transport modes to include in statistics
            
        Returns:
            Dictionary with commute statistics
        """
        if transport_modes is None:
            transport_modes = ["public_transport", "cycling", "walking", "driving"]
        
        stats = {}
        
        for mode in transport_modes:
            commute_times = []
            
            for prop in properties:
                if mode == "public_transport" and prop.commute_public_transport:
                    commute_times.append(prop.commute_public_transport)
                elif mode == "cycling" and prop.commute_cycling:
                    commute_times.append(prop.commute_cycling)
                elif mode == "walking" and prop.commute_walking:
                    commute_times.append(prop.commute_walking)
                elif mode == "driving" and prop.commute_driving:
                    commute_times.append(prop.commute_driving)
            
            if commute_times:
                stats[mode] = {
                    "count": len(commute_times),
                    "min": min(commute_times),
                    "max": max(commute_times),
                    "avg": sum(commute_times) / len(commute_times)
                }
            else:
                stats[mode] = {
                    "count": 0,
                    "min": None,
                    "max": None,
                    "avg": None
                }
        
        return stats