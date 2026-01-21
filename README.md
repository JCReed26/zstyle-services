# ZStyle Services

Executive Function Coach - AI-powered personal productivity assistant

## What is ZStyle Services

ZStyle Services is an AI-powered Executive Function Coach system built on Google's Agent Development Kit (ADK). It provides a personal productivity assistant that helps users manage goals, tasks, schedules, and build systems that work for their individual needs.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Google API key (for Gemini models)
- Telegram bot token (for Telegram integration)

### Initial Setup

1. Copy `.env.example` to `.env` and configure:

   ```bash
   cp .env.example .env
   ```

2. Configure environment variables in `.env`:
   - `GOOGLE_API_KEY` - Google API key for Gemini models
   - `TELEGRAM_BOT_TOKEN` - Telegram bot token
   - `SECRET_KEY` - Secret key for encryption (32+ characters)
   - `DATABASE_URL` - PostgreSQL connection string (local container)
   - `POSTGRES_USER` - PostgreSQL username (default: postgres)
   - `POSTGRES_PASSWORD` - PostgreSQL password
   - `POSTGRES_DB` - PostgreSQL database name (default: zstyle_db)

3. Initialize local PostgreSQL database:
   - **Start PostgreSQL container**: `docker compose up -d db`
   - **Run migration**: `docker compose cp docs/migrations/001_initial_schema.sql db:/tmp/` then `docker compose exec db psql -U postgres -d zstyle_db -f /tmp/001_initial_schema.sql`
   - **Verify**: Application verifies connection on startup

4. Install dependencies:

   ```bash
   make install
   ```

5. Start development server:

   ```bash
   make dev
   ```

   Or run with Docker:

   ```bash
   make docker-up
   ```

## Architecture Overview

```
zstyle-services/
├── app/                    # Application core
│   ├── config.py          # Configuration
│   ├── logger.py          # Logging
│   ├── security.py        # Security utilities
│   └── main.py            # Entry point
├── agent/                 # AI agents
│   └── exec_func_coach/   # Executive Function Coach agent
├── api/                   # API routes
│   ├── api/              # API endpoints
│   ├── auth/              # Authentication endpoints
│   ├── oauth/             # OAuth endpoints
│   └── telegram_webhook.py
├── channels/              # Communication channels
│   ├── base.py           # Base channel classes
│   ├── router.py         # Message routing
│   └── telegram_bot/     # Telegram channel implementation
├── database/             # Database layer
│   ├── engine.py         # Database engine
│   ├── models.py         # SQLAlchemy models
│   └── repositories.py   # Repository pattern
├── services/             # Business logic
│   ├── activity_log.py
│   ├── auth_service.py
│   ├── credential_service.py
│   └── ...
└── tools/                # Agent tools
    └── ticktick_tool.py
```

### Components

#### Agent

- `/agent/exec_func_coach/` - Executive Function Coach agent
- Acts as friend and guide to creating a life that moves the day to day forward
- Helps create, set and reach goals and design systems to improve the experience of life
- Uses Google ADK framework
- Integrates with Google Calendar, TickTick, and more for life management

#### Services

- `/services/memory/` - Long-term memory storage & RAG (No sessions just users and memory)
- `/services/activity_log.py` - Activity logging service
- `/services/auth_service.py` - Authentication service
- `/services/credential_service.py` - Secure credential storage

#### API

- `/api/api/` - REST API endpoints
- `/api/auth/` - Authentication endpoints (phone auth)
- `/api/oauth/` - OAuth endpoints (Google, TickTick)
- `/api/telegram_webhook.py` - Telegram webhook handler

## Development

### Running the Application

```bash
# Development server with hot reload
make dev

# Or using Docker
make docker-up
```

### Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration
```

### Code Quality

```bash
# Run linters
make lint

# Format code
make format
```

## Testing

Tests are organized into:
- `tests/unit/` - Unit tests (fast, isolated)
- `tests/integration/` - Integration tests (may use external services)
- `tests/api/` - API endpoint tests

Run tests with:

```bash
make test
```

For integration tests against local PostgreSQL:

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/zstyle_db"
make test-integration
```

## Next Steps

- Admin Dashboards For User Management and Viewing
- Create Proper User Onboarding Process
- Establish Memory, Credentials, and Infra CI/CD Prod vs Dev Bot
