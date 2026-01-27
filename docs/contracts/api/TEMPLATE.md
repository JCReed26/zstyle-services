# API Contract: [Endpoint Name]

**Version**: v1
**Last Updated**: [Date]
**Status**: ✅ Active | 🚧 Draft | ❌ Deprecated
**Created**: [Date]

## Version History

### v1 (Current)
- **Date**: [Date]
- **Changes**: Initial version
- **Breaking Changes**: None

### v2 (Planned/Future)
- **Date**: [Date if planned]
- **Changes**: [Description of changes]
- **Breaking Changes**: [List breaking changes]

## Endpoint

```
[HTTP Method] /api/v1/[endpoint-path]
```

## Description

[What this endpoint does]

## Authentication

- **Required**: Yes | No
- **Method**: [JWT, Bearer Token, etc.]
- **Scopes**: [If applicable]

## Request

### Headers

```
Authorization: Bearer [token]
Content-Type: application/json
```

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| [param] | [type] | Yes/No | [Description] |

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| [param] | [type] | Yes/No | [Description] |

### Request Body

```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Request Schema (Pydantic)

```python
from pydantic import BaseModel

class RequestModel(BaseModel):
    field1: str
    field2: Optional[int] = None
```

## Response

### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

### Response Schema (Pydantic)

```python
from pydantic import BaseModel

class ResponseModel(BaseModel):
    success: bool
    data: DataModel
```

### Error Responses

#### 400 Bad Request

```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "field": "error message"
  }
}
```

#### 401 Unauthorized

```json
{
  "success": false,
  "error": "Authentication required"
}
```

#### 404 Not Found

```json
{
  "success": false,
  "error": "Resource not found"
}
```

#### 500 Internal Server Error

```json
{
  "success": false,
  "error": "Internal server error"
}
```

## Examples

### cURL Example

```bash
curl -X POST https://api.example.com/api/v1/endpoint \
  -H "Authorization: Bearer [token]" \
  -H "Content-Type: application/json" \
  -d '{"field1": "value1"}'
```

### Python Example

```python
import requests

response = requests.post(
    "https://api.example.com/api/v1/endpoint",
    headers={"Authorization": f"Bearer {token}"},
    json={"field1": "value1"}
)
```


## Related Documents

- Plan: `docs/working/plans/[feature-name].md`
- Research: `docs/working/research/[topic].md`
- ADR: `docs/architecture/decisions/[decision-id].md`
