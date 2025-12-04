# ZStyle Services Refactoring Plan

## Product Requirements (PRD)

### Goal
Create a centralized, simple, and maintainable Agent Service ("ZStyle") that helps users organize their lives (Executive Function Coach). The system must use Google ADK for core agent capabilities (sessions, memory, credentials) and Supabase for persistence.

### Core Components
1.  **Centralized Session Service**: `ZStyleSessionService` acts as the single source of truth for user sessions, managing connections to Supabase.
2.  **Agent**: A Google ADK-based agent ("Executive Function Coach") with access to Google Calendar and memory tools.
3.  **Interfaces**:
    *   **FastAPI**: Standard ADK CLI endpoints (`/apps/...`).
    *   **Telegram Bot**: Main user interface for text (and future audio) interaction.
4.  **Database**: Supabase (PostgreSQL) storing Users and Sessions.

### User Flows
1.  **New User**:
    *   User messages Telegram Bot.
    *   Bot checks if User exists in `ZStyleSessionService`.
    *   If not, creates User in Supabase.
    *   Starts a new Session.
2.  **Returning User**:
    *   User messages Bot.
    *   Bot retrieves active Session from Service.
    *   Agent receives message + context.
    *   Agent responds.
3.  **Calendar Action**:
    *   User asks to schedule an event.
    *   Agent uses `CalendarToolset`.
    *   Agent confirms action.

---

## Implementation Plan

### Phase 1: Foundation & Cleanup (Database & Service)
- [ ] **Clean up `database/` folder**:
    - [ ] Remove unused models: `agent_config.py`, `artifact.py`, `credential.py`, `memory.py`.
    - [ ] Update `user.py` and `session.py` to match Supabase schema requirements.
- [ ] **Setup Supabase Connection**:
    - [ ] Create `database/supabase_db.py` using `sqlalchemy` + `asyncpg`.
    - [ ] Replace `sqlite_db.py` usages.
- [ ] **Implement `ZStyleSessionService`**:
    - [ ] Inherit/Adapt from ADK's `DatabaseSessionService`.
    - [ ] Implement methods: `create_session`, `get_session`, `save_session`.
    - [ ] Ensure it reads/writes to the `sessions` table in Supabase.
- [ ] **Remove Legacy Code**:
    - [ ] Delete `services/telegram_mcp/` folder (consolidating on standard Bot API).

### Phase 2: Core Agent Wiring
- [ ] **Update `services/auth/credential_service.py`**:
    - [ ] Ensure it can retrieve Google Credentials for the `CalendarToolset`.
- [ ] **Update `agents/exec_func_coach/agent.py`**:
    - [ ] Configure `root_agent` to use the `ZStyleSessionService`.
    - [ ] Ensure `CalendarToolset` is correctly initialized with credentials.
- [ ] **Update `main.py`**:
    - [ ] Ensure `lifespan` manages the Supabase connection pool.
    - [ ] Verify ADK FastAPI app is initialized with the correct agent and service.

### Phase 3: Telegram Bot Integration
- [ ] **Refactor `services/telegram_bot.py`**:
    - [ ] Use `python-telegram-bot` (standard API).
    - [ ] Implement `/start` to register/fetch user via `ZStyleSessionService` (or via API endpoint).
    - [ ] Implement Message Handler: Text -> Agent API -> Text Response -> User.
    - [ ] Add basic structure for Voice handling (download file, placeholder for processing).

### Phase 4: Testing & Documentation
- [ ] **Testing**:
    - [ ] Create `tests/test_session_flow.py`: Verify User creation and Session persistence.
    - [ ] Create `tests/test_agent_calendar.py`: Verify Agent can call Calendar tool.
- [ ] **Documentation**:
    - [ ] Update `README.md` with setup instructions (Env vars for Supabase, Telegram, Google).

## Testing Checklist
- [ ] **Database**: Can connect to Supabase and list tables?
- [ ] **Session**: Can create a session and retrieve it by ID?
- [ ] **Agent**: Can the agent reply to "Hello"?
- [ ] **Calendar**: Can the agent list events from the user's calendar?
- [ ] **Telegram**: Does the bot reply to messages?
