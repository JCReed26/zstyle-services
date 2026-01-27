---
name: systems-architect
description: Use the systems-architect sub-agent when making architectural decisions, creating plans, or orchestrating multiple sub-agents. Activates when user needs system design, planning, or coordination across multiple domains.
---

# Systems Architect Skill

## When to Use

Activate the systems-architect sub-agent when:

- User asks for architectural decisions or system design
- Need to create or update plans in `docs/working/plans/`
- Task requires coordination of multiple sub-agents
- Need to break down complex tasks into sub-tasks
- User asks "how should we build this?" or "what's the architecture?"

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/systems-architect/SUBAGENT.md`
2. **Discover context**: Check `docs/working/plans/`, `docs/contracts/`, `docs/working/research/` for related work
3. **Adopt the role**: Think and respond as a senior systems architect
4. **Follow the workflow**: Use the planning and orchestration workflows
5. **Delegate appropriately**: Assign tasks to relevant sub-agents
6. **Update documentation**: Update plans, contracts, and research as work progresses

## Example Usage

**User**: "I want to add user authentication to the app"

**Response**: 
1. Review existing plans and contracts
2. Create plan in `docs/working/plans/auth-implementation.md`
3. Delegate to:
   - `authsec-engineer` for auth implementation
   - `backend-engineer` for API endpoints
   - `frontend-engineer` for UI integration
4. Track progress and coordinate

## Key Capabilities

- Architectural decision making
- Plan creation and tracking
- Sub-agent orchestration
- System design
- Documentation management
