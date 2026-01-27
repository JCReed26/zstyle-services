---
name: mobile-developer
description: Use the mobile-developer sub-agent when building React Native mobile apps, integrating with APIs, or working on mobile-specific features. Activates when user needs mobile development, React Native, Expo, or native feature integration.
---

# Mobile Developer Skill

## When to Use

Activate the mobile-developer sub-agent when:

- User asks for mobile app implementation or React Native code
- Need to build mobile UI components
- Working on Expo app development
- Need to integrate native device features (camera, location, etc.)
- User mentions "mobile", "React Native", "Expo", "iOS", "Android", or "native features"
- Need to integrate mobile app with FastAPI backend

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/mobile-developer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/contracts/api/` for API specifications
   - Check `docs/working/plans/` for related mobile plans
   - Use semantic search to find related mobile code
3. **Check API contracts**: Always review `docs/contracts/api/` before implementation
4. **Follow patterns**: Use React Native and Expo patterns provided
5. **Test**: Write tests for mobile code (Jest, React Native Testing Library)
6. **Update contracts**: Update API contracts if implementation differs

## Example Usage

**User**: "Create a mobile login screen"

**Response**:
1. Check `docs/contracts/api/auth-endpoints.md` for API spec
2. Review mobile UI/UX designs if available
3. Implement React Native component with Expo
4. Add API integration with error handling
5. Add loading states and user feedback
6. Test on iOS and Android simulators
7. Write tests

## Key Capabilities

- React Native component development
- Expo SDK integration
- API integration
- Native feature integration
- State management
- Error handling
- Mobile testing
