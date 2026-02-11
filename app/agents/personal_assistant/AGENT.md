# Personal Assistant

## Purpose
Background execution agent that manages email, calendar, and tasks on behalf of the user. Acts as the exec coach's exclusive worker for external actions.

## Personality & Tone
Efficient, precise, proactive. Summarizes before acting. Confirms destructive actions.

## System Prompt Rationale
- Role definition covers the three core domains: email, calendar, tasks
- Memory context enables learning user preferences (email tone, priority patterns)
- Safety closing prevents accidental sends/deletes without confirmation

## Design Decisions

### Q: Why is this agent the exec coach's exclusive worker?
A: Per federated architecture (ADR-002), the personal assistant is the only agent that executes external actions. Other specialists request actions through the exec coach, which delegates to the personal assistant. This centralizes side effects.

### Q: Why gemini-2.0-flash with temperature 0.3?
A: Lower temperature than other agents because this agent executes real actions (sending emails, managing tasks). Precision matters more than creativity here.

### Q: Why wrap Gmail tools in a try/except?
A: Gmail credentials may not exist in all environments (dev, CI, testing). The agent should still load and respond conversationally even without Gmail access.

### Q: What tools does this agent have?
A: Gmail toolkit (search, read, send, draft). Planned: Google Calendar, TickTick task management, file management.

### Q: What's the scope boundary?
A: DOES: email triage, drafting, sending, calendar management, task CRUD, scheduling. DOES NOT: coaching (-> exec coach), fitness advice (-> fitness coach), meal planning (-> nutritionist).

### Q: How does memory work?
A: Stores assistant interactions separately. Tracks: email preferences, response templates, scheduling patterns, task management style.

## Prompt Engineering Notes
- Consider adding email tone/style preferences to prompt
- May need structured output for email drafts (to, subject, body)
- Action confirmation pattern needs to be robust

## Future Considerations
- Google Calendar integration
- TickTick API for task management
- Background job execution (scheduled emails, reminders)
- Action queue for exec coach delegation
