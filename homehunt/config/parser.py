"""
Configuration file parser for HomeHunt
Handles YAML and JSON configuration files with validation
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import ValidationError

from homehunt.cli.config import SearchConfig
from homehunt.core.models import Portal, PropertyType

from .models import AdvancedSearchConfig, ConfigFormat, SavedSearchProfile


class ConfigParserError(Exception):
    """Configuration parsing error"""
    pass


class ConfigParser:
    """Parser for HomeHunt configuration files"""
    
    @staticmethod
    def detect_format(file_path: Path) -> ConfigFormat:
        """Detect configuration file format from extension"""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif suffix == '.json':
            return ConfigFormat.JSON
        else:
            raise ConfigParserError(f"Unsupported file format: {suffix}")
    
    @staticmethod
    def load_file(file_path: Path) -> Dict[str, Any]:
        """Load configuration file content"""
        if not file_path.exists():
            raise ConfigParserError(f"Configuration file not found: {file_path}")
        
        try:
            content = file_path.read_text(encoding='utf-8')
            format_type = ConfigParser.detect_format(file_path)
            
            if format_type == ConfigFormat.YAML:
                return yaml.safe_load(content) or {}
            elif format_type == ConfigFormat.JSON:
                return json.loads(content)
            else:
                raise ConfigParserError(f"Unsupported format: {format_type}")
                
        except yaml.YAMLError as e:
            raise ConfigParserError(f"Invalid YAML syntax: {e}")
        except json.JSONDecodeError as e:
            raise ConfigParserError(f"Invalid JSON syntax: {e}")
        except Exception as e:
            raise ConfigParserError(f"Error reading file: {e}")
    
    @staticmethod
    def save_file(config: AdvancedSearchConfig, file_path: Path, format_type: Optional[ConfigFormat] = None) -> None:
        """Save configuration to file"""
        if format_type is None:
            format_type = ConfigParser.detect_format(file_path)
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            config_dict = config.model_dump(exclude_none=True, mode='json')
            
            if format_type == ConfigFormat.YAML:
                content = yaml.dump(
                    config_dict,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2
                )
            elif format_type == ConfigFormat.JSON:
                content = json.dumps(config_dict, indent=2, ensure_ascii=False)
            else:
                raise ConfigParserError(f"Unsupported format: {format_type}")
            
            file_path.write_text(content, encoding='utf-8')
            
        except Exception as e:
            raise ConfigParserError(f"Error saving file: {e}")
    
    @staticmethod
    def normalize_enum_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize enum values in configuration data"""
        normalized = data.copy()
        
        # Normalize portal values
        if 'portals' in normalized:
            portals = []
            for portal in normalized['portals']:
                if isinstance(portal, str):
                    try:
                        portals.append(Portal(portal.lower()))
                    except ValueError:
                        raise ConfigParserError(f"Invalid portal: {portal}")
                else:
                    portals.append(portal)
            normalized['portals'] = portals
        
        # Normalize property types
        if 'property_types' in normalized:
            prop_types = []
            for prop_type in normalized['property_types']:
                if isinstance(prop_type, str):
                    try:
                        prop_types.append(PropertyType(prop_type.lower()))
                    except ValueError:
                        raise ConfigParserError(f"Invalid property type: {prop_type}")
                else:
                    prop_types.append(prop_type)
            normalized['property_types'] = prop_types
        
        return normalized
    
    @staticmethod
    def parse_search_config(data: Dict[str, Any]) -> SearchConfig:
        """Parse a SearchConfig from dictionary data"""
        try:
            # Normalize enum values
            normalized_data = ConfigParser.normalize_enum_values(data)
            return SearchConfig(**normalized_data)
        except ValidationError as e:
            raise ConfigParserError(f"Invalid search configuration: {e}")
        except Exception as e:
            raise ConfigParserError(f"Error parsing search config: {e}")
    
    @staticmethod
    def parse_profile(data: Dict[str, Any]) -> SavedSearchProfile:
        """Parse a SavedSearchProfile from dictionary data"""
        try:
            # Extract and parse the search config
            if 'search' not in data:
                raise ConfigParserError("Profile missing 'search' configuration")
            
            search_data = data['search']
            search_config = ConfigParser.parse_search_config(search_data)
            
            # Create profile with parsed search config
            profile_data = data.copy()
            profile_data['search'] = search_config
            
            return SavedSearchProfile(**profile_data)
        except ValidationError as e:
            raise ConfigParserError(f"Invalid profile configuration: {e}")
        except Exception as e:
            raise ConfigParserError(f"Error parsing profile: {e}")
    
    @staticmethod
    def parse_config(file_path: Union[str, Path]) -> AdvancedSearchConfig:
        """
        Parse configuration file into AdvancedSearchConfig
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            AdvancedSearchConfig instance
            
        Raises:
            ConfigParserError: If parsing fails
        """
        file_path = Path(file_path)
        
        try:
            # Load raw data
            raw_data = ConfigParser.load_file(file_path)
            
            # Parse profiles
            if 'profiles' not in raw_data:
                raise ConfigParserError("Configuration missing 'profiles' section")
            
            profiles = []
            for i, profile_data in enumerate(raw_data['profiles']):
                try:
                    profile = ConfigParser.parse_profile(profile_data)
                    profiles.append(profile)
                except ConfigParserError as e:
                    raise ConfigParserError(f"Error in profile {i + 1}: {e}")
            
            # Build final config
            config_data = raw_data.copy()
            config_data['profiles'] = profiles
            
            return AdvancedSearchConfig(**config_data)
            
        except ValidationError as e:
            raise ConfigParserError(f"Configuration validation failed: {e}")
        except ConfigParserError:
            raise
        except Exception as e:
            raise ConfigParserError(f"Unexpected error parsing configuration: {e}")
    
    @staticmethod
    def create_template_config() -> AdvancedSearchConfig:
        """Create a template configuration with examples"""
        from homehunt.cli.config import FurnishedType, SortOrder
        from homehunt.core.models import Portal, PropertyType
        
        from .models import CommuteFilter, MultiLocationConfig, NotificationConfig
        
        # Example search config
        search_config = SearchConfig(
            portals=[Portal.RIGHTMOVE, Portal.ZOOPLA],
            location="SW1A 1AA",
            radius=1.0,
            min_price=1500,
            max_price=3000,
            min_bedrooms=1,
            max_bedrooms=2,
            property_types=[PropertyType.FLAT],
            furnished=FurnishedType.ANY,
            parking=True,
            sort_order=SortOrder.PRICE_ASC,
            max_results=50
        )
        
        # Example commute filter
        commute_filter = CommuteFilter(
            destination="Canary Wharf",
            max_time=45,
            transport_modes=["public_transport", "cycling"],
            departure_times=["08:00", "09:00"]
        )
        
        # Example multi-location config
        multi_location = MultiLocationConfig(
            name="Central London Areas",
            locations=["King's Cross", "London Bridge", "Canary Wharf"],
            combine_results=True,
            max_results_per_location=20
        )
        
        # Example notification config
        notifications = NotificationConfig(
            enabled=False,
            new_properties=True,
            price_changes=True,
            immediate_alerts=True,
            daily_summary=False
        )
        
        # Example profile
        profile = SavedSearchProfile(
            name="family_homes",
            description="Family-friendly homes with good transport links",
            search=search_config,
            multi_location=multi_location,
            commute_filters=[commute_filter],
            notifications=notifications,
            enable_scoring=True,
            score_weights={
                "price": 0.3,
                "commute": 0.4,
                "size": 0.2,
                "features": 0.1
            },
            auto_export=True,
            export_formats=["csv", "json"]
        )
        
        # Main config
        config = AdvancedSearchConfig(
            name="HomeHunt Search Configuration",
            description="Example configuration with multiple search profiles",
            profiles=[profile],
            global_commute_filters=[commute_filter],
            concurrent_searches=2,
            save_to_database=True
        )
        
        return config