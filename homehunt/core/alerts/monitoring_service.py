"""
Property monitoring service for continuous incremental syncing
Tracks new properties, price changes, and sends alerts via Telegram
"""

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from rich.console import Console
from structlog import get_logger

from homehunt.core.db import Database
from homehunt.core.models import PropertyListing

if TYPE_CHECKING:
    from homehunt.config.executor import ConfigExecutor
    from homehunt.config.models import AdvancedSearchConfig, NotificationConfig
    from homehunt.core.alerts.telegram_bot import TelegramBot

logger = get_logger()
console = Console()


class PropertyMonitor:
    """Monitors properties for changes and sends alerts"""

    def __init__(
        self,
        database: Database,
        telegram_bot: "TelegramBot | None" = None,
        config: "NotificationConfig | None" = None,
    ):
        """Initialize property monitor"""
        from homehunt.config.models import NotificationConfig
        
        self.db = database
        self.bot = telegram_bot
        self.config = config or NotificationConfig()
        self.is_running = False
        self._last_check_time: datetime | None = None
        self._property_cache: dict[str, PropertyListing] = {}
        self._alerted_properties: set[str] = set()
        self._alerted_changes: set[tuple[str, str]] = (
            set()
        )  # (property_id, change_type)

    async def start_monitoring(
        self,
        check_interval: int = 300,  # 5 minutes
        search_config: "AdvancedSearchConfig | None" = None,
    ) -> None:
        """Start continuous monitoring loop"""
        self.is_running = True
        logger.info("property_monitoring_started", check_interval=check_interval)

        # Initialize bot if configured
        if self.bot and self.config.enabled:
            await self.bot.start()
            await self.bot.bot.send_message(
                chat_id=self.bot.chat_id,
                text="🚀 Property monitoring started! I'll alert you about new listings and changes.",
            )

        while self.is_running:
            try:
                # Check for changes
                new_properties, changed_properties = await self._check_for_changes()

                # Send alerts
                if self.config.enabled and self.bot:
                    await self._send_alerts(new_properties, changed_properties)

                # Run scheduled searches if config provided
                if search_config:
                    await self._run_scheduled_searches(search_config)

                # Send summaries if scheduled
                await self._check_send_summaries()

                # Update last check time
                self._last_check_time = datetime.utcnow()

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error("monitoring_error", error=str(e))
                await asyncio.sleep(60)  # Wait a minute before retrying

    async def stop_monitoring(self) -> None:
        """Stop monitoring gracefully"""
        self.is_running = False

        if self.bot:
            await self.bot.bot.send_message(
                chat_id=self.bot.chat_id, text="🛑 Property monitoring stopped."
            )
            await self.bot.stop()

        logger.info("property_monitoring_stopped")

    async def _check_for_changes(
        self,
    ) -> tuple[list[PropertyListing], list[PropertyListing]]:
        """Check database for new properties and changes"""
        new_properties = []
        changed_properties = []

        # Get recent properties
        since_time = self._last_check_time or datetime.utcnow() - timedelta(hours=1)

        # Query for properties updated since last check
        recent_properties = await self.db.get_properties_since(since_time)

        for property in recent_properties:
            property_id = property.property_id

            # Check if it's a new property
            if property_id not in self._property_cache:
                if property_id not in self._alerted_properties:
                    new_properties.append(property)
                    self._alerted_properties.add(property_id)
            else:
                # Check for changes
                cached = self._property_cache[property_id]
                changes = self._detect_changes(cached, property)

                if changes:
                    # Check if we haven't alerted about this specific change
                    change_key = (property_id, ",".join(changes))
                    if change_key not in self._alerted_changes:
                        changed_properties.append(property)
                        self._alerted_changes.add(change_key)

            # Update cache
            self._property_cache[property_id] = property

        logger.info(
            "changes_detected",
            new_count=len(new_properties),
            changed_count=len(changed_properties),
        )

        return new_properties, changed_properties

    def _detect_changes(self, old: PropertyListing, new: PropertyListing) -> list[str]:
        """Detect what changed between two property versions"""
        changes = []

        # Price change
        if old.price != new.price:
            changes.append("price")

        # Status change
        if old.is_active != new.is_active:
            changes.append("status")

        # Availability date change
        if old.available_from != new.available_from:
            changes.append("availability")

        return changes

    async def _send_alerts(
        self,
        new_properties: list[PropertyListing],
        changed_properties: list[PropertyListing],
    ) -> None:
        """Send alerts for new and changed properties"""

        # Send new property alerts
        if self.config.new_properties and new_properties:
            for property in new_properties:
                await self.bot.send_property_alert(property, alert_type="new")
                await asyncio.sleep(1)  # Rate limiting

        # Send change alerts
        if self.config.price_changes and changed_properties:
            for property in changed_properties:
                # Determine change type
                alert_type = (
                    "price_change"  # Could be enhanced to detect specific change
                )
                await self.bot.send_property_alert(property, alert_type=alert_type)
                await asyncio.sleep(1)  # Rate limiting

    async def _run_scheduled_searches(self, config: "AdvancedSearchConfig") -> None:
        """Run scheduled searches from configuration"""
        from homehunt.config.executor import ConfigExecutor
        
        # Check if any profiles have scheduled execution
        for profile in config.profiles:
            if profile.schedule_enabled and self._should_run_profile(profile):
                logger.info("running_scheduled_search", profile=profile.name)

                # Execute the search
                executor = ConfigExecutor(config)
                results = await executor.execute_profile(profile)

                # Update last run time
                profile.last_run = datetime.utcnow()
                profile.total_runs += 1

                logger.info(
                    "scheduled_search_completed",
                    profile=profile.name,
                    results=len(results),
                )

    def _should_run_profile(self, profile) -> bool:
        """Check if a profile should run based on schedule"""
        if not profile.schedule_cron:
            return False

        # Simple implementation - could be enhanced with proper cron parsing
        # For now, just check if enough time has passed
        if not profile.last_run:
            return True

        # Example: Run every hour
        time_since_last = datetime.utcnow() - profile.last_run
        return time_since_last.total_seconds() > 3600

    async def _check_send_summaries(self) -> None:
        """Check if it's time to send daily/weekly summaries"""
        now = datetime.utcnow()

        # Daily summary (send at 9 AM UTC)
        if self.config.daily_summary and now.hour == 9 and now.minute < 5:
            if (
                not hasattr(self, "_last_daily_summary")
                or (now - self._last_daily_summary).days >= 1
            ):
                await self._send_daily_summary()
                self._last_daily_summary = now

        # Weekly summary (send on Monday at 9 AM UTC)
        if (
            self.config.weekly_summary
            and now.weekday() == 0
            and now.hour == 9
            and now.minute < 5
        ):
            if (
                not hasattr(self, "_last_weekly_summary")
                or (now - self._last_weekly_summary).days >= 7
            ):
                await self._send_weekly_summary()
                self._last_weekly_summary = now

    async def _send_daily_summary(self) -> None:
        """Send daily summary of properties"""
        # Get properties from last 24 hours
        since = datetime.utcnow() - timedelta(days=1)
        properties = await self.db.get_properties_since(since)

        if properties and self.bot:
            await self.bot.send_batch_alert(properties, summary_type="daily")
            logger.info("daily_summary_sent", property_count=len(properties))

    async def _send_weekly_summary(self) -> None:
        """Send weekly summary of properties"""
        # Get properties from last 7 days
        since = datetime.utcnow() - timedelta(days=7)
        properties = await self.db.get_properties_since(since)

        if properties and self.bot:
            await self.bot.send_batch_alert(properties, summary_type="weekly")
            logger.info("weekly_summary_sent", property_count=len(properties))


class MonitoringService:
    """High-level service for managing property monitoring"""

    def __init__(self, database: Database):
        """Initialize monitoring service"""
        self.db = database
        self.monitor: PropertyMonitor | None = None
        self.bot: "TelegramBot | None" = None

    async def initialize(self, config: "NotificationConfig") -> None:
        """Initialize monitoring with configuration"""
        from homehunt.core.alerts.telegram_bot import TelegramBot
        
        if config.enabled and config.telegram_bot_token:
            # Create Telegram bot
            self.bot = TelegramBot(config)
            await self.bot.initialize()

            # Create monitor
            self.monitor = PropertyMonitor(
                database=self.db, telegram_bot=self.bot, config=config
            )

            logger.info("monitoring_service_initialized")
        else:
            logger.warning(
                "monitoring_disabled",
                enabled=config.enabled,
                has_token=bool(config.telegram_bot_token),
            )

    async def start(
        self,
        check_interval: int = 300,
        search_config: "AdvancedSearchConfig | None" = None,
    ) -> None:
        """Start monitoring service"""
        if self.monitor:
            # Run in background
            asyncio.create_task(
                self.monitor.start_monitoring(check_interval, search_config)
            )
        else:
            logger.error("monitoring_not_initialized")

    async def stop(self) -> None:
        """Stop monitoring service"""
        if self.monitor:
            await self.monitor.stop_monitoring()

    async def send_test_message(self) -> bool:
        """Send a test message to verify bot configuration"""
        if self.bot:
            try:
                await self.bot.bot.send_message(
                    chat_id=self.bot.chat_id,
                    text="✅ HomeHunt bot is configured correctly! You'll receive property alerts here.",
                )
                return True
            except Exception as e:
                logger.error("test_message_failed", error=str(e))
                return False
        return False
