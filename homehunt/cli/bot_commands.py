"""
Telegram bot management commands for HomeHunt CLI
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from homehunt.config.loader import ConfigLoader
from homehunt.config.models import AdvancedSearchConfig, NotificationConfig
from homehunt.core.alerts import AlertService, MonitoringService
from homehunt.core.db import Database

console = Console()
app = typer.Typer(help="Telegram bot management commands")


@app.command()
async def setup(
    bot_token: str | None = typer.Option(None, "--token", help="Telegram bot token"),
    chat_id: str | None = typer.Option(None, "--chat-id", help="Telegram chat ID"),
    config_file: Path | None = typer.Option(
        None, "--config", help="Configuration file to update"
    ),
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", help="Interactive setup mode"
    ),
):
    """Set up Telegram bot configuration"""
    try:
        # Load existing config if provided
        config = None
        if config_file and config_file.exists():
            config = ConfigLoader.load_config(config_file)
            console.print(f"[green]Loaded configuration from {config_file}[/green]")

        # Interactive mode
        if interactive and not bot_token:
            console.print("\n[bold]HomeHunt Telegram Bot Setup[/bold]\n")
            console.print("To use the Telegram bot, you need:")
            console.print("1. A bot token from @BotFather")
            console.print("2. Your chat ID (you can get this by messaging your bot)\n")

            bot_token = Prompt.ask("Enter your Telegram bot token")

        if interactive and not chat_id:
            chat_id = Prompt.ask("Enter your Telegram chat ID")

        if not bot_token or not chat_id:
            console.print("[red]Bot token and chat ID are required[/red]")
            return

        # Create notification config
        notification_config = NotificationConfig(
            enabled=True,
            telegram_bot_token=bot_token,
            telegram_chat_id=chat_id,
            new_properties=True,
            price_changes=True,
            immediate_alerts=True,
        )

        # Test the connection
        console.print("\n[yellow]Testing bot connection...[/yellow]")
        db = Database()
        alert_service = AlertService(db)
        await alert_service.initialize(notification_config)

        if await alert_service.test_connection():
            console.print("[green]✓ Bot connection successful![/green]")

            # Save config if requested
            if config_file:
                if config:
                    config.global_notifications = notification_config
                else:
                    # Create minimal config
                    from homehunt.cli.config import SearchConfig
                    from homehunt.config.models import SavedSearchProfile

                    config = AdvancedSearchConfig(
                        name="Bot Configuration",
                        global_notifications=notification_config,
                        profiles=[
                            SavedSearchProfile(
                                name="default",
                                search=SearchConfig(
                                    location="London", max_price=2000, min_bedrooms=1
                                ),
                            )
                        ],
                    )

                ConfigLoader.save_config(config, config_file)
                console.print(f"\n[green]Configuration saved to {config_file}[/green]")

            console.print("\n[bold]Next steps:[/bold]")
            console.print("1. Run 'homehunt bot-start' to start monitoring")
            console.print("2. Or add bot config to your search profiles")

        else:
            console.print(
                "[red]✗ Bot connection failed. Please check your token and chat ID.[/red]"
            )

    except Exception as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
async def start(
    config_file: Path = typer.Argument(
        ..., help="Configuration file with bot settings"
    ),
    check_interval: int = typer.Option(
        300, "--interval", help="Check interval in seconds"
    ),
    daemon: bool = typer.Option(False, "--daemon", help="Run as background daemon"),
):
    """Start the Telegram bot for continuous monitoring"""
    try:
        # Load configuration
        config = ConfigLoader.load_config(config_file)

        if not config.global_notifications or not config.global_notifications.enabled:
            console.print("[red]Notifications are not enabled in configuration[/red]")
            console.print("Run 'homehunt bot-setup' to configure the bot")
            return

        # Initialize services
        db = Database()
        await db.create_tables_async()

        monitoring_service = MonitoringService(db)
        await monitoring_service.initialize(config.global_notifications)

        console.print(
            f"[green]Starting bot monitoring (interval: {check_interval}s)...[/green]"
        )
        console.print("Press Ctrl+C to stop\n")

        if daemon:
            console.print("[yellow]Running in daemon mode[/yellow]")
            # In real implementation, would use proper daemonization

        # Start monitoring
        await monitoring_service.start(
            check_interval=check_interval, search_config=config
        )

        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping bot...[/yellow]")
            await monitoring_service.stop()
            console.print("[green]Bot stopped[/green]")

    except Exception as e:
        console.print(f"[red]Failed to start bot: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
async def test(
    config_file: Path | None = typer.Option(
        None, "--config", help="Configuration file"
    ),
    bot_token: str | None = typer.Option(
        None, "--token", help="Bot token (if not in config)"
    ),
    chat_id: str | None = typer.Option(
        None, "--chat-id", help="Chat ID (if not in config)"
    ),
):
    """Test Telegram bot connection and send a test message"""
    try:
        # Get notification config
        notification_config = None

        if config_file and config_file.exists():
            config = ConfigLoader.load_config(config_file)
            notification_config = config.global_notifications

        if not notification_config and bot_token and chat_id:
            notification_config = NotificationConfig(
                enabled=True, telegram_bot_token=bot_token, telegram_chat_id=chat_id
            )

        if not notification_config:
            console.print(
                "[red]Please provide either a config file or bot token/chat ID[/red]"
            )
            return

        # Test connection
        console.print("[yellow]Testing bot connection...[/yellow]")
        db = Database()
        alert_service = AlertService(db)
        await alert_service.initialize(notification_config)

        if await alert_service.test_connection():
            console.print("[green]✓ Test message sent successfully![/green]")
        else:
            console.print("[red]✗ Failed to send test message[/red]")

    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def status(config_file: Path = typer.Argument(..., help="Configuration file")):
    """Check bot configuration status"""
    try:
        # Load configuration
        config = ConfigLoader.load_config(config_file)

        # Create status table
        table = Table(title="Telegram Bot Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        if config.global_notifications:
            notif = config.global_notifications
            table.add_row("Enabled", "✓" if notif.enabled else "✗")
            table.add_row(
                "Bot Token",
                (
                    "***" + notif.telegram_bot_token[-6:]
                    if notif.telegram_bot_token
                    else "Not set"
                ),
            )
            table.add_row("Chat ID", notif.telegram_chat_id or "Not set")
            table.add_row("New Properties", "✓" if notif.new_properties else "✗")
            table.add_row("Price Changes", "✓" if notif.price_changes else "✗")
            table.add_row("Immediate Alerts", "✓" if notif.immediate_alerts else "✗")
            table.add_row("Daily Summary", "✓" if notif.daily_summary else "✗")
            table.add_row("Weekly Summary", "✓" if notif.weekly_summary else "✗")
        else:
            table.add_row("Status", "Not configured")

        console.print(table)

        # Show profile-specific notifications
        profiles_with_notif = [
            p for p in config.profiles if p.notifications and p.notifications.enabled
        ]
        if profiles_with_notif:
            console.print(
                f"\n[cyan]Profiles with notifications: {', '.join(p.name for p in profiles_with_notif)}[/cyan]"
            )

    except Exception as e:
        console.print(f"[red]Failed to check status: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def monitor(
    check_interval: int = typer.Option(
        300, "--interval", help="Check interval in seconds"
    )
):
    """Start property monitoring in the current terminal"""
    console.print("[green]Starting property monitor...[/green]")
    console.print(f"Checking every {check_interval} seconds")
    console.print("This command runs the monitor in the foreground.")
    console.print("Use 'bot-start' with --daemon for background operation.")
    console.print("\nPress Ctrl+C to stop")

    # This is a placeholder - actual implementation would use the monitoring service
    try:
        while True:
            console.print("[dim]Checking for new properties...[/dim]")
            import time

            time.sleep(check_interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")


# Wrap async commands for sync Typer
def setup_sync(**kwargs):
    """Sync wrapper for setup command"""
    asyncio.run(setup(**kwargs))


def start_sync(**kwargs):
    """Sync wrapper for start command"""
    asyncio.run(start(**kwargs))


def test_sync(**kwargs):
    """Sync wrapper for test command"""
    asyncio.run(test(**kwargs))


# Override the async commands with sync versions
app.command("setup")(setup_sync)
app.command("start")(start_sync)
app.command("test")(test_sync)
