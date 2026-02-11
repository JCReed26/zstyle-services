# Development Setup Guide

## Phase 1: Executive Function Coach with OpenMemory

This setup creates a working local development environment with:
- Backend FastAPI server with LangGraph agent
- Frontend Next.js chat interface
- OpenMemory for persistent conversation context

## Prerequisites

1. **Free up disk space** - You need at least 2GB free
   - Current status: DISK FULL (0 bytes available)
   - Run: `docker system prune -a` to clean Docker
   - Or: `npm cache clean --force` to clean npm cache

2. **Docker Desktop** - Must be running

3. **Google API Key** - For Gemini LLM
   - Get one at: https://makersuite.google.com/app/apikey
   - Add to `.env` file: `GOOGLE_API_KEY=your_key_here`

## Setup Steps

### 1. Configure Environment

```bash
# Edit .env file and add your Google API key
nano .env
# Set: GOOGLE_API_KEY=your_actual_key
```

### 2. Start Services

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# This starts:
# - Backend API at http://localhost:8000
# - Frontend at http://localhost:3000
# - OpenMemory at http://localhost:8080
```

### 3. Test the System

1. Open http://localhost:3000
2. Type: "Hi, I need help with time management"
3. Agent should respond
4. Ask: "What did I just ask you about?"
5. Agent should remember (using OpenMemory)

### 4. Verify OpenMemory

```bash
# Check OpenMemory is working
curl http://localhost:8080/health

# Check backend
curl http://localhost:8000/health
```

## Troubleshooting

### Disk Space Issues

If you see "ENOSPC: no space left on device":

```bash
# Clean Docker (will remove all unused images)
docker system prune -a --volumes

# Clean npm cache
npm cache clean --force

# Find large files
du -sh * | sort -h
```

### OpenMemory Connection Issues

If backend can't connect to OpenMemory:

```bash
# Check OpenMemory logs
docker-compose -f docker-compose.dev.yml logs openmemory

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

### Agent Not Responding

Check backend logs:

```bash
docker-compose -f docker-compose.dev.yml logs backend
```

Common issues:
- Missing GOOGLE_API_KEY in .env
- OpenMemory not started
- LangGraph dependencies missing

## Development Workflow

### Hot Reload

Both frontend and backend support hot reload:
- Backend: Changes to `/app` reload automatically
- Frontend: Changes to `/frontend` reload automatically

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Just backend
docker-compose -f docker-compose.dev.yml logs -f backend

# Just frontend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### Stopping Services

```bash
# Stop all
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (clears OpenMemory data)
docker-compose -f docker-compose.dev.yml down -v
```

## Next Steps

Once Phase 1 is working:
- **Phase 2**: Add other agents (Fitness Coach, Nutritionist, Personal Assistant) with A2A protocol
- **Phase 3**: Add simple authentication for multi-user support

## Architecture Overview

```
┌─────────────┐     HTTP      ┌─────────────┐
│   Frontend  │ ───────────▶  │   Backend   │
│  (Next.js)  │               │  (FastAPI)  │
└─────────────┘               └──────┬──────┘
                                     │
                              ┌──────┴──────┐
                              │             │
                         ┌────▼────┐   ┌────▼────────┐
                         │  Agent  │   │ OpenMemory  │
                         │LangGraph│   │  (Persist)  │
                         └─────────┘   └─────────────┘
```

## Files Created

- `/docker-compose.dev.yml` - Docker services
- `/Dockerfile.dev` - Backend container
- `/app/main.py` - FastAPI app
- `/app/core/memory.py` - OpenMemory integration
- `/app/agents/exec_func_coach/agent.py` - LangGraph agent
- `/frontend/app/page.tsx` - Chat UI
- `/frontend/Dockerfile.dev` - Frontend container
