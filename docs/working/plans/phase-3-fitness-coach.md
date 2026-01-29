# Plan: Phase 3 - Fitness Coach & A2A Integration

**Status**: ⏳ Pending
**Created**: 2026-01-26
**Version**: v1

## Objective
Introduce the first **Specialist Agent**. This validates the "Federated" architecture by having an independent agent (Fitness Coach) communicate with the Core (Executive Coach) via API.

## Tasks

### 1. Fitness Coach Agent Service
- [ ] **Agent Setup**
  - **Owner**: ai-engineer
  - Create independent module `app/agents/fitness/`.
  - Define `FitnessState` (Workout Logs, PRs, Injuries).
- [ ] **Strava Integration**
  - **Owner**: backend-engineer
  - Implement `StravaClient`.
  - Tools: `fetch_activities`, `analyze_performance`.

### 2. A2A API Implementation
- [ ] **Internal Endpoints**
  - **Owner**: systems-architect
  - `POST /api/internal/fitness/update`: For Exec Coach to send data to Fitness.
  - `POST /api/internal/exec/request`: For Fitness to ask Exec Coach for actions.
- [ ] **Handoff Logic**
  - **Owner**: ai-engineer
  - Implement prompt logic: When User says "How's my running?", Exec Coach calls `fitness.analyze()`.

### 3. "Request Action" Workflow
- [ ] **Scheduling Loop**
  - **Owner**: systems-architect
  - **Fitness Agent**: Generates "Run 5k Tuesday".
  - **Fitness Agent**: Calls `Exec.request_action("schedule", "Run 5k", "Tuesday")`.
  - **Exec Coach**: Receives request -> Delegates to Personal Assistant.
  - **PA**: Adds to Google Calendar.

## Success Criteria
- [ ] User sees "Fitness Plan" in Dashboard.
- [ ] User tells Exec Coach "I'm sick".
- [ ] Exec Coach notifies Fitness Coach.
- [ ] Fitness Coach updates plan and requests Calendar cleanup via Exec Coach.

## Risks
- **Risk**: Circular dependencies in A2A calls.
  - **Mitigation**: Strict "Hub & Spoke" rule. Fitness never calls Nutrition directly; always via Hub.
