"""
Configuration manager for HomeHunt
Handles loading, saving, and managing configuration profiles
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .models import AdvancedSearchConfig, SavedSearchProfile
from .parser import ConfigParser, ConfigParserError

console = Console()


class ConfigManagerError(Exception):
    """Configuration manager error"""
    pass


class ConfigManager:
    """Manager for HomeHunt configuration files and profiles"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory for configuration files (defaults to ~/.homehunt/config)
        """
        if config_dir is None:
            config_dir = Path.home() / ".homehunt" / "config"
        
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default config file locations
        self.default_config_file = self.config_dir / "default.yaml"
        self.profiles_dir = self.config_dir / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)
    
    def list_config_files(self) -> List[Path]:
        """List all configuration files in the config directory"""
        config_files = []
        
        # Add main config files
        for pattern in ["*.yaml", "*.yml", "*.json"]:
            config_files.extend(self.config_dir.glob(pattern))
        
        # Add profile files
        for pattern in ["*.yaml", "*.yml", "*.json"]:
            config_files.extend(self.profiles_dir.glob(pattern))
        
        return sorted(config_files)
    
    def load_config(self, config_path: Optional[Path] = None) -> AdvancedSearchConfig:
        """
        Load configuration from file
        
        Args:
            config_path: Path to config file (defaults to default.yaml)
            
        Returns:
            AdvancedSearchConfig instance
            
        Raises:
            ConfigManagerError: If loading fails
        """
        if config_path is None:
            config_path = self.default_config_file
        
        if not config_path.exists():
            raise ConfigManagerError(f"Configuration file not found: {config_path}")
        
        try:
            return ConfigParser.parse_config(config_path)
        except ConfigParserError as e:
            raise ConfigManagerError(f"Failed to load configuration: {e}")
    
    def save_config(self, config: AdvancedSearchConfig, config_path: Optional[Path] = None) -> None:
        """
        Save configuration to file
        
        Args:
            config: Configuration to save
            config_path: Path to save to (defaults to default.yaml)
            
        Raises:
            ConfigManagerError: If saving fails
        """
        if config_path is None:
            config_path = self.default_config_file
        
        try:
            ConfigParser.save_file(config, config_path)
        except ConfigParserError as e:
            raise ConfigManagerError(f"Failed to save configuration: {e}")
    
    def create_default_config(self, overwrite: bool = False) -> Path:
        """
        Create default configuration file with examples
        
        Args:
            overwrite: Whether to overwrite existing file
            
        Returns:
            Path to created config file
            
        Raises:
            ConfigManagerError: If creation fails
        """
        if self.default_config_file.exists() and not overwrite:
            raise ConfigManagerError(
                f"Default config already exists: {self.default_config_file}. "
                "Use overwrite=True to replace it."
            )
        
        try:
            template_config = ConfigParser.create_template_config()
            self.save_config(template_config, self.default_config_file)
            return self.default_config_file
        except Exception as e:
            raise ConfigManagerError(f"Failed to create default config: {e}")
    
    def list_profiles(self, config_path: Optional[Path] = None) -> List[SavedSearchProfile]:
        """
        List all profiles in a configuration
        
        Args:
            config_path: Path to config file (defaults to default.yaml)
            
        Returns:
            List of SavedSearchProfile instances
        """
        try:
            config = self.load_config(config_path)
            return config.profiles
        except ConfigManagerError:
            return []
    
    def get_profile(self, name: str, config_path: Optional[Path] = None) -> Optional[SavedSearchProfile]:
        """
        Get a specific profile by name
        
        Args:
            name: Profile name
            config_path: Path to config file
            
        Returns:
            SavedSearchProfile if found, None otherwise
        """
        try:
            config = self.load_config(config_path)
            return config.get_profile(name)
        except ConfigManagerError:
            return None
    
    def add_profile(self, profile: SavedSearchProfile, config_path: Optional[Path] = None) -> None:
        """
        Add a profile to configuration
        
        Args:
            profile: Profile to add
            config_path: Path to config file
            
        Raises:
            ConfigManagerError: If adding fails
        """
        try:
            config = self.load_config(config_path)
            config.add_profile(profile)
            self.save_config(config, config_path)
        except (ConfigManagerError, ValueError) as e:
            raise ConfigManagerError(f"Failed to add profile: {e}")
    
    def remove_profile(self, name: str, config_path: Optional[Path] = None) -> bool:
        """
        Remove a profile from configuration
        
        Args:
            name: Profile name to remove
            config_path: Path to config file
            
        Returns:
            True if profile was removed, False if not found
            
        Raises:
            ConfigManagerError: If removal fails
        """
        try:
            config = self.load_config(config_path)
            removed = config.remove_profile(name)
            if removed:
                self.save_config(config, config_path)
            return removed
        except ConfigManagerError as e:
            raise ConfigManagerError(f"Failed to remove profile: {e}")
    
    def validate_config(self, config_path: Path) -> List[str]:
        """
        Validate configuration file and return any errors
        
        Args:
            config_path: Path to config file
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            config = ConfigParser.parse_config(config_path)
            
            # Additional validation checks
            if not config.profiles:
                errors.append("Configuration must have at least one profile")
            
            # Check for duplicate profile names
            profile_names = [p.name for p in config.profiles]
            if len(profile_names) != len(set(profile_names)):
                errors.append("Profile names must be unique")
            
            # Validate each profile
            for i, profile in enumerate(config.profiles):
                profile_errors = self._validate_profile(profile)
                for error in profile_errors:
                    errors.append(f"Profile '{profile.name}' (#{i+1}): {error}")
                    
        except ConfigParserError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected validation error: {e}")
        
        return errors
    
    def _validate_profile(self, profile: SavedSearchProfile) -> List[str]:
        """Validate individual profile"""
        errors = []
        
        # Check required fields
        if not profile.name.strip():
            errors.append("Profile name cannot be empty")
        
        # Validate commute filters
        if profile.commute_filters:
            for i, commute_filter in enumerate(profile.commute_filters):
                if not commute_filter.destination.strip():
                    errors.append(f"Commute filter #{i+1}: destination cannot be empty")
        
        # Validate export settings
        if profile.auto_export and profile.export_formats:
            if "google_sheets" in profile.export_formats:
                # Could add Google Sheets credential validation here
                pass
            
            if profile.export_path:
                try:
                    export_path = Path(profile.export_path)
                    if not export_path.parent.exists():
                        errors.append(f"Export directory does not exist: {export_path.parent}")
                except Exception:
                    errors.append("Invalid export path")
        
        return errors
    
    def show_config_summary(self, config_path: Optional[Path] = None) -> None:
        """Display a summary of the configuration"""
        try:
            config = self.load_config(config_path)
            
            console.print(f"\n[bold cyan]Configuration Summary[/bold cyan]")
            console.print(f"Name: {config.name or 'Unnamed'}")
            console.print(f"Description: {config.description or 'No description'}")
            console.print(f"Version: {config.version}")
            console.print(f"Profiles: {len(config.profiles)}")
            
            if config.profiles:
                table = Table(title="Search Profiles")
                table.add_column("Name", style="cyan")
                table.add_column("Description", style="white")
                table.add_column("Location(s)", style="yellow")
                table.add_column("Commute Filters", style="green")
                table.add_column("Auto Export", style="magenta")
                
                for profile in config.profiles:
                    # Get location info
                    if profile.multi_location:
                        locations = f"{len(profile.multi_location.locations)} locations"
                    else:
                        locations = profile.search.location
                    
                    # Get commute info
                    commute_count = len(profile.commute_filters) if profile.commute_filters else 0
                    if config.global_commute_filters:
                        commute_count += len(config.global_commute_filters)
                    commute_info = f"{commute_count} filters" if commute_count > 0 else "None"
                    
                    # Export info
                    export_info = "Yes" if profile.auto_export else "No"
                    
                    table.add_row(
                        profile.name,
                        profile.description or "-",
                        locations,
                        commute_info,
                        export_info
                    )
                
                console.print(table)
                
        except ConfigManagerError as e:
            console.print(f"[red]Error loading configuration: {e}[/red]")
    
    def get_config_dir(self) -> Path:
        """Get the configuration directory path"""
        return self.config_dir
    
    def backup_config(self, config_path: Optional[Path] = None) -> Path:
        """
        Create a backup of the configuration file
        
        Args:
            config_path: Path to config file
            
        Returns:
            Path to backup file
        """
        if config_path is None:
            config_path = self.default_config_file
        
        if not config_path.exists():
            raise ConfigManagerError(f"Configuration file not found: {config_path}")
        
        # Create backup with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_suffix(f".backup_{timestamp}{config_path.suffix}")
        
        backup_path.write_bytes(config_path.read_bytes())
        return backup_path