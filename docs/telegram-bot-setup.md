# HomeHunt Telegram Bot Setup Guide

This guide will help you set up real-time property alerts via Telegram for your HomeHunt searches.

## Features

- 🆕 **Instant Alerts**: Get notified immediately when new properties match your criteria
- 💷 **Price Drop Alerts**: Know when properties reduce their asking price
- 📊 **Daily/Weekly Summaries**: Receive regular digests of property activity
- 🚇 **Commute Filtering**: Only get alerts for properties within your commute requirements
- 🤖 **Interactive Bot**: View properties, save favorites, and manage alerts from Telegram

## Quick Start

### 1. Create Your Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` to BotFather
3. Choose a name for your bot (e.g., "My Property Hunter")
4. Choose a username ending in `bot` (e.g., `my_property_hunter_bot`)
5. Save the bot token that BotFather gives you

### 2. Get Your Chat ID

1. Send a message to your new bot
2. Visit this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Find your chat ID in the response (look for `"chat":{"id":123456789}`)

### 3. Configure HomeHunt

#### Option A: Interactive Setup
```bash
homehunt bot-setup
```

#### Option B: Use Configuration File
1. Copy the example configuration:
   ```bash
   cp configs/simple_bot_alert.yaml my_bot_config.yaml
   ```

2. Edit `my_bot_config.yaml` and add your bot token and chat ID:
   ```yaml
   global_notifications:
     enabled: true
     telegram_bot_token: "YOUR_BOT_TOKEN_HERE"
     telegram_chat_id: "YOUR_CHAT_ID_HERE"
   ```

### 4. Test Your Bot

```bash
homehunt bot-test --config my_bot_config.yaml
```

You should receive a test message in Telegram!

## Usage Examples

### One-Time Search with Alerts

Run a property search and get Telegram alerts for new finds:

```bash
homehunt run-config my_bot_config.yaml
```

### Continuous Monitoring

Start the bot to continuously monitor for new properties:

```bash
# Check every 5 minutes (default)
homehunt bot-start my_bot_config.yaml

# Check every 10 minutes
homehunt bot-start my_bot_config.yaml --interval 600

# Run as background daemon (Linux/Mac)
nohup homehunt bot-start my_bot_config.yaml &
```

### Simple Command Line Search with Alerts

```bash
# First, set up bot credentials
homehunt bot-setup --token YOUR_BOT_TOKEN --chat-id YOUR_CHAT_ID

# Then run searches that will send alerts
homehunt search "London E14" --max-price 2000 --min-beds 1
```

## Advanced Configuration

### Multiple Search Profiles

Monitor different types of properties with `bot_monitoring.yaml`:

```yaml
profiles:
  - name: "City Apartment"
    search:
      location: "London EC2"
      max_price: 2500
      property_types: [flat]
    commute_filters:
      - destination: "Liverpool Street"
        max_time: 20
        
  - name: "Family Home"
    search:
      location: "Richmond"
      min_bedrooms: 3
      garden: true
      parking: true
```

### Alert Customization

Control what triggers alerts:

```yaml
global_notifications:
  # Alert types
  new_properties: true     # New listings
  price_changes: true      # Price drops
  status_changes: false    # Availability changes
  
  # Alert timing
  immediate_alerts: true   # Send right away
  daily_summary: true      # 9 AM daily digest
  weekly_summary: false    # Monday weekly report
```

### Commute-Based Filtering

Only get alerts for properties with acceptable commute times:

```yaml
commute_filters:
  - destination: "Bank Station"
    max_time: 30
    transport_modes: [public_transport]
    departure_times: ["08:00", "08:30"]
```

## Bot Commands

Once your bot is running, you can interact with it on Telegram:

- `/start` - Welcome message and bot info
- `/help` - Show all available commands
- `/status` - Check bot configuration status
- `/recent` - Show recently found properties
- `/stats` - View search statistics

## Property Alert Format

When a new property is found, you'll receive a formatted message with:

- Property title and price
- Location with Google Maps link
- Number of bedrooms and bathrooms
- Special features (parking, garden, pets allowed)
- Direct link to view on Rightmove/Zoopla
- Action buttons to save or hide properties

## Troubleshooting

### Bot Not Responding

1. Check your bot token is correct
2. Verify your chat ID
3. Ensure the bot is running: `homehunt bot-status --config your_config.yaml`

### Not Receiving Alerts

1. Check notifications are enabled in your config
2. Verify properties match your search criteria
3. Check the monitoring interval isn't too long
4. Review logs for any errors

### Connection Errors

1. Ensure you have internet connectivity
2. Check Telegram isn't blocked on your network
3. Verify your bot hasn't been deleted or disabled

## Running as a Service

### Linux (systemd)

Create `/etc/systemd/system/homehunt-bot.service`:

```ini
[Unit]
Description=HomeHunt Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/homehunt
ExecStart=/home/youruser/miniconda3/envs/home_hunt_env/bin/homehunt bot-start /home/youruser/homehunt/my_bot_config.yaml
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable homehunt-bot
sudo systemctl start homehunt-bot
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.homehunt.bot.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.homehunt.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/youruser/miniconda3/envs/home_hunt_env/bin/homehunt</string>
        <string>bot-start</string>
        <string>/Users/youruser/homehunt/my_bot_config.yaml</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.homehunt.bot.plist
```

## Security Best Practices

1. **Keep your bot token secret** - Never commit it to version control
2. **Use environment variables** for sensitive data:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token"
   export TELEGRAM_CHAT_ID="your_chat_id"
   ```
3. **Restrict bot access** - Only share your bot username with trusted people
4. **Regular updates** - Keep HomeHunt and dependencies updated

## Next Steps

- Explore advanced search configurations in `configs/alex_search.yaml`
- Set up multiple monitoring profiles for different property types
- Configure quiet hours to avoid alerts at night
- Integrate with Google Sheets for property tracking

Happy house hunting! 🏠🤖