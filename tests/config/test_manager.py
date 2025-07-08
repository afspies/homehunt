"""
Tests for configuration manager
"""

import tempfile
from pathlib import Path

import pytest

from homehunt.cli.config import SearchConfig
from homehunt.config.manager import ConfigManager, ConfigManagerError
from homehunt.config.models import AdvancedSearchConfig, SavedSearchProfile
from homehunt.core.models import Portal


class TestConfigManager:
    """Test ConfigManager functionality"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create ConfigManager with temporary directory"""
        return ConfigManager(temp_config_dir)
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        search_config = SearchConfig(
            location="SW1A 1AA",
            portals=[Portal.RIGHTMOVE],
            min_price=1500
        )
        
        profile = SavedSearchProfile(
            name="test_profile",
            search=search_config
        )
        
        return AdvancedSearchConfig(
            name="Test Config",
            profiles=[profile]
        )
    
    def test_init_creates_directories(self, temp_config_dir):
        """Test that ConfigManager creates necessary directories"""
        manager = ConfigManager(temp_config_dir)
        
        assert manager.config_dir.exists()
        assert manager.profiles_dir.exists()
        assert manager.default_config_file == temp_config_dir / "default.yaml"
    
    def test_save_and_load_config(self, config_manager, test_config):
        """Test saving and loading configuration"""
        # Save config
        config_manager.save_config(test_config)
        
        # Verify file exists
        assert config_manager.default_config_file.exists()
        
        # Load config
        loaded_config = config_manager.load_config()
        
        assert loaded_config.name == "Test Config"
        assert len(loaded_config.profiles) == 1
        assert loaded_config.profiles[0].name == "test_profile"
    
    def test_load_nonexistent_config(self, config_manager):
        """Test loading non-existent configuration"""
        with pytest.raises(ConfigManagerError, match="Configuration file not found"):
            config_manager.load_config()
    
    def test_create_default_config(self, config_manager):
        """Test creating default configuration"""
        config_path = config_manager.create_default_config()
        
        assert config_path.exists()
        assert config_path == config_manager.default_config_file
        
        # Verify we can load it
        loaded_config = config_manager.load_config()
        assert loaded_config.name == "HomeHunt Search Configuration"
        assert len(loaded_config.profiles) >= 1
    
    def test_create_default_config_already_exists(self, config_manager, test_config):
        """Test creating default config when one already exists"""
        # Create initial config
        config_manager.save_config(test_config)
        
        # Try to create default without overwrite
        with pytest.raises(ConfigManagerError, match="Default config already exists"):
            config_manager.create_default_config(overwrite=False)
        
        # Should work with overwrite=True
        config_path = config_manager.create_default_config(overwrite=True)
        assert config_path.exists()
    
    def test_list_config_files(self, config_manager, test_config):
        """Test listing configuration files"""
        # Initially empty
        files = config_manager.list_config_files()
        assert len(files) == 0
        
        # Save a config
        config_manager.save_config(test_config)
        
        # Should find the config file
        files = config_manager.list_config_files()
        assert len(files) == 1
        assert files[0].name == "default.yaml"
    
    def test_list_profiles(self, config_manager, test_config):
        """Test listing profiles from configuration"""
        # No config yet
        profiles = config_manager.list_profiles()
        assert len(profiles) == 0
        
        # Save config and list profiles
        config_manager.save_config(test_config)
        profiles = config_manager.list_profiles()
        
        assert len(profiles) == 1
        assert profiles[0].name == "test_profile"
    
    def test_get_profile(self, config_manager, test_config):
        """Test getting specific profile by name"""
        config_manager.save_config(test_config)
        
        # Get existing profile
        profile = config_manager.get_profile("test_profile")
        assert profile is not None
        assert profile.name == "test_profile"
        
        # Get non-existent profile
        profile = config_manager.get_profile("nonexistent")
        assert profile is None
    
    def test_add_profile(self, config_manager, test_config):
        """Test adding a new profile to configuration"""
        config_manager.save_config(test_config)
        
        # Create new profile
        new_search = SearchConfig(
            location="E14",
            portals=[Portal.ZOOPLA],
            max_price=2500
        )
        
        new_profile = SavedSearchProfile(
            name="new_profile",
            search=new_search
        )
        
        # Add profile
        config_manager.add_profile(new_profile)
        
        # Verify it was added
        loaded_config = config_manager.load_config()
        assert len(loaded_config.profiles) == 2
        assert loaded_config.get_profile("new_profile") is not None
    
    def test_add_duplicate_profile(self, config_manager, test_config):
        """Test adding profile with duplicate name"""
        config_manager.save_config(test_config)
        
        # Try to add profile with same name
        duplicate_search = SearchConfig(
            location="Different Location",
            portals=[Portal.ZOOPLA]
        )
        
        duplicate_profile = SavedSearchProfile(
            name="test_profile",  # Same name as existing
            search=duplicate_search
        )
        
        with pytest.raises(ConfigManagerError, match="Failed to add profile"):
            config_manager.add_profile(duplicate_profile)
    
    def test_remove_profile(self, config_manager, test_config):
        """Test removing a profile from configuration"""
        config_manager.save_config(test_config)
        
        # Remove existing profile
        removed = config_manager.remove_profile("test_profile")
        assert removed
        
        # Verify it was removed
        loaded_config = config_manager.load_config()
        assert len(loaded_config.profiles) == 0
        
        # Try to remove non-existent profile
        removed = config_manager.remove_profile("nonexistent")
        assert not removed
    
    def test_validate_config_valid(self, config_manager, test_config):
        """Test validating a valid configuration"""
        config_manager.save_config(test_config)
        
        errors = config_manager.validate_config(config_manager.default_config_file)
        assert len(errors) == 0
    
    def test_validate_config_no_profiles(self, config_manager):
        """Test validating configuration with no profiles"""
        # Create config without profiles
        invalid_config = AdvancedSearchConfig(
            name="Invalid Config",
            profiles=[]  # Empty profiles list
        )
        
        config_manager.save_config(invalid_config)
        
        errors = config_manager.validate_config(config_manager.default_config_file)
        assert len(errors) > 0
        assert any("at least one profile" in error for error in errors)
    
    def test_validate_config_empty_profile_name(self, config_manager):
        """Test validating configuration with empty profile name"""
        search_config = SearchConfig(
            location="SW1A 1AA",
            portals=[Portal.RIGHTMOVE]
        )
        
        # Create profile with empty name
        invalid_profile = SavedSearchProfile(
            name="",  # Empty name
            search=search_config
        )
        
        invalid_config = AdvancedSearchConfig(
            profiles=[invalid_profile]
        )
        
        config_manager.save_config(invalid_config)
        
        errors = config_manager.validate_config(config_manager.default_config_file)
        assert len(errors) > 0
        assert any("name cannot be empty" in error for error in errors)
    
    def test_backup_config(self, config_manager, test_config):
        """Test creating configuration backup"""
        config_manager.save_config(test_config)
        
        backup_path = config_manager.backup_config()
        
        assert backup_path.exists()
        assert "backup_" in backup_path.name
        assert backup_path.suffix == ".yaml"
        
        # Verify backup content
        backup_config = config_manager.load_config(backup_path)
        assert backup_config.name == test_config.name
    
    def test_backup_nonexistent_config(self, config_manager):
        """Test backing up non-existent configuration"""
        with pytest.raises(ConfigManagerError, match="Configuration file not found"):
            config_manager.backup_config()
    
    def test_get_config_dir(self, config_manager, temp_config_dir):
        """Test getting configuration directory path"""
        assert config_manager.get_config_dir() == temp_config_dir