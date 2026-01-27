# Agent Contract: systems-architect ↔ backend-engineer

**Version**: v1
**Last Updated**: [Date]
**Status**: ✅ Active

## Overview

Contract defining communication between systems-architect (orchestrator) and backend-engineer (implementer) for backend/API tasks.

## Communication Pattern

**Direct delegation**: systems-architect directly delegates backend tasks to backend-engineer with clear requirements and API contract references.

## Request (systems-architect → backend-engineer)

### Request Schema

```python
from pydantic import BaseModel
from typing import Optional

class BackendTaskRequest(BaseModel):
    task: str  # Description of backend task
    api_contract_ref: Optional[str] = None  # Reference to API contract (create or update)
    database_schema_ref: Optional[str] = None  # Reference to database schema if needed
    plan_ref: Optional[str] = None  # Reference to plan document
    context: dict  # Additional context
    user_id: Optional[str] = None  # User context if needed
```

### Request Example

```python
request = BackendTaskRequest(
    task="Implement user endpoint GET /api/v1/users/{user_id}",
    api_contract_ref="docs/contracts/api/user-endpoints.md",
    database_schema_ref="docs/reference/database-schema.md",
    plan_ref="docs/working/plans/user-api.md",
    context={"requirements": "Return user data, handle not found"},
    user_id=None
)
```

## Response (backend-engineer → systems-architect)

### Response Schema

```python
from pydantic import BaseModel
from typing import Optional

class BackendTaskResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    files_created: list[str] = []
    files_modified: list[str] = []
    tests_written: list[str] = []
    contract_updated: bool = False  # Whether API contract was updated
    error: Optional[str] = None
    notes: Optional[str] = None
```

### Response Example

```python
response = BackendTaskResponse(
    success=True,
    result={"endpoint": "/api/v1/users/{user_id}", "status": "implemented"},
    files_created=["app/api/routes/users.py"],
    files_modified=["app/api/main.py"],
    tests_written=["tests/api/test_users.py"],
    contract_updated=False,
    error=None,
    notes="Implemented with proper error handling and validation"
)
```

## Error Handling

### Error Cases

1. **Invalid Request**: Request doesn't match schema
2. **Contract Conflict**: Implementation differs from contract
3. **Database Error**: Database operation fails
4. **Test Failure**: Tests fail after implementation

### Error Response

```python
response = BackendTaskResponse(
    success=False,
    result=None,
    error="Database connection failed",
    notes="Check database configuration and connection string"
)
```

## Validation

### Request Validation

- Task description must be clear
- API contract reference must exist if provided
- Database schema reference must exist if provided

### Response Validation

- Success must be boolean
- Contract updated flag must reflect actual changes
- Error must be descriptive

## Logging

- Log all requests and responses
- Log database operations
- Log API contract changes
- Log errors with full context

## Related Documents

- Plan: `docs/working/plans/[feature-name].md`
- API Contract: `docs/contracts/api/[endpoint].md`
- Research: `docs/working/research/[topic].md`
