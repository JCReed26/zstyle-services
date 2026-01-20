# ZStyle Services - Architecture Documentation

## Overview

ZStyle Services is an AI-powered Executive Function Coach system built on Google's Agent Development Kit (ADK). It provides a personal productivity assistant that helps users manage goals, tasks, schedules, and build systems that work for their individual needs.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Communication Layer (channels/)                        │
│ - TelegramChannel (polling mode)                       │
│ - API Bridge (/api/chat)                               │
│ - NormalizedMessage abstraction                        │
└───────────────────┬───────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Routing Layer (channels/router.py)                     │
│ - MessageRouter                                        │
│ - Routes to ADK Runner                                 │
│ - Activity logging                                      │
└───────────────────┬───────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│ Agent Layer (agent/exec_func_coach/)                   │
│ - Google ADK Runner                                    │
│ - Executive Function Coach Agent                       │
│ - Tools: TickTick, Google Calendar, Gmail              │
└───────────────────┬───────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Memory   │  │ Database │  │ Services │
│(OpenMem) │  │(Supabase)│  │(Creds,   │
│          │  │          │  │ Auth)    │
└──────────┘  └──────────┘  └──────────┘
```

## Core Components

### 1. Communication Layer (`channels/`)

**Purpose**: Abstract away channel-specific details and provide a unified interface to the agent layer.

#### NormalizedMessage Format

All channels convert their native message format to `NormalizedMessage`:

```python
@dataclass
class NormalizedMessage:
    channel: str                    # "telegram", "api", etc.
    user_id: str                    # Internal ZStyle user ID
    channel_user_id: str            # Channel-specific user ID
    session_id: str                 # Conversation session ID
    content_type: MessageType       # TEXT, IMAGE, VOICE, etc.
    text: Optional[str]             # Message text
    attachments: List[bytes]        # Binary attachments
    metadata: Dict[str, Any]       # Channel-specific metadata
```

**Why this design?**
- Agents never need to know which channel a message came from
- Easy to add new channels without changing agent code
- Consistent interface for all communication sources

#### Current Channels

**Telegram Channel** (`channels/telegram_bot/`)
- Supports text, images, voice, documents
- Commands: `/start`, `/newchat`, `/help`, `/logs`
- Uses polling mode (no webhook)
- User ID mapping (Telegram ID → Internal User ID)

**API Bridge** (`app/main.py` - `/api/chat`)
- HTTP endpoint for external integrations
- Accepts `BridgeRequest` (JSON-safe NormalizedMessage)
- Base64-encoded attachments

### 2. Routing Layer (`channels/router.py`)

**Purpose**: Bridge between communication layer and agent layer.

#### MessageRouter Responsibilities

1. **Message Conversion**: Converts NormalizedMessage to ADK Content format
2. **Agent Invocation**: Routes messages to ADK Runner
3. **Activity Logging**: Logs all user interactions
4. **Error Handling**: Graceful error recovery

#### Flow

```
NormalizedMessage → MessageRouter.route()
    ↓
1. Log incoming message
    ↓
2. Get/create ADK session (ephemeral conversation state)
    ↓
3. Convert to ADK Content format
    ↓
4. Run agent via ADK Runner
    ↓
5. Agent retrieves long-term memory from OpenMemory
    ↓
6. Log response
    ↓
7. Return text response
```

**Why separate routing layer?**
- Single point of integration for all channels
- Consistent error handling
- Activity logging in one place
- Easy to add middleware (rate limiting, auth, etc.)

### 3. Agent Layer (`agent/exec_func_coach/`)

**Purpose**: Core AI agent logic using Google ADK framework.

#### Google ADK Integration

**ADK (Agent Development Kit)** provides:
- Agent execution framework
- Session management (ephemeral conversation state)
- Memory service integration (long-term semantic memory)
- Tool calling infrastructure
- Multi-modal support (text, images, audio)

#### Executive Function Coach Agent

**Location**: `agent/exec_func_coach/`

**Capabilities**:
1. **Personal Assistant**
   - Orchestrates multiple services
   - Manages reminders via memory service
   - Accesses user context and goals

2. **Executive Function Coach**
   - Goal setting and tracking
   - Task management and prioritization
   - Gentle reminders and accountability
   - Schedule organization
   - System design for users (including ADHD/Autism support)

**Tools Available**:
- **TickTick**: Task management (create, retrieve, update tasks)
- **Google Calendar**: Event management
- **Gmail**: Email management
- **OpenMemory**: Long-term memory storage

**Memory Integration**:
- Automatically stores conversation data to OpenMemory
- Retrieves relevant memories for context via semantic search
- Persists user preferences, goals, and systems
- No manual memory management required

### 4. Memory Service (`services/openmemory_adk_service.py`)

**Purpose**: Long-term semantic memory storage using OpenMemory.

#### OpenMemory Architecture

**OpenMemory** is a separate HTTP service that provides:
- Vector-based memory storage
- Semantic search capabilities (RAG)
- User namespacing for multi-tenancy
- Metadata support

**Integration Points**:
1. **OpenMemoryClient** (`services/openmemory_client.py`)
   - HTTP client for OpenMemory API
   - Handles authentication
   - Provides store/search methods

2. **OpenMemoryADKService** (`services/openmemory_adk_service.py`)
   - Implements ADK `BaseMemoryService` interface
   - Automatically called by ADK Runner
   - Converts ADK sessions to memory format

**Memory Flow**:
```
ADK Session → OpenMemoryADKService.add_session_to_memory()
    ↓
Format session data as content string
    ↓
OpenMemoryClient.store_memory()
    ↓
OpenMemory HTTP API → Vector storage + indexing
```

**Memory Retrieval**:
```
Agent needs context → ADK Runner calls search_memory()
    ↓
OpenMemoryADKService.search_memory()
    ↓
OpenMemoryClient.search_memories()
    ↓
Semantic search in OpenMemory → Formatted results returned to agent
```

**Note on Sessions vs Memory**:
- **ADK Sessions**: Ephemeral conversation state for managing the current request/response cycle. Stored in-memory, lightweight, not persisted.
- **OpenMemory**: Long-term semantic memory that persists across conversations. Stores user preferences, goals, past conversations, and retrieves relevant context via semantic search.

### 5. Database Layer (`database/`)

**Purpose**: Persistent storage for users, credentials, activity logs, and OAuth states.

#### Database Models

**User** (`database/models.py`)
- Core user identity
- Maps channel IDs (Telegram) to internal user IDs
- Links to Supabase Auth users

**Credential** (`database/models.py`)
- Encrypted OAuth tokens and API keys
- Supports refresh tokens
- Expiration tracking
- **SECURITY**: Never indexed by RAG/memory systems

**ActivityLog** (`database/models.py`)
- Timestamped user activity tracking
- Source tracking (Telegram, API, System, etc.)
- Structured extra_data for filtering

**OAuthState** (`database/models.py`)
- OAuth state tokens for CSRF protection
- Expiration tracking

#### Database Engine

**Current Setup**:
- Production: PostgreSQL (Supabase) - required
- Uses `DATABASE_URL` environment variable
- Async SQLAlchemy with connection pooling

**Repository Pattern**:
- All database operations go through repositories (`database/repositories.py`)
- Provides abstraction layer for database access
- Consistent error handling

### 6. Services Layer (`services/`)

**Purpose**: Business logic and external service integrations.

#### Key Services

**CredentialService** (`services/credential_service.py`)
- Encrypts/decrypts sensitive tokens using Fernet encryption
- Stores credentials per user/service
- Handles token refresh logic

**ActivityLogService** (`services/activity_log.py`)
- Logs user interactions
- Retrieves recent activity
- Formats logs for display

### 7. Security (`app/security.py`)

**Purpose**: Encryption utilities for sensitive data storage.

**Credential Encryption**:
- Uses Fernet symmetric encryption
- Key derived from SECRET_KEY via PBKDF2HMAC
- Encrypts tokens, refresh tokens, API keys
- Simple, effective encryption for credential storage

## Data Flow Examples

### Example 1: User sends Telegram message

```
1. Telegram polling → TelegramChannel receives update
   ↓
2. Normalize to NormalizedMessage
   ↓
3. MessageRouter.route()
   ↓
4. Get/create ADK session (ephemeral)
   ↓
5. Convert to ADK Content
   ↓
6. ADK Runner.run_async()
   ↓
7. Agent retrieves relevant memories from OpenMemory
   ↓
8. Agent processes with tools/memory
   ↓
9. Response collected
   ↓
10. TelegramChannel.send_response()
```

### Example 2: Agent accesses user memory

```
1. Agent needs context
   ↓
2. ADK Runner calls memory_service.search_memory()
   ↓
3. OpenMemoryADKService.search_memory()
   ↓
4. OpenMemoryClient.search_memories()
   ↓
5. HTTP GET to OpenMemory API
   ↓
6. Semantic search in vector store
   ↓
7. Results formatted and returned
   ↓
8. Agent uses context in response
```

## Deployment Architecture

### Docker Compose Setup

**Services**:
1. **app**: Main FastAPI + ADK service (port 8000)
2. **telegram-bot**: Telegram channel using polling (connects to app)
3. **openmemory**: OpenMemory HTTP server (port 8080)

### Environment Configuration

**Required Variables**:
- `GOOGLE_API_KEY`: Gemini API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `SECRET_KEY`: Encryption key (32+ chars)
- `DATABASE_URL`: PostgreSQL connection string (Supabase)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key

**Optional Variables**:
- `OPENMEMORY_URL`: OpenMemory service URL (default: http://openmemory:8080)
- `OPENMEMORY_API_KEY`: OpenMemory API key
- OAuth client IDs/secrets

## Technology Stack

### Core Framework
- **FastAPI**: Web framework (async, type-safe)
- **Google ADK**: Agent framework
- **SQLAlchemy**: ORM (async)
- **Pydantic**: Data validation

### External Services
- **OpenMemory**: Memory/RAG service
- **TickTick**: Task management API
- **Google APIs**: Calendar, Gmail
- **Telegram**: Bot API (polling mode)

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Local development
- **PostgreSQL**: Production database (Supabase)

## Design Decisions

### Why Separate Channels?

**Decision**: Abstract channels into separate layer with NormalizedMessage format.

**Rationale**:
- Agents don't need channel-specific knowledge
- Easy to add new channels
- Consistent interface
- Enables multi-channel users

### Why OpenMemory Instead of Database?

**Decision**: Use separate OpenMemory service for long-term memory.

**Rationale**:
- Semantic search capabilities (RAG)
- Vector-based storage
- Separate scaling concerns
- User-isolated memory storage

### Why In-Memory ADK Sessions?

**Decision**: Use InMemorySessionService for ADK sessions.

**Rationale**:
- ADK sessions are ephemeral conversation state (single request/response cycle)
- Long-term memory is handled by OpenMemory
- Simple implementation, no external dependencies
- Sessions are lightweight and don't need persistence

### Why PostgreSQL Only?

**Decision**: Use PostgreSQL (Supabase) for all environments.

**Rationale**:
- Production-ready from day one
- Supports concurrent access
- Scalable architecture
- Built-in authentication via Supabase Auth
- Row Level Security (RLS) support
- Managed service reduces operational overhead

## Glossary

- **ADK**: Agent Development Kit (Google framework)
- **MCP**: Model Context Protocol
- **RAG**: Retrieval-Augmented Generation
- **NormalizedMessage**: Standard message format across channels
- **ADK Session**: Ephemeral conversation state for managing request/response cycles
- **OpenMemory**: Long-term semantic memory storage with vector search
