---
name: authsec-engineer
description: Use the authsec-engineer sub-agent when implementing authentication, authorization, or security features. Activates when user needs auth, security, or data protection work.
---

# AuthSec Engineer Skill

## When to Use

Activate the authsec-engineer sub-agent when:

- User asks for authentication or login features
- Need to implement security measures
- Working on authorization or RBAC
- User mentions "auth", "security", "login", "permissions", or "protection"
- Need security audit or review

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/authsec-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/working/research/` for auth research
   - Check `docs/contracts/api/` for auth endpoints
   - Check `docs/working/error-logs.md` for security issues
3. **Follow security patterns**: Use provided authentication patterns
4. **Security checklist**: Verify all security requirements
5. **Test security**: Write security-focused tests
6. **Document**: Document security decisions in ADRs if significant
7. **Update contracts**: Update auth contracts when implementing

## Example Usage

**User**: "Add JWT authentication"

**Response**:
1. Design auth flow
2. Implement JWT token generation/validation
3. Add password hashing
4. Create auth middleware
5. Add security headers
6. Write security tests

## Key Capabilities

- Authentication implementation
- Authorization and RBAC
- Security hardening
- Password security
- Security auditing
