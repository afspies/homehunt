"""
Tests for configuration models
"""

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from homehunt.cli.config import FurnishedType, SearchConfig, SortOrder
from homehunt.config.models import (
    AdvancedSearchConfig,
    CommuteFilter,
    MultiLocationConfig,
    NotificationConfig,
    SavedSearchProfile,
)
from homehunt.core.models import Portal, PropertyType


class TestCommuteFilter:
    """Test CommuteFilter model"""
    
    def test_valid_commute_filter(self):
        """Test creating a valid commute filter"""
        commute_filter = CommuteFilter(
            destination="Canary Wharf",
            max_time=45,
            transport_modes=["public_transport", "cycling"],
            departure_times=["08:00", "09:00"]
        )
        
        assert commute_filter.destination == "Canary Wharf"
        assert commute_filter.max_time == 45
        assert commute_filter.transport_modes == ["public_transport", "cycling"]
        assert commute_filter.departure_times == ["08:00", "09:00"]
        assert commute_filter.weight == 1.0
        assert not commute_filter.return_journey
    
    def test_invalid_transport_mode(self):
        """Test validation of invalid transport modes"""
        with pytest.raises(ValidationError, match="Invalid transport mode"):
            CommuteFilter(
                destination="King's Cross",
                max_time=30,
                transport_modes=["invalid_mode"]
            )
    
    def test_invalid_time_format(self):
        """Test validation of invalid time format"""
        with pytest.raises(ValidationError, match="Time must be in HH:MM format"):
            CommuteFilter(
                destination="London Bridge",
                max_time=30,
                departure_times=["25:00"]  # Invalid hour
            )
        
        with pytest.raises(ValidationError, match="Time must be in HH:MM format"):
            CommuteFilter(
                destination="London Bridge",
                max_time=30,
                departure_times=["08:70"]  # Invalid minute
            )
    
    def test_return_journey_settings(self):
        """Test return journey configuration"""
        commute_filter = CommuteFilter(
            destination="Westminster",
            max_time=40,
            return_journey=True,
            return_departure_times=["17:30", "18:00"]
        )
        
        assert commute_filter.return_journey
        assert commute_filter.return_departure_times == ["17:30", "18:00"]


class TestMultiLocationConfig:
    """Test MultiLocationConfig model"""
    
    def test_valid_multi_location(self):
        """Test creating a valid multi-location config"""
        config = MultiLocationConfig(
            name="Central London",
            locations=["King's Cross", "London Bridge", "Canary Wharf"],
            combine_results=True,
            max_results_per_location=25
        )
        
        assert config.name == "Central London"
        assert len(config.locations) == 3
        assert config.combine_results
        assert config.max_results_per_location == 25
    
    def test_location_overrides(self):
        """Test location-specific parameter overrides"""
        config = MultiLocationConfig(
            name="Mixed Areas",
            locations=["Expensive Area", "Budget Area"],
            location_overrides={
                "Expensive Area": {"min_price": 2000, "max_price": 5000},
                "Budget Area": {"min_price": 1000, "max_price": 2000}
            }
        )
        
        assert "Expensive Area" in config.location_overrides
        assert config.location_overrides["Expensive Area"]["min_price"] == 2000
    
    def test_empty_locations_validation(self):
        """Test validation of empty locations list"""
        with pytest.raises(ValidationError, match="at least 1 item"):
            MultiLocationConfig(
                name="Empty",
                locations=[]
            )


class TestNotificationConfig:
    """Test NotificationConfig model"""
    
    def test_default_notification_config(self):
        """Test default notification configuration"""
        config = NotificationConfig()
        
        assert not config.enabled
        assert config.new_properties
        assert config.price_changes
        assert not config.status_changes
        assert config.immediate_alerts
        assert not config.daily_summary
    
    def test_telegram_configuration(self):
        """Test Telegram notification settings"""
        config = NotificationConfig(
            enabled=True,
            telegram_bot_token="123456:ABC-DEF",
            telegram_chat_id="@mychannel",
            immediate_alerts=True,
            daily_summary=True
        )
        
        assert config.enabled
        assert config.telegram_bot_token == "123456:ABC-DEF"
        assert config.telegram_chat_id == "@mychannel"
        assert config.immediate_alerts
        assert config.daily_summary
    
    def test_email_configuration(self):
        """Test email notification settings"""
        config = NotificationConfig(
            email_enabled=True,
            email_smtp_server="smtp.gmail.com",
            email_from="alerts@homehunt.com",
            email_to=["user@example.com", "backup@example.com"]
        )
        
        assert config.email_enabled
        assert config.email_smtp_server == "smtp.gmail.com"
        assert len(config.email_to) == 2


class TestSavedSearchProfile:
    """Test SavedSearchProfile model"""
    
    def create_test_search_config(self) -> SearchConfig:
        """Create a test search configuration"""
        return SearchConfig(
            portals=[Portal.RIGHTMOVE],
            location="SW1A 1AA",
            min_price=1500,
            max_price=3000,
            min_bedrooms=1,
            property_types=[PropertyType.FLAT],
            furnished=FurnishedType.ANY,
            sort_order=SortOrder.PRICE_ASC
        )
    
    def test_basic_profile(self):
        """Test creating a basic search profile"""
        search_config = self.create_test_search_config()
        
        profile = SavedSearchProfile(
            name="test_profile",
            description="Test search profile",
            search=search_config
        )
        
        assert profile.name == "test_profile"
        assert profile.description == "Test search profile"
        assert profile.search.location == "SW1A 1AA"
        assert not profile.enable_scoring
        assert not profile.auto_export
    
    def test_profile_with_commute_filters(self):
        """Test profile with commute filtering"""
        search_config = self.create_test_search_config()
        commute_filter = CommuteFilter(
            destination="Canary Wharf",
            max_time=45,
            transport_modes=["public_transport"]
        )
        
        profile = SavedSearchProfile(
            name="commuter_profile",
            search=search_config,
            commute_filters=[commute_filter]
        )
        
        assert len(profile.commute_filters) == 1
        assert profile.commute_filters[0].destination == "Canary Wharf"
    
    def test_profile_with_scoring(self):
        """Test profile with scoring enabled"""
        search_config = self.create_test_search_config()
        
        profile = SavedSearchProfile(
            name="scored_profile",
            search=search_config,
            enable_scoring=True,
            score_weights={
                "price": 0.3,
                "commute": 0.4,
                "size": 0.2,
                "features": 0.1
            }
        )
        
        assert profile.enable_scoring
        assert profile.score_weights["price"] == 0.3
        assert sum(profile.score_weights.values()) == 1.0
    
    def test_profile_with_export_settings(self):
        """Test profile with export configuration"""
        search_config = self.create_test_search_config()
        
        profile = SavedSearchProfile(
            name="export_profile",
            search=search_config,
            auto_export=True,
            export_formats=["csv", "json"],
            export_path=Path("/tmp/exports")
        )
        
        assert profile.auto_export
        assert "csv" in profile.export_formats
        assert "json" in profile.export_formats
        assert profile.export_path == Path("/tmp/exports")
    
    def test_invalid_export_format(self):
        """Test validation of invalid export formats"""
        search_config = self.create_test_search_config()
        
        with pytest.raises(ValidationError, match="Invalid export format"):
            SavedSearchProfile(
                name="invalid_export",
                search=search_config,
                export_formats=["invalid_format"]
            )
    
    def test_profile_metadata(self):
        """Test profile metadata fields"""
        search_config = self.create_test_search_config()
        
        profile = SavedSearchProfile(
            name="metadata_profile",
            search=search_config
        )
        
        assert profile.total_runs == 0
        assert profile.last_run is None
        assert isinstance(profile.created_at, datetime)


class TestAdvancedSearchConfig:
    """Test AdvancedSearchConfig model"""
    
    def create_test_profile(self, name: str = "test") -> SavedSearchProfile:
        """Create a test profile"""
        search_config = SearchConfig(
            portals=[Portal.RIGHTMOVE],
            location="SW1A 1AA",
            min_price=1500,
            max_price=3000
        )
        
        return SavedSearchProfile(
            name=name,
            search=search_config
        )
    
    def test_basic_config(self):
        """Test creating a basic advanced configuration"""
        profile = self.create_test_profile()
        
        config = AdvancedSearchConfig(
            name="Test Configuration",
            profiles=[profile]
        )
        
        assert config.name == "Test Configuration"
        assert len(config.profiles) == 1
        assert config.version == "1.0"
        assert config.concurrent_searches == 3
        assert config.save_to_database
    
    def test_multiple_profiles(self):
        """Test configuration with multiple profiles"""
        profiles = [
            self.create_test_profile("profile1"),
            self.create_test_profile("profile2"),
            self.create_test_profile("profile3")
        ]
        
        config = AdvancedSearchConfig(
            profiles=profiles,
            concurrent_searches=2
        )
        
        assert len(config.profiles) == 3
        assert config.concurrent_searches == 2
    
    def test_unique_profile_names_validation(self):
        """Test validation of unique profile names"""
        profiles = [
            self.create_test_profile("duplicate"),
            self.create_test_profile("duplicate")  # Same name
        ]
        
        with pytest.raises(ValidationError, match="Profile names must be unique"):
            AdvancedSearchConfig(profiles=profiles)
    
    def test_get_profile(self):
        """Test getting profile by name"""
        profiles = [
            self.create_test_profile("profile1"),
            self.create_test_profile("profile2")
        ]
        
        config = AdvancedSearchConfig(profiles=profiles)
        
        found_profile = config.get_profile("profile1")
        assert found_profile is not None
        assert found_profile.name == "profile1"
        
        not_found = config.get_profile("nonexistent")
        assert not_found is None
    
    def test_add_profile(self):
        """Test adding a new profile"""
        profile1 = self.create_test_profile("profile1")
        config = AdvancedSearchConfig(profiles=[profile1])
        
        profile2 = self.create_test_profile("profile2")
        config.add_profile(profile2)
        
        assert len(config.profiles) == 2
        assert config.get_profile("profile2") is not None
    
    def test_add_duplicate_profile(self):
        """Test adding profile with duplicate name"""
        profile1 = self.create_test_profile("duplicate")
        config = AdvancedSearchConfig(profiles=[profile1])
        
        profile2 = self.create_test_profile("duplicate")
        
        with pytest.raises(ValueError, match="already exists"):
            config.add_profile(profile2)
    
    def test_remove_profile(self):
        """Test removing a profile"""
        profiles = [
            self.create_test_profile("profile1"),
            self.create_test_profile("profile2")
        ]
        
        config = AdvancedSearchConfig(profiles=profiles)
        
        removed = config.remove_profile("profile1")
        assert removed
        assert len(config.profiles) == 1
        assert config.get_profile("profile1") is None
        
        not_removed = config.remove_profile("nonexistent")
        assert not not_removed
    
    def test_global_commute_filters(self):
        """Test global commute filters"""
        profile = self.create_test_profile()
        commute_filter = CommuteFilter(
            destination="Global Destination",
            max_time=60
        )
        
        config = AdvancedSearchConfig(
            profiles=[profile],
            global_commute_filters=[commute_filter]
        )
        
        assert len(config.global_commute_filters) == 1
        assert config.global_commute_filters[0].destination == "Global Destination"
    
    def test_execution_settings(self):
        """Test execution configuration settings"""
        profile = self.create_test_profile()
        
        config = AdvancedSearchConfig(
            profiles=[profile],
            concurrent_searches=5,
            delay_between_searches=2.5,
            deduplicate_across_profiles=False
        )
        
        assert config.concurrent_searches == 5
        assert config.delay_between_searches == 2.5
        assert not config.deduplicate_across_profiles
    
    def test_logging_settings(self):
        """Test logging and monitoring configuration"""
        profile = self.create_test_profile()
        
        config = AdvancedSearchConfig(
            profiles=[profile],
            enable_detailed_logging=True,
            log_file=Path("/var/log/homehunt.log")
        )
        
        assert config.enable_detailed_logging
        assert config.log_file == Path("/var/log/homehunt.log")