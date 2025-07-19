#!/usr/bin/env python3
"""Test script to verify export headers and data extraction"""

import asyncio
from homehunt.core.models import PropertyListing, Portal, PropertyType, ExtractionMethod, LetType
from homehunt.exports.service import ExportService
from homehunt.exports.models import ExportConfig, ExportFormat
from homehunt.core.db import Database
from datetime import datetime
import csv

async def test_export_headers():
    """Test if CSV export includes headers"""
    
    # Create sample properties with all fields
    properties = [
        PropertyListing(
            url="https://rightmove.co.uk/property-1",
            property_id="123456",
            portal=Portal.RIGHTMOVE,
            extraction_method=ExtractionMethod.DIRECT_HTTP,
            title="Modern 2 Bed Flat with Parking",
            price="£2000 pcm",
            bedrooms=2,
            bathrooms=1,
            property_type=PropertyType.FLAT,
            area="Westminster",
            postcode="SW1A 1AA",
            address="123 Test Street, Westminster, London SW1A 1AA",
            latitude=51.501364,
            longitude=-0.141890,
            furnished="Furnished",
            parking=True,
            garden=False,
            balcony=True,
            pets_allowed=True,
            let_type=LetType.LONG_TERM,
            is_active=True,
            description="Beautiful modern flat with parking and balcony",
            features=["Parking", "Balcony", "Pets Allowed"],
            images=["https://example.com/img1.jpg"],
            agent_name="Test Estate Agents",
            agent_phone="020 1234 5678",
            # Fields removed as they don't exist in model
        ),
        PropertyListing(
            url="https://zoopla.co.uk/property-2", 
            property_id="789012",
            portal=Portal.ZOOPLA,
            extraction_method=ExtractionMethod.FIRECRAWL,
            title="Spacious 3 Bed House with Garden",
            price="£3000 pcm",
            bedrooms=3,
            bathrooms=2,
            property_type=PropertyType.HOUSE,
            area="Richmond",
            postcode="TW9 1DN",
            address="456 Test Road, Richmond, London TW9 1DN",
            latitude=51.460854,
            longitude=-0.305084,
            furnished="Unfurnished",
            parking=True,
            garden=True,
            balcony=False,
            pets_allowed=False,
            let_type=LetType.LONG_TERM,
            is_active=True,
            description="Large family home with garden",
            features=["Garden", "Parking", "Garage"],
            images=["https://example.com/img2.jpg"],
            agent_name="Premium Properties",
            agent_phone="020 9876 5432"
        )
    ]
    
    # Initialize database and export service
    db = Database()
    await db.create_tables_async()
    export_service = ExportService(db)
    
    # Create export config for CSV
    config = ExportConfig(
        format=ExportFormat.CSV,
        output_path="test_export_headers.csv"
    )
    
    # Export to CSV
    print("Exporting properties to CSV...")
    result = await export_service.export_properties(config, properties)
    print(f"Export success: {result.success}")
    print(f"Properties exported: {result.properties_exported}")
    if result.output_location:
        print(f"Exported to: {result.output_location}")
    output_path = result.output_location
    
    # Read and check CSV
    print("\nChecking CSV contents...")
    with open(output_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        if rows:
            # Print header row
            print(f"\nHeader row ({len(rows[0])} columns):")
            for i, header in enumerate(rows[0]):
                print(f"  {i+1}. {header}")
            
            # Print data rows
            print(f"\nData rows: {len(rows)-1}")
            if len(rows) > 1:
                print("\nFirst data row sample:")
                for i, (header, value) in enumerate(zip(rows[0], rows[1])):
                    if value:  # Only show non-empty values
                        print(f"  {header}: {value}")
        else:
            print("ERROR: CSV file is empty!")
    
    # Also export as JSON to compare
    config_json = ExportConfig(
        format=ExportFormat.JSON,
        output_path="test_export_headers.json"
    )
    
    json_result = await export_service.export_properties(config_json, properties)
    print(f"\nAlso exported to JSON for comparison: {json_result.output_location}")
    
    # Check which fields are missing in export
    all_fields = [
        'url', 'property_id', 'portal', 'extraction_method', 'title', 'price',
        'bedrooms', 'bathrooms', 'property_type', 'area', 'postcode', 'address',
        'latitude', 'longitude', 'furnished', 'parking', 'garden', 'balcony',
        'pets_allowed', 'let_type', 'is_active', 'description', 'features',
        'images', 'agent_name', 'agent_phone', 'first_seen', 'last_scraped',
        'commute_public_transport', 'commute_cycling', 'commute_walking', 'commute_driving'
    ]
    
    if rows:
        exported_fields = rows[0]
        missing_fields = [f for f in all_fields if f not in exported_fields]
        if missing_fields:
            print(f"\nMissing fields in CSV export:")
            for field in missing_fields:
                print(f"  - {field}")
    
    # Cleanup
    await db.close()

if __name__ == "__main__":
    asyncio.run(test_export_headers())