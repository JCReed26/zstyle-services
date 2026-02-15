# ZStyle Services - CopilotKit + LangGraph + OpenMemory

## Purpose

AI-powered monorepo: CopilotKit frontend, LangGraph agent (Gemini), persistent memory (OpenMemory), and extensible MCP servers. The todo list demonstrates **agent-driven UI** with bidirectional state sync.

## Architecture

This is a **Turborepo monorepo** with three services:

### Repository Structure

```
/
├── agents/                          # 🎯 PRIMARY: AI Engineering Focus
│   ├── main.py                      # Agent entry point (2 endpoints)
│   ├── pyproject.toml               # Python deps (uv)
│   ├── langgraph.json               # LangGraph config (2 endpoints)
│   ├── README.md                    # Agent development guide
│   └── src/
│       └── agents/                  # Agent graph definitions
│           ├── exec_func_coach/     # Executive function coach with OpenMemory
│           └── personal_assistant/ # Connections assistant (basic chat)
├── frontend/                        # 🎨 SUPPORTING: UI Layer
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Main page
│   │   │   └── api/copilotkit/      # CopilotKit API route
│   │   ├── components/
│   │   │   ├── canvas/              # Todo list UI (agent state driven)
│   │   │   ├── example-layout/      # Layout: chat + canvas side-by-side
│   │   │   └── generative-ui/       # Generative UI components
│   │   └── hooks/                   # CopilotKit hooks
│   └── package.json
├── mcp/                             # 🔌 MCP SERVERS: Extensible Tools
│   ├── README.md                    # MCP development guide
│   └── open_memory/                 # OpenMemory persistent memory MCP (git submodule)
├── infrastructure/                  # 🔧 SUPPORTING: Services
│   └── docker/                      # Dockerfiles
│       ├── Dockerfile.agent
│       └── Dockerfile.app
├── docker-compose.yml               # 3 services: memory, agent, app
├── package.json                     # pnpm monorepo root with Turborepo
├── pnpm-workspace.yaml              # "frontend/", "mcp/*"
└── turbo.json
```

## Agents

Two simple chatbot agents:

1. **exec_func_coach**: Executive function coach with OpenMemory MCP for persistent context
2. **personal_assistant**: Basic connections assistant (no MCP)

## Configuration

- **LLM**: Google Gemini (`gemini-2.0-flash` default, configurable via `GEMINI_MODEL`)
- **Endpoints**: `exec_func_coach`, `personal_assistant`
- **Frontend**: Connects to `exec_func_coach` endpoint
- **MCP**: OpenMemory persistent memory (connected to exec_func_coach only)

## Development

```bash
pnpm install          # Install JS dependencies
pnpm dev              # Start frontend
cd agents && uv run langgraph dev --port 8123 --no-browser  # Start agent

# Or with Docker:
docker compose up --build
```

## Services

| Service | Port | Tech |
|---------|------|------|
| app | 3000 | Next.js 16, CopilotKit v2 |
| agent | 8123 | LangGraph, Gemini (2 endpoints) |
| memory | 8080 | OpenMemory (SQLite + Gemini embeddings) |

## Environment

```bash
GOOGLE_API_KEY=       # Required: Gemini LLM + OpenMemory embeddings
LANGSMITH_API_KEY=    # Optional: LangSmith tracing
```
