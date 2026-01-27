---
name: research
description: Comprehensive research workflow to gather information, evaluate solutions, and document findings. Ensures thorough research before implementation decisions.
---

# Research Workflow

## Overview

This workflow ensures thorough research before making implementation decisions. Follow these steps to gather comprehensive information and make informed choices.

## Phase 1: Define Research Question

### 1. Clarify What You Need to Know

**Formulate clear research questions**:

- What problem are we trying to solve?
- What information do we need?
- What are the constraints?
- What is the scope?

**Example Questions**:
- "How do I implement JWT authentication in FastAPI?"
- "What's the best way to test LangChain agents?"
- "How should I structure a multi-agent system?"

### 2. Identify Research Areas

**Break down into research areas**:

- Technical approach
- Best practices
- Existing solutions
- Libraries/tools
- Performance considerations
- Security considerations

## Phase 2: Gather Information

### 1. Search Documentation

**Check official documentation**:

```bash
# LangChain docs
# Visit: https://python.langchain.com/docs/

# FastAPI docs
# Visit: https://fastapi.tiangolo.com/

# Python docs
# Visit: https://docs.python.org/
```

**Action**: Read relevant sections, look for examples, understand APIs.

### 2. Check Existing Research (Natural Discovery)

**Before researching, check if research already exists**:

```python
# Use semantic search to find existing research
codebase_search "research on [topic]"
codebase_search "decisions about [topic]"
```

**Discovery Patterns**:

1. **Check Research Docs** (`docs/working/research/`):
   - Use semantic search: "research about [topic]"
   - Check research index: `docs/working/research/README.md`
   - Review existing research to build on it

2. **Check Architecture Decisions** (`docs/architecture/decisions/`):
   - Use semantic search: "architecture decisions about [topic]"
   - Review ADRs for related decisions
   - Understand past rationale

3. **Check Plans** (`docs/working/plans/`):
   - Use semantic search: "plans related to [topic]"
   - Review plans for context on past work

**Action**: Build on existing research rather than starting from scratch.

### 3. Search Codebase

**Check existing code**:

```python
# Use semantic search for code discovery
codebase_search "How is [feature] implemented?"
codebase_search "Where is [pattern] used?"
codebase_search "What patterns exist for [task]?"
```

**Action**: Understand how similar problems were solved in this codebase.

### 4. Search External Resources

**Use web search and resources**:

- GitHub repositories (similar projects)
- Stack Overflow (common patterns)
- Blog posts (tutorials and guides)
- Documentation (official docs)
- Forums (community discussions)

**Action**: Gather multiple perspectives and approaches.

### 5. Check Error Logs and Past Issues

**Review past problems**:

```python
# Use semantic search for error patterns
codebase_search "errors related to [topic]"
```

- Check `docs/working/error-logs.md` for similar errors
- Learn from past mistakes and solutions
- Document what didn't work

**Action**: Avoid repeating past mistakes.

### 6. Review API Contracts and Plans

**Check project context**:

```python
# Use semantic search for contracts and plans
codebase_search "API contracts for [endpoint]"
codebase_search "plans for [feature]"
```

- Review `docs/contracts/api/` for API constraints
- Review `docs/working/plans/` for related work
- Understand project constraints and requirements

**Action**: Ensure research aligns with project constraints.

## Phase 3: Evaluate Solutions

### 1. List Options

**Document all options found**:

```markdown
## Option 1: [Name]
- **Description**: [What it is]
- **Pros**: [Advantages]
- **Cons**: [Disadvantages]
- **Complexity**: [Low/Medium/High]
- **Dependencies**: [What's needed]

## Option 2: [Name]
...
```

### 2. Compare Options

**Evaluate against criteria**:

- **Fit for purpose**: Does it solve the problem?
- **Complexity**: How hard is it to implement?
- **Performance**: How does it perform?
- **Maintainability**: How easy is it to maintain?
- **Security**: Are there security concerns?
- **Dependencies**: What dependencies does it add?
- **Community support**: Is it well-maintained?

### 3. Check Compatibility

**Verify compatibility**:

- Works with FastAPI?
- Works with LangChain?
- Works with Python version?
- Works with existing code?
- Works with deployment setup?

### 4. Consider Trade-offs

**Document trade-offs**:

- What are we giving up?
- What are we gaining?
- What are the risks?
- What are the costs?

## Phase 4: Make Recommendation

### 1. Choose Best Option

**Based on evaluation, choose**:

```markdown
## Recommendation

**Chosen Option**: [Option Name]

**Rationale**: [Why this option]

**Alternatives Considered**: [Other options and why not chosen]

**Trade-offs**: [What we're giving up/gaining]
```

### 2. Document Decision

**Create decision document**:

```markdown
# Decision: [Title]

**Date**: [Date]
**Context**: [What problem we're solving]
**Decision**: [What we decided]
**Rationale**: [Why]
**Alternatives**: [What else we considered]
**Trade-offs**: [What we're giving up]
**Impact**: [What this affects]
```

### 3. Plan Implementation

**If proceeding, create implementation plan**:

- What needs to be done?
- What are the steps?
- What are the dependencies?
- What are the risks?

## Phase 5: Document Findings

### 1. Create Research Document

**Document in `docs/working/research/[topic].md`**:

```markdown
# Research: [Topic]

## Research Question
[What we were trying to find out]

## Sources
- [Source 1]: [URL or reference]
- [Source 2]: [URL or reference]

## Findings
[Key findings from research]

## Options Evaluated
[Options and evaluation]

## Recommendation
[Chosen approach and rationale]

## Implementation Notes
[Notes for implementation]

## References
[Links and citations]
```

### 2. Update Relevant Documentation

**If research affects**:
- Architecture decisions → Update architecture docs
- API design → Update contracts
- Implementation patterns → Update coding standards

### 3. Share Learnings

**Document patterns and insights**:
- What worked well?
- What didn't work?
- What would we do differently?
- What patterns to reuse?

## Research Checklist

**Define**:
- [ ] Clarified research question
- [ ] Identified research areas

**Gather**:
- [ ] Searched official documentation
- [ ] Searched codebase
- [ ] Searched external resources
- [ ] Checked error logs
- [ ] Reviewed contracts and plans

**Evaluate**:
- [ ] Listed all options
- [ ] Compared options
- [ ] Checked compatibility
- [ ] Considered trade-offs

**Decide**:
- [ ] Chose best option
- [ ] Documented decision
- [ ] Planned implementation

**Document**:
- [ ] Created research document
- [ ] Updated relevant docs
- [ ] Shared learnings

## Example Research Scenarios

### Scenario 1: Choosing Authentication Method

**Research Question**: "What's the best authentication method for our FastAPI app?"

**Research Areas**:
- JWT vs sessions
- OAuth integration
- Security best practices
- FastAPI patterns

**Sources**:
- FastAPI security docs
- OWASP authentication guidelines
- Existing codebase patterns
- Error logs for auth issues

**Evaluation**:
- Option 1: JWT tokens
- Option 2: Session-based
- Option 3: OAuth

**Recommendation**: JWT tokens (stateless, scalable, FastAPI-friendly)

### Scenario 2: Testing LangChain Agents

**Research Question**: "How should we test LangChain agents?"

**Research Areas**:
- LangChain testing patterns
- Mocking LLMs
- Testing tools
- Testing state transitions

**Sources**:
- LangChain testing docs
- LangChain GitHub examples
- Existing test patterns
- TDD workflow

**Evaluation**:
- Option 1: Mock LLM calls
- Option 2: Use test LLM
- Option 3: Integration tests

**Recommendation**: Mock LLM calls for unit tests, integration tests for workflows

## Research Tools

```bash
# Web search
# Use browser or search tools

# Code search
grep -r "pattern" app/
codebase_search "query"

# Documentation
# Visit official docs websites

# GitHub search
# Search: github.com/search?q=langchain+fastapi

# Package search
# Visit: pypi.org
```
