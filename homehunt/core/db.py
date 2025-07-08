"""
Database models and connection management for HomeHunt
"""

import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Session, SQLModel, create_engine, func, select, update

from .models import ExtractionMethod, LetType, Portal, PropertyType

if TYPE_CHECKING:
    from .models import PropertyListing


class Listing(SQLModel, table=True):
    """
    Main property listing table
    Stores all scraped property data with full history tracking
    """

    # Primary identification
    uid: str = Field(
        primary_key=True, description="Unique identifier: portal:property_id"
    )
    portal: Portal = Field(index=True, description="Property portal")
    property_id: str = Field(index=True, description="Portal-specific property ID")
    url: str = Field(description="Direct property URL")

    # Location data
    address: Optional[str] = Field(None, description="Property address")
    postcode: Optional[str] = Field(None, index=True, description="Full postcode")
    area: Optional[str] = Field(None, index=True, description="Area/district")
    latitude: Optional[float] = Field(None, description="Property latitude coordinate")
    longitude: Optional[float] = Field(None, description="Property longitude coordinate")

    # Property details
    price: Optional[str] = Field(None, description="Raw price text")
    price_numeric: Optional[int] = Field(
        None, index=True, description="Monthly rent in pence"
    )
    bedrooms: Optional[int] = Field(None, index=True, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    property_type: Optional[PropertyType] = Field(
        None, index=True, description="Property type"
    )

    # Additional details
    furnished: Optional[str] = Field(None, description="Furnished status")
    available_date: Optional[str] = Field(None, description="Available from date")
    description: Optional[str] = Field(None, description="Property description")
    features: Optional[str] = Field(None, description="JSON array of features")
    
    # Property amenities and features
    parking: Optional[bool] = Field(None, description="Has parking space/garage")
    garden: Optional[bool] = Field(None, description="Has garden/outdoor space")
    balcony: Optional[bool] = Field(None, description="Has balcony/terrace")
    pets_allowed: Optional[bool] = Field(None, description="Pets allowed")
    
    # Rental details
    let_type: Optional[LetType] = Field(None, description="Type of rental let")

    # Agent information
    agent_name: Optional[str] = Field(None, description="Estate agent name")
    agent_phone: Optional[str] = Field(None, description="Agent contact number")

    # Extraction metadata
    extraction_method: ExtractionMethod = Field(
        description="Method used for extraction"
    )
    content_length: Optional[int] = Field(None, description="Raw content size")
    title: Optional[str] = Field(None, description="Page title")
    images: Optional[str] = Field(None, description="JSON array of image URLs")

    # Tracking and timestamps
    first_seen: datetime = Field(
        default_factory=datetime.utcnow, description="First discovery"
    )
    last_scraped: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="Last successful scrape",
    )
    scrape_count: int = Field(default=1, description="Number of times scraped")
    is_active: bool = Field(default=True, index=True, description="Property is still available")
    status: str = Field(default="active", index=True, description="Property status")

    # Commute analysis
    commute_public_transport: Optional[int] = Field(
        None, description="Public transport time in minutes"
    )
    commute_cycling: Optional[int] = Field(None, description="Cycling time in minutes")
    commute_walking: Optional[int] = Field(None, description="Walking time in minutes")
    commute_driving: Optional[int] = Field(None, description="Driving time in minutes")

    # Metadata storage
    property_metadata: Optional[str] = Field(None, description="JSON metadata")

    @classmethod
    def from_property_listing(cls, listing: "PropertyListing") -> "Listing":
        """Create database record from PropertyListing model"""
        return cls(
            uid=listing.uid,
            portal=listing.portal,
            property_id=listing.property_id,
            url=listing.url,
            address=listing.address,
            postcode=listing.postcode,
            area=listing.area,
            latitude=listing.latitude,
            longitude=listing.longitude,
            price=listing.price,
            price_numeric=listing.price_numeric,
            bedrooms=listing.bedrooms,
            bathrooms=listing.bathrooms,
            property_type=listing.property_type,
            furnished=listing.furnished,
            available_date=listing.available_date,
            description=listing.description,
            features=json.dumps(listing.features) if listing.features is not None else None,
            parking=listing.parking,
            garden=listing.garden,
            balcony=listing.balcony,
            pets_allowed=listing.pets_allowed,
            let_type=listing.let_type,
            agent_name=listing.agent_name,
            agent_phone=listing.agent_phone,
            extraction_method=listing.extraction_method,
            content_length=listing.content_length,
            title=listing.title,
            images=json.dumps(listing.images) if listing.images is not None else None,
            first_seen=listing.first_seen,
            last_scraped=listing.last_scraped,
            scrape_count=listing.scrape_count,
            is_active=listing.is_active,
            commute_public_transport=listing.commute_public_transport,
            commute_cycling=listing.commute_cycling,
            commute_walking=listing.commute_walking,
            commute_driving=listing.commute_driving,
            property_metadata=json.dumps(listing.to_dict()),
        )

    def to_property_listing(self) -> "PropertyListing":
        """Convert database record to PropertyListing model"""
        from .models import PropertyListing

        # Parse JSON fields
        features = json.loads(self.features) if self.features else []
        images = json.loads(self.images) if self.images else []

        return PropertyListing(
            portal=self.portal,
            property_id=self.property_id,
            url=self.url,
            uid=self.uid,
            address=self.address,
            postcode=self.postcode,
            area=self.area,
            latitude=self.latitude,
            longitude=self.longitude,
            price=self.price,
            price_numeric=self.price_numeric,
            bedrooms=self.bedrooms,
            bathrooms=self.bathrooms,
            property_type=self.property_type,
            furnished=self.furnished,
            available_date=self.available_date,
            description=self.description,
            features=features,
            parking=self.parking,
            garden=self.garden,
            balcony=self.balcony,
            pets_allowed=self.pets_allowed,
            let_type=self.let_type,
            agent_name=self.agent_name,
            agent_phone=self.agent_phone,
            extraction_method=self.extraction_method,
            content_length=self.content_length,
            title=self.title,
            images=images,
            first_seen=self.first_seen,
            last_scraped=self.last_scraped,
            scrape_count=self.scrape_count,
            is_active=self.is_active,
            commute_public_transport=self.commute_public_transport,
            commute_cycling=self.commute_cycling,
            commute_walking=self.commute_walking,
            commute_driving=self.commute_driving,
        )


class PriceHistory(SQLModel, table=True):
    """
    Price change tracking for properties
    """

    id: Optional[int] = Field(primary_key=True, default=None)
    property_uid: str = Field(
        foreign_key="listing.uid", index=True, description="Reference to property"
    )
    price: str = Field(description="Price at time of recording")
    price_numeric: Optional[int] = Field(None, description="Numeric price in pence")
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="When price was recorded",
    )

    # Price change analysis
    price_change: Optional[int] = Field(
        None, description="Change from previous price in pence"
    )
    price_change_percent: Optional[float] = Field(
        None, description="Percentage change from previous price"
    )


class SearchHistory(SQLModel, table=True):
    """
    Track search configurations and results
    """

    id: Optional[int] = Field(primary_key=True, default=None)
    search_config: str = Field(description="JSON search configuration")
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True,
        description="When search was executed",
    )

    # Results summary
    total_found: int = Field(description="Total properties found")
    new_properties: int = Field(description="New properties discovered")
    updated_properties: int = Field(description="Existing properties updated")

    # Performance metrics
    execution_time: Optional[float] = Field(
        None, description="Search execution time in seconds"
    )
    api_calls: Optional[int] = Field(None, description="Number of API calls made")
    success_rate: Optional[float] = Field(
        None, description="Success rate of scraping attempts"
    )


class Database:
    """
    Database connection and operations manager
    """

    def __init__(self, database_url: str = "sqlite:///homehunt.db"):
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.async_engine = create_async_engine(
            database_url.replace("sqlite:///", "sqlite+aiosqlite:///"), echo=False
        )
        self.async_session = sessionmaker(
            self.async_engine, class_=AsyncSession, expire_on_commit=False
        )
        self.logger = logging.getLogger(__name__)

    def create_tables(self):
        """Create all database tables"""
        SQLModel.metadata.create_all(self.engine)
        self.logger.info("Database tables created")

    async def create_tables_async(self):
        """Create all database tables asynchronously"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        self.logger.info("Database tables created asynchronously")

    def get_session(self) -> Session:
        """Get synchronous database session"""
        return Session(self.engine)

    async def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session"""
        return self.async_session()

    async def save_property(self, listing: "PropertyListing") -> bool:
        """
        Save or update a property listing

        Args:
            listing: PropertyListing to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            async with self.async_session() as session:
                # Check if property already exists
                result = await session.execute(
                    select(Listing).where(Listing.uid == listing.uid)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing property
                    existing.last_scraped = datetime.utcnow()
                    existing.scrape_count += 1

                    # Update fields that might have changed
                    existing.price = listing.price
                    existing.price_numeric = listing.price_numeric
                    existing.description = listing.description
                    existing.available_date = listing.available_date
                    existing.agent_name = listing.agent_name
                    existing.agent_phone = listing.agent_phone
                    existing.parking = listing.parking
                    existing.garden = listing.garden
                    existing.balcony = listing.balcony
                    existing.pets_allowed = listing.pets_allowed
                    existing.let_type = listing.let_type
                    existing.latitude = listing.latitude
                    existing.longitude = listing.longitude
                    existing.is_active = listing.is_active
                    existing.status = "active"

                    # Track price changes
                    if (
                        existing.price_numeric
                        and listing.price_numeric
                        and existing.price_numeric != listing.price_numeric
                    ):
                        price_change = PriceHistory(
                            property_uid=listing.uid,
                            price=listing.price,
                            price_numeric=listing.price_numeric,
                            price_change=listing.price_numeric - existing.price_numeric,
                            price_change_percent=(
                                (listing.price_numeric - existing.price_numeric)
                                / existing.price_numeric
                            )
                            * 100,
                        )
                        session.add(price_change)

                    self.logger.info(f"Updated property {listing.uid}")
                else:
                    # Create new property
                    db_listing = Listing.from_property_listing(listing)
                    session.add(db_listing)
                    self.logger.info(f"Created new property {listing.uid}")

                await session.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error saving property {listing.uid}: {e}")
            return False

    async def get_property(self, uid: str) -> Optional["PropertyListing"]:
        """Get a property by UID"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Listing).where(Listing.uid == uid)
                )
                listing = result.scalar_one_or_none()

                if listing:
                    return listing.to_property_listing()
                return None

        except Exception as e:
            self.logger.error(f"Error getting property {uid}: {e}")
            return None

    async def search_properties(
        self,
        portal: Optional[Portal] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        bedrooms: Optional[int] = None,
        property_type: Optional[PropertyType] = None,
        postcode_area: Optional[str] = None,
        max_commute: Optional[int] = None,
        limit: int = 100,
    ) -> List["PropertyListing"]:
        """
        Search properties with filters

        Args:
            portal: Filter by portal
            min_price: Minimum price in pence
            max_price: Maximum price in pence
            bedrooms: Exact number of bedrooms
            property_type: Property type filter
            postcode_area: Postcode area filter
            max_commute: Maximum commute time in minutes
            limit: Maximum results to return

        Returns:
            List of PropertyListing objects
        """
        try:
            async with self.async_session() as session:
                query = select(Listing).where(Listing.is_active == True)

                if portal:
                    query = query.where(Listing.portal == portal)

                if min_price:
                    query = query.where(Listing.price_numeric >= min_price)

                if max_price:
                    query = query.where(Listing.price_numeric <= max_price)

                if bedrooms:
                    query = query.where(Listing.bedrooms == bedrooms)

                if property_type:
                    query = query.where(Listing.property_type == property_type)

                if postcode_area:
                    query = query.where(Listing.postcode.like(f"{postcode_area}%"))

                if max_commute:
                    query = query.where(Listing.commute_public_transport <= max_commute)

                query = query.limit(limit).order_by(Listing.last_scraped.desc())

                result = await session.execute(query)
                listings = result.scalars().all()

                return [listing.to_property_listing() for listing in listings]

        except Exception as e:
            self.logger.error(f"Error searching properties: {e}")
            return []

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            async with self.async_session() as session:
                # Total properties by portal
                portal_stats = await session.execute(
                    select(
                        Listing.portal,
                        func.count(Listing.uid).label("total"),
                        func.count(Listing.price_numeric).label("with_price"),
                        func.avg(Listing.price_numeric).label("avg_price"),
                    ).group_by(Listing.portal)
                )

                # Recent activity
                recent_activity = await session.execute(
                    select(func.count(Listing.uid)).where(
                        Listing.last_scraped >= datetime.utcnow() - timedelta(days=1)
                    )
                )

                # Price ranges
                price_stats = await session.execute(
                    select(
                        func.min(Listing.price_numeric).label("min_price"),
                        func.max(Listing.price_numeric).label("max_price"),
                        func.avg(Listing.price_numeric).label("avg_price"),
                    ).where(Listing.price_numeric.is_not(None))
                )

                portal_results = portal_stats.fetchall()
                price_result = price_stats.first()
                
                return {
                    "portal_stats": [
                        {
                            "portal": row[0].value if hasattr(row[0], 'value') else str(row[0]),
                            "total": row[1],
                            "with_price": row[2],
                            "avg_price": row[3]
                        }
                        for row in portal_results
                    ],
                    "recent_activity": recent_activity.scalar(),
                    "price_stats": {
                        "min_price": price_result[0] if price_result else None,
                        "max_price": price_result[1] if price_result else None,
                        "avg_price": price_result[2] if price_result else None,
                    } if price_result else {},
                    "last_updated": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}

    async def cleanup_old_data(self, days: int = 30):
        """Remove old inactive properties"""
        try:
            async with self.async_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Mark old properties as inactive
                await session.execute(
                    update(Listing)
                    .where(Listing.last_scraped < cutoff_date)
                    .values(is_active=False, status="inactive")
                )

                await session.commit()
                self.logger.info(f"Cleaned up properties older than {days} days")

        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")

    async def close(self):
        """Close database connections"""
        await self.async_engine.dispose()
        self.engine.dispose()


# Global database instance
db = Database()


async def init_db():
    """Initialize database with tables"""
    await db.create_tables_async()


async def get_db() -> Database:
    """Get database instance"""
    return db
