# ZStyle Services - Architecture Documentation

## Overview

ZStyle Services is an AI-powered Executive Function Coach system built on Google's Agent Development Kit (ADK). It provides a personal productivity assistant that helps users manage goals, tasks, schedules, and build systems that work for their individual needs.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Communication Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Telegram   │  │    API       │  │   Webhook    │      │
│  │   Channel    │  │   Bridge     │  │   Router     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                 │
│                    NormalizedMessage                        │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Routing Layer                          │
│                    MessageRouter                            │
│  - Normalizes messages                                      │
│  - Manages ADK sessions                                     │
│  - Routes to agent layer                                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Agent Layer                            │
│              Google ADK Runner + Agents                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Executive Function Coach Agent              │    │
│  │  - Goal setting and tracking                        │    │
│  │  - Task management                                  │    │
│  │  - Calendar integration                             │    │
│  │  - Memory-aware coaching                            │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Memory     │   │    Tools     │   │  Sessions    │
│   Service    │   │              │   │              │
│ (OpenMemory) │   │ TickTick     │   │  (InMemory)  │
│              │   │ Google APIs  │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Core Components

### 1. Communication Layer (`channels/`)

**Purpose**: Abstract away channel-specific details and provide a unified interface to the agent layer.

#### Base Channel Architecture

- **`BaseInputChannel`**: Abstract base for all channels
  - Handles message normalization
  - Provides response sending interface
  - Used for stateless channels (webhooks, API endpoints)

- **`ConversationalChannel`**: Extended base for chat interfaces
  - Maintains conversation context with 300-second keep-alive
  - Handles session management
  - Used for Telegram, Discord, Slack, etc.

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
- Enables multi-channel user experiences

#### Current Channels

**Telegram Channel** (`channels/telegram_bot/`)
- Supports text, images, voice, documents
- Commands: `/start`, `/newchat`, `/help`, `/logs`
- Webhook and polling modes
- User ID mapping (Telegram ID → Internal User ID)

**API Bridge** (`main.py` - `/api/chat`)
- HTTP endpoint for external integrations
- Accepts `BridgeRequest` (JSON-safe NormalizedMessage)
- Base64-encoded attachments

### 2. Routing Layer (`channels/router.py`)

**Purpose**: Bridge between communication layer and agent layer.

#### MessageRouter Responsibilities

1. **Message Normalization**: Converts NormalizedMessage to ADK Content format
2. **Session Management**: Creates/maintains ADK sessions per user
3. **Agent Invocation**: Routes messages to ADK Runner
4. **Activity Logging**: Logs all user interactions
5. **Error Handling**: Graceful error recovery

#### Flow

```
NormalizedMessage → MessageRouter.route()
    ↓
1. Log incoming message
    ↓
2. Get/create ADK session
    ↓
3. Convert to ADK Content format
    ↓
4. Run agent via ADK Runner
    ↓
5. Log response
    ↓
6. Return text response
```

**Why separate routing layer?**
- Single point of integration for all channels
- Centralized session management
- Consistent error handling
- Activity logging in one place
- Easy to add middleware (rate limiting, auth, etc.)

### 3. Agent Layer (`agents/`)

**Purpose**: Core AI agent logic using Google ADK framework.

#### Google ADK Integration

**ADK (Agent Development Kit)** provides:
- Agent execution framework
- Session management
- Memory service integration
- Tool calling infrastructure
- Multi-modal support (text, images, audio)

**Why ADK?**
- DEV FILL IN: [Reasoning for choosing ADK over other frameworks]
- Provides built-in session management
- Integrates with Google's Gemini models
- Supports tool calling and memory services
- Handles complex agent workflows

#### Executive Function Coach Agent

**Location**: `agents/exec_func_coach/`

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
- Automatically stores session data to OpenMemory
- Retrieves relevant memories for context
- Persists user preferences, goals, and systems
- No manual memory management required

### 4. Memory Service (`services/memory/`)

**Purpose**: Long-term memory storage using OpenMemory.

#### OpenMemory Architecture

**OpenMemory** is a separate HTTP service that provides:
- Vector-based memory storage
- Semantic search capabilities
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

**Why OpenMemory?**
- DEV FILL IN: [Reasoning for choosing OpenMemory]
- Provides semantic search (RAG capabilities)
- Separate service enables scaling
- User-isolated memory storage
- Metadata support for filtering

**Memory Flow**:
```
ADK Session → OpenMemoryADKService.add_session_to_memory()
    ↓
Format session data as content string
    ↓
OpenMemoryClient.store_memory()
    ↓
OpenMemory HTTP API
    ↓
Vector storage + indexing
```

**Memory Retrieval**:
```
Agent needs context → ADK Runner calls search_memory()
    ↓
OpenMemoryADKService.search_memory()
    ↓
OpenMemoryClient.search_memories()
    ↓
Semantic search in OpenMemory
    ↓
Formatted results returned to agent
```

### 5. Database Layer (`core/database/`)

**Purpose**: Persistent storage for users, credentials, activity logs, and memories.

#### Database Models

**User** (`core/database/models/user.py`)
- Core user identity
- Maps channel IDs (Telegram, Discord) to internal user IDs
- User profile information

**Credential** (`core/database/models/credential.py`)
- Encrypted OAuth tokens and API keys
- Supports refresh tokens
- Expiration tracking
- **SECURITY**: Never indexed by RAG/memory systems

**ActivityLog** (`core/database/models/activity_log.py`)
- Timestamped user activity tracking
- Source tracking (Telegram, API, System, etc.)
- Structured extra_data for filtering

**UserMemory** (`core/database/models/memory.py`)
- DEV FILL IN: [Purpose and usage]
- May be redundant with OpenMemory - needs clarification

#### Database Engine

**Current Setup**:
- Development: SQLite (`sqlite+aiosqlite:///zstyle.db`)
- Production: PostgreSQL (commented out, needs environment variable)

**Why SQLAlchemy Async?**
- Async/await support for FastAPI
- Type-safe queries
- Migration support (Alembic)
- Database-agnostic queries

**Issues**:
- ⚠️ Production config is commented out (see NECESSARY-FIXES.md)
- ⚠️ No migrations directory (Alembic initialized but not used)
- ⚠️ Duplicate `database/` directory exists (legacy code)

### 6. Services Layer (`services/`)

**Purpose**: Business logic and external service integrations.

#### Key Services

**CredentialService** (`services/credential_service.py`)
- Encrypts/decrypts sensitive tokens
- Stores credentials per user/service
- Handles token refresh logic
- Uses Fernet encryption (PBKDF2 key derivation)

**ActivityLogService** (`services/activity_log.py`)
- Logs user interactions
- Retrieves recent activity
- Formats logs for display

**TickTickService** (`services/ticktick/ticktick_service.py`)
- OAuth flow for TickTick
- Client initialization
- Token management

### 7. Security Layer (`core/security.py`)

**Purpose**: Encryption and security utilities.

#### Encryption

**Credential Encryption**:
- Uses Fernet (symmetric encryption)
- Key derived from SECRET_KEY via PBKDF2HMAC
- Encrypts tokens, refresh tokens, API keys

**Issues**:
- ⚠️ Salt derived from SECRET_KEY (weakens security)
- ⚠️ No key rotation mechanism
- ⚠️ Single point of failure if SECRET_KEY compromised

**Webhook Verification**:
- ⚠️ Not implemented (placeholder returns False)
- ⚠️ Security risk for webhook endpoints

### 8. API Layer (`interface/`)

**Purpose**: HTTP endpoints and OAuth flows.

#### Routes

**API Routes** (`interface/api/routes.py`)
- `/api/health` - Health check
- `/api/user/state` - User state retrieval

**OAuth Routes** (`interface/oauth/`)
- Google OAuth flow
- TickTick OAuth flow

**Webhook Routes** (`interface/telegram_webhook.py`)
- `/webhook/telegram` - Telegram webhook endpoint
- Processes Telegram updates
- Routes to TelegramChannel

## Data Flow Examples

### Example 1: User sends Telegram message

```
1. Telegram → Webhook endpoint
   ↓
2. TelegramChannel.process_webhook_update()
   ↓
3. Normalize to NormalizedMessage
   ↓
4. MessageRouter.route()
   ↓
5. Get/create ADK session
   ↓
6. Convert to ADK Content
   ↓
7. ADK Runner.run_async()
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

### Example 3: Agent creates TickTick task

```
1. Agent decides to create task
   ↓
2. Calls TickTick tool
   ↓
3. Tool fetches credentials via CredentialService
   ↓
4. Decrypts OAuth token
   ↓
5. Initializes TickTickClient
   ↓
6. Creates task via TickTick API
   ↓
7. Returns result to agent
   ↓
8. Agent responds to user
```

## Deployment Architecture

### Docker Compose Setup

**Services**:
1. **app**: Main FastAPI + ADK service (port 8000)
2. **telegram-bot**: Telegram channel (connects to app)
3. **openmemory**: OpenMemory HTTP server (port 8080)

**Current Issues**:
- ⚠️ SQLite file shared between containers (locking issues)
- ⚠️ No production docker-compose override
- ⚠️ No nginx/SSL termination

### Environment Configuration

**Required Variables**:
- `GOOGLE_API_KEY`: Gemini API key
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `SECRET_KEY`: Encryption key (32+ chars)

**Optional Variables**:
- `DATABASE_URL`: PostgreSQL connection string
- `OPENMEMORY_URL`: OpenMemory service URL
- `OPENMEMORY_API_KEY`: OpenMemory API key
- OAuth client IDs/secrets

## Scalability Considerations

### Current Limitations

1. **In-Memory Session Storage**
   - Sessions lost on restart
   - Cannot scale horizontally
   - No session persistence

2. **SQLite Database**
   - Single-file database
   - No concurrent writes
   - Not suitable for production

3. **In-Memory Conversation Contexts**
   - Lost on restart
   - No sharing between instances

### Scaling Strategy

**Short-term**:
- Replace SQLite with PostgreSQL
- Use Redis for session storage
- Use Redis for conversation contexts

**Long-term**:
- Horizontal scaling with load balancer
- Database read replicas
- Caching layer (Redis)
- Message queue for async processing

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
- **Telegram**: Bot API

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Local development
- **SQLite**: Development database
- **PostgreSQL**: Production database (planned)

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
- DEV FILL IN: [Reasoning]
- Semantic search capabilities
- Vector-based storage
- Separate scaling concerns

### Why In-Memory Sessions?

**Decision**: Use InMemorySessionService for ADK sessions.

**Rationale**:
- DEV FILL IN: [Initial reasoning - likely simplicity]
- **Issue**: Doesn't scale, needs replacement

### Why SQLite for Development?

**Decision**: Use SQLite for local development.

**Rationale**:
- Simple setup (no database server needed)
- Easy to reset during development
- Fast for small datasets
- **Issue**: Production config commented out

## Future Architecture Considerations

### Planned Features

1. **Agent-to-Agent (A2A)**
   - Multiple specialized agents
   - Agent orchestration
   - Currently disabled (`a2a=False`)

2. **MCP Servers**
   - Telegram MCP for group chats
   - Twilio MCP for voice reminders

3. **Admin Dashboard**
   - User management
   - Activity viewing
   - System monitoring

### Architecture Evolution

**Current**: Monolithic FastAPI app with separate channel processes

**Future Considerations**:
- Microservices architecture (if team grows)
- Event-driven architecture (for agent-to-agent)
- Serverless functions (for specific tasks)

**When to Consider**:
- Team size > 8 developers
- Need independent deployment schedules
- Different scaling requirements per component
- Technology diversity requirements

## Glossary

- **ADK**: Agent Development Kit (Google framework)
- **A2A**: Agent-to-Agent communication
- **MCP**: Model Context Protocol
- **RAG**: Retrieval-Augmented Generation
- **NormalizedMessage**: Standard message format across channels
- **ConversationContext**: Short-term conversation state (300s keep-alive)
- **ADK Session**: ADK framework session (separate from conversation context)
