#!/usr/bin/env python3
"""Test coordinate extraction functionality"""

import sys
sys.path.insert(0, '/Users/alex/conductor/repo/homehunt/santiago')
from homehunt.scrapers.feature_extractor import extract_coordinates_from_maps_embed, extract_coordinates_from_text

# Test data with Rightmove map URL
test_html = """
<html>
<head><title>Test Property</title></head>
<body>
    <h1>2 bedroom flat for rent</h1>
    <div class="property-map">
        <img src="https://media.rightmove.co.uk/map/_generate?width=400&height=400&latitude=51.48552&longitude=-0.13718&zoom=15" alt="Map">
    </div>
    <p>Beautiful property in London</p>
</body>
</html>
"""

# Test coordinate extraction from map embed
print("Testing coordinate extraction from Rightmove map URL...")
coords = extract_coordinates_from_maps_embed(test_html)
if coords:
    print(f"✓ Successfully extracted coordinates: lat={coords[0]}, lon={coords[1]}")
else:
    print("✗ Failed to extract coordinates from map URL")

# Test with alternative format
test_html2 = """
<html>
<body>
    <script>
        var propertyData = {
            location: {
                latitude: 51.5074,
                longitude: -0.1278
            }
        };
    </script>
</body>
</html>
"""

print("\nTesting coordinate extraction from text...")
coords2 = extract_coordinates_from_text(test_html2)
if coords2:
    print(f"✓ Successfully extracted coordinates: lat={coords2[0]}, lon={coords2[1]}")
else:
    print("✗ Failed to extract coordinates from text")

# Test with coordinates in URL parameters
test_html3 = """
<html>
<body>
    <iframe src="https://maps.google.com/maps?q=51.5074,-0.1278&z=15"></iframe>
</body>
</html>
"""

print("\nTesting coordinate extraction from Google Maps URL...")
coords3 = extract_coordinates_from_text(test_html3)
if coords3:
    print(f"✓ Successfully extracted coordinates: lat={coords3[0]}, lon={coords3[1]}")
else:
    print("✗ Failed to extract coordinates from Google Maps URL")

# Test PropertyListing creation with coordinates
print("\n\nTesting PropertyListing coordinate extraction...")
from homehunt.core.models import PropertyListing, Portal, ExtractionMethod, ScrapingResult

# Create a mock extraction result
extraction_result = ScrapingResult(
    url="https://rightmove.co.uk/properties/123456",
    success=True,
    portal=Portal.RIGHTMOVE,
    property_id="123456",
    data={
        "title": "2 bedroom flat for rent in Westminster",
        "price": "£2000 pcm",
        "raw_content": test_html,  # This should now be included
    },
    extraction_method=ExtractionMethod.DIRECT_HTTP,
)

# Create PropertyListing
listing = PropertyListing.from_extraction_result(extraction_result)
print(f"PropertyListing created:")
print(f"  - Title: {listing.title}")
print(f"  - Latitude: {listing.latitude}")
print(f"  - Longitude: {listing.longitude}")

if listing.latitude and listing.longitude:
    print("✓ Coordinates successfully extracted in PropertyListing!")
else:
    print("✗ Coordinates NOT extracted in PropertyListing")