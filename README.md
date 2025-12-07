# ZStyle Services

Executive Function Coach - AI-powered personal productivity assistant

## Architecture

app - hosts ADK fast api app

telegram_bot - hosts telegram bot with polling

## Components

### Agent

- `/agents/exec_func_coach/` - Executive Function Coach agent
- Acts as friend and guide to creating a life that moves the day to day forward
- Helps create set and reach goals and Design systems to improve the experience of life
- Uses Google ADK framework
- Integrates with Google Calendar, TickTick, and more for life management

### Services

- `/services/memory/` - Long-term memory storage & RAG (No sessions just users and memory)
- `/services/artifacts/` - File and document storage
- `/services/activity_log.py` - Session management

### MCP (Model Context Protocol)

- none implemented yet to come soon
- idea 1: telegram mcp but for group chats with a2a agents working together
- idea 2: twilio mcp server for agent to call users as reminder

## Setup

1. Copy `.env.example` to `.env` and configure:

   ```bash
   cp .env.example .env
   ```

2. Run with Docker:

   ```bash
   bash ddup.sh
   ```

## Development

- SQLite Database for initial development (move to supabase for prod)

## Next Steps

- Admin Dashboards For User Management and Viewing
- Create Proper User Onboarding Process
- Establish Memory, Credentials, and Infra CI/CD Prod vs Dev Bot