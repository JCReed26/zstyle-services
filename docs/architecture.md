# ZStyle Architecture Overview

## System Diagram

```
                            +---------------------------+
                            |     COMMUNICATION LAYER   |
                            +---------------------------+
                            |   BaseInputChannel (ABC)  |
                            |   - TelegramChannel       |
                            |   - APIChannel (ADK Dev)  |
                            |   - [Future: Discord...]  |
                            +-------------+-------------+
                                          |
                                          v
                            +---------------------------+
                            |      MESSAGE ROUTER       |
                            |   (Normalizes input to    |
                            |    ADK-compatible format) |
                            +-------------+-------------+
                                          |
                                          v
+------------------+        +---------------------------+        +---------------------+
|  STRUCTURED DB   | <----> |       AGENT LAYER         | <----> |  OPENMEMORY STORE   |
| (SQLite/Postgres)|        +---------------------------+        | (Local Vector DB)   |
| - Users          |        |  exec_func_coach (root)   |        | - Semantic Search   |
| - Activity Logs  |        |  - sub_agent_1 (future)   |        | - RAG Capabilities  |
| - Credentials    |        |  - sub_agent_2 (future)   |        +---------------------+
+------------------+        +---------------------------+
                            |  ZStyleMemoryService      |
                            |  OpenMemoryService        |
                            +---------------------------+
```

## Core Components

### 1. Communication Layer (`/channels/`)

Input channels handle receiving messages from external sources and sending responses.

- **BaseInputChannel**: Abstract base class for all channels
- **ConversationalChannel**: Extended base for human chat interfaces (300s keep-alive)
- **TelegramChannel**: Telegram bot implementation
- **MessageRouter**: Bridges channels to ADK agent layer

### 2. Agent Layer (`/agents/`)

AI agents powered by Google ADK (Gemini models).

- **exec_func_coach**: Root agent - Executive Function Coach
- Sub-agents can be added for specialized tasks

### 3. Memory Service (`/services/memory/`)

**Memory-First Architecture**: Instead of storing chat history, we use structured and semantic memory.

- **ZStyleMemoryService**: Manages standardized slots (CURRENT_GOAL, USER_PREFERENCES, etc.) in the structured SQL database.
- **OpenMemoryService**: Provides a local vector-based memory engine for semantic search and long-term storage (RAG).
- **UserContext**: Aggregated view for agent injection, combining both structured and semantic insights.

### 4. Database (`/database/`)

SQLite for development, PostgreSQL (Supabase) for production.

**Models:**
- `User`: Core user entity with channel mappings
- `UserMemory`: Structured memory storage
- `ActivityLog`: Per-user activity tracking
- `Credential`: Secure token storage (isolated from RAG)

### 5. Activity Logging (`/services/activity_log.py`)

Per-user chronological log of all system interactions for transparency.

## Data Flow

### User Message Flow

1. User sends message via channel (Telegram, etc.)
2. Channel normalizes to `NormalizedMessage`
3. Router loads user context from memory
4. Router converts to ADK Content format
5. Agent processes with context
6. Response sent back through channel
7. Activity logged

### Memory Flow

1. Agent needs user context → calls `get_user_context()`
2. Memory service loads standardized slots
3. Context injected into agent prompt
4. Agent makes decisions based on context
5. Important information stored back to memory slots

## Governance Rules

1. **Secrets Isolation**: Credentials table is NEVER indexed by RAG
2. **Channel Agnosticism**: Agent code never imports from `/channels/`
3. **Memory Standardization**: Use `MemorySlot` enum for common data

## Directory Structure

```
zstyle-services/
├── main.py                          # FastAPI + ADK entrypoint
├── reset_db.py                      # Database reset script
├── docker-compose.yml               # Container orchestration
├── Dockerfile
├── agents/
│   └── exec_func_coach/
│       ├── agent.py                 # Root agent definition
│       └── tools.py                 # Agent tools
├── channels/
│   ├── base.py                      # BaseInputChannel ABC
│   ├── router.py                    # MessageRouter
│   └── telegram_bot/
│       └── channel.py               # TelegramChannel
├── database/
│   ├── engine.py                    # SQLAlchemy setup
│   └── models/
│       ├── user.py
│       ├── memory.py
│       ├── activity_log.py
│       └── credential.py
├── services/
│   ├── activity_log.py
│   └── memory/
│       └── memory_service.py
└── docs/
    └── architecture.md
```

## Adding New Components

### Adding a New Channel

1. Create directory: `channels/your_channel/`
2. Implement `BaseInputChannel` or `ConversationalChannel`
3. Add to docker-compose.yml as a new service
4. Set `AGENT_URL=http://app:8000`

### Adding a New Agent

1. Create directory: `agents/your_agent/`
2. Define agent with tools
3. Add as sub_agent to exec_func_coach or expose independently

### Adding a New Memory Slot

1. Add to `MemorySlot` enum in `database/models/memory.py`
2. Document expected data structure
3. Update agent instructions to reference the slot
