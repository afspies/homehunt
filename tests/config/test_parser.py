"""
Tests for configuration parser
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from homehunt.cli.config import FurnishedType, SearchConfig, SortOrder
from homehunt.config.models import AdvancedSearchConfig, SavedSearchProfile
from homehunt.config.parser import ConfigFormat, ConfigParser, ConfigParserError
from homehunt.core.models import Portal, PropertyType


class TestConfigParser:
    """Test ConfigParser functionality"""
    
    def test_detect_yaml_format(self):
        """Test detecting YAML file format"""
        yaml_path = Path("config.yaml")
        assert ConfigParser.detect_format(yaml_path) == ConfigFormat.YAML
        
        yml_path = Path("config.yml")
        assert ConfigParser.detect_format(yml_path) == ConfigFormat.YAML
    
    def test_detect_json_format(self):
        """Test detecting JSON file format"""
        json_path = Path("config.json")
        assert ConfigParser.detect_format(json_path) == ConfigFormat.JSON
    
    def test_detect_unsupported_format(self):
        """Test detecting unsupported file format"""
        with pytest.raises(ConfigParserError, match="Unsupported file format"):
            ConfigParser.detect_format(Path("config.txt"))
    
    def test_load_yaml_file(self):
        """Test loading YAML configuration file"""
        yaml_content = """
        name: "Test Config"
        version: "1.0"
        profiles:
          - name: "test_profile"
            search:
              location: "SW1A 1AA"
              portals: ["rightmove"]
              min_price: 1500
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            data = ConfigParser.load_file(Path(f.name))
            
            assert data["name"] == "Test Config"
            assert len(data["profiles"]) == 1
            assert data["profiles"][0]["name"] == "test_profile"
        
        Path(f.name).unlink()  # Clean up
    
    def test_load_json_file(self):
        """Test loading JSON configuration file"""
        json_content = {
            "name": "Test Config",
            "version": "1.0",
            "profiles": [
                {
                    "name": "test_profile",
                    "search": {
                        "location": "SW1A 1AA",
                        "portals": ["rightmove"],
                        "min_price": 1500
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f)
            f.flush()
            
            data = ConfigParser.load_file(Path(f.name))
            
            assert data["name"] == "Test Config"
            assert len(data["profiles"]) == 1
            assert data["profiles"][0]["name"] == "test_profile"
        
        Path(f.name).unlink()  # Clean up
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file"""
        with pytest.raises(ConfigParserError, match="Configuration file not found"):
            ConfigParser.load_file(Path("nonexistent.yaml"))
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML syntax"""
        invalid_yaml = """
        name: "Test Config"
        invalid: [unclosed bracket
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            
            with pytest.raises(ConfigParserError, match="Invalid YAML syntax"):
                ConfigParser.load_file(Path(f.name))
        
        Path(f.name).unlink()  # Clean up
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON syntax"""
        invalid_json = """
        {
            "name": "Test Config",
            "invalid": [unclosed bracket
        }
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(invalid_json)
            f.flush()
            
            with pytest.raises(ConfigParserError, match="Invalid JSON syntax"):
                ConfigParser.load_file(Path(f.name))
        
        Path(f.name).unlink()  # Clean up
    
    def test_normalize_enum_values(self):
        """Test normalizing enum values in configuration"""
        data = {
            "portals": ["rightmove", "zoopla"],
            "property_types": ["flat", "house"]
        }
        
        normalized = ConfigParser.normalize_enum_values(data)
        
        assert normalized["portals"] == [Portal.RIGHTMOVE, Portal.ZOOPLA]
        assert normalized["property_types"] == [PropertyType.FLAT, PropertyType.HOUSE]
    
    def test_normalize_invalid_portal(self):
        """Test normalizing invalid portal value"""
        data = {"portals": ["invalid_portal"]}
        
        with pytest.raises(ConfigParserError, match="Invalid portal"):
            ConfigParser.normalize_enum_values(data)
    
    def test_normalize_invalid_property_type(self):
        """Test normalizing invalid property type"""
        data = {"property_types": ["invalid_type"]}
        
        with pytest.raises(ConfigParserError, match="Invalid property type"):
            ConfigParser.normalize_enum_values(data)
    
    def test_parse_search_config(self):
        """Test parsing SearchConfig from dictionary"""
        data = {
            "location": "SW1A 1AA",
            "portals": ["rightmove"],
            "min_price": 1500,
            "max_price": 3000,
            "property_types": ["flat"],
            "furnished": "any",
            "sort_order": "price_asc"
        }
        
        search_config = ConfigParser.parse_search_config(data)
        
        assert search_config.location == "SW1A 1AA"
        assert search_config.portals == [Portal.RIGHTMOVE]
        assert search_config.min_price == 1500
        assert search_config.property_types == [PropertyType.FLAT]
        assert search_config.furnished == FurnishedType.ANY
        assert search_config.sort_order == SortOrder.PRICE_ASC
    
    def test_parse_invalid_search_config(self):
        """Test parsing invalid SearchConfig"""
        data = {
            "location": "",  # Invalid: empty location
            "min_price": -100  # Invalid: negative price
        }
        
        with pytest.raises(ConfigParserError, match="Invalid search configuration"):
            ConfigParser.parse_search_config(data)
    
    def test_parse_profile(self):
        """Test parsing SavedSearchProfile from dictionary"""
        data = {
            "name": "test_profile",
            "description": "Test profile",
            "search": {
                "location": "SW1A 1AA",
                "portals": ["rightmove"],
                "min_price": 1500
            },
            "enable_scoring": True
        }
        
        profile = ConfigParser.parse_profile(data)
        
        assert profile.name == "test_profile"
        assert profile.description == "Test profile"
        assert profile.search.location == "SW1A 1AA"
        assert profile.enable_scoring
    
    def test_parse_profile_missing_search(self):
        """Test parsing profile without search configuration"""
        data = {
            "name": "invalid_profile"
            # Missing 'search' field
        }
        
        with pytest.raises(ConfigParserError, match="missing 'search' configuration"):
            ConfigParser.parse_profile(data)
    
    def test_parse_complete_config(self):
        """Test parsing complete configuration file"""
        config_data = {
            "name": "Complete Test Config",
            "version": "1.0",
            "profiles": [
                {
                    "name": "profile1",
                    "search": {
                        "location": "SW1A 1AA",
                        "portals": ["rightmove"],
                        "min_price": 1500
                    }
                },
                {
                    "name": "profile2",
                    "search": {
                        "location": "E14",
                        "portals": ["zoopla"],
                        "max_price": 2500
                    }
                }
            ],
            "concurrent_searches": 2,
            "save_to_database": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            
            config = ConfigParser.parse_config(Path(f.name))
            
            assert config.name == "Complete Test Config"
            assert len(config.profiles) == 2
            assert config.profiles[0].name == "profile1"
            assert config.profiles[1].name == "profile2"
            assert config.concurrent_searches == 2
            assert config.save_to_database
        
        Path(f.name).unlink()  # Clean up
    
    def test_parse_config_missing_profiles(self):
        """Test parsing configuration without profiles"""
        config_data = {
            "name": "Invalid Config"
            # Missing 'profiles' field
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            
            with pytest.raises(ConfigParserError, match="missing 'profiles' section"):
                ConfigParser.parse_config(Path(f.name))
        
        Path(f.name).unlink()  # Clean up
    
    def test_save_yaml_file(self):
        """Test saving configuration to YAML file"""
        # Create a test configuration
        search_config = SearchConfig(
            location="SW1A 1AA",
            portals=[Portal.RIGHTMOVE],
            min_price=1500
        )
        
        profile = SavedSearchProfile(
            name="test_profile",
            search=search_config
        )
        
        config = AdvancedSearchConfig(
            name="Test Config",
            profiles=[profile]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            temp_path = Path(f.name)
        
        # Save and reload
        ConfigParser.save_file(config, temp_path, ConfigFormat.YAML)
        
        # Verify file was created and has correct content
        assert temp_path.exists()
        
        loaded_config = ConfigParser.parse_config(temp_path)
        assert loaded_config.name == "Test Config"
        assert len(loaded_config.profiles) == 1
        assert loaded_config.profiles[0].name == "test_profile"
        
        temp_path.unlink()  # Clean up
    
    def test_save_json_file(self):
        """Test saving configuration to JSON file"""
        # Create a test configuration
        search_config = SearchConfig(
            location="E14",
            portals=[Portal.ZOOPLA],
            max_price=2500
        )
        
        profile = SavedSearchProfile(
            name="json_profile",
            search=search_config
        )
        
        config = AdvancedSearchConfig(
            name="JSON Config",
            profiles=[profile]
        )
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        # Save and reload
        ConfigParser.save_file(config, temp_path, ConfigFormat.JSON)
        
        # Verify file was created and has correct content
        assert temp_path.exists()
        
        loaded_config = ConfigParser.parse_config(temp_path)
        assert loaded_config.name == "JSON Config"
        assert len(loaded_config.profiles) == 1
        assert loaded_config.profiles[0].name == "json_profile"
        
        temp_path.unlink()  # Clean up
    
    def test_create_template_config(self):
        """Test creating template configuration"""
        template = ConfigParser.create_template_config()
        
        assert template.name == "HomeHunt Search Configuration"
        assert len(template.profiles) == 1
        assert template.profiles[0].name == "family_homes"
        assert template.profiles[0].search.location == "SW1A 1AA"
        assert template.profiles[0].commute_filters is not None
        assert len(template.profiles[0].commute_filters) == 1
        assert template.global_commute_filters is not None
        assert len(template.global_commute_filters) == 1