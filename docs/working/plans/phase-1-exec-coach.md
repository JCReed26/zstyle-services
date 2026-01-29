# Plan: Phase 1 - Executive Function Coach (The Core)

**Status**: ⏳ Pending
**Created**: 2026-01-26
**Version**: v1

## Objective
Establish the **Core System Hub**. Build the Executive Function Coach as the primary interface that can manage user context, route basic intents, and maintain the "Life Operating System" state.

## Tasks

### 1. Core Infrastructure
- [ ] **Project Scaffold**
  - **Owner**: systems-architect
  - Set up Monorepo structure: `apps/api`, `apps/web`, `apps/mobile`.
  - Configure `docker-compose.yml` (Postgres, Redis, OpenMemory).
- [ ] **FastAPI Gateway**
  - **Owner**: backend-engineer
  - Implement base API with `CopilotKit` integration.
  - Setup Authentication (User ID / Token management).

### 2. Executive Function Coach Agent
- [ ] **Graph Definition**
  - **Owner**: ai-engineer
  - Create `app/agents/executive/graph.py`.
  - Define `ExecutiveState` (User Profile, Active Goals, System Status).
- [ ] **Routing Logic**
  - **Owner**: ai-engineer
  - Implement "Intent Classifier" node.
  - Detect intents: `GENERAL_CHAT`, `UPDATE_GOAL`, `FITNESS_ROUTINE` (mocks), `NUTRITION_PLAN` (mocks).
- [ ] **Context Management**
  - **Owner**: backend-engineer
  - Implement OpenMemory client.
  - Create tools for `read_context` and `update_context`.

### 3. User Interface (Dashboard)
- [ ] **Web Dashboard (Next.js)**
  - **Owner**: frontend-engineer
  - Create "Life Dashboard" layout.
  - Sections: "Chat", "Life Goals" (Read-only), "Active Agents" (List).
- [ ] **Voice Input**
  - **Owner**: frontend-engineer
  - Implement "Microphone" component for long-form voice prompts (using OpenAI Whisper or browser API).

## Success Criteria
- [ ] User can log in and see the Dashboard.
- [ ] User can speak/type a "Life Update" ("I'm moving next month").
- [ ] Executive Coach updates OpenMemory with this new fact.
- [ ] Executive Coach replies with a confirmation.

## Risks
- **Risk**: OpenMemory integration complexity.
  - **Mitigation**: Start with a simple JSON-based memory store in Postgres if OpenMemory setup delays occur.
