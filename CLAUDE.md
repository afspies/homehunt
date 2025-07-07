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
- Repository initialized
- Implementation plan reviewed
- Todo list created with 10 phases
- README.md created

## Next Steps
Start with Phase 0: Project Setup
- Create directory structure
- Setup conda environment
- Create requirements files
- Configure pre-commit hooks

## API Keys Required
- TravelTime API (free tier)
- Telegram Bot Token
- Google Sheets Service Account

## Remember
- Commit after EVERY completed todo
- Use descriptive commit messages
- Keep commits atomic and focused
- Push to remote after each phase completion