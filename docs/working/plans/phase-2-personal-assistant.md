# Plan: Phase 2 - Personal Assistant (Background Execution)

**Status**: ⏳ Pending
**Created**: 2026-01-26
**Version**: v1

## Objective
Implement the "Hands" of the Executive Function Coach. This phase builds the **Personal Assistant** as a background worker and the **Job Queue** system, enabling the Core to execute changes in the real world.

## Tasks

### 1. Job Queue System
- [ ] **Queue Infrastructure**
  - **Owner**: backend-engineer
  - Setup `Arq` or `Celery` with Redis.
  - Create `JobRegistry` for tracking task status.
- [ ] **Supervisor Delegation Tool**
  - **Owner**: ai-engineer
  - Create `delegate_to_assistant` tool for Executive Coach.
  - capabilities: `schedule_event`, `add_task`, `send_email`.

### 2. Personal Assistant Worker
- [ ] **Worker Logic**
  - **Owner**: backend-engineer
  - Implement `PersonalAssistantWorker` class.
  - Connect to `TickTick` (via API/Wrapper) and `Google Calendar`.
- [ ] **Auth Token Management**
  - **Owner**: authsec-engineer
  - Implement OAuth refresh flow for background jobs (crucial for "offline" updates).

### 3. Feedback Loop
- [ ] **Status Streaming**
  - **Owner**: frontend-engineer
  - Connect Frontend to Job Status stream.
  - Render "Progress Bar" in the chat when Assistant is working.

## Success Criteria
- [ ] Executive Coach receives "Add 5 tasks" request.
- [ ] Delegates to Job Queue.
- [ ] Personal Assistant Worker executes TickTick API calls.
- [ ] User sees progress bar complete in Dashboard.

## Risks
- **Risk**: Token expiry during background jobs.
  - **Mitigation**: Robust "Refresh & Retry" logic in the Worker.
