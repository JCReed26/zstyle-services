# Monorepo Restructure Plan

## What Currently Exists

Everything lives under `zstyle-frontend/` subdirectory:

```
zstyle-frontend/
├── apps/
│   ├── app/         → Next.js 16 + CopilotKit frontend (chat + canvas + generative UI)
│   ├── agent/       → Python LangGraph agent (todo tools, CopilotKit state sync, OpenAI gpt-5.2)
│   └── mcp/         → Three.js visualization MCP server (Node.js)
├── docker/
│   ├── Dockerfile.app
│   ├── Dockerfile.agent
│   └── Dockerfile.mcp
├── docker-compose.yml   → 3 services: agent(8123), mcp(3108), app(3000)
├── package.json         → pnpm monorepo root with Turborepo
├── pnpm-workspace.yaml  → workspace: apps/app, apps/agent, apps/mcp
├── turbo.json
├── .env.example
├── CLAUDE.md
├── README.md
└── TODO.md
```

**Key observations:**
- Agent uses `openai` + `langchain-openai` with `gpt-5.2` → must switch to Gemini
- Agent connects to CopilotKit MCP at `https://mcp.copilotkit.ai` → no OpenMemory connection
- Frontend has full CopilotKit v2 setup with bidirectional state sync → keep as-is
- Three.js MCP server is self-contained → keep as-is
- Docker Compose uses `copilotkit-network` bridge → will expand for OpenMemory
- Turborepo orchestrates dev/build for JS packages → keep (it's useful, not bloat)

---

## Target Structure

```
/ (repo root)
├── agents/                → Python LangGraph agent (moved from apps/agent/)
│   ├── main.py
│   ├── pyproject.toml
│   ├── langgraph.json
│   └── src/
├── apps/                  → Next.js CopilotKit frontend (moved from apps/app/)
│   ├── src/
│   ├── package.json
│   └── ...
├── mcp/                   → Root-level MCP directory (scalable, add more servers here)
│   └── threejs/           → Three.js visualization MCP (moved from apps/mcp/)
│       ├── server.ts
│       ├── package.json
│       └── ...
├── open_memory/                → CaviraOSS/OpenMemory service (NEW)
│   └── (cloned/configured OpenMemory source)
├── docker/
│   ├── Dockerfile.agent
│   ├── Dockerfile.app
│   ├── Dockerfile.mcp-threejs
│   └── Dockerfile.openmemory
├── docker-compose.yml     → 4 services: agent, app, mcp-threejs, memory
├── package.json           → pnpm monorepo root (for JS packages)
├── pnpm-workspace.yaml    → workspace: "Apps/", "MCP/*"
├── turbo.json
├── .env.example
└── README.md
```

**Why `mcp/*` glob in pnpm-workspace.yaml:** Every subdirectory under `mcp/` with a `package.json` becomes a workspace package automatically. To add a new MCP server later, just create `mcp/my-new-server/` with a `package.json` — no config changes needed.

---

## Changes By Step (with git commits)

### Step 1: Flatten repo structure to root
**What:** Move all files from `zstyle-frontend/` to repo root. Remove the wrapper directory.
**Files moved:** Everything under `zstyle-frontend/` → `/`
**Git commit:** `"restructure: flatten zstyle-frontend/ to repo root"`

### Step 2: Rename directories to match target layout
**What:**
- `apps/app/` → `Apps/`
- `apps/agent/` → `agents/`
- `apps/mcp/` → `mcp/threejs/`
- `docker/` → `docker/`
- Remove empty `apps/` directory
**Update:**
- `pnpm-workspace.yaml` → `packages: ["apps/", "mcp/*"]`
- `package.json` scripts → update turbo filter names to match new package names
- Turbo config → no changes (task-based, not path-based)
**Git commit:** `"restructure: rename to Agents/, Apps/, MCP/threejs/, Docker/"`

### Step 3: Add CaviraOSS/OpenMemory as Memory service
**What:**
- Create `open_memory/` directory
- Clone CaviraOSS/OpenMemory or add as git submodule
- OpenMemory runs on port **8080**, dashboard UI included, MCP endpoint at `/mcp`
- Uses SQLite by default (zero config)
- Configure to use Gemini embeddings (avoids OpenAI cost)
**New files:**
- `open_memory/` — OpenMemory source
- `Docker/Dockerfile.openmemory` — builds OpenMemory
**Git commit:** `"feat: add CaviraOSS/OpenMemory as Memory service"`

### Step 4: Switch agent from OpenAI to Google Gemini
**What:**
- In `agents/pyproject.toml`: remove `openai`, `langchain-openai`; add `langchain-google-genai`; bump `langchain>=1.2.5`
- In `agents/main.py`: replace `model="gpt-5.2"` with Gemini model via `ChatGoogleGenerativeAI`
- In `.env.example`: replace `OPENAI_API_KEY` with `GOOGLE_API_KEY`
**Git commit:** `"feat: switch agent LLM from OpenAI to Google Gemini"`

### Step 5: Connect agent to OpenMemory MCP
**What:**
- In `agents/main.py`: add OpenMemory as a second MCP server in the `MultiServerMCPClient` config
- The agent connects to `http://memory:8080/mcp` over Docker network
- This gives the agent: `openmemory_query`, `openmemory_store`, `openmemory_list`, `openmemory_get`, `openmemory_reinforce`
- Keep existing CopilotKit MCP connection alongside it
**Code change in main.py:**
```python
client = MultiServerMCPClient({
    "copilotkit": {
        "transport": "http",
        "url": "https://mcp.copilotkit.ai",
    },
    "openmemory": {
        "transport": "http",
        "url": os.environ.get("OPENMEMORY_MCP_URL", "http://localhost:8080/mcp"),
    }
})
```
**Git commit:** `"feat: connect LangGraph agent to OpenMemory MCP"`

### Step 6: Update Docker Compose for all 4 services + update Dockerfiles
**What:**
- Add `memory` service (port 8080, OpenMemory with dashboard)
- Update `agent` service: `GOOGLE_API_KEY` env, `OPENMEMORY_MCP_URL=http://memory:8080/mcp`, depends_on memory
- Rename `mcp` → `mcp-threejs` for clarity (future MCPs will have their own names)
- Update all Dockerfile COPY paths to match new directory names
- `docker/Dockerfile.agent` → paths from `agents/`
- `docker/Dockerfile.app` → paths from `apps/`
- `docker/Dockerfile.mcp-threejs` → paths from `mcp/threejs/`
- `docker/Dockerfile.openmemory` → new, builds OpenMemory
- All services on `copilotkit-network`
**Service dependency chain:**
```
memory (8080) ← agent (8123) depends_on memory
                    ↑
mcp-threejs (3108)  app (3000) depends_on agent (healthy)
```
**Git commit:** `"feat: docker-compose with 4 services, updated Dockerfiles"`

### Step 7: Verify frontend networking over Docker
**What:**
- Verify `apps/src/app/api/copilotkit/route.ts` uses `LANGGRAPH_DEPLOYMENT_URL` env var correctly (it does: `http://agent:8123`)
- Verify `apps/src/app/api/copilotkit/ag-ui-middleware.ts` uses `MCP_SERVER_URL` env var
- Verify docker-compose passes correct env vars to the app service
- Fix if any references are stale after the move
**Git commit (if changes needed):** `"fix: frontend Docker network configuration"`

### Step 8: Update README.md, .env.example, and cleanup
**What:**
- Rewrite `README.md`: QuickStart guide, architecture overview, service descriptions, how to add new MCP servers
- Update `.env.example` with all required env vars
- Update `agents/langgraph.json` env path (was `../../.env`, now `../.env`)
- Clean up stale `CLAUDE.md` path references
- Update `.gitignore` if needed
**Git commit:** `"docs: README, env config, and cleanup for new monorepo structure"`

### Step 9: Final push
**What:** Push all commits to `claude/setup-monorepo-structure-m4dwF`

---

## Environment Variables (Final State)

```env
# Required: Google Gemini API key for the LangGraph agent
GOOGLE_API_KEY=

# Optional: LangSmith for tracing
LANGSMITH_API_KEY=

# Docker service URLs (auto-configured in docker-compose.yml)
# LANGGRAPH_DEPLOYMENT_URL=http://agent:8123
# MCP_SERVER_URL=http://mcp-threejs:3108/mcp
# OPENMEMORY_MCP_URL=http://memory:8080/mcp
```

---

## Decisions Made

1. **Keep Turborepo + pnpm workspaces** — useful for orchestrating dev/build/lint across Apps/ and all MCP/* packages. Not bloat.
2. **`MCP/*` glob workspace** — every subdirectory under `MCP/` auto-registers as a pnpm workspace. Add new MCPs by just creating a folder. No config edits needed.
3. **MCP service naming** — Docker services for MCPs use `mcp-<name>` convention (e.g., `mcp-threejs`). Easy to add `mcp-foo` later in docker-compose.
4. **OpenMemory uses SQLite** by default — zero config, no extra DB service. Can switch to PostgreSQL later by adding a `db` service.
5. **Agent keeps both MCP connections** — CopilotKit MCP (generative UI tools) + OpenMemory MCP (persistent memory).
6. **Gemini model** — `gemini-2.0-flash` as default (fast, capable, generous free tier). Configurable via env var.
7. **agents/ is NOT a pnpm workspace** — it's Python-only (uv/pyproject.toml). pnpm workspaces only cover JS packages.
