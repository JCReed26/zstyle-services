---
name: backend-engineer
description: Use the backend-engineer sub-agent when building FastAPI endpoints, database schemas, or server-side logic. Activates when user needs backend development, API creation, or database work.
---

# Backend Engineer Skill

## When to Use

Activate the backend-engineer sub-agent when:

- User asks for API endpoints or backend code
- Need to design database schemas
- Working on FastAPI routes
- User mentions "backend", "API", "database", or "server-side"
- Need to update API contracts

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/backend-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/contracts/api/` for existing API contracts
   - Check `docs/working/plans/` for related plans
   - Check `docs/working/research/` for related research
   - Use semantic search to find related code
3. **Check contracts**: Review `docs/contracts/api/` before implementing
4. **Follow FastAPI patterns**: Use the provided patterns
5. **Update contracts**: Keep contracts in sync with implementation, version if breaking changes
6. **Test**: Write tests using TDD approach
7. **Update error logs**: Document errors and solutions in `docs/working/error-logs.md`

## Example Usage

**User**: "Create an endpoint to get user data"

**Response**:
1. Check `docs/contracts/api/user-endpoints.md`
2. Design Pydantic models
3. Implement FastAPI route
4. Add error handling
5. Write tests
6. Update contract if needed

## Key Capabilities

- FastAPI development
- Database design
- API contract management
- Request/response validation
- Error handling
