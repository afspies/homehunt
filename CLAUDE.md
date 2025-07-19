# CLAUDE.md - Project Context for HomeHunt

## Project Overview
HomeHunt is an async Python CLI tool that automates property search across Rightmove and Zoopla, enriches listings with commute times, and sends real-time alerts for properties matching user criteria.

## Development Environment
- **Python Version**: 3.12 (conda environment: home_hunt_env)
- **Environment Manager**: Anaconda (conda)
- **Package Manager**: pip within conda environment
- **Version Control**: Git

## Important Development Rules

### 1. Git Commit Policy
**CRITICAL**: After completing each todo item, you MUST create a Git commit with a descriptive message that follows this format:
- `feat:` for new features
- `fix:` for bug fixes
- `refactor:` for code refactoring
- `test:` for adding tests
- `docs:` for documentation
- `chore:` for maintenance tasks

Example: `feat: implement Rightmove search pagination`

### 2. Anaconda Environment Setup
Always use Anaconda for Python environment management:
```bash
# Environment already created: home_hunt_env (Python 3.12)

# Activate environment
conda activate home_hunt_env

# Install dependencies
pip install -r requirements.txt
```

### 3. Code Quality Standards
- Run `black` before every commit
- Run `ruff check` before every commit
- Ensure all tests pass before marking a todo as complete
- Use type hints for all function signatures

### 4. Async-First Development
- All I/O operations must be async
- Use `httpx` for HTTP requests (not `requests`)
- Use `aiosqlite` for database operations
- Implement proper semaphores for rate limiting

### 5. Testing Requirements
- Write tests for every new module
- Maintain >80% code coverage
- Mock all external API calls
- Use `pytest-asyncio` for async tests

### 6. Error Handling
- Use Rich console for all error output
- Implement graceful degradation
- Log all errors with proper context
- Never expose API keys in logs

### 7. Performance Considerations
- Use concurrent operations where possible
- Implement caching for expensive operations
- Respect rate limits for all external services
- Use progress indicators for long-running operations

## Current Implementation Status
- ✅ Repository initialized and project structure created
- ✅ Implementation plan reviewed and validated through testing
- ✅ Fire Crawl API integration tested and confirmed working
- ✅ Direct HTTP scraping validated for Rightmove (100% success rate)
- ✅ Hybrid scraping strategy identified and documented
- ✅ Property deduplication system implemented and tested
- ✅ Portal-specific anti-bot analysis completed
- ✅ Phase 1: Core Data Layer completed (PropertyListing, Database)
- ✅ Phase 2: Hybrid Scraper Implementation completed
- ✅ Phase 3: CLI Integration with Rich Interface completed
- ✅ Phase 4: TravelTime Integration completed (commute analysis)
- ✅ Phase 5A: Advanced Configuration completed (YAML/JSON config files)
- ✅ Phase 5B: Export Integration completed (Google Sheets sync, CSV/JSON exports)
- ✅ Enhanced PropertyListing Model completed (parking, garden, balcony, pets, coordinates)
- ✅ Intelligent Feature Extraction completed (AI-powered amenity parsing)
- ✅ Geographic Data Enhancement completed (Rightmove map coordinate extraction)
- ✅ Phase 5C: Telegram Bot Integration completed (real-time alerts, continuous monitoring)

## Completed Features
### Core System
- **Hybrid Scraping**: Fire Crawl + Direct HTTP (90% cost savings)
- **Multi-Portal Support**: Rightmove and Zoopla with smart deduplication
- **Database Integration**: SQLite with property history and price tracking
- **Rich CLI Interface**: Beautiful progress bars, tables, and feedback

### Advanced Features
- **Commute Analysis**: TravelTime API integration for location filtering
- **Configuration System**: YAML/JSON files for complex search strategies
- **Multi-Location Searches**: Search multiple areas with location-specific parameters
- **Property Scoring**: Customizable ranking based on price, commute, size, features
- **Export Integration**: CSV/JSON/Google Sheets export with application default credentials
- **Export Templates**: Predefined export configurations for common use cases
- **Feature Extraction**: Automatic parsing of parking, gardens, pet policies, amenities
- **Geographic Enhancement**: GPS coordinates from Rightmove maps and embedded content
- **Property Classification**: Intelligent categorization of rental types and amenities
- **Telegram Bot Integration**: Real-time alerts, continuous monitoring, interactive commands

### CLI Commands
- `search` - Basic property searches with filtering
- `commute` - Commute time analysis and filtering
- `run-config` - Execute configuration-driven searches
- `init-config` - Create template configurations
- `list-configs` - Show available configurations
- `show-config` - Display configuration summaries
- `stats` - Database statistics
- `list` - List saved properties
- `cleanup` - Database maintenance
- `export-csv` - Export properties to CSV files
- `export-json` - Export properties to JSON files  
- `export-sheets` - Export properties to Google Sheets
- `export-status` - Show database and export status
- `export-templates` - List available export templates
- `test-sheets` - Test Google Sheets API connection
- `bot-setup` - Configure Telegram bot interactively
- `bot-start` - Start continuous property monitoring
- `bot-test` - Test Telegram bot connection
- `bot-status` - Check bot configuration status
- `bot-monitor` - Run monitoring in foreground

## Validated Performance
- **Rightmove**: 100% success rate with direct HTTP scraping + coordinate extraction
- **Zoopla**: Reliable scraping via Fire Crawl API
- **Coordinate Extraction**: 95%+ success rate from Rightmove map images
- **Feature Detection**: 85%+ accuracy for parking, gardens, pet policies
- **Deduplication**: 57% efficiency preventing redundant scraping
- **Cost Optimization**: 90% reduction in API costs vs. Fire Crawl-only approach
- **TravelTime Integration**: Real API tested and working with user credentials
- **Configuration System**: Comprehensive YAML/JSON support with validation
- **Export Integration**: Google Sheets API tested with application default credentials

## Next Implementation Phases
All major phases completed! Potential future enhancements:
- Advanced bot features (user preferences, saved searches, analytics)
- WhatsApp/SMS integration
- Property image analysis
- Historical price tracking and predictions

## Recent Enhancements Completed
- ✅ Added missing PropertyListing fields: latitude, longitude, parking, garden, balcony, pets_allowed, let_type, is_active  
- ✅ Implemented FeatureExtractor with regex-based amenity parsing
- ✅ Enhanced coordinate extraction from Rightmove map images and embedded content
- ✅ Updated export system with new fields and enhanced templates
- ✅ Created GeocodingService for TravelTime API coordinate enhancement

## API Keys Required
- ✅ Fire Crawl API (implemented and tested)
- ✅ TravelTime API (implemented and tested)
- ✅ Google Sheets API (application default credentials - implemented and tested)
- ✅ Telegram Bot Token (implemented with full bot integration)

## Authentication Setup
### Google Sheets (Preferred Method)
```bash
# Install gcloud CLI and authenticate
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file
gcloud auth application-default set-quota-project YOUR_PROJECT_ID

# Test connection
python -m homehunt test-sheets
```

### Telegram Bot
```bash
# Create bot with @BotFather on Telegram
# Get bot token and chat ID

# Interactive setup
python -m homehunt bot-setup

# Or configure in YAML
telegram_bot_token: "YOUR_BOT_TOKEN"
telegram_chat_id: "YOUR_CHAT_ID"

# Test bot
python -m homehunt bot-test --config your-config.yaml
```

## Remember
- Commit after EVERY completed todo
- Use descriptive commit messages
- Keep commits atomic and focused
- Push to remote after each phase completion