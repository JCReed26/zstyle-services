# Agent Contract: systems-architect ↔ frontend-engineer

**Version**: v1
**Last Updated**: [Date]
**Status**: ✅ Active

## Overview

Contract defining communication between systems-architect (orchestrator) and frontend-engineer (implementer) for frontend tasks.

## Communication Pattern

**Direct delegation**: systems-architect directly delegates frontend tasks to frontend-engineer with clear requirements and context.

## Request (systems-architect → frontend-engineer)

### Request Schema

```python
from pydantic import BaseModel
from typing import Optional

class FrontendTaskRequest(BaseModel):
    task: str  # Description of frontend task
    api_contract_ref: Optional[str] = None  # Reference to API contract
    design_ref: Optional[str] = None  # Reference to design specs
    plan_ref: Optional[str] = None  # Reference to plan document
    context: dict  # Additional context
    user_id: Optional[str] = None  # User context if needed
```

### Request Example

```python
request = FrontendTaskRequest(
    task="Implement user profile page with API integration",
    api_contract_ref="docs/contracts/api/user-endpoints.md",
    design_ref="design-specs/user-profile.md",
    plan_ref="docs/working/plans/user-profile.md",
    context={"requirements": "Show user data, edit profile"},
    user_id=None
)
```

## Response (frontend-engineer → systems-architect)

### Response Schema

```python
from pydantic import BaseModel
from typing import Optional

class FrontendTaskResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    files_created: list[str] = []
    files_modified: list[str] = []
    tests_written: list[str] = []
    error: Optional[str] = None
    notes: Optional[str] = None
```

### Response Example

```python
response = FrontendTaskResponse(
    success=True,
    result={"component": "UserProfile", "status": "implemented"},
    files_created=["app/frontend/components/UserProfile.tsx"],
    files_modified=["app/frontend/routes.tsx"],
    tests_written=["tests/frontend/test_user_profile.tsx"],
    error=None,
    notes="Implemented with error handling and loading states"
)
```

## Error Handling

### Error Cases

1. **Invalid Request**: Request doesn't match schema or missing required context
2. **API Contract Missing**: Referenced API contract doesn't exist
3. **Implementation Error**: Frontend implementation fails
4. **Test Failure**: Tests fail after implementation

### Error Response

```python
response = FrontendTaskResponse(
    success=False,
    result=None,
    error="API contract not found: docs/contracts/api/user-endpoints.md",
    notes="Please provide valid API contract reference"
)
```

## Validation

### Request Validation

- Task description must be clear and specific
- API contract reference must exist if provided
- Context must include necessary information

### Response Validation

- Success must be boolean
- Files created/modified must be valid paths
- Error must be descriptive if success is false

## Logging

- Log all requests and responses
- Log errors with full context
- Log file changes for tracking

## Related Documents

- Plan: `docs/working/plans/[feature-name].md`
- API Contract: `docs/contracts/api/[endpoint].md`
- Research: `docs/working/research/[topic].md`
