"""
Advanced configuration models for HomeHunt
Supports YAML/JSON configuration files with complex search criteria
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from homehunt.cli.config import CommuteConfig, SearchConfig


class ConfigFormat(str, Enum):
    """Supported configuration file formats"""
    
    YAML = "yaml"
    JSON = "json"


class NotificationConfig(BaseModel):
    """Configuration for notifications and alerts"""
    
    enabled: bool = Field(
        False,
        description="Enable notifications"
    )
    
    # Telegram settings
    telegram_bot_token: Optional[str] = Field(
        None,
        description="Telegram bot token for alerts"
    )
    telegram_chat_id: Optional[str] = Field(
        None,
        description="Telegram chat ID for sending messages"
    )
    
    # Email settings (future)
    email_enabled: bool = Field(
        False,
        description="Enable email notifications"
    )
    email_smtp_server: Optional[str] = Field(
        None,
        description="SMTP server for email notifications"
    )
    email_from: Optional[str] = Field(
        None,
        description="From email address"
    )
    email_to: Optional[List[str]] = Field(
        None,
        description="List of recipient email addresses"
    )
    
    # Notification triggers
    new_properties: bool = Field(
        True,
        description="Alert on new properties"
    )
    price_changes: bool = Field(
        True,
        description="Alert on price changes"
    )
    status_changes: bool = Field(
        False,
        description="Alert on availability status changes"
    )
    
    # Frequency settings
    immediate_alerts: bool = Field(
        True,
        description="Send immediate alerts for new matches"
    )
    daily_summary: bool = Field(
        False,
        description="Send daily summary of activity"
    )
    weekly_summary: bool = Field(
        False,
        description="Send weekly summary report"
    )


class CommuteFilter(BaseModel):
    """Enhanced commute filtering configuration"""
    
    destination: str = Field(
        ...,
        description="Commute destination (address or postcode)"
    )
    
    max_time: int = Field(
        ...,
        description="Maximum commute time in minutes",
        ge=1,
        le=180
    )
    
    transport_modes: List[str] = Field(
        default=["public_transport"],
        description="Transport modes to consider"
    )
    
    departure_times: List[str] = Field(
        default=["08:00"],
        description="Departure times to check (HH:MM format)"
    )
    
    # Advanced commute options
    return_journey: bool = Field(
        False,
        description="Also check return journey times"
    )
    
    return_departure_times: Optional[List[str]] = Field(
        None,
        description="Return journey departure times"
    )
    
    weekend_commute: bool = Field(
        False,
        description="Include weekend commute times"
    )
    
    weight: float = Field(
        1.0,
        description="Weight for this commute filter in scoring",
        ge=0.0,
        le=2.0
    )
    
    @field_validator('transport_modes')
    def validate_transport_modes(cls, v):
        """Validate transport modes"""
        valid_modes = {"public_transport", "cycling", "walking", "driving"}
        for mode in v:
            if mode not in valid_modes:
                raise ValueError(f"Invalid transport mode: {mode}")
        return v
    
    @field_validator('departure_times', 'return_departure_times')
    def validate_times(cls, v):
        """Validate time format"""
        if v:
            for time_str in v:
                try:
                    hours, minutes = time_str.split(':')
                    hour = int(hours)
                    minute = int(minutes)
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                except (ValueError, AttributeError):
                    raise ValueError(f"Time must be in HH:MM format: {time_str}")
        return v


class MultiLocationConfig(BaseModel):
    """Configuration for searching multiple locations"""
    
    name: str = Field(
        ...,
        description="Name for this location group"
    )
    
    locations: List[str] = Field(
        ...,
        description="List of locations to search",
        min_items=1
    )
    
    # Location-specific overrides
    location_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description="Per-location parameter overrides"
    )
    
    # Combination strategy
    combine_results: bool = Field(
        True,
        description="Combine results from all locations"
    )
    
    max_results_per_location: Optional[int] = Field(
        None,
        description="Maximum results per individual location"
    )


class SavedSearchProfile(BaseModel):
    """A saved search profile with all configurations"""
    
    name: str = Field(
        ...,
        description="Profile name"
    )
    
    description: Optional[str] = Field(
        None,
        description="Profile description"
    )
    
    # Base search configuration
    search: SearchConfig = Field(
        ...,
        description="Base search configuration"
    )
    
    # Multi-location support
    multi_location: Optional[MultiLocationConfig] = Field(
        None,
        description="Multi-location search configuration"
    )
    
    # Commute filtering
    commute_filters: Optional[List[CommuteFilter]] = Field(
        None,
        description="List of commute filters to apply"
    )
    
    # Notifications
    notifications: Optional[NotificationConfig] = Field(
        None,
        description="Notification settings for this profile"
    )
    
    # Scoring and ranking
    enable_scoring: bool = Field(
        False,
        description="Enable property scoring based on criteria"
    )
    
    score_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Weights for different scoring factors"
    )
    
    # Export settings
    auto_export: bool = Field(
        False,
        description="Automatically export results"
    )
    
    export_formats: Optional[List[str]] = Field(
        None,
        description="Export formats (csv, json, google_sheets)"
    )
    
    export_path: Optional[Path] = Field(
        None,
        description="Export file path (for CSV/JSON)"
    )
    
    # Scheduling
    schedule_enabled: bool = Field(
        False,
        description="Enable scheduled execution"
    )
    
    schedule_cron: Optional[str] = Field(
        None,
        description="Cron expression for scheduling"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Profile creation timestamp"
    )
    
    last_run: Optional[datetime] = Field(
        None,
        description="Last execution timestamp"
    )
    
    total_runs: int = Field(
        0,
        description="Total number of executions"
    )
    
    @field_validator('export_formats')
    def validate_export_formats(cls, v):
        """Validate export formats"""
        if v:
            valid_formats = {"csv", "json", "google_sheets"}
            for fmt in v:
                if fmt not in valid_formats:
                    raise ValueError(f"Invalid export format: {fmt}")
        return v


class AdvancedSearchConfig(BaseModel):
    """
    Advanced configuration supporting multiple search profiles,
    complex filtering, and automation features
    """
    
    version: str = Field(
        "1.0",
        description="Configuration schema version"
    )
    
    name: Optional[str] = Field(
        None,
        description="Configuration name"
    )
    
    description: Optional[str] = Field(
        None,
        description="Configuration description"
    )
    
    # Global settings
    global_notifications: Optional[NotificationConfig] = Field(
        None,
        description="Global notification settings"
    )
    
    # Search profiles
    profiles: List[SavedSearchProfile] = Field(
        ...,
        description="List of search profiles to execute",
        min_items=1
    )
    
    # Global commute destinations (applied to all profiles)
    global_commute_filters: Optional[List[CommuteFilter]] = Field(
        None,
        description="Global commute filters applied to all profiles"
    )
    
    # Execution settings
    concurrent_searches: int = Field(
        3,
        description="Maximum concurrent searches",
        ge=1,
        le=10
    )
    
    delay_between_searches: float = Field(
        1.0,
        description="Delay between searches in seconds",
        ge=0.0,
        le=60.0
    )
    
    # Database settings
    deduplicate_across_profiles: bool = Field(
        True,
        description="Deduplicate properties across all profiles"
    )
    
    save_to_database: bool = Field(
        True,
        description="Save results to database"
    )
    
    # Monitoring and logging
    enable_detailed_logging: bool = Field(
        False,
        description="Enable detailed execution logging"
    )
    
    log_file: Optional[Path] = Field(
        None,
        description="Log file path"
    )
    
    # Default export settings
    default_export_path: Optional[Path] = Field(
        None,
        description="Default export directory"
    )
    
    @field_validator('profiles')
    def validate_unique_profile_names(cls, v):
        """Ensure profile names are unique"""
        names = [profile.name for profile in v]
        if len(names) != len(set(names)):
            raise ValueError("Profile names must be unique")
        return v
    
    def get_profile(self, name: str) -> Optional[SavedSearchProfile]:
        """Get a profile by name"""
        for profile in self.profiles:
            if profile.name == name:
                return profile
        return None
    
    def add_profile(self, profile: SavedSearchProfile) -> None:
        """Add a new profile"""
        if self.get_profile(profile.name):
            raise ValueError(f"Profile '{profile.name}' already exists")
        self.profiles.append(profile)
    
    def remove_profile(self, name: str) -> bool:
        """Remove a profile by name"""
        for i, profile in enumerate(self.profiles):
            if profile.name == name:
                del self.profiles[i]
                return True
        return False