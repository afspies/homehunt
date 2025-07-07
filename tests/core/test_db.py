"""
Tests for database models and operations
"""

from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from homehunt.core.db import Database, Listing, PriceHistory, SearchHistory
from homehunt.core.models import ExtractionMethod, Portal, PropertyListing, PropertyType


@pytest.fixture
def test_db():
    """Create test database instance"""
    return Database("sqlite:///test_homehunt.db")


@pytest.fixture
async def async_test_db():
    """Create async test database instance"""
    db = Database("sqlite:///test_homehunt_async.db")
    await db.create_tables_async()
    yield db
    await db.close()


@pytest.fixture
def sample_property_listing():
    """Create sample PropertyListing for testing"""
    return PropertyListing(
        portal=Portal.RIGHTMOVE,
        property_id="164209706",
        url="https://www.rightmove.co.uk/properties/164209706",
        extraction_method=ExtractionMethod.DIRECT_HTTP,
        address="Grosvenor Road, London, SW1V",
        postcode="SW1V 3SA",
        area="Victoria",
        price="£2,385 pcm",
        bedrooms=1,
        bathrooms=1,
        property_type=PropertyType.APARTMENT,
        furnished="Furnished",
        title="1 bedroom apartment for rent in Grosvenor Road, London, SW1V",
        content_length=327486,
        images=["https://media.rightmove.co.uk/image1.jpg"],
        commute_public_transport=25,
        commute_cycling=15,
    )


class TestListing:
    """Test Listing database model"""

    def test_create_listing_from_property(self, sample_property_listing):
        """Test creating database listing from PropertyListing"""
        db_listing = Listing.from_property_listing(sample_property_listing)

        assert db_listing.uid == "rightmove:164209706"
        assert db_listing.portal == Portal.RIGHTMOVE
        assert db_listing.property_id == "164209706"
        assert db_listing.address == "Grosvenor Road, London, SW1V"
        assert db_listing.postcode == "SW1V 3SA"
        assert db_listing.price_numeric == 238500
        assert db_listing.bedrooms == 1
        assert db_listing.property_type == PropertyType.APARTMENT
        assert db_listing.extraction_method == ExtractionMethod.DIRECT_HTTP
        assert db_listing.commute_public_transport == 25

        # Check JSON fields
        import json

        assert json.loads(db_listing.images) == [
            "https://media.rightmove.co.uk/image1.jpg"
        ]
        assert json.loads(db_listing.features) == []

    def test_convert_to_property_listing(self, sample_property_listing):
        """Test converting database listing back to PropertyListing"""
        # Create DB listing
        db_listing = Listing.from_property_listing(sample_property_listing)

        # Convert back to PropertyListing
        converted_listing = db_listing.to_property_listing()

        assert converted_listing.portal == sample_property_listing.portal
        assert converted_listing.property_id == sample_property_listing.property_id
        assert converted_listing.uid == sample_property_listing.uid
        assert converted_listing.address == sample_property_listing.address
        assert converted_listing.price_numeric == sample_property_listing.price_numeric
        assert converted_listing.bedrooms == sample_property_listing.bedrooms
        assert converted_listing.property_type == sample_property_listing.property_type
        assert converted_listing.images == sample_property_listing.images


class TestDatabase:
    """Test Database operations"""

    def test_create_tables(self, test_db):
        """Test creating database tables"""
        test_db.create_tables()

        # Check tables exist by creating a session
        with test_db.get_session() as session:
            # Should not raise an exception
            result = session.execute(select(Listing).limit(1))
            assert result is not None

    @pytest.mark.asyncio
    async def test_save_property(self, async_test_db, sample_property_listing):
        """Test saving a property to database"""
        success = await async_test_db.save_property(sample_property_listing)
        assert success is True

        # Verify it was saved
        saved_property = await async_test_db.get_property(sample_property_listing.uid)
        assert saved_property is not None
        assert saved_property.uid == sample_property_listing.uid
        assert saved_property.portal == sample_property_listing.portal
        assert saved_property.address == sample_property_listing.address

    @pytest.mark.asyncio
    async def test_update_existing_property(
        self, async_test_db, sample_property_listing
    ):
        """Test updating an existing property"""
        # Save initial property
        await async_test_db.save_property(sample_property_listing)

        # Update the property
        updated_listing = sample_property_listing.model_copy()
        updated_listing.price = "£2,500 pcm"
        updated_listing.price_numeric = 250000
        updated_listing.description = "Updated description"

        success = await async_test_db.save_property(updated_listing)
        assert success is True

        # Verify update
        saved_property = await async_test_db.get_property(updated_listing.uid)
        assert saved_property.price == "£2,500 pcm"
        assert saved_property.price_numeric == 250000
        assert saved_property.description == "Updated description"
        assert saved_property.scrape_count == 2  # Should increment

    @pytest.mark.asyncio
    async def test_price_change_tracking(self, async_test_db, sample_property_listing):
        """Test price change tracking"""
        # Save initial property
        await async_test_db.save_property(sample_property_listing)

        # Update with different price
        updated_listing = sample_property_listing.model_copy()
        updated_listing.price = "£2,500 pcm"
        updated_listing.price_numeric = 250000

        await async_test_db.save_property(updated_listing)

        # Check price history was created
        async with async_test_db.async_session() as session:
            result = await session.execute(
                select(PriceHistory).where(
                    PriceHistory.property_uid == sample_property_listing.uid
                )
            )
            price_history = result.scalars().all()

            assert len(price_history) == 1
            assert price_history[0].price == "£2,500 pcm"
            assert price_history[0].price_numeric == 250000
            assert price_history[0].price_change == 11500  # 250000 - 238500

    @pytest.mark.asyncio
    async def test_search_properties(self, async_test_db):
        """Test searching properties with filters"""
        # Create test properties
        properties = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="1",
                url="https://example.com/1",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                price_numeric=200000,  # £2,000
                bedrooms=1,
                property_type=PropertyType.FLAT,
                postcode="SW1V 3SA",
            ),
            PropertyListing(
                portal=Portal.ZOOPLA,
                property_id="2",
                url="https://example.com/2",
                extraction_method=ExtractionMethod.FIRECRAWL,
                price_numeric=300000,  # £3,000
                bedrooms=2,
                property_type=PropertyType.HOUSE,
                postcode="SW1A 1AA",
            ),
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="3",
                url="https://example.com/3",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                price_numeric=150000,  # £1,500
                bedrooms=1,
                property_type=PropertyType.STUDIO,
                postcode="E1 6AN",
            ),
        ]

        # Save all properties
        for prop in properties:
            await async_test_db.save_property(prop)

        # Test various searches

        # Search by portal
        rightmove_results = await async_test_db.search_properties(
            portal=Portal.RIGHTMOVE
        )
        assert len(rightmove_results) == 2

        # Search by price range
        mid_range_results = await async_test_db.search_properties(
            min_price=175000, max_price=275000
        )
        assert len(mid_range_results) == 1
        assert mid_range_results[0].price_numeric == 200000

        # Search by bedrooms
        one_bed_results = await async_test_db.search_properties(bedrooms=1)
        assert len(one_bed_results) == 2

        # Search by property type
        flat_results = await async_test_db.search_properties(
            property_type=PropertyType.FLAT
        )
        assert len(flat_results) == 1

        # Search by postcode area
        sw_results = await async_test_db.search_properties(postcode_area="SW1")
        assert len(sw_results) == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self, async_test_db):
        """Test getting database statistics"""
        # Create some test data
        properties = [
            PropertyListing(
                portal=Portal.RIGHTMOVE,
                property_id="1",
                url="https://example.com/1",
                extraction_method=ExtractionMethod.DIRECT_HTTP,
                price_numeric=200000,
            ),
            PropertyListing(
                portal=Portal.ZOOPLA,
                property_id="2",
                url="https://example.com/2",
                extraction_method=ExtractionMethod.FIRECRAWL,
                price_numeric=300000,
            ),
        ]

        for prop in properties:
            await async_test_db.save_property(prop)

        stats = await async_test_db.get_statistics()

        assert "portal_stats" in stats
        assert "recent_activity" in stats
        assert "price_stats" in stats
        assert "last_updated" in stats

    @pytest.mark.asyncio
    async def test_cleanup_old_data(self, async_test_db):
        """Test cleaning up old data"""
        # Create old property
        old_property = PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="old",
            url="https://example.com/old",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
            last_scraped=datetime.utcnow() - timedelta(days=35),
        )

        # Create recent property
        recent_property = PropertyListing(
            portal=Portal.RIGHTMOVE,
            property_id="recent",
            url="https://example.com/recent",
            extraction_method=ExtractionMethod.DIRECT_HTTP,
        )

        await async_test_db.save_property(old_property)
        await async_test_db.save_property(recent_property)

        # Clean up old data
        await async_test_db.cleanup_old_data(days=30)

        # Check that old property is marked inactive
        async with async_test_db.async_session() as session:
            result = await session.execute(
                select(Listing).where(Listing.property_id == "old")
            )
            old_listing = result.scalar_one_or_none()

            assert old_listing is not None
            assert old_listing.status == "inactive"

            # Check that recent property is still active
            result = await session.execute(
                select(Listing).where(Listing.property_id == "recent")
            )
            recent_listing = result.scalar_one_or_none()

            assert recent_listing is not None
            assert recent_listing.status == "active"


class TestPriceHistory:
    """Test PriceHistory model"""

    def test_create_price_history(self):
        """Test creating price history record"""
        price_history = PriceHistory(
            property_uid="rightmove:164209706",
            price="£2,500 pcm",
            price_numeric=250000,
            price_change=11500,
            price_change_percent=4.8,
        )

        assert price_history.property_uid == "rightmove:164209706"
        assert price_history.price == "£2,500 pcm"
        assert price_history.price_numeric == 250000
        assert price_history.price_change == 11500
        assert price_history.price_change_percent == 4.8
        assert isinstance(price_history.recorded_at, datetime)


class TestSearchHistory:
    """Test SearchHistory model"""

    def test_create_search_history(self):
        """Test creating search history record"""
        search_config = {
            "location": "Victoria, London",
            "min_price": 2000,
            "max_price": 3000,
            "portals": ["rightmove", "zoopla"],
        }

        search_history = SearchHistory(
            search_config=str(search_config),
            total_found=25,
            new_properties=5,
            updated_properties=3,
            execution_time=45.2,
            api_calls=12,
            success_rate=0.95,
        )

        assert search_history.total_found == 25
        assert search_history.new_properties == 5
        assert search_history.updated_properties == 3
        assert search_history.execution_time == 45.2
        assert search_history.api_calls == 12
        assert search_history.success_rate == 0.95
        assert isinstance(search_history.executed_at, datetime)
