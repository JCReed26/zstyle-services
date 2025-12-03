# Architecture Overview

## Components

### Main Application
- `main.py`: FastAPI application with Google ADK integration
- Database initialization and lifecycle management

### Agent Layer
- `/agents/exec_func_coach/`: Executive Function Coach implementation
- Tool integration for external services

### Service Layer
- `/services/auth/`: Authentication and credential management
- `/services/memory/`: Long-term memory storage
- `/services/artifacts/`: File and content management
- `/services/session_service.py`: Session management

### MCP Integration
- `/services/telegram_mcp/`: Model Context Protocol for Telegram
- Provides messaging capabilities through MCP

## Data Flow

1. User interacts with Telegram bot
2. MCP handles Telegram communication
3. Request forwarded to appropriate agent
4. Agent processes request using tools and services
5. Response sent back through MCP to user