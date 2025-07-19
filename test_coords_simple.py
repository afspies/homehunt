#!/usr/bin/env python3
"""Simple test for coordinate extraction"""

import re
from typing import Optional, Tuple

def extract_coordinates_from_maps_embed(html: str) -> Optional[Tuple[float, float]]:
    """Extract coordinates from embedded map URLs in HTML"""
    if not html:
        return None
    
    # Rightmove map URL pattern
    rightmove_pattern = r'https://media\.rightmove\.co\.uk/map/_generate\?[^"]*latitude=([\-\d\.]+)&longitude=([\-\d\.]+)'
    
    match = re.search(rightmove_pattern, html)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            return (lat, lon)
        except (ValueError, IndexError):
            pass
    
    return None

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

print("Testing coordinate extraction from Rightmove map URL...")
coords = extract_coordinates_from_maps_embed(test_html)
if coords:
    print(f"✓ Successfully extracted coordinates: lat={coords[0]}, lon={coords[1]}")
else:
    print("✗ Failed to extract coordinates from map URL")

# Now test the actual feature_extractor module
print("\nImporting actual feature_extractor module...")
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Direct import of the module
    import importlib.util
    spec = importlib.util.spec_from_file_location("feature_extractor", "homehunt/scrapers/feature_extractor.py")
    feature_extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feature_extractor)
    
    # Test with the actual function
    coords2 = feature_extractor.extract_coordinates_from_maps_embed(test_html)
    if coords2:
        print(f"✓ Actual module extracted coordinates: lat={coords2[0]}, lon={coords2[1]}")
    else:
        print("✗ Actual module failed to extract coordinates")
        
except Exception as e:
    print(f"✗ Error importing feature_extractor: {e}")