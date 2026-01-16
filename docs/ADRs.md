# Architecture Decision Records (ADRs)

This document records architectural decisions made for the ZStyle Services project. Each ADR follows the standard format: Context, Decision, Consequences.

---

## ADR-001: Database Selection and Migration Strategy

**Status**: Proposed

**Date**: [Current Date]

**Context**:
The system needs persistent storage for users, credentials, activity logs, and memories. Currently using SQLite for development with plans to move to PostgreSQL for production.

**Decision**:
- Use SQLite for local development (simple setup, no server required)
- Use PostgreSQL for production (scalability, concurrent access)
- Use SQLAlchemy async for database abstraction
- Use Alembic for database migrations
- Environment-based configuration (DATABASE_URL environment variable)

**Consequences**:

**Positive**:
- SQLite enables fast local development
- PostgreSQL provides production scalability
- SQLAlchemy provides database-agnostic queries
- Alembic enables version-controlled schema changes
- Environment-based config follows 12-factor principles

**Negative**:
- Requires maintaining compatibility between SQLite and PostgreSQL
- Some PostgreSQL-specific features unavailable in SQLite
- Migration complexity for schema changes
- Additional infrastructure for PostgreSQL in production

**Alternatives Considered**:
- MongoDB: Rejected - relational data model better fits use case
- DynamoDB: Rejected - team familiarity with SQL, cost considerations
- Single database for all environments: Rejected - SQLite insufficient for production

**Implementation Notes**:
- Database URL automatically switches based on environment
- Connection pooling configured for PostgreSQL
- Migrations tested on both databases

---

## ADR-002: Session Storage Architecture

**Status**: Deprecated (Current: In-Memory)

**Date**: [Current Date]

**Context**:
ADK Runner requires session storage for maintaining conversation state. Current implementation uses InMemorySessionService which doesn't scale.

**Decision** (Current - Deprecated):
- Use InMemorySessionService for initial development
- Sessions stored in process memory
- Sessions lost on restart

**Consequences**:

**Positive**:
- Simple implementation
- No external dependencies
- Fast access

**Negative**:
- Sessions lost on restart
- Cannot scale horizontally
- No session persistence
- Poor user experience after deployments

**Decision** (Proposed):
- Replace with Redis-backed session storage
- Sessions persist across restarts
- Enables horizontal scaling
- TTL-based expiration

**Alternatives Considered**:
- PostgreSQL sessions: Rejected - Redis faster for session data
- Database sessions: Rejected - Performance concerns
- Stateless sessions (JWT): Considered but ADK requires session objects

**Implementation Plan**:
1. Create RedisSessionService implementing ADK BaseSessionService
2. Update main.py to use RedisSessionService
3. Add Redis to docker-compose.yml
4. Migrate existing sessions (if any)
5. Update tests

---

## ADR-003: Channel Abstraction with NormalizedMessage

**Status**: Accepted

**Date**: [Initial Implementation Date]

**Context**:
System needs to support multiple communication channels (Telegram, API, future Discord/Slack). Agents shouldn't need channel-specific knowledge.

**Decision**:
- Create channel abstraction layer
- All channels convert to NormalizedMessage format
- Agents receive NormalizedMessage, never channel-specific data
- MessageRouter handles conversion to ADK format

**Consequences**:

**Positive**:
- Agents are channel-agnostic
- Easy to add new channels
- Consistent interface
- Enables multi-channel users
- Clear separation of concerns

**Negative**:
- Additional abstraction layer
- Some channel-specific features may be lost
- Conversion overhead (minimal)

**Alternatives Considered**:
- Channel-specific agents: Rejected - code duplication
- Direct channel-to-agent integration: Rejected - tight coupling
- Message queue: Considered but overkill for current scale

**Examples**:
- Telegram channel converts Update → NormalizedMessage
- API bridge converts JSON → NormalizedMessage
- Future Discord channel converts Discord message → NormalizedMessage

---

## ADR-004: Memory Service Architecture (OpenMemory)

**Status**: Accepted

**Date**: [Implementation Date]

**Context**:
Agents need long-term memory that persists across conversations. Memory should support semantic search for context retrieval.

**Decision**:
- Use separate OpenMemory HTTP service
- Implement OpenMemoryADKService as ADK BaseMemoryService
- Memory automatically persisted by ADK Runner
- Semantic search via OpenMemory API

**Consequences**:

**Positive**:
- Semantic search capabilities (RAG)
- Separate service enables independent scaling
- User-isolated memory storage
- Metadata support for filtering
- Automatic memory persistence

**Negative**:
- Additional service dependency
- Network latency for memory operations
- Service availability critical for agent functionality
- Requires OpenMemory service deployment

**Alternatives Considered**:
- Database storage: Rejected - no semantic search
- In-memory storage: Rejected - doesn't persist
- Vector database (Pinecone/Weaviate): Considered but OpenMemory provides HTTP API integration

**Implementation Notes**:
- OpenMemory runs as separate Docker service
- Failures in memory operations don't break agent flow
- Memory search results formatted for ADK consumption

---

## ADR-005: Error Handling and Retry Strategy

**Status**: Proposed

**Date**: [Current Date]

**Context**:
Current error handling is generic and doesn't distinguish between transient and permanent failures. No retry logic for transient errors.

**Decision**:
- Classify errors as Transient or Permanent
- Implement retry logic for transient errors (exponential backoff)
- Provide user-friendly error messages based on error type
- Log all errors with correlation IDs

**Consequences**:

**Positive**:
- Better user experience
- Automatic recovery from transient failures
- Clearer error messages
- Reduced false error reports
- Better observability

**Negative**:
- Additional complexity
- Need to carefully classify errors
- Retry logic may mask underlying issues

**Error Classification**:
- Transient: Network errors, 5xx HTTP errors, timeouts
- Permanent: 4xx HTTP errors, validation errors, authentication errors

**Retry Strategy**:
- Max 3 attempts
- Exponential backoff (1s, 2s, 4s)
- Only retry transient errors
- Log all retry attempts

**Alternatives Considered**:
- Always retry: Rejected - may cause issues with permanent errors
- No retry: Current approach - poor user experience
- Circuit breaker: Considered for future implementation

---

## ADR-006: Encryption Key Management

**Status**: Accepted (with improvements needed)

**Date**: [Current Date]

**Context**:
Sensitive credentials (OAuth tokens, API keys) must be encrypted at rest. Current implementation uses Fernet encryption with key derived from SECRET_KEY.

**Decision** (Current):
- Use Fernet symmetric encryption
- Derive key from SECRET_KEY via PBKDF2HMAC
- Salt derived from SECRET_KEY (needs improvement)
- Single encryption key for all credentials

**Consequences**:

**Positive**:
- Credentials encrypted at rest
- Standard encryption library (cryptography)
- Key derivation adds security

**Negative**:
- Salt derived from SECRET_KEY weakens security
- No key rotation mechanism
- Single point of failure if SECRET_KEY compromised
- All credentials use same key

**Decision** (Proposed Improvement):
- Use separate salt stored securely
- Implement key rotation mechanism
- Consider Key Management Service for production

**Alternatives Considered**:
- Asymmetric encryption: Rejected - unnecessary complexity
- Key per credential: Considered but complex key management
- Hardware Security Module: Considered for future production

**Security Notes**:
- SECRET_KEY must be 32+ characters
- Never commit SECRET_KEY to version control
- Rotate SECRET_KEY periodically (requires credential re-encryption)

---

## ADR-007: Conversation Context Keep-Alive

**Status**: Accepted

**Date**: [Implementation Date]

**Context**:
Conversational channels need to maintain short-term conversation context. Full conversation history may be too large and privacy-sensitive.

**Decision**:
- Implement 300-second (5 minute) keep-alive window
- Context expires after inactivity
- Context stored in memory (needs Redis for scaling)
- Fresh context created after expiration

**Consequences**:

**Positive**:
- Natural conversation windows
- Privacy-friendly (context expires)
- Prevents unbounded memory growth
- User can manually clear with /newchat

**Negative**:
- Context lost after timeout
- May interrupt long conversations
- Currently in-memory (lost on restart)

**Alternatives Considered**:
- Permanent context: Rejected - privacy and memory concerns
- User-configurable timeout: Considered but adds complexity
- Context in database: Considered but performance concerns

**Future Improvements**:
- Move to Redis for persistence
- Configurable timeout per user
- Context compression for long conversations

---

## ADR-008: FastAPI Application Structure

**Status**: Proposed

**Date**: [Current Date]

**Context**:
Current main.py is 280+ lines with multiple responsibilities. Needs better organization for maintainability.

**Decision**:
- Refactor into app/ directory structure
- Separate concerns: factory, lifespan, routes, bridge
- Follow FastAPI best practices
- Maintain backward compatibility

**Consequences**:

**Positive**:
- Clear separation of concerns
- Easier testing
- Better code organization
- Follows FastAPI patterns
- Easier to maintain

**Negative**:
- Refactoring effort
- Need to update imports
- Temporary complexity during migration

**Structure**:
```
app/
├── factory.py      # Application creation
├── lifespan.py     # Startup/shutdown
├── bridge.py       # Channel bridge setup
└── routes/         # Route modules
```

**Alternatives Considered**:
- Keep current structure: Rejected - maintenance burden
- Microservices: Considered but premature optimization
- Domain-driven design: Considered but overkill for current scale

---

## ADR-009: Health Check Implementation

**Status**: Proposed

**Date**: [Current Date]

**Context**:
Current health check endpoint doesn't verify dependencies. Load balancers and orchestration systems need comprehensive health information.

**Decision**:
- Implement comprehensive health checks
- Verify database connectivity
- Verify OpenMemory service availability
- Return appropriate HTTP status codes
- Include dependency status in response

**Consequences**:

**Positive**:
- Detects dependency failures
- Enables proper load balancer health checks
- Better observability
- Faster incident detection
- Industry best practice

**Negative**:
- Additional endpoint complexity
- Health checks may add latency
- Need to handle dependency failures gracefully

**Health Check Levels**:
- Liveness: Service is running
- Readiness: Service can handle requests
- Startup: Dependencies available

**Alternatives Considered**:
- Simple ping: Current approach - insufficient
- Separate health endpoints: Considered but adds complexity
- Health check service: Considered but overkill

---

## ADR-010: Observability Strategy

**Status**: Proposed

**Date**: [Current Date]

**Context**:
System needs observability for debugging, monitoring, and performance optimization. Current logging is basic.

**Decision**:
- Implement structured logging (JSON in production)
- Add request correlation IDs
- Add distributed tracing (OpenTelemetry)
- Add metrics collection (Prometheus)
- Use correlation IDs for request tracing

**Consequences**:

**Positive**:
- Better debugging capabilities
- Performance monitoring
- Request tracing across services
- Industry standard tools
- Easier incident response

**Negative**:
- Additional infrastructure
- Performance overhead (minimal)
- Learning curve for team
- Additional dependencies

**Tools**:
- Logging: Python logging + JSON formatter
- Tracing: OpenTelemetry
- Metrics: Prometheus
- Visualization: Grafana (future)

**Alternatives Considered**:
- No observability: Rejected - essential for production
- Commercial APM: Considered but cost concerns
- Basic logging only: Rejected - insufficient for debugging

---

## ADR Template

For future ADRs, use this template:

```markdown
## ADR-XXX: [Title]

**Status**: [Proposed | Accepted | Deprecated | Superseded]

**Date**: [YYYY-MM-DD]

**Context**:
[What is the issue that we're seeing that is motivating this decision?]

**Decision**:
[What is the change that we're proposing/doing?]

**Consequences**:

**Positive**:
- [List positive impacts]

**Negative**:
- [List negative impacts]

**Alternatives Considered**:
- [Option 1]: [Why rejected]
- [Option 2]: [Why rejected]

**Implementation Notes**:
[Any implementation details or considerations]
```

---

## ADR Status Legend

- **Proposed**: Decision under consideration
- **Accepted**: Decision approved and implemented
- **Deprecated**: Decision replaced by newer ADR
- **Superseded**: Decision replaced by ADR-XXX
