"""
Tests for Telegram bot functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homehunt.config.models import NotificationConfig
from homehunt.core.alerts import TelegramBot, AlertService, MonitoringService
from homehunt.core.models import PropertyListing, Portal
from homehunt.core.db import Database


@pytest.fixture
def notification_config():
    """Create test notification config"""
    return NotificationConfig(
        enabled=True,
        telegram_bot_token="test_token_123",
        telegram_chat_id="123456789",
        new_properties=True,
        price_changes=True,
        immediate_alerts=True,
    )


@pytest.fixture
def sample_property():
    """Create sample property for testing"""
    return PropertyListing(
        portal=Portal.RIGHTMOVE,
        property_id="rm_123",
        url="https://rightmove.co.uk/property/123",
        title="Beautiful 2 bed flat",
        price="£1,500",
        price_numeric=150000,
        location="London E14",
        bedrooms=2,
        bathrooms=1,
        property_type="flat",
        latitude=51.5074,
        longitude=-0.1278,
        parking=True,
        garden=False,
        pets_allowed=True,
        description="A lovely flat in Canary Wharf",
    )


@pytest.mark.asyncio
async def test_telegram_bot_initialization(notification_config):
    """Test Telegram bot initialization"""
    bot = TelegramBot(notification_config)
    
    assert bot.bot_token == "test_token_123"
    assert bot.chat_id == "123456789"
    assert bot.config == notification_config
    assert not bot.is_running


@pytest.mark.asyncio
async def test_telegram_bot_message_formatting(notification_config, sample_property):
    """Test property message formatting"""
    bot = TelegramBot(notification_config)
    
    # Test new property message
    message = bot._format_property_message(sample_property, "new")
    
    assert "🆕" in message
    assert "Beautiful 2 bed flat" in message
    assert "£1,500/month" in message
    assert "London E14" in message
    assert "2 bed" in message
    assert "🚗 Parking" in message
    assert "🐕 Pets OK" in message
    assert "View on Map" in message
    assert sample_property.url in message


@pytest.mark.asyncio
async def test_batch_message_formatting(notification_config, sample_property):
    """Test batch message formatting"""
    bot = TelegramBot(notification_config)
    
    properties = [sample_property, sample_property]  # Two properties for testing
    message = bot._format_batch_message(properties, "daily")
    
    assert "📊 Daily Summary" in message
    assert "Found 2 properties" in message
    assert "London E14" in message
    assert "£1,500" in message


@pytest.mark.asyncio
async def test_alert_service_initialization(notification_config):
    """Test alert service initialization"""
    db = MagicMock(spec=Database)
    alert_service = AlertService(db)
    
    with patch.object(MonitoringService, 'initialize', new=AsyncMock()) as mock_init:
        await alert_service.initialize(notification_config)
        
        assert alert_service.config == notification_config
        mock_init.assert_called_once_with(notification_config)


@pytest.mark.asyncio
async def test_alert_service_send_immediate_alert(notification_config, sample_property):
    """Test sending immediate alert"""
    db = MagicMock(spec=Database)
    alert_service = AlertService(db)
    alert_service.config = notification_config
    
    # Mock the bot
    mock_bot = AsyncMock(spec=TelegramBot)
    mock_bot.send_property_alert = AsyncMock(return_value=True)
    alert_service.bot = mock_bot
    
    result = await alert_service.send_immediate_alert(sample_property)
    
    assert result is True
    mock_bot.send_property_alert.assert_called_once_with(sample_property, alert_type="new")


@pytest.mark.asyncio
async def test_alert_service_notify_new_properties(notification_config, sample_property):
    """Test notifying about new properties"""
    db = MagicMock(spec=Database)
    alert_service = AlertService(db)
    alert_service.config = notification_config
    
    # Mock the bot
    mock_bot = AsyncMock(spec=TelegramBot)
    mock_bot.send_property_alert = AsyncMock(return_value=True)
    alert_service.bot = mock_bot
    
    properties = [sample_property]
    await alert_service.notify_new_properties(properties)
    
    mock_bot.send_property_alert.assert_called_once_with(sample_property, alert_type="new")


@pytest.mark.asyncio
async def test_monitoring_service_initialization(notification_config):
    """Test monitoring service initialization"""
    db = MagicMock(spec=Database)
    monitoring_service = MonitoringService(db)
    
    with patch('homehunt.core.alerts.monitoring_service.TelegramBot') as mock_bot_class:
        mock_bot = AsyncMock(spec=TelegramBot)
        mock_bot_class.return_value = mock_bot
        
        await monitoring_service.initialize(notification_config)
        
        assert monitoring_service.bot is not None
        assert monitoring_service.monitor is not None
        mock_bot.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_monitoring_service_send_test_message(notification_config):
    """Test sending test message"""
    db = MagicMock(spec=Database)
    monitoring_service = MonitoringService(db)
    
    # Mock bot
    mock_bot = AsyncMock(spec=TelegramBot)
    mock_bot.bot = AsyncMock()
    mock_bot.bot.send_message = AsyncMock()
    mock_bot.chat_id = "123456789"
    monitoring_service.bot = mock_bot
    
    result = await monitoring_service.send_test_message()
    
    assert result is True
    mock_bot.bot.send_message.assert_called_once()
    call_args = mock_bot.bot.send_message.call_args
    assert call_args[1]['chat_id'] == "123456789"
    assert "HomeHunt bot is configured correctly" in call_args[1]['text']


@pytest.mark.asyncio
async def test_property_keyboard_creation(notification_config, sample_property):
    """Test inline keyboard creation for properties"""
    bot = TelegramBot(notification_config)
    
    keyboard = bot._create_property_keyboard(sample_property)
    
    # Should have 2 rows
    assert len(keyboard.inline_keyboard) == 2
    
    # First row should have View Property and Map buttons
    first_row = keyboard.inline_keyboard[0]
    assert len(first_row) == 2
    assert first_row[0].text == "🔗 View Property"
    assert first_row[0].url == sample_property.url
    assert first_row[1].text == "🗺 Map"
    
    # Second row should have Save and Hide buttons
    second_row = keyboard.inline_keyboard[1]
    assert len(second_row) == 2
    assert second_row[0].text == "⭐ Save"
    assert second_row[0].callback_data == f"save_{sample_property.property_id}"
    assert second_row[1].text == "🚫 Hide"
    assert second_row[1].callback_data == f"hide_{sample_property.property_id}"