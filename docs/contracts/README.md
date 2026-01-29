# Contracts Index

Formal contracts defining interfaces between components.

## Purpose

Contracts serve as:

- **API Specifications**: Define endpoint interfaces
- **Agent Contracts**: Define inter-agent communication
- **Version Control**: Track contract versions
- **Breaking Changes**: Document when contracts change

## Contract Types

### API Contracts (`api/`)

Define FastAPI endpoint specifications:

- Request/response models
- Error responses
- Authentication requirements
- Version information

## Contract Versioning

Contracts are versioned when breaking changes occur:

- **v1**: Initial version
- **v2**: Breaking changes from v1
- **v3**: Breaking changes from v2

Version information is included in contract files.

## Creating a Contract

1. Use the template: `api/TEMPLATE.md` or `agents/TEMPLATE.md`
2. Name file: `[endpoint-name].md` or `[agent-pair].md`
3. Define request/response schemas
4. Document error cases
5. Version the contract
6. Update this README with contract link

## Contract Template

- API Contract: [api/TEMPLATE.md](api/TEMPLATE.md)
- Agent Contract: [agents/TEMPLATE.md](agents/TEMPLATE.md)

## Best Practices

- **Check existing contracts** before creating new ones
- **Version contracts** when making breaking changes
- **Document breaking changes** explicitly
- **Keep contracts updated** with actual implementation
- **Reference contracts** in plans and code
