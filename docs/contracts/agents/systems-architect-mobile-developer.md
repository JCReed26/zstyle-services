# Agent Contract: systems-architect ↔ mobile-developer

**Version**: v1
**Last Updated**: [Date]
**Status**: ✅ Active
**Created**: [Date]

## Overview

Contract defining communication between systems-architect (orchestrator) and mobile-developer (implementer) for mobile app tasks.

## Communication Pattern

**Direct delegation**: systems-architect directly delegates mobile app tasks to mobile-developer with clear requirements and context.

## Request (systems-architect → mobile-developer)

### Request Schema

```python
from pydantic import BaseModel
from typing import Optional

class MobileTaskRequest(BaseModel):
    task: str  # Description of mobile task
    api_contract_ref: Optional[str] = None  # Reference to API contract
    design_ref: Optional[str] = None  # Reference to mobile design specs
    plan_ref: Optional[str] = None  # Reference to plan document
    native_features: list[str] = []  # Required native features (camera, location, etc.)
    context: dict  # Additional context
    user_id: Optional[str] = None  # User context if needed
```

### Request Example

```python
request = MobileTaskRequest(
    task="Implement user profile screen with camera integration",
    api_contract_ref="docs/contracts/api/user-endpoints.md",
    design_ref="design-specs/mobile-user-profile.md",
    plan_ref="docs/working/plans/mobile-user-profile.md",
    native_features=["camera"],
    context={"requirements": "Show user data, edit profile, upload photo"},
    user_id=None
)
```

## Response (mobile-developer → systems-architect)

### Response Schema

```python
from pydantic import BaseModel
from typing import Optional

class MobileTaskResponse(BaseModel):
    success: bool
    result: Optional[dict] = None
    files_created: list[str] = []
    files_modified: list[str] = []
    tests_written: list[str] = []
    platforms_tested: list[str] = []  # ["ios", "android"]
    error: Optional[str] = None
    notes: Optional[str] = None
```

### Response Example

```python
response = MobileTaskResponse(
    success=True,
    result={"screen": "UserProfile", "status": "implemented"},
    files_created=["mobile/screens/UserProfile.tsx"],
    files_modified=["mobile/navigation/AppNavigator.tsx"],
    tests_written=["mobile/__tests__/UserProfile.test.tsx"],
    platforms_tested=["ios", "android"],
    error=None,
    notes="Implemented with camera integration and error handling"
)
```

## Error Handling

### Error Cases

1. **Invalid Request**: Request doesn't match schema or missing required context
2. **API Contract Missing**: Referenced API contract doesn't exist
3. **Native Feature Unavailable**: Required native feature not available on platform
4. **Implementation Error**: Mobile implementation fails
5. **Test Failure**: Tests fail after implementation

### Error Response

```python
response = MobileTaskResponse(
    success=False,
    result=None,
    error="Camera permission not granted on iOS",
    notes="User needs to grant camera permission in settings"
)
```

## Validation

### Request Validation

- Task description must be clear and specific
- API contract reference must exist if provided
- Native features must be valid Expo capabilities
- Context must include necessary information

### Response Validation

- Success must be boolean
- Files created/modified must be valid paths
- Platforms tested must include at least one platform
- Error must be descriptive if success is false

## Logging

- Log all requests and responses
- Log native feature usage
- Log errors with full context
- Log file changes for tracking

## Related Documents

- Plan: `docs/working/plans/[feature-name].md`
- API Contract: `docs/contracts/api/[endpoint].md`
- Research: `docs/working/research/[topic].md`
