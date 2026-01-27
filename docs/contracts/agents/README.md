# Agent Contracts Index

Contracts defining inter-agent communication protocols.

## Purpose

Agent contracts define:
- How agents communicate with each other
- Request/response schemas
- Error handling patterns
- Validation requirements
- Logging requirements

## Contract Structure

Each contract follows the template in `TEMPLATE.md` and includes:
- Communication pattern
- Request schema (Pydantic models)
- Response schema (Pydantic models)
- Error handling
- Validation rules
- Logging requirements

## Active Contracts

- [systems-architect ↔ frontend-engineer](systems-architect-frontend-engineer.md) - Web frontend (Next.js)
- [systems-architect ↔ mobile-developer](systems-architect-mobile-developer.md) - Mobile app (React Native/Expo)
- [systems-architect ↔ backend-engineer](systems-architect-backend-engineer.md)

*More contracts will be added as agent pairs are defined.*

## Creating a Contract

1. Use the template: `TEMPLATE.md`
2. Name file: `[agent-a]-[agent-b].md`
3. Define request/response schemas
4. Document error cases
5. Version the contract
6. Update this README with contract link

## Best Practices

- **Check existing contracts** before creating new ones
- **Version contracts** when making breaking changes
- **Document breaking changes** explicitly
- **Keep contracts updated** with actual implementation
- **Reference contracts** in plans and agent definitions
