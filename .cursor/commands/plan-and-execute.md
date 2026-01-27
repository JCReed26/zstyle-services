---
name: plan-and-execute
description: Comprehensive planning and execution workflow that gathers all necessary context before creating and executing a plan. Ensures proper context gathering, planning, validation, and execution.
---

# Plan and Execute Workflow

## Overview

This workflow ensures thorough context gathering before planning, then creates and executes plans systematically. Follow these steps to ensure nothing is missed.

## Phase 1: Gather Context (Natural Discovery)

**Context discovery happens automatically** - use semantic search and pattern matching to find relevant information. Don't manually tag files; let discovery tools find what's needed.

### 1. Understand the Request

**Read the user's request carefully** and identify:
- What is the goal?
- What are the constraints?
- What is the scope?
- What is the timeline?

### 2. Natural Context Discovery

Use semantic search to discover relevant context:

```python
# Use codebase_search for semantic discovery
codebase_search "How is [feature] implemented?"
codebase_search "Where are [related concepts] used?"
codebase_search "What patterns exist for [task]?"
```

**Discovery Patterns**:

1. **Check Existing Plans** (`docs/working/plans/`):
   - Use semantic search: "plans related to [feature]"
   - Check plan index: `docs/working/plans/README.md`
   - Review plans to avoid duplicate work

2. **Check API Contracts** (`docs/contracts/api/`):
   - Use semantic search: "API contracts for [endpoint]"
   - Check contracts index: `docs/contracts/README.md`
   - Review contracts to understand interfaces

3. **Check Research** (`docs/working/research/`):
   - Use semantic search: "research on [topic]"
   - Check research index: `docs/working/research/README.md`
   - Review research to learn from past decisions

4. **Check Error Logs** (`docs/working/error-logs.md`):
   - Search error logs for similar issues
   - Learn from past errors and solutions
   - Avoid repeating mistakes

5. **Check Architecture Decisions** (`docs/architecture/decisions/`):
   - Use semantic search: "architecture decisions about [topic]"
   - Review ADRs for relevant decisions
   - Understand rationale for past choices

6. **Check Codebase**:
   - Use `codebase_search` for semantic code discovery
   - Find related code patterns
   - Understand existing implementation

7. **Check Tests**:
   - Use semantic search: "tests for [feature]"
   - Review test patterns
   - Understand coverage

**Key Principle**: Discovery is automatic - use semantic search tools rather than manually checking files. The agent will find relevant context naturally.

## Phase 2: Plan Creation

### 1. Create Plan Document

Create or update plan in `docs/working/plans/[feature-name].md`:

```markdown
# Plan: [Feature Name]

## Objective
[Clear statement of what we're building]

## Context
[What we learned from context gathering]

## Tasks
- [ ] Task 1: [Description]
- [ ] Task 2: [Description]
- [ ] Task 3: [Description]

## Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2

## Sub-Agent Assignments
- Task 1 → backend-engineer
- Task 2 → frontend-engineer
- Task 3 → systems-architect (coordination)

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Risks and Mitigation
- Risk 1: [Mitigation]
- Risk 2: [Mitigation]

## Notes
[Any additional notes]
```

### 2. Break Down Tasks

For each task, ensure:
- **Clear scope**: What exactly needs to be done?
- **Clear owner**: Which sub-agent handles this?
- **Clear dependencies**: What must happen first?
- **Clear success criteria**: How do we know it's done?

### 3. Identify Required Sub-Agents

Based on tasks, identify which sub-agents are needed:
- `systems-architect` - Coordination and planning
- `backend-engineer` - API and database work
- `frontend-engineer` - UI implementation
- `ui-ux-designer` - Design work
- `authsec-engineer` - Security and auth
- `docker-engineer` - Containerization
- `devops-engineer` - CI/CD and deployment
- `ai-engineer` - LangChain agents

## Phase 3: Validate Plan

### 1. Review Plan Completeness

Check that plan includes:
- [ ] Clear objective
- [ ] All tasks identified
- [ ] Dependencies mapped
- [ ] Sub-agents assigned
- [ ] Success criteria defined
- [ ] Risks identified

### 2. Verify Context

Confirm we have:
- [ ] Reviewed existing plans
- [ ] Reviewed API contracts
- [ ] Reviewed documentation
- [ ] Reviewed codebase
- [ ] Reviewed tests
- [ ] Understood constraints

### 3. Check Feasibility

Verify:
- [ ] Tasks are achievable
- [ ] Dependencies are clear
- [ ] Timeline is realistic
- [ ] Resources are available

## Phase 4: Execute Plan

### 1. Start with First Task

Begin with tasks that have no dependencies:

```bash
# Example: Start backend task
# Activate backend-engineer sub-agent
# Follow backend-engineer workflow
# Update plan: mark task as in progress
```

### 2. Update Plan Progress

As you work, update the plan:

```markdown
## Tasks
- [x] Task 1: [Description] ✅ Completed
- [ ] Task 2: [Description] 🔄 In Progress
- [ ] Task 3: [Description] ⏳ Pending
```

### 3. Coordinate Sub-Agents

When tasks require multiple agents:

1. **Delegate clearly**: Assign tasks with clear instructions
2. **Provide context**: Share relevant contracts and docs
3. **Check progress**: Verify sub-agents are on track
4. **Integrate results**: Combine outputs from sub-agents

### 4. Handle Blockers

When encountering blockers:

1. **Document blocker**: Add to plan notes
2. **Assess impact**: How does this affect the plan?
3. **Find solution**: Research or ask for help
4. **Update plan**: Adjust tasks if needed

### 5. Validate Each Task

Before marking a task complete:

- [ ] Code is implemented
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Contracts updated (if API changed)
- [ ] Code reviewed (if applicable)

## Phase 5: Review and Iterate

### 1. Review Completed Work

After completing all tasks:

```bash
# Run all tests
pytest tests/ -v

# Check for linting issues
ruff check app/

# Verify documentation
ls -la docs/contracts/
```

### 2. Update Documentation

Ensure:
- [ ] Plans updated with completion status
- [ ] API contracts updated (if changed)
- [ ] Feature docs updated
- [ ] Error logs updated (if errors occurred)

### 3. Reflect and Learn

Document:
- What went well?
- What could be improved?
- What would we do differently?
- Any patterns to reuse?

## Checklist

Use this checklist for every plan:

**Context Gathering**:
- [ ] Understood user request
- [ ] Checked existing plans
- [ ] Reviewed API contracts
- [ ] Reviewed documentation
- [ ] Reviewed codebase
- [ ] Reviewed tests

**Planning**:
- [ ] Created plan document
- [ ] Broke down tasks
- [ ] Identified sub-agents
- [ ] Mapped dependencies
- [ ] Defined success criteria

**Validation**:
- [ ] Plan is complete
- [ ] Context is sufficient
- [ ] Plan is feasible

**Execution**:
- [ ] Started with first task
- [ ] Updated progress
- [ ] Coordinated sub-agents
- [ ] Handled blockers
- [ ] Validated each task

**Review**:
- [ ] Reviewed completed work
- [ ] Updated documentation
- [ ] Reflected and learned

## Example Usage

**User**: "Add user authentication"

**Workflow**:
1. **Gather Context**: Check plans, contracts, docs, codebase, tests
2. **Create Plan**: `docs/working/plans/auth-implementation.md`
3. **Validate Plan**: Review completeness and feasibility
4. **Execute**: 
   - Delegate to `authsec-engineer` for auth logic
   - Delegate to `backend-engineer` for API endpoints
   - Delegate to `frontend-engineer` for UI
5. **Review**: Test, update docs, reflect
