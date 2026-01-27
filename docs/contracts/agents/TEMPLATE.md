# Agent Contract: [Agent A] ↔ [Agent B]

**Version**: v1
**Last Updated**: [Date]
**Status**: ✅ Active | 🚧 Draft | ❌ Deprecated

## Overview

[Description of communication between agents]

## Communication Pattern

[How agents communicate:
- Direct call
- Event-based
- Through orchestrator
- etc.]

## Request (Agent A → Agent B)

### Request Schema

```python
from pydantic import BaseModel

class AgentRequest(BaseModel):
    task: str
    context: dict
    user_id: str
```

### Request Example

```python
request = AgentRequest(
    task="process_user_request",
    context={"query": "example"},
    user_id="user123"
)
```

## Response (Agent B → Agent A)

### Response Schema

```python
from pydantic import BaseModel

class AgentResponse(BaseModel):
    success: bool
    result: dict
    error: Optional[str] = None
```

### Response Example

```python
response = AgentResponse(
    success=True,
    result={"processed": "data"},
    error=None
)
```

## Error Handling

### Error Cases

1. **Invalid Request**: Request doesn't match schema
2. **Processing Error**: Agent B fails to process
3. **Timeout**: Request times out
4. **Unavailable**: Agent B is unavailable

### Error Response

```python
response = AgentResponse(
    success=False,
    result=None,
    error="Error description"
)
```

## Validation

### Request Validation

[How requests are validated]

### Response Validation

[How responses are validated]

## Logging

[What is logged:
- Request/response
- Errors
- Performance metrics
- etc.]


## Related Documents

- Plan: `docs/working/plans/[feature-name].md`
- Research: `docs/working/research/[topic].md`
- ADR: `docs/architecture/decisions/[decision-id].md`
