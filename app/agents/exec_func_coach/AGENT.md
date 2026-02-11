# Executive Function Coach

## Purpose
Central hub agent that helps users manage tasks, habits, and goals through executive function coaching.

## Personality & Tone
Supportive, organized, actionable. Coaches rather than dictates. Breaks complex goals into manageable steps.

## System Prompt Rationale
- Opens with role definition to anchor behavior
- Injects memory context to maintain conversation continuity
- Closes with behavioral guidelines (supportive, organized, actionable)

## Design Decisions

### Q: Why is this the hub agent?
A: Per federated architecture (ADR-002), the exec function coach orchestrates other agents. It's the user's primary interface — all other agents report through it.

### Q: Why gemini-2.0-flash-exp?
A: Fast inference for conversational coaching. The -exp variant gives access to latest capabilities. Can swap to pro for complex reasoning if needed.

### Q: Why temperature 0.7?
A: Balances creativity (motivational coaching) with consistency (task tracking). Lower would be too rigid, higher too unpredictable.

### Q: What tools will this agent need?
A: Currently none. Planned: task management (TickTick), calendar integration, delegation to specialist agents.

### Q: What's the scope boundary?
A: DOES: daily planning, habit tracking, goal setting, task breakdown, delegating to specialists. DOES NOT: direct fitness programming, meal planning, email management — delegates those.

### Q: How does memory work?
A: OpenMemory stores conversation turns. On each message, retrieves top 5 relevant past interactions for context. Enables long-term relationship building.

## Prompt Engineering Notes
- Current prompt is minimal — room to expand with structured output formats
- Consider adding few-shot examples for task breakdown style
- May need separate prompts for different modes (planning, review, coaching)

## Future Considerations
- Tool calling for TickTick task creation
- Handoff protocol to specialist agents
- Structured output for daily/weekly plans
- Multi-turn planning workflows with conditional branching
