# Development Setup Guide

This guide creates a working local development environment with:
- Backend FastAPI server with LangGraph agents
- Frontend Next.js chat interface
- OpenMemory (CaviraOSS) for persistent conversation context via MCP

---

## Step-by-Step Setup

### Step 1: Prerequisites

- **Docker Desktop** — must be running
- **Google API Key** — for Gemini LLM: https://makersuite.google.com/app/apikey

### Step 2: Initialize OpenMemory Submodule

The OpenMemory backend is provided as a git submodule. Initialize it once:

```bash
git submodule update --init openmemory-repo
```

You should see `openmemory-repo/packages/openmemory-js/` populated with source files.

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:

- `GOOGLE_API_KEY` — your Gemini API key
- `OPENMEMORY_URL` — leave as `http://openmemory:8080` for Docker
- `JWT_SECRET_KEY` — change for production
- (Optional) `OM_TIER`, `OM_EMBEDDINGS`, `OM_API_KEY` — OpenMemory overrides

### Step 4: Start Services

```bash
docker compose up --build
```

This starts:
- **Backend** at http://localhost:8000
- **Frontend** at http://localhost:3000
- **OpenMemory API** at http://localhost:8080

### Step 5: Verify OpenMemory

```bash
curl http://localhost:8080/health
```

Expected: `{"status":"ok"}` or similar.

### Step 6: Test the System

1. Open http://localhost:3000
2. Send: "Hi, I need help with time management"
3. Ask: "What did I just ask you about?"
4. The agent should remember via OpenMemory.

### Step 7: (Optional) Enable Cursor MCP

When OpenMemory is running, Cursor can use its MCP tools. The project includes `.cursor/mcp.json` pointing at `http://localhost:8080/mcp`.

**Available tools:** `openmemory_query`, `openmemory_store`, `openmemory_list`, `openmemory_get`, `openmemory_reinforce`

Ensure `docker compose up` is running, then Cursor connects automatically. For global config, copy the openmemory entry to `~/.cursor/mcp.json`.

---

## Troubleshooting

### Docker Build Fails / "unexpected end of JSON input"

Docker cache may be corrupted:

```bash
docker compose down
docker system prune -a
docker compose up --build
```

### OpenMemory Submodule Empty

```bash
git submodule update --init openmemory-repo
```

If it fails, ensure you have network access and the CaviraOSS/OpenMemory repo is reachable.

### Backend Can't Connect to OpenMemory

- Ensure `OPENMEMORY_URL=http://openmemory:8080` in `.env`
- Wait for OpenMemory healthcheck (about 30s after start)
- Check logs: `docker compose logs openmemory`

### Agent Not Responding

- Verify `GOOGLE_API_KEY` is set in `.env`
- Check backend logs: `docker compose logs backend`

---

## Development Workflow

| Command | Description |
|--------|-------------|
| `docker compose up --build` | Start all services |
| `docker compose logs -f openmemory` | View OpenMemory logs |
| `docker compose down` | Stop services |
| `docker compose down -v` | Stop and remove volumes (clears OpenMemory data) |

---

## Architecture

```
┌─────────────┐     HTTP      ┌─────────────┐
│   Frontend  │ ───────────▶  │   Backend   │
│  (Next.js)  │               │  (FastAPI)  │
│  :3000      │               │   :8000     │
└─────────────┘               └──────┬──────┘
                                     │
                              MCP over HTTP
                                     │
                              ┌──────▼──────────────┐
                              │  MemoryManager      │
                              │  (MCP client)       │
                              └──────┬─────────────┘
                                     │
                              ┌──────▼────────┐
                              │  OpenMemory   │
                              │  API + MCP    │
                              │    :8080      │
                              └───────────────┘
```

---

## Files Reference

- `.env.example` — Environment template (copy to `.env`)
- `docker-compose.yml` — Backend, frontend, OpenMemory
- `.cursor/mcp.json` — Cursor MCP config for OpenMemory
- `openmemory-repo/` — CaviraOSS/OpenMemory (git submodule)
