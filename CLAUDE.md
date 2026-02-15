# ZStyle Services - CopilotKit + LangGraph + OpenMemory

## Purpose

AI-powered monorepo: CopilotKit frontend, LangGraph agent (Gemini), persistent memory (OpenMemory), and extensible MCP servers. The todo list demonstrates **agent-driven UI** with bidirectional state sync.

## Architecture

This is a **Turborepo monorepo** with four services:

### Repository Structure

```
/
├── agents/                          # Python LangGraph agent
│   ├── main.py                      # Agent entry point (Gemini + MCP clients)
│   ├── pyproject.toml               # Python deps (uv)
│   ├── langgraph.json               # LangGraph config
│   └── src/
│       ├── todos.py                 # Todo tools and AgentState schema
│       ├── query.py                 # Data query tool
│       └── db.csv                   # Sample data
├── Apps/                            # Next.js 16 frontend
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
├── mcp/                             # MCP servers (add new ones as subdirs)
│   └── threejs/                     # Three.js 3D visualization MCP
│       ├── server.ts                # MCP server entry
│       ├── server-utils.ts          # HTTP transport utils
│       ├── src/                     # React widget components
│       └── package.json
├── open_memory/                     # CaviraOSS/OpenMemory (git submodule)
├── docker/                          # Dockerfiles
│   ├── Dockerfile.agent
│   ├── Dockerfile.app
│   └── Dockerfile.mcp-threejs
├── docker-compose.yml               # 4 services: memory, agent, mcp-threejs, app
├── package.json                     # pnpm monorepo root with Turborepo
├── pnpm-workspace.yaml              # "apps/", "mcp/*"
└── turbo.json
```

## Key Pattern: Agent State with CopilotKit v2

State lives in the agent backend and syncs bidirectionally with the frontend.

1. **Agent defines state** (`agents/src/todos.py`): `AgentState(TypedDict)` with `todos: list[Todo]`
2. **Agent modifies state** via `manage_todos` tool → `Command(update={"todos": ...})`
3. **Frontend reads** via `useAgent()` hook → `agent.state.todos`
4. **Frontend writes** via `agent.setState({ todos: ... })`

## Agent Configuration

- **LLM**: Google Gemini (`gemini-2.0-flash` default, configurable via `GEMINI_MODEL`)
- **MCP Clients**: CopilotKit MCP (generative UI) + OpenMemory MCP (persistent memory)
- **Tools**: `manage_todos`, `get_todos`, `query_data`, + MCP tools

## Development

```bash
pnpm install          # Install JS dependencies
pnpm dev              # Start frontend + MCP servers
cd agents && uv run langgraph dev --port 8123 --no-browser  # Start agent

# Or with Docker:
docker compose up --build
```

## Services

| Service | Port | Tech |
|---------|------|------|
| app | 3000 | Next.js 16, CopilotKit v2 |
| agent | 8123 | LangGraph, Gemini |
| mcp-threejs | 3108 | Three.js MCP server |
| memory | 8080 | OpenMemory (SQLite + Gemini embeddings) |

## Environment

```bash
GOOGLE_API_KEY=       # Required: Gemini LLM + OpenMemory embeddings
LANGSMITH_API_KEY=    # Optional: LangSmith tracing
```
