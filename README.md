# ZStyle Services

AI-powered monorepo with CopilotKit frontend, LangGraph agent (Gemini), persistent memory (OpenMemory), and extensible MCP servers.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  apps/       │────▶│  agents/     │────▶│  open_memory │
│  Next.js 16  │     │  LangGraph   │     │  OpenMemory  │
│  port 3000   │     │  port 8123   │     │  port 8080   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  mcp/threejs │
                    │  Three.js 3D │
                    │  port 3108   │
                    └──────────────┘
```

## Repository Structure

```
/
├── agents/          → Python LangGraph agent (Gemini-powered)
├── apps/            → Next.js 16 + CopilotKit frontend
├── mcp/             → MCP servers (add new ones here)
│   └── threejs/     → Three.js 3D visualization MCP
├── open_memory/          → CaviraOSS/OpenMemory (git submodule)
├── docker/          → Dockerfiles for all services
├── docker-compose.yml
├── package.json     → pnpm monorepo root
└── pnpm-workspace.yaml  → "apps/", "mcp/*"
```

## Quick Start

```bash
# 1. Clone with submodules
git clone --recurse-submodules <repo-url>
cd zstyle-services

# 2. Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 3. Run with Docker
docker compose up --build

# 4. Open http://localhost:3000
```

## Development (without Docker)

```bash
# Install JS dependencies
pnpm install

# Start all JS apps (frontend + MCP servers)
pnpm dev

# Start agent separately (requires Python 3.12+ and uv)
cd agents && uv run langgraph dev --port 8123 --no-browser
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 3000 | Next.js frontend with CopilotKit chat + canvas |
| `agent` | 8123 | LangGraph agent with Gemini LLM |
| `mcp-threejs` | 3108 | Three.js 3D visualization MCP server |
| `open_memory` | 8080 | OpenMemory persistent memory + MCP |

## Adding a New MCP Server

1. Create `mcp/your-server/` with a `package.json`
2. It auto-registers as a pnpm workspace (via `mcp/*` glob)
3. Add a Dockerfile at `docker/Dockerfile.mcp-your-server`
4. Add a service entry in `docker-compose.yml`

## Environment Variables

See [.env.example](.env.example) for all configuration options.

## Tech Stack

- **Frontend**: Next.js 16, React 19, TailwindCSS 4, CopilotKit v2
- **Agent**: LangGraph (Python), Google Gemini (gemini-2.0-flash)
- **Memory**: CaviraOSS/OpenMemory (SQLite + Gemini embeddings)
- **MCP**: Three.js visualization server
- **Infra**: Docker Compose, Turborepo, pnpm workspaces
