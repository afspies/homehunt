"""
Core data models and database functionality for HomeHunt
"""

from .db import Database, Listing, PriceHistory, SearchHistory, db, get_db, init_db
from .models import (
    ExtractionMethod,
    Portal,
    PropertyListing,
    PropertyType,
    ScrapingResult,
    SearchConfig,
)

__all__ = [
    # Models
    "PropertyListing",
    "SearchConfig",
    "ScrapingResult",
    "Portal",
    "PropertyType",
    "ExtractionMethod",
    # Database
    "Database",
    "Listing",
    "PriceHistory",
    "SearchHistory",
    "db",
    "init_db",
    "get_db",
]
