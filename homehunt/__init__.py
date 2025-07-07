"""
HomeHunt: Async Property Search & Commute Analysis Tool

A powerful CLI tool for automated property search across UK property portals
with intelligent commute time analysis and real-time alerts.
"""

__version__ = "0.1.0"
__author__ = "HomeHunt Team"
__email__ = "contact@homehunt.dev"

from .core.db import Database, Listing
from .core.models import PropertyListing, SearchConfig

__all__ = [
    "PropertyListing",
    "SearchConfig",
    "Database",
    "Listing",
]
