# HomeHunt 🏡

A powerful async Python CLI tool that automates property search across Rightmove and Zoopla, enriches listings with commute times, and sends real-time alerts for properties matching your criteria.

## Features

- **Multi-Portal Scraping**: Concurrent scraping from Rightmove and Zoopla
- **Smart Deduplication**: Cross-portal property matching with price history tracking
- **Commute Analysis**: Enriches properties with public transport and cycling times via TravelTime API
- **Real-time Alerts**: Telegram notifications for new matching properties
- **Export Options**: Google Sheets integration and CSV export
- **Beautiful CLI**: Rich console output with progress tracking and visual feedback
- **Async Architecture**: High-performance concurrent operations throughout

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/homehunt.git
cd homehunt

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and add your API keys
cp .env.example .env

# Run your first search
python -m homehunt scrape \
  --area "Oxford" \
  --radius-miles 10 \
  --min-price 400000 \
  --max-price 750000 \
  --min-beds 2 \
  --max-commute-pt 45 \
  --destination "OX1 3JS" \
  --alert
```

## Configuration

### Environment Variables

Create a `.env` file with the following:

```env
# TravelTime API (free tier: 10k requests/day)
TRAVELTIME_APP_ID=your_app_id
TRAVELTIME_API_KEY=your_api_key

# Telegram Bot (optional, for alerts)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Google Sheets (optional, for export)
GOOGLE_SHEETS_CREDS_PATH=path/to/service-account-key.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

### Getting API Keys

1. **TravelTime API**: Sign up at [TravelTime Developer Portal](https://account.traveltime.com/signup)
2. **Telegram Bot**: Create a bot via [@BotFather](https://t.me/botfather) on Telegram
3. **Google Sheets**: Create a service account in Google Cloud Console

## Usage

### Basic Search

```bash
python -m homehunt scrape --area "London" --radius-miles 5
```

### With Filters

```bash
python -m homehunt scrape \
  --area "Cambridge" \
  --radius-miles 10 \
  --min-price 300000 \
  --max-price 500000 \
  --min-beds 2 \
  --max-commute-pt 30 \
  --destination "CB2 1TN"
```

### Scheduling

Set up automated searches using cron:

```bash
# Run every 2 hours between 8am-10pm
0 8-22/2 * * * cd /path/to/homehunt && ./venv/bin/python -m homehunt scrape [options]
```

## Architecture

```
homehunt/
├── cli.py                    # Typer CLI entry point
├── config.py                 # Configuration management
├── core/
│   ├── models.py            # Pydantic data models
│   ├── db.py                # SQLModel database layer
│   ├── scraper/             # Portal-specific scrapers
│   ├── dedup.py             # Deduplication logic
│   ├── filters.py           # Property filters
│   ├── commute/             # TravelTime integration
│   └── alerts/              # Notification system
├── exporters/               # Export functionality
└── utils/                   # Helpers and utilities
```

## Development

### Setup Development Environment

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest --cov=homehunt

# Format code
black homehunt/
ruff check homehunt/ --fix

# Type checking
mypy homehunt/
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=homehunt --cov-report=html

# Specific test file
pytest tests/test_scrapers.py
```

## Roadmap

- [x] Rightmove scraper
- [x] TravelTime integration
- [x] Telegram alerts
- [ ] Zoopla scraper
- [ ] Google Sheets export
- [ ] School catchment filters
- [ ] Crime statistics integration
- [ ] Web dashboard
- [ ] Mobile app

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the CLI
- Uses [Rich](https://rich.readthedocs.io/) for beautiful console output
- Powered by [SQLModel](https://sqlmodel.tiangolo.com/) for the database layer
- Commute data from [TravelTime API](https://www.traveltime.com/)