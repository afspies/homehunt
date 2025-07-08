"""
Geocoding service for adding coordinates to properties
"""

import asyncio
import logging
from typing import List, Optional

from homehunt.core.db import Database
from homehunt.core.models import PropertyListing
from .client import TravelTimeClient


class GeocodingService:
    """Service for adding geocoding data to properties"""
    
    def __init__(self, traveltime_client: Optional[TravelTimeClient] = None, db: Optional[Database] = None):
        self.client = traveltime_client or TravelTimeClient()
        self.db = db or Database()
        self.logger = logging.getLogger(__name__)
    
    async def geocode_property(self, property_listing: PropertyListing) -> bool:
        """
        Add coordinates to a property listing
        
        Args:
            property_listing: Property to geocode
            
        Returns:
            True if geocoding was successful
        """
        # Skip if already has coordinates
        if property_listing.latitude and property_listing.longitude:
            return True
        
        # Build address for geocoding
        address_parts = []
        if property_listing.address:
            address_parts.append(property_listing.address)
        if property_listing.postcode:
            address_parts.append(property_listing.postcode)
        if property_listing.area and property_listing.area not in ' '.join(address_parts):
            address_parts.append(property_listing.area)
        
        if not address_parts:
            self.logger.warning(f"No address data for property {property_listing.uid}")
            return False
        
        full_address = ', '.join(address_parts)
        
        try:
            result = await self.client.geocode(full_address)
            if result:
                property_listing.latitude = result.lat
                property_listing.longitude = result.lng
                self.logger.debug(f"Geocoded {property_listing.uid}: {result.lat}, {result.lng}")
                return True
            else:
                self.logger.warning(f"Failed to geocode property {property_listing.uid}: {full_address}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error geocoding property {property_listing.uid}: {e}")
            return False
    
    async def geocode_properties_batch(self, properties: List[PropertyListing], max_concurrent: int = 5) -> int:
        """
        Geocode multiple properties with rate limiting
        
        Args:
            properties: List of properties to geocode
            max_concurrent: Maximum concurrent geocoding requests
            
        Returns:
            Number of successfully geocoded properties
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def geocode_with_semaphore(prop: PropertyListing) -> bool:
            async with semaphore:
                return await self.geocode_property(prop)
        
        # Filter properties that need geocoding
        properties_to_geocode = [
            prop for prop in properties 
            if not (prop.latitude and prop.longitude)
        ]
        
        if not properties_to_geocode:
            self.logger.info("No properties need geocoding")
            return 0
        
        self.logger.info(f"Geocoding {len(properties_to_geocode)} properties")
        
        # Execute geocoding with concurrency control
        tasks = [geocode_with_semaphore(prop) for prop in properties_to_geocode]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for result in results if result is True)
        
        self.logger.info(f"Successfully geocoded {success_count}/{len(properties_to_geocode)} properties")
        
        return success_count
    
    async def geocode_database_properties(
        self, 
        portal: Optional[str] = None,
        missing_only: bool = True,
        limit: int = 1000
    ) -> int:
        """
        Geocode properties from database
        
        Args:
            portal: Optional portal filter (rightmove/zoopla)
            missing_only: Only geocode properties without coordinates
            limit: Maximum number of properties to process
            
        Returns:
            Number of successfully geocoded properties
        """
        try:
            from homehunt.core.models import Portal
            
            # Build search parameters
            search_kwargs = {'limit': limit}
            if portal:
                search_kwargs['portal'] = Portal(portal.lower())
            
            # Get properties from database
            properties = await self.db.search_properties(**search_kwargs)
            
            if missing_only:
                properties = [
                    prop for prop in properties 
                    if not (prop.latitude and prop.longitude)
                ]
            
            if not properties:
                self.logger.info("No properties found for geocoding")
                return 0
            
            # Geocode properties
            success_count = await self.geocode_properties_batch(properties)
            
            # Save updated properties back to database
            saved_count = 0
            for prop in properties:
                if prop.latitude and prop.longitude:
                    success = await self.db.save_property(prop)
                    if success:
                        saved_count += 1
            
            self.logger.info(f"Saved {saved_count} geocoded properties to database")
            
            return success_count
            
        except Exception as e:
            self.logger.error(f"Error geocoding database properties: {e}")
            return 0
    
    async def close(self):
        """Close database connections"""
        await self.db.close()


async def geocode_properties_cli(
    portal: Optional[str] = None,
    missing_only: bool = True,
    limit: int = 1000
) -> None:
    """
    CLI function for geocoding properties
    
    Args:
        portal: Optional portal filter
        missing_only: Only geocode properties without coordinates  
        limit: Maximum number of properties to process
    """
    service = GeocodingService()
    
    try:
        success_count = await service.geocode_database_properties(
            portal=portal,
            missing_only=missing_only,
            limit=limit
        )
        
        print(f"Successfully geocoded {success_count} properties")
        
    except Exception as e:
        print(f"Error during geocoding: {e}")
    finally:
        await service.close()