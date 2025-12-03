# ZStyle Services

Executive Function Coach - AI-powered personal productivity assistant

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   User      │    │   Telegram       │    │   AI Agent       │
│             │◄──►│   (MCP)          │◄──►│                  │
│   Telegram  │    │                  │    │  Exec Function   │
│   Client    │    │  MCP Server      │    │  Coach          │
└─────────────┘    └──────────────────┘    └──────────────────┘
                                    │
                                    │    ┌──────────────────┐
                                    └───►│   Services       │
                                         │                  │
                                         │  - Auth          │
                                         │  - Memory        │
                                         │  - Artifacts     │
                                         │  - Sessions      │
                                         └──────────────────┘
                                                         │
                                                         │
                                            ┌─────────────▼─────────────┐
                                            │                           │
                                            │        Database           │
                                            │      (SQLite)             │
                                            │                           │
                                            └───────────────────────────┘
```

## Components

### Agent
- `/agents/exec_func_coach/` - Executive Function Coach agent
- Uses Google ADK framework
- Integrates with Google Calendar and Telegram via MCP

### Services
- `/services/auth/` - OAuth and credential management
- `/services/memory/` - Long-term memory storage
- `/services/artifacts/` - File and document storage
- `/services/session_service.py` - Session management

### MCP (Model Context Protocol)
- `/services/telegram_mcp/` - Telegram integration via MCP
- Provides messaging, chat, and notification capabilities

## Setup

1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

2. Generate Telegram session string:
   ```bash
   python services/telegram_mcp/session_string_generator.py
   ```

3. Run with Docker:
   ```bash
   docker-compose up --build
   ```

## Development

- Main entry: `main.py`
- Tests: `pytest` in `/tests/` directory
- Database: SQLite (can be switched to other engines)