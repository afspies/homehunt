"""
Telegram Bot integration for HomeHunt
Provides real-time property alerts and bot command handling
"""

import asyncio

from rich.console import Console
from structlog import get_logger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from homehunt.config.models import NotificationConfig
from homehunt.core.models import PropertyListing

logger = get_logger()
console = Console()


class TelegramBot:
    """Telegram bot for property alerts and user interaction"""

    def __init__(self, config: NotificationConfig):
        """Initialize Telegram bot with configuration"""
        self.config = config
        self.bot_token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.application: Application | None = None
        self.bot: Bot | None = None
        self.is_running = False
        self.active_subscriptions: set[str] = set()

    async def initialize(self) -> None:
        """Initialize the bot application"""
        try:
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot

            # Register command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(
                CommandHandler("subscribe", self.cmd_subscribe)
            )
            self.application.add_handler(
                CommandHandler("unsubscribe", self.cmd_unsubscribe)
            )
            self.application.add_handler(
                CommandHandler("list", self.cmd_list_subscriptions)
            )
            self.application.add_handler(
                CommandHandler("recent", self.cmd_recent_properties)
            )
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))

            # Register callback query handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(self.handle_callback))

            # Initialize application
            await self.application.initialize()
            await self.application.start()

            logger.info(
                "telegram_bot_initialized",
                bot_username=(await self.bot.get_me()).username,
            )

        except Exception as e:
            logger.error("telegram_bot_initialization_failed", error=str(e))
            raise

    async def start(self) -> None:
        """Start the bot polling"""
        if not self.application:
            await self.initialize()

        self.is_running = True
        logger.info("telegram_bot_started")

        # Start polling
        await self.application.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Stop the bot gracefully"""
        if self.application and self.is_running:
            self.is_running = False
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("telegram_bot_stopped")

    async def send_property_alert(
        self, property: PropertyListing, alert_type: str = "new"
    ) -> bool:
        """Send a property alert to the configured chat"""
        try:
            message = self._format_property_message(property, alert_type)
            keyboard = self._create_property_keyboard(property)

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

            logger.info(
                "property_alert_sent",
                property_id=property.property_id,
                alert_type=alert_type,
            )
            return True

        except Exception as e:
            logger.error(
                "property_alert_failed", property_id=property.property_id, error=str(e)
            )
            return False

    async def send_batch_alert(
        self, properties: list[PropertyListing], summary_type: str = "daily"
    ) -> bool:
        """Send a batch alert for multiple properties"""
        try:
            if not properties:
                return True

            message = self._format_batch_message(properties, summary_type)

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

            # Send individual property details if not too many
            if len(properties) <= 5:
                for prop in properties:
                    await asyncio.sleep(0.5)  # Rate limiting
                    await self.send_property_alert(prop, alert_type="summary")

            logger.info(
                "batch_alert_sent",
                property_count=len(properties),
                summary_type=summary_type,
            )
            return True

        except Exception as e:
            logger.error("batch_alert_failed", error=str(e))
            return False

    def _format_property_message(
        self, property: PropertyListing, alert_type: str
    ) -> str:
        """Format a property listing for Telegram message"""
        emoji_map = {
            "new": "🆕",
            "price_change": "💷",
            "status_change": "🔄",
            "summary": "📍",
        }

        emoji = emoji_map.get(alert_type, "🏠")

        # Build message with HTML formatting
        message = f"<b>{emoji} {property.title}</b>\n\n"

        # Price information
        message += f"💰 <b>£{property.price:,}/month</b>"
        if alert_type == "price_change" and property.price_history:
            # Get previous price from history
            message += f" (was £{property.price_history[-1]:,})"
        message += "\n\n"

        # Location
        message += f"📍 {property.location}\n"
        if property.latitude and property.longitude:
            message += f"🗺 <a href='https://maps.google.com/?q={property.latitude},{property.longitude}'>View on Map</a>\n"

        # Property details
        message += f"\n🛏 {property.bedrooms} bed"
        if property.bathrooms:
            message += f" • 🚿 {property.bathrooms} bath"
        if property.property_type:
            message += f" • 🏠 {property.property_type}"
        message += "\n"

        # Features
        features = []
        if property.parking:
            features.append("🚗 Parking")
        if property.garden:
            features.append("🌳 Garden")
        if property.balcony:
            features.append("🏙 Balcony")
        if property.pets_allowed:
            features.append("🐕 Pets OK")

        if features:
            message += f"\n✨ {' • '.join(features)}\n"

        # Availability
        if property.available_from:
            message += f"\n📅 Available from: {property.available_from}\n"

        # Description preview
        if property.description:
            desc_preview = property.description[:150]
            if len(property.description) > 150:
                desc_preview += "..."
            message += f"\n📝 {desc_preview}\n"

        # Link
        message += f"\n🔗 <a href='{property.url}'>View Property</a>"

        # Metadata
        message += (
            f"\n\n<i>Listed on {property.source} • ID: {property.property_id}</i>"
        )

        return message

    def _format_batch_message(
        self, properties: list[PropertyListing], summary_type: str
    ) -> str:
        """Format a batch of properties for summary message"""
        emoji = "📊" if summary_type == "daily" else "📈"

        message = f"<b>{emoji} {summary_type.title()} Summary</b>\n"
        message += f"Found {len(properties)} properties\n\n"

        # Group by location
        by_location: dict[str, list[PropertyListing]] = {}
        for prop in properties:
            location = prop.location.split(",")[0]  # Get main area
            if location not in by_location:
                by_location[location] = []
            by_location[location].append(prop)

        # Summary by location
        for location, props in by_location.items():
            message += f"📍 <b>{location}</b> ({len(props)} properties)\n"

            # Price range
            prices = [p.price for p in props]
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)

            message += f"   💰 £{min_price:,} - £{max_price:,}/month"
            message += f" (avg: £{avg_price:,.0f})\n"

            # Bedroom breakdown
            bedroom_counts = {}
            for prop in props:
                beds = prop.bedrooms
                bedroom_counts[beds] = bedroom_counts.get(beds, 0) + 1

            bed_summary = []
            for beds, count in sorted(bedroom_counts.items()):
                bed_summary.append(f"{beds}-bed: {count}")
            message += f"   🛏 {', '.join(bed_summary)}\n\n"

        return message

    def _create_property_keyboard(
        self, property: PropertyListing
    ) -> InlineKeyboardMarkup:
        """Create inline keyboard for property actions"""
        keyboard = []

        # First row: View and Map
        row1 = [InlineKeyboardButton("🔗 View Property", url=property.url)]
        if property.latitude and property.longitude:
            map_url = (
                f"https://maps.google.com/?q={property.latitude},{property.longitude}"
            )
            row1.append(InlineKeyboardButton("🗺 Map", url=map_url))
        keyboard.append(row1)

        # Second row: Actions
        row2 = [
            InlineKeyboardButton(
                "⭐ Save", callback_data=f"save_{property.property_id}"
            ),
            InlineKeyboardButton(
                "🚫 Hide", callback_data=f"hide_{property.property_id}"
            ),
        ]
        keyboard.append(row2)

        return InlineKeyboardMarkup(keyboard)

    # Command handlers
    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command"""
        welcome_message = """
🏠 <b>Welcome to HomeHunt Bot!</b>

I'll help you find your perfect property by sending real-time alerts when new listings match your criteria.

<b>Available Commands:</b>
/help - Show all commands
/status - Check bot status
/subscribe - Manage alert subscriptions
/recent - Show recent properties
/stats - View search statistics

<b>Getting Started:</b>
1. Set up your search criteria in the HomeHunt CLI
2. Enable notifications in your config
3. I'll alert you when new properties are found!

Ready to find your dream home? 🎯
        """

        await update.message.reply_text(welcome_message, parse_mode="HTML")

    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command"""
        help_message = """
<b>🤖 HomeHunt Bot Commands</b>

<b>Basic Commands:</b>
/start - Welcome message
/help - This help message
/status - Check bot and search status

<b>Subscription Management:</b>
/subscribe - Subscribe to property alerts
/unsubscribe - Unsubscribe from alerts
/list - List active subscriptions

<b>Property Commands:</b>
/recent - Show recent properties
/stats - View search statistics

<b>Alert Types:</b>
• 🆕 New Properties - Immediate alerts
• 💷 Price Changes - When prices drop
• 📊 Daily Summary - Daily digest
• 📈 Weekly Report - Weekly overview

<b>Tips:</b>
• Use inline buttons to save or hide properties
• Click map links to view property locations
• Configure search criteria via HomeHunt CLI
        """

        await update.message.reply_text(help_message, parse_mode="HTML")

    async def cmd_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command"""
        status = "🟢 Active" if self.is_running else "🔴 Inactive"

        message = f"""
<b>🤖 Bot Status</b>

Status: {status}
Chat ID: <code>{update.effective_chat.id}</code>
Subscriptions: {len(self.active_subscriptions)}

<b>Notification Settings:</b>
• New Properties: {'✅' if self.config.new_properties else '❌'}
• Price Changes: {'✅' if self.config.price_changes else '❌'}
• Daily Summary: {'✅' if self.config.daily_summary else '❌'}
• Weekly Summary: {'✅' if self.config.weekly_summary else '❌'}
        """

        await update.message.reply_text(message, parse_mode="HTML")

    async def cmd_subscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /subscribe command"""
        # This would integrate with the configuration system
        await update.message.reply_text(
            "🔔 To manage subscriptions, please use the HomeHunt CLI:\n"
            "<code>homehunt bot-config</code>",
            parse_mode="HTML",
        )

    async def cmd_unsubscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /unsubscribe command"""
        await update.message.reply_text(
            "🔕 To unsubscribe, please use the HomeHunt CLI:\n"
            "<code>homehunt bot-config</code>",
            parse_mode="HTML",
        )

    async def cmd_list_subscriptions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /list command"""
        if not self.active_subscriptions:
            await update.message.reply_text("📭 No active subscriptions")
            return

        message = "<b>📬 Active Subscriptions</b>\n\n"
        for sub in self.active_subscriptions:
            message += f"• {sub}\n"

        await update.message.reply_text(message, parse_mode="HTML")

    async def cmd_recent_properties(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /recent command"""
        # This would fetch from database
        await update.message.reply_text(
            "📋 To view recent properties, please use the HomeHunt CLI:\n"
            "<code>homehunt list --limit 10</code>",
            parse_mode="HTML",
        )

    async def cmd_stats(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /stats command"""
        # This would fetch from database
        await update.message.reply_text(
            "📊 To view statistics, please use the HomeHunt CLI:\n"
            "<code>homehunt stats</code>",
            parse_mode="HTML",
        )

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        if data.startswith("save_"):
            property_id = data.replace("save_", "")
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"⭐ Property {property_id} saved!")

        elif data.startswith("hide_"):
            property_id = data.replace("hide_", "")
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"🚫 Property {property_id} hidden!")
