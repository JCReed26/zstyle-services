# Architecture Documentation

Architecture decisions and system design documentation.

## Purpose

This directory contains:
- **Architecture Decision Records (ADRs)**: Documented architectural decisions
- **System Design**: Overall system architecture
- **Design Patterns**: Patterns used in the system

## Architecture Decision Records

ADRs document important architectural decisions:
- **Context**: What problem are we solving?
- **Decision**: What did we decide?
- **Rationale**: Why did we choose this?
- **Alternatives**: What else did we consider?
- **Consequences**: What are the trade-offs?

See [decisions/README.md](decisions/README.md) for ADR index.

## Creating an ADR

1. Use the template: `decisions/TEMPLATE.md`
2. Name file: `[decision-id]-[short-title].md`
3. Fill in context, decision, rationale
4. Document alternatives and consequences
5. Update decisions README with ADR link

## ADR Template

See [decisions/TEMPLATE.md](decisions/TEMPLATE.md) for the ADR structure.

## Best Practices

- **Document significant decisions** that affect architecture
- **Include rationale** for why decisions were made
- **Document alternatives** that were considered
- **Update ADRs** if decisions change
- **Reference ADRs** in plans and code
