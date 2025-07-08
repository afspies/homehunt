"""
Tests for configuration executor
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from homehunt.cli.config import SearchConfig
from homehunt.config.executor import ConfigExecutor, ConfigExecutorError
from homehunt.config.models import AdvancedSearchConfig, CommuteFilter, SavedSearchProfile
from homehunt.core.models import Portal, PropertyListing


class TestConfigExecutor:
    """Test ConfigExecutor functionality"""
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration"""
        search_config = SearchConfig(
            location="SW1A 1AA",
            portals=[Portal.RIGHTMOVE],
            min_price=1500,
            max_price=3000
        )
        
        profile = SavedSearchProfile(
            name="test_profile",
            search=search_config
        )
        
        return AdvancedSearchConfig(
            name="Test Config",
            profiles=[profile],
            save_to_database=False  # Disable database for tests
        )
    
    @pytest.fixture
    def mock_properties(self):
        """Create mock property listings"""
        return [
            PropertyListing(
                url="https://rightmove.co.uk/1",
                title="Test Property 1",
                price="£2000 pcm",
                bedrooms=2,
                portal=Portal.RIGHTMOVE,
                area="Test Area 1"
            ),
            PropertyListing(
                url="https://rightmove.co.uk/2", 
                title="Test Property 2",
                price="£2500 pcm",
                bedrooms=3,
                portal=Portal.RIGHTMOVE,
                area="Test Area 2"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_basic_execution(self, test_config, mock_properties):
        """Test basic configuration execution"""
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            result = await executor.execute()
            
            assert len(result) == 2
            assert result[0].title == "Test Property 1"
            assert result[1].title == "Test Property 2"
            
            # Verify search was called once
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dry_run(self, test_config):
        """Test dry run execution"""
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            result = await executor.execute(dry_run=True)
            
            assert len(result) == 0
            # Verify search was not called
            mock_search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_profile_filtering(self, test_config, mock_properties):
        """Test execution with specific profile names"""
        # Add another profile
        extra_search = SearchConfig(
            location="E14",
            portals=[Portal.ZOOPLA],
            max_price=2000
        )
        
        extra_profile = SavedSearchProfile(
            name="extra_profile",
            search=extra_search
        )
        
        test_config.profiles.append(extra_profile)
        
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            # Execute only the first profile
            result = await executor.execute(profile_names=["test_profile"])
            
            assert len(result) == 2
            # Should be called only once (for test_profile)
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_nonexistent_profile(self, test_config, mock_properties):
        """Test execution with non-existent profile name"""
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            result = await executor.execute(profile_names=["nonexistent"])
            
            assert len(result) == 0
            mock_search.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_deduplication(self, test_config):
        """Test property deduplication"""
        # Create properties with duplicate URLs
        duplicate_properties = [
            PropertyListing(
                url="https://rightmove.co.uk/1",
                title="Property 1",
                portal=Portal.RIGHTMOVE
            ),
            PropertyListing(
                url="https://rightmove.co.uk/1",  # Duplicate URL
                title="Property 1 Duplicate",
                portal=Portal.RIGHTMOVE
            ),
            PropertyListing(
                url="https://rightmove.co.uk/2",
                title="Property 2",
                portal=Portal.RIGHTMOVE
            )
        ]
        
        test_config.deduplicate_across_profiles = True
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = duplicate_properties
            
            result = await executor.execute()
            
            # Should have deduplicated to 2 unique properties
            assert len(result) == 2
            assert result[0].url == "https://rightmove.co.uk/1"
            assert result[1].url == "https://rightmove.co.uk/2"
    
    @pytest.mark.asyncio
    async def test_scoring(self, test_config, mock_properties):
        """Test property scoring"""
        # Enable scoring
        test_config.profiles[0].enable_scoring = True
        test_config.profiles[0].score_weights = {
            "price": 0.5,
            "size": 0.3,
            "features": 0.2
        }
        
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            result = await executor.execute()
            
            # Properties should have calculated scores
            assert hasattr(result[0], 'calculated_score')
            assert hasattr(result[1], 'calculated_score')
            
            # Properties should be sorted by score (descending)
            scores = [getattr(prop, 'calculated_score', 0) for prop in result]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_multi_location_search(self, mock_properties):
        """Test multi-location search execution"""
        from homehunt.config.models import MultiLocationConfig
        
        search_config = SearchConfig(
            location="Base Location",  # Will be overridden
            portals=[Portal.RIGHTMOVE],
            min_price=1500
        )
        
        multi_location = MultiLocationConfig(
            name="Multi Location Test",
            locations=["Location A", "Location B"],
            combine_results=True
        )
        
        profile = SavedSearchProfile(
            name="multi_location_profile",
            search=search_config,
            multi_location=multi_location
        )
        
        config = AdvancedSearchConfig(
            profiles=[profile],
            save_to_database=False
        )
        
        executor = ConfigExecutor(config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            result = await executor.execute()
            
            # Should be called twice (once for each location)
            assert mock_search.call_count == 2
            
            # Should return combined results
            assert len(result) == 4  # 2 properties × 2 locations
    
    @pytest.mark.asyncio
    async def test_error_handling(self, test_config):
        """Test error handling during execution"""
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.side_effect = Exception("Search failed")
            
            result = await executor.execute()
            
            # Should handle error gracefully and return empty list
            assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, mock_properties):
        """Test concurrent execution of multiple profiles"""
        # Create multiple profiles
        profiles = []
        for i in range(3):
            search_config = SearchConfig(
                location=f"Location {i}",
                portals=[Portal.RIGHTMOVE],
                min_price=1500
            )
            
            profile = SavedSearchProfile(
                name=f"profile_{i}",
                search=search_config
            )
            
            profiles.append(profile)
        
        config = AdvancedSearchConfig(
            profiles=profiles,
            concurrent_searches=2,  # Limit concurrency
            save_to_database=False
        )
        
        executor = ConfigExecutor(config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            result = await executor.execute()
            
            # Should execute all profiles
            assert mock_search.call_count == 3
            assert len(result) == 6  # 2 properties × 3 profiles
    
    @pytest.mark.asyncio
    async def test_delay_between_searches(self, test_config, mock_properties):
        """Test delay between searches"""
        # Enable delay
        test_config.delay_between_searches = 0.1  # 100ms for testing
        
        # Add multi-location to trigger delays
        from homehunt.config.models import MultiLocationConfig
        
        multi_location = MultiLocationConfig(
            name="Delay Test",
            locations=["Location A", "Location B"]
        )
        
        test_config.profiles[0].multi_location = multi_location
        
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            import time
            start_time = time.time()
            
            await executor.execute()
            
            end_time = time.time()
            
            # Should have taken at least the delay time
            assert end_time - start_time >= 0.1
    
    @pytest.mark.asyncio
    async def test_metadata_update(self, test_config, mock_properties):
        """Test profile metadata updates"""
        profile = test_config.profiles[0]
        initial_runs = profile.total_runs
        
        executor = ConfigExecutor(test_config)
        
        with patch('homehunt.cli.search_command.search_properties') as mock_search:
            mock_search.return_value = mock_properties
            
            await executor.execute()
            
            # Metadata should be updated
            assert profile.total_runs == initial_runs + 1
            assert profile.last_run is not None