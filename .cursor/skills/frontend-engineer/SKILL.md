---
name: frontend-engineer
description: Use the frontend-engineer sub-agent when building Next.js web applications with shadcn/ui and Tailwind CSS, integrating with APIs. Activates when user needs web frontend development, Next.js, or web UI implementation.
---

# Frontend Engineer Skill

## When to Use

Activate the frontend-engineer sub-agent when:

- User asks for web UI implementation or Next.js code
- Need to build Next.js web applications
- Working with shadcn/ui components and Tailwind CSS
- Need to integrate Next.js frontend with FastAPI backend
- Working on web client-side state management
- User mentions "frontend", "Next.js", "web", "shadcn", "Tailwind", or "web UI"
- **Note**: For mobile apps, use `mobile-developer` instead

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/frontend-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/contracts/api/` for API specifications
   - Check `docs/working/plans/` for related plans
   - Use semantic search to find related code/docs
3. **Check API contracts**: Always review `docs/contracts/api/` before implementation
4. **Follow patterns**: Use the API integration patterns provided
5. **Test**: Write tests for frontend code
6. **Update contracts**: Update API contracts if implementation differs

## Example Usage

**User**: "Create a user profile page"

**Response**:
1. Check `docs/contracts/api/user-endpoints.md` for API spec
2. Review UI/UX designs if available
3. Implement component with API integration
4. Add error handling and loading states
5. Write tests

## Key Capabilities

- UI component development
- API integration
- State management
- Error handling
- Frontend testing
