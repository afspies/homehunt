"""
Alert service for managing property notifications
Integrates with Telegram bot and monitoring service
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from structlog import get_logger

from homehunt.core.db import Database
from homehunt.core.models import PropertyListing

if TYPE_CHECKING:
    from homehunt.config.models import NotificationConfig
    from homehunt.core.alerts.monitoring_service import MonitoringService
    from homehunt.core.alerts.telegram_bot import TelegramBot

logger = get_logger()


class AlertService:
    """Main service for handling all property alerts"""

    def __init__(self, database: Database):
        """Initialize alert service"""
        from homehunt.core.alerts.monitoring_service import MonitoringService
        
        self.db = database
        self.monitoring_service = MonitoringService(database)
        self.bot: TelegramBot | None = None
        self.config: NotificationConfig | None = None

    async def initialize(self, config: NotificationConfig) -> None:
        """Initialize alert service with configuration"""
        self.config = config

        if config.enabled and config.telegram_bot_token:
            # Initialize monitoring service
            await self.monitoring_service.initialize(config)
            self.bot = self.monitoring_service.bot

            logger.info("alert_service_initialized")
        else:
            logger.info("alert_service_disabled")

    async def send_immediate_alert(self, property: PropertyListing) -> bool:
        """Send immediate alert for a single property"""
        if not self.config or not self.config.immediate_alerts:
            return False

        if self.bot:
            return await self.bot.send_property_alert(property, alert_type="new")

        return False

    async def send_batch_alert(self, properties: list[PropertyListing]) -> bool:
        """Send alert for multiple properties"""
        if not self.config or not self.bot:
            return False

        return await self.bot.send_batch_alert(properties, summary_type="batch")

    async def notify_new_properties(self, properties: list[PropertyListing]) -> None:
        """Notify about new properties found during search"""
        if not self.config or not self.config.enabled:
            return

        if self.config.immediate_alerts and self.bot:
            for property in properties:
                await self.send_immediate_alert(property)

        logger.info("new_properties_notified", count=len(properties))

    async def notify_price_change(
        self, property: PropertyListing, old_price: int, new_price: int
    ) -> None:
        """Notify about a price change"""
        if not self.config or not self.config.price_changes:
            return

        if self.bot:
            # Add price change info to property
            property.price_history = property.price_history or []
            property.price_history.append(old_price)

            await self.bot.send_property_alert(property, alert_type="price_change")

        logger.info(
            "price_change_notified",
            property_id=property.property_id,
            old_price=old_price,
            new_price=new_price,
        )

    async def test_connection(self) -> bool:
        """Test the alert connection"""
        if self.monitoring_service:
            return await self.monitoring_service.send_test_message()
        return False

    async def start_monitoring(self, check_interval: int = 300) -> None:
        """Start continuous monitoring"""
        if self.monitoring_service:
            await self.monitoring_service.start(check_interval)

    async def stop_monitoring(self) -> None:
        """Stop monitoring"""
        if self.monitoring_service:
            await self.monitoring_service.stop()
