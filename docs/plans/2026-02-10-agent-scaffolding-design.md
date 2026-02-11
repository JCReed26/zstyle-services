# Agent Scaffolding & Test Infrastructure Design

**Date:** 2026-02-10
**Status:** Approved

## Summary

Standardize all 4 agents (exec_func_coach, fitness_coach, nutritionist, personal_assistant) to use LangGraph StateGraph with OpenMemory, add pytest + LangSmith testing, wire up FastAPI routes, and create AGENT.md documentation per agent.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent pattern | All LangGraph StateGraph | Consistent architecture, extensible with tools/branching |
| Testing | pytest + LangSmith tracing | Best for prompt engineering iteration |
| Memory | All agents get OpenMemory | Each agent builds own memory namespace |
| Documentation | AGENT.md per directory | Lives next to code, Q&A format for design decisions |
| API routes | Unified `/api/v1/chat/{agent_name}` | Single endpoint pattern, agent registry dict |

## Agent File Structure

```
app/agents/{agent_name}/
├── __init__.py      # Exports chat() function
├── agent.py         # LangGraph StateGraph definition
├── prompts.py       # System prompt + templates
├── tools.py         # Agent-specific tools
├── state.py         # AgentState TypedDict
└── AGENT.md         # Design decisions, Q&A, prompt notes
```

## Workflow Pattern

```
START → retrieve_context → generate_response → save_to_memory → END
```

- State: `messages`, `user_id`, `context`
- Memory namespace: `{agent_name}:{user_id}`
- Tools bound via `llm.bind_tools(tools)` in generate_response

## Test Structure

```
tests/
├── conftest.py
├── agents/
│   ├── test_exec_func_coach.py
│   ├── test_fitness_coach.py
│   ├── test_nutritionist.py
│   └── test_personal_assistant.py
└── api/
    └── test_routes.py
```

- Unit tests: mock LLM, verify graph wiring
- Prompt smoke tests: `@pytest.mark.llm`, real LLM + LangSmith
- API tests: FastAPI TestClient

## API

- `POST /api/v1/chat/{agent_name}` with `ChatRequest(user_id, message)` → `ChatResponse(response, agent)`
- Agent registry dict maps names to chat functions
- 404 if agent_name not in registry
