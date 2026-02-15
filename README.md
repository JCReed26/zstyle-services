# ZStyle Services

> This repo is for the autonomous-executive-assistant. It is becoming the backend to a dream app of mine.

AI-powered monorepo with CopilotKit frontend, LangGraph agent (Gemini), persistent memory (OpenMemory), and extensible MCP servers.

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

## Development

```bash
# Without Docker - Install JS dependencies
pnpm install

# Start frontend
pnpm dev

# Start agent (requires Python 3.12+ and uv)
cd agents && uv run langgraph dev --port 8123 --no-browser

# Environment setup
cp .env.example .env
# Add GOOGLE_API_KEY to .env
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 3000 | Next.js frontend with CopilotKit chat |
| `agent` | 8123 | LangGraph agent with Gemini LLM (2 endpoints: exec_func_coach, personal_assistant) |
| `memory` | 8080 | OpenMemory persistent memory + MCP |

## Tech Stack

- **Frontend**: Next.js 16, React 19, TailwindCSS 4, CopilotKit v2
- **Agents**: LangGraph (Python), Google Gemini (gemini-2.0-flash), 2 endpoints
- **Memory**: CaviraOSS/OpenMemory (SQLite + Gemini embeddings, MCP server)
- **Infra**: Docker Compose, Turborepo, pnpm workspaces
