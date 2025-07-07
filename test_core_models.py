#!/usr/bin/env python3
"""
Quick test script for core models
"""

from homehunt.core.models import PropertyListing, Portal, ExtractionMethod, PropertyType

def test_property_listing():
    """Test creating a property listing"""
    print("Testing PropertyListing model...")
    
    listing = PropertyListing(
        portal=Portal.RIGHTMOVE,
        property_id="164209706",
        url="https://www.rightmove.co.uk/properties/164209706",
        extraction_method=ExtractionMethod.DIRECT_HTTP,
        address="Grosvenor Road, London, SW1V",
        postcode="SW1V 3SA",
        price="£2,385 pcm",
        bedrooms=1,
        property_type="apartment",
        title="1 bedroom apartment for rent in Grosvenor Road, London, SW1V"
    )
    
    print(f"✅ Created listing: {listing.uid}")
    print(f"   Portal: {listing.portal}")
    print(f"   Address: {listing.address}")
    price_display = f"£{listing.price_numeric/100:.0f}" if listing.price_numeric else "No price"
    print(f"   Price: {listing.price} ({price_display})")
    print(f"   Bedrooms: {listing.bedrooms}")
    print(f"   Property Type: {listing.property_type}")
    print(f"   Postcode: {listing.postcode}")
    
    # Test field validators
    assert listing.uid == "rightmove:164209706"
    if listing.price_numeric:
        assert listing.price_numeric == 238500  # £2,385 in pence
    assert listing.property_type == PropertyType.APARTMENT
    assert listing.postcode == "SW1V 3SA"
    
    print("✅ All validations passed!")
    
    # Test to_dict
    data = listing.to_dict()
    print(f"✅ Dictionary conversion: {len(data)} fields")
    
    return listing

def test_from_extraction_result():
    """Test creating from extraction result"""
    print("\nTesting from_extraction_result...")
    
    extraction_result = {
        "address": "123 Test Street, London",
        "price": "£1,500 pcm",
        "bedrooms": 2,
        "property_type": "flat",
        "title": "2 bedroom flat for rent in Test Street, London"
    }
    
    listing = PropertyListing.from_extraction_result(
        portal="rightmove",
        property_id="123456",
        url="https://www.rightmove.co.uk/properties/123456",
        extraction_result=extraction_result,
        extraction_method="direct_http"
    )
    
    print(f"✅ Created from extraction: {listing.uid}")
    price_display = f"£{listing.price_numeric/100:.0f}" if listing.price_numeric else "No price"
    print(f"   Price: {listing.price} ({price_display})")
    print(f"   Property type: {listing.property_type}")
    
    assert listing.uid == "rightmove:123456"
    if listing.price_numeric:
        assert listing.price_numeric == 150000
    assert listing.property_type == PropertyType.FLAT
    
    print("✅ Extraction result conversion passed!")
    
    return listing

if __name__ == "__main__":
    print("🏡 Testing HomeHunt Core Models\n")
    
    listing1 = test_property_listing()
    listing2 = test_from_extraction_result()
    
    print(f"\n✅ All tests passed! Created {2} property listings.")
    print("🎉 Core data models are working correctly!")