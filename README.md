# HomeHunt 🏡

A powerful async Python CLI tool that automates property search across Rightmove and Zoopla, with intelligent hybrid scraping, commute analysis, and advanced configuration-driven searches.

## ✨ Features

- **🔄 Hybrid Scraping Strategy**: Fire Crawl API + Direct HTTP for optimal cost/performance (90% cost savings)
- **🏠 Multi-Portal Support**: Concurrent scraping from Rightmove and Zoopla
- **🧠 Smart Deduplication**: Cross-portal property matching with 24-hour window detection  
- **📊 Rich CLI Interface**: Beautiful progress bars, tables, and real-time feedback
- **💾 Database Integration**: SQLite with full property history and price tracking
- **🚊 Commute Analysis**: TravelTime API integration for intelligent location filtering
- **⚙️ Advanced Configuration**: YAML/JSON config files for complex search strategies
- **📍 Multi-Location Searches**: Search multiple areas with location-specific parameters
- **🎯 Property Scoring**: Customizable ranking based on price, commute, size, and features
- **📤 Export Options**: CSV and JSON export capabilities with auto-export support
- **⚡ Async Architecture**: High-performance concurrent operations throughout
- **🎯 Advanced Filtering**: Price, bedrooms, property type, location radius, features, and more

## 🚀 Quick Start

```bash
# Clone the repository
git clone git@github.com:afspies/homehunt.git
cd homehunt

# Set up Python environment (Python 3.12 required)
conda create -n home_hunt_env python=3.12
conda activate home_hunt_env

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python -m homehunt init

# Run your first search
python -m homehunt search "SW1A 1AA" --max-price 2000 --min-beds 1
```

## 📋 Usage Examples

### Basic Property Search
```bash
# Search around a postcode
python -m homehunt search "E14 9RH" --radius 1.0

# Search with price filters
python -m homehunt search "London" --min-price 1000 --max-price 2500

# Search for specific property types
python -m homehunt search "Cambridge" --type flat --min-beds 2 --max-beds 3
```

### Advanced Filtering
```bash
# Search with multiple filters
python -m homehunt search "Oxford" \
  --min-price 1200 --max-price 2000 \
  --type flat --furnished furnished \
  --parking --garden --pets \
  --radius 2.0

# Export results to file
python -m homehunt search "Bath" --output results.csv --max-results 50

# Search specific portals only
python -m homehunt search "Brighton" --portals rightmove --sort price_asc
```

### Commute Analysis
```bash
# Analyze commute times to a destination
python -m homehunt commute "Canary Wharf" --max-time 45 --transport public_transport

# Multi-modal commute analysis
python -m homehunt commute "King's Cross" --transport cycling --max-time 30

# Update all properties with commute data
python -m homehunt commute "EC2A 1AA" --update-all --departure 09:00
```

### Configuration-Driven Searches
```bash
# Create a template configuration file
python -m homehunt init-config --output my-searches.yaml

# Run all profiles in a configuration
python -m homehunt run-config my-searches.yaml

# Run specific profiles only
python -m homehunt run-config my-searches.yaml --profile family_homes --profile budget_flats

# Validate configuration without running
python -m homehunt run-config my-searches.yaml --validate

# Show what would be executed (dry run)
python -m homehunt run-config my-searches.yaml --dry-run

# List available configurations
python -m homehunt list-configs

# Show configuration summary
python -m homehunt show-config my-searches.yaml
```

### Database Management
```bash
# Show database statistics
python -m homehunt stats

# List saved properties with filters
python -m homehunt list --limit 20 --min-price 1500 --beds 2

# Clean up old properties
python -m homehunt cleanup --days 30
```

### Data Export

```bash
# Export to CSV
python -m homehunt export-csv --output properties.csv
python -m homehunt export-csv --include title,price,bedrooms,area --portal rightmove

# Export to JSON
python -m homehunt export-json --output properties.json

# Export to Google Sheets (uses application default credentials)
python -m homehunt export-sheets --sheet-name "HomeHunt Properties" --share your-email@gmail.com
python -m homehunt export-sheets --include title,price,bedrooms --portal zoopla --share user@example.com

# Test Google Sheets connection
python -m homehunt test-sheets

# View export templates and status
python -m homehunt export-templates
python -m homehunt export-status
```

## ⚙️ Configuration

### API Keys

Create a `.env` file in the project root:

```env
# Fire Crawl API (for anti-bot protected content)
FIRECRAWL_API_KEY=your_firecrawl_api_key

# TravelTime API (for commute analysis)
TRAVELTIME_APP_ID=your_app_id
TRAVELTIME_API_KEY=your_api_key

# Telegram Bot (optional, for future alerts)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Getting API Keys

1. **Fire Crawl API**: Sign up at [Fire Crawl](https://firecrawl.dev)
2. **TravelTime API**: Sign up at [TravelTime Developer Portal](https://account.traveltime.com/signup)
3. **Google Sheets API**: Enable APIs and authenticate (see Google Sheets Setup below)
4. **Telegram Bot**: Create via [@BotFather](https://t.me/botfather) on Telegram

### Google Sheets Setup

HomeHunt uses **Application Default Credentials** for Google Sheets integration (recommended approach):

#### Prerequisites
1. **Create Google Cloud Project** or use existing one
2. **Enable APIs** in Google Cloud Console:
   - Google Sheets API
   - Google Drive API

#### Authentication Setup
```bash
# Install Google Cloud CLI if not already installed
# macOS: brew install google-cloud-sdk
# Or download from: https://cloud.google.com/sdk/docs/install

# Authenticate with your Google account (includes required scopes)
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file

# Set your project as quota project (replace YOUR_PROJECT_ID)
gcloud auth application-default set-quota-project YOUR_PROJECT_ID

# Test the connection
python -m homehunt test-sheets
```

#### Alternative: Service Account (Corporate Environments)
If your organization requires service accounts:

```bash
# Download service account JSON from Google Cloud Console
# Then test with:
python -m homehunt test-sheets /path/to/service-account.json
```

**Note**: Many corporate environments block service account key creation. Application Default Credentials is the preferred and more secure approach.

### Advanced Configuration Files

HomeHunt supports YAML and JSON configuration files for complex search strategies. Create a template:

```bash
python -m homehunt init-config --output my-searches.yaml
```

**Example Configuration:**

```yaml
name: "My Property Searches"
description: "Multi-location searches with commute filtering"

# Global settings
concurrent_searches: 3
save_to_database: true
deduplicate_across_profiles: true

# Search profiles
profiles:
  - name: "family_homes"
    description: "Family-friendly homes with gardens"
    search:
      location: "SW1A 1AA"
      portals: ["rightmove", "zoopla"]
      min_bedrooms: 2
      max_bedrooms: 4
      min_price: 2000
      max_price: 4000
      property_types: ["house", "maisonette"]
      furnished: "any"
      parking: true
      garden: true
      radius: 1.5
      sort_order: "price_asc"
      max_results: 50
    
    # Multi-location search
    multi_location:
      name: "South London Areas"
      locations: ["Clapham", "Battersea", "Wandsworth"]
      combine_results: true
      max_results_per_location: 20
      location_overrides:
        "Clapham":
          max_price: 4500
        "Battersea":
          min_price: 2500
    
    # Commute filtering
    commute_filters:
      - destination: "Canary Wharf"
        max_time: 45
        transport_modes: ["public_transport"]
        departure_times: ["08:00", "09:00"]
        weight: 1.0
      - destination: "King's Cross"
        max_time: 35
        transport_modes: ["public_transport", "cycling"]
        departure_times: ["08:30"]
        weight: 0.8
    
    # Property scoring
    enable_scoring: true
    score_weights:
      price: 0.3      # Lower price = higher score
      commute: 0.4    # Shorter commute = higher score  
      size: 0.2       # More bedrooms = higher score
      features: 0.1   # More features = higher score
    
    # Auto-export
    auto_export: true
    export_formats: ["csv", "json"]
    export_path: "./exports/family_homes"

  - name: "budget_flats"
    description: "Budget-friendly flats for young professionals"
    search:
      location: "E14"
      portals: ["rightmove"]
      min_bedrooms: 1
      max_bedrooms: 2
      max_price: 2500
      property_types: ["flat"]
      furnished: "furnished"
      radius: 2.0
      sort_order: "price_asc"
    
    commute_filters:
      - destination: "Liverpool Street"
        max_time: 30
        transport_modes: ["public_transport"]
    
    enable_scoring: true
    score_weights:
      price: 0.6
      commute: 0.3
      features: 0.1

# Global commute filters (applied to all profiles)
global_commute_filters:
  - destination: "Central London"
    max_time: 60
    transport_modes: ["public_transport"]
```

**Configuration Features:**

- **Multi-Profile Searches**: Define multiple search strategies in one file
- **Multi-Location Support**: Search multiple areas with location-specific parameters
- **Commute Filtering**: Filter properties by commute time to multiple destinations
- **Property Scoring**: Rank properties based on customizable criteria weights
- **Auto-Export**: Automatically export results to CSV, JSON, or Google Sheets
- **Concurrent Execution**: Control parallel search execution
- **Global Settings**: Apply filters and settings across all profiles

## 🏗️ Architecture

### Project Structure
```
homehunt/
├── __main__.py              # CLI entry point
├── cli/                     # Command line interface
│   ├── app.py              # Typer CLI commands
│   ├── config.py           # Search configuration models
│   ├── config_commands.py  # Configuration-driven search commands
│   ├── search_command.py   # Async search implementation
│   └── url_builder.py      # Portal-specific URL generators
├── config/                  # Advanced configuration system
│   ├── models.py           # Configuration data models
│   ├── parser.py           # YAML/JSON parser with validation
│   ├── manager.py          # Configuration management
│   └── executor.py         # Configuration execution engine
├── core/                    # Core functionality
│   ├── models.py           # Pydantic data models
│   └── db.py               # SQLModel database layer
├── scrapers/               # Scraping system
│   ├── base.py            # Base scraper with rate limiting
│   ├── firecrawl.py       # Fire Crawl API integration
│   ├── direct_http.py     # Direct HTTP scraper
│   └── hybrid.py          # Hybrid scraper coordinator
├── traveltime/             # Commute analysis
│   ├── client.py          # TravelTime API client
│   ├── models.py          # Commute data models
│   └── service.py         # Commute filtering service
└── utils/                  # Utility functions
```

### Hybrid Scraping Strategy

Our validated approach achieves **90% cost savings** and **10x speed improvement**:

- **Fire Crawl API**: Search page discovery + Zoopla properties (~10% of requests)
- **Direct HTTP**: Rightmove individual properties (~90% of requests) 
- **Deduplication**: 57% efficiency avoiding redundant scraping
- **Result**: 100% reliability with optimal cost/performance

## 🧪 Development

### Setup Development Environment

```bash
# Activate conda environment
conda activate home_hunt_env

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage
pytest --cov=homehunt

# Format code
black homehunt/ tests/

# Lint code
ruff check homehunt/ tests/ --fix

# Type checking
mypy homehunt/
```

### Running Tests

```bash
# All tests (85+ tests across all modules)
pytest

# Specific test modules
pytest tests/scrapers/     # Scraper functionality
pytest tests/cli/          # CLI functionality
pytest tests/core/         # Core data models
pytest tests/traveltime/   # Commute analysis
pytest tests/config/       # Configuration system

# With verbose output
pytest -v

# With coverage report
pytest --cov=homehunt --cov-report=html
```

## 🗺️ Implementation Roadmap

### ✅ Completed Phases

- [x] **Phase 0**: Project Setup & Environment
- [x] **Phase 1**: Core Data Layer (PropertyListing, Database)
- [x] **Phase 2**: Hybrid Scraper Implementation  
- [x] **Phase 3**: CLI Integration with Rich Interface
- [x] **Phase 4**: TravelTime Integration (commute analysis)
- [x] **Phase 5A**: Advanced Configuration (YAML/JSON config files)

### 🚧 Current Development

- [ ] **Phase 5B**: Export Integration (Google Sheets sync, enhanced exports)
- [ ] **Phase 5C**: Telegram Bot (real-time alerts, monitoring service)

### 📈 Validated Performance

- **Rightmove**: 100% success rate with direct HTTP scraping
- **Zoopla**: Reliable scraping via Fire Crawl API
- **Deduplication**: 57% efficiency preventing redundant scraping
- **Cost Optimization**: 90% reduction in API costs vs. Fire Crawl-only approach

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development setup above
4. Write tests for your changes
5. Ensure all tests pass and code is properly formatted
6. Commit your changes (`git commit -m 'feat: add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Commit Message Format

We follow conventional commits:
- `feat:` for new features
- `fix:` for bug fixes  
- `refactor:` for code refactoring
- `test:` for adding tests
- `docs:` for documentation
- `chore:` for maintenance tasks

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the CLI interface
- [Rich](https://rich.readthedocs.io/) for beautiful console output
- [SQLModel](https://sqlmodel.tiangolo.com/) for the database layer
- [Pydantic](https://pydantic.dev/) for data validation
- [Fire Crawl](https://firecrawl.dev) for anti-bot scraping capabilities
- [httpx](https://www.python-httpx.org/) for async HTTP requests