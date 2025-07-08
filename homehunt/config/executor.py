"""
Configuration execution service for HomeHunt
Handles running searches based on advanced configuration files
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress

from homehunt.cli.search_command import search_properties
from homehunt.core.db import Database
from homehunt.core.models import PropertyListing
from homehunt.traveltime.service import TravelTimeService
from homehunt.traveltime.client import TravelTimeClient

from .models import AdvancedSearchConfig, SavedSearchProfile

console = Console()


class ConfigExecutorError(Exception):
    """Configuration execution error"""
    pass


class ConfigExecutor:
    """Executes searches based on configuration files"""
    
    def __init__(self, config: AdvancedSearchConfig):
        """
        Initialize executor with configuration
        
        Args:
            config: Advanced search configuration
        """
        self.config = config
        self.db: Optional[Database] = None
        self.traveltime_service: Optional[TravelTimeService] = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize required services"""
        if self.config.save_to_database:
            self.db = Database()
        
        # Initialize TravelTime service if commute filters are present
        has_commute_filters = (
            self.config.global_commute_filters or
            any(p.commute_filters for p in self.config.profiles)
        )
        
        if has_commute_filters:
            try:
                traveltime_client = TravelTimeClient()
                self.traveltime_service = TravelTimeService(self.db or Database(), traveltime_client)
            except ValueError:
                console.print("[yellow]Warning: TravelTime API not configured, skipping commute filtering[/yellow]")
    
    async def execute(
        self,
        profile_names: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> List[PropertyListing]:
        """
        Execute searches based on configuration
        
        Args:
            profile_names: Specific profile names to run (all if None)
            dry_run: If True, show what would be done without executing
            
        Returns:
            List of found properties
            
        Raises:
            ConfigExecutorError: If execution fails
        """
        try:
            # Filter profiles
            profiles_to_run = self._filter_profiles(profile_names)
            
            if not profiles_to_run:
                raise ConfigExecutorError("No profiles to execute")
            
            if dry_run:
                return self._dry_run_summary(profiles_to_run)
            
            # Execute searches
            all_properties = await self._execute_searches(profiles_to_run)
            
            # Apply global post-processing
            all_properties = await self._apply_global_processing(all_properties)
            
            # Update profile metadata
            await self._update_profile_metadata(profiles_to_run)
            
            return all_properties
            
        except Exception as e:
            raise ConfigExecutorError(f"Execution failed: {e}")
        finally:
            await self._cleanup()
    
    def _filter_profiles(self, profile_names: Optional[List[str]]) -> List[SavedSearchProfile]:
        """Filter profiles based on names"""
        if profile_names:
            profiles = [p for p in self.config.profiles if p.name in profile_names]
            missing = set(profile_names) - {p.name for p in profiles}
            if missing:
                console.print(f"[yellow]Warning: Profiles not found: {', '.join(missing)}[/yellow]")
        else:
            profiles = self.config.profiles
        
        return profiles
    
    def _dry_run_summary(self, profiles: List[SavedSearchProfile]) -> List[PropertyListing]:
        """Show dry run summary"""
        console.print(f"[yellow]DRY RUN - {len(profiles)} profile(s) would be executed:[/yellow]")
        
        for profile in profiles:
            console.print(f"  • {profile.name}")
            console.print(f"    Location: {profile.search.location}")
            
            if profile.multi_location:
                console.print(f"    Multi-location: {len(profile.multi_location.locations)} locations")
            
            if profile.commute_filters:
                console.print(f"    Commute filters: {len(profile.commute_filters)}")
            
            if profile.auto_export:
                console.print(f"    Auto-export: {', '.join(profile.export_formats or [])}")
        
        return []
    
    async def _execute_searches(self, profiles: List[SavedSearchProfile]) -> List[PropertyListing]:
        """Execute searches for all profiles"""
        all_properties = []
        semaphore = asyncio.Semaphore(self.config.concurrent_searches)
        
        async def run_profile(profile: SavedSearchProfile) -> List[PropertyListing]:
            """Run search for single profile"""
            async with semaphore:
                try:
                    properties = await self._execute_single_profile(profile)
                    console.print(f"[green]✓ {profile.name}: {len(properties)} properties[/green]")
                    return properties
                except Exception as e:
                    console.print(f"[red]✗ {profile.name}: {e}[/red]")
                    return []
        
        # Execute with progress tracking
        with Progress(console=console) as progress:
            task = progress.add_task("Executing searches...", total=len(profiles))
            
            tasks = [run_profile(profile) for profile in profiles]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_properties.extend(result)
                progress.advance(task)
        
        return all_properties
    
    async def _execute_single_profile(self, profile: SavedSearchProfile) -> List[PropertyListing]:
        """Execute search for a single profile"""
        properties = []
        
        if profile.multi_location:
            # Multi-location search
            for location in profile.multi_location.locations:
                location_config = profile.search.model_copy()
                location_config.location = location
                
                # Apply location overrides
                if (profile.multi_location.location_overrides and 
                    location in profile.multi_location.location_overrides):
                    overrides = profile.multi_location.location_overrides[location]
                    for key, value in overrides.items():
                        if hasattr(location_config, key):
                            setattr(location_config, key, value)
                
                # Limit results per location
                if profile.multi_location.max_results_per_location:
                    location_config.max_results = profile.multi_location.max_results_per_location
                
                # Execute search
                location_properties = await search_properties(
                    location_config,
                    save_to_db=self.config.save_to_database,
                    output_file=None,
                    show_progress=False
                )
                
                properties.extend(location_properties)
                
                # Delay between locations
                if self.config.delay_between_searches > 0:
                    await asyncio.sleep(self.config.delay_between_searches)
        else:
            # Single location search
            properties = await search_properties(
                profile.search,
                save_to_db=self.config.save_to_database,
                output_file=None,
                show_progress=False
            )
        
        # Apply profile-specific processing
        properties = await self._apply_profile_processing(profile, properties)
        
        return properties
    
    async def _apply_profile_processing(
        self, 
        profile: SavedSearchProfile, 
        properties: List[PropertyListing]
    ) -> List[PropertyListing]:
        """Apply profile-specific processing"""
        
        # Apply commute filtering
        if profile.commute_filters and self.traveltime_service:
            properties = await self._apply_commute_filtering(profile.commute_filters, properties)
        
        # Apply scoring
        if profile.enable_scoring and profile.score_weights:
            properties = self._apply_scoring(profile.score_weights, properties)
        
        # Handle exports
        if profile.auto_export and profile.export_formats:
            await self._handle_exports(profile, properties)
        
        return properties
    
    async def _apply_global_processing(self, properties: List[PropertyListing]) -> List[PropertyListing]:
        """Apply global processing to all properties"""
        
        # Apply global commute filtering
        if self.config.global_commute_filters and self.traveltime_service:
            properties = await self._apply_commute_filtering(
                self.config.global_commute_filters, 
                properties
            )
        
        # Deduplicate across profiles
        if self.config.deduplicate_across_profiles:
            initial_count = len(properties)
            properties = self._deduplicate_properties(properties)
            dedup_count = initial_count - len(properties)
            if dedup_count > 0:
                console.print(f"[blue]Removed {dedup_count} duplicate properties[/blue]")
        
        return properties
    
    async def _apply_commute_filtering(
        self, 
        commute_filters: List, 
        properties: List[PropertyListing]
    ) -> List[PropertyListing]:
        """Apply commute filtering to properties"""
        if not self.traveltime_service:
            return properties
        
        filtered_properties = properties
        
        for commute_filter in commute_filters:
            # Apply each commute filter
            try:
                filtered_properties = await self.traveltime_service.filter_by_commute(
                    properties=filtered_properties,
                    max_commute_time=commute_filter.max_time,
                    transport_mode=commute_filter.transport_modes[0] if commute_filter.transport_modes else "public_transport"
                )
            except Exception as e:
                console.print(f"[yellow]Warning: Commute filtering failed for {commute_filter.destination}: {e}[/yellow]")
        
        return filtered_properties
    
    def _apply_scoring(self, score_weights: dict, properties: List[PropertyListing]) -> List[PropertyListing]:
        """Apply scoring algorithm to properties"""
        for prop in properties:
            score = 0.0
            
            # Price scoring (lower price = higher score)
            if 'price' in score_weights and prop.price:
                try:
                    price_value = float(prop.price.replace('£', '').replace(',', '').replace(' pcm', ''))
                    # Normalize to 0-1 scale (max reasonable price £5000)
                    price_score = max(0, 1 - (price_value / 5000))
                    score += price_score * score_weights['price']
                except (ValueError, AttributeError):
                    pass
            
            # Commute scoring
            if 'commute' in score_weights:
                # Use existing commute data if available
                commute_score = 0.0
                commute_count = 0
                
                for mode in ['public_transport', 'cycling', 'walking', 'driving']:
                    commute_time = getattr(prop, f'commute_{mode}', None)
                    if commute_time:
                        # Normalize to 0-1 scale (max reasonable commute 90 min)
                        mode_score = max(0, 1 - (commute_time / 90))
                        commute_score += mode_score
                        commute_count += 1
                
                if commute_count > 0:
                    commute_score /= commute_count
                    score += commute_score * score_weights['commute']
            
            # Size scoring
            if 'size' in score_weights and prop.bedrooms:
                # Normalize to 0-1 scale (max 4 bedrooms)
                size_score = min(1.0, prop.bedrooms / 4)
                score += size_score * score_weights['size']
            
            # Feature scoring
            if 'features' in score_weights:
                feature_score = 0.0
                feature_count = 0
                
                # Check boolean features
                for feature in ['parking', 'garden', 'balcony']:
                    if hasattr(prop, feature):
                        feature_count += 1
                        if getattr(prop, feature, False):
                            feature_score += 1
                
                if feature_count > 0:
                    feature_score /= feature_count
                    score += feature_score * score_weights['features']
            
            # Store calculated score
            setattr(prop, 'calculated_score', score)
        
        # Sort by score (highest first)
        return sorted(properties, key=lambda p: getattr(p, 'calculated_score', 0), reverse=True)
    
    async def _handle_exports(self, profile: SavedSearchProfile, properties: List[PropertyListing]) -> None:
        """Handle property exports for profile"""
        if not properties:
            return
        
        # Use advanced export configs if available
        if profile.export_configs:
            from homehunt.exports.service import ExportService
            from homehunt.core.db import Database
            export_service = ExportService(self.db or Database())
            
            for export_config in profile.export_configs:
                try:
                    result = await export_service.export_properties(export_config, properties)
                    if result.success:
                        console.print(f"[green]✓ Exported {result.properties_exported} properties via {result.format.value}[/green]")
                        if result.output_location:
                            console.print(f"  Location: {result.output_location}")
                    else:
                        console.print(f"[red]✗ Export failed: {result.error_message}[/red]")
                except Exception as e:
                    console.print(f"[red]Export error: {e}[/red]")
        
        # Fallback to legacy export settings
        elif profile.auto_export and profile.export_formats:
            export_count = len(properties)
            formats = ', '.join(profile.export_formats or [])
            console.print(f"[blue]Note: Would export {export_count} properties to {formats}[/blue]")
            console.print(f"[yellow]Consider upgrading to export_configs for full functionality[/yellow]")
    
    def _deduplicate_properties(self, properties: List[PropertyListing]) -> List[PropertyListing]:
        """Remove duplicate properties based on URL"""
        seen_urls = set()
        deduplicated = []
        
        for prop in properties:
            if prop.url not in seen_urls:
                seen_urls.add(prop.url)
                deduplicated.append(prop)
        
        return deduplicated
    
    async def _update_profile_metadata(self, profiles: List[SavedSearchProfile]) -> None:
        """Update profile execution metadata"""
        current_time = datetime.utcnow()
        
        for profile in profiles:
            profile.last_run = current_time
            profile.total_runs += 1
    
    async def _cleanup(self) -> None:
        """Clean up resources"""
        if self.db:
            await self.db.close()