# Architecture Decision Records (ADRs)

This document records architectural decisions made for the ZStyle Services project. Each ADR follows the standard format: Context, Decision, Consequences.

---

## ADR-001: Database Selection

**Status**: Accepted

**Decision**: Use PostgreSQL (Supabase) for all environments with async SQLAlchemy.

**Rationale**: Production-ready, supports concurrent access, scalable, built-in auth via Supabase.

---

## ADR-002: Session vs Memory Architecture

**Status**: Accepted

**Context**: ADK requires session management, but long-term memory needs semantic search.

**Decision**:

- Use InMemorySessionService for ADK sessions (ephemeral conversation state)
- Use OpenMemory for long-term semantic memory (persistent, searchable)

**Rationale**:

- ADK sessions are lightweight, ephemeral state for managing single request/response cycles
- OpenMemory provides semantic search (RAG) for long-term user context
- Separation of concerns: sessions = conversation flow, memory = persistent knowledge

---

## ADR-003: Channel Abstraction with NormalizedMessage

**Status**: Accepted

**Decision**: Abstract channels into separate layer with NormalizedMessage format.

**Rationale**: Agents are channel-agnostic, easy to add new channels, consistent interface.

---

## ADR-004: Memory Service Architecture (OpenMemory)

**Status**: Accepted

**Decision**: Use separate OpenMemory HTTP service for long-term semantic memory.

**Rationale**: Semantic search capabilities (RAG), vector-based storage, separate scaling concerns.

---

## ADR-005: Encryption for Credentials

**Status**: Accepted

**Decision**: Use Fernet symmetric encryption with key derived from SECRET_KEY via PBKDF2HMAC with a fixed salt per environment.

**Rationale**: Simple, effective encryption for credential storage. Standard library (cryptography), adequate for current scale. Fixed salt ensures consistency within an environment.

**Implementation Details**:

- Salt: Fixed per environment (`b'zstyle_salt_2024'` - should be stored securely in production)
- Key derivation: PBKDF2HMAC with 100,000 iterations
- Encryption: Fernet symmetric encryption

**Security Notes**:

- SECRET_KEY must be 32+ characters
- Never commit SECRET_KEY to version control
- For production at scale, consider Key Management Service

---

## ADR-006: Telegram Polling Mode

**Status**: Accepted

**Decision**: Use polling mode for Telegram bot instead of webhooks.

**Rationale**: Simpler implementation, no webhook infrastructure needed, adequate for current scale.

---

## ADR-007: Conversation Context Keep-Alive

**Status**: Accepted

**Decision**: Implement 300-second (5 minute) keep-alive window for conversation contexts.

**Rationale**: Natural conversation windows, privacy-friendly (context expires), prevents unbounded memory growth.

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
