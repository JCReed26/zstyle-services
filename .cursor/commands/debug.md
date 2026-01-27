---
name: debug
description: Systematic debugging workflow to identify, isolate, and fix issues. Follows a methodical approach to root cause analysis.
---

# Debug Workflow

## Overview

This workflow provides a systematic approach to debugging issues. Follow these steps to efficiently identify and resolve problems.

## Phase 1: Understand the Problem

### 1. Reproduce the Issue

**First, reproduce the problem**:

```bash
# Run the failing code
python app/main.py

# Run the failing test
pytest tests/test_specific.py::test_name -v

# Trigger the error condition
curl -X POST http://localhost:8000/api/endpoint
```

**Document**:
- What were you doing when it failed?
- What was the expected behavior?
- What actually happened?
- Can you reproduce it consistently?

### 2. Gather Error Information

**Collect all error details**:

```bash
# Check logs
tail -n 100 logs/app.log
grep -i "error" logs/app.log

# Check console output
# Copy full error traceback

# Check system logs (if applicable)
journalctl -u service-name -n 100
```

**Document**:
- Full error message
- Stack trace
- Error code/status
- Timestamp
- Environment (dev/staging/prod)

### 3. Check Error Logs (Natural Discovery)

**Before debugging, check if this error was seen before**:

```python
# Use semantic search to find similar errors
codebase_search "errors related to [error-type]"
codebase_search "issues with [component]"
codebase_search "solutions for [error-message]"
```

**Discovery Patterns**:

1. **Check Error Logs** (`docs/working/error-logs.md`):
   - Use semantic search: "errors like [error-message]"
   - Search by error category (auth, API, database, etc.)
   - Review solutions that worked
   - Review solutions that didn't work (to avoid repeating)

2. **Check Related Documentation**:
   - Check `docs/contracts/api/` if API-related
   - Check `docs/working/research/` for related research
   - Check `docs/architecture/decisions/` for related decisions

**Action**: Learn from past errors and solutions. Document new errors with full context.

## Phase 2: Isolate the Issue

### 1. Identify the Scope

**Determine**:
- Is this a frontend issue?
- Is this a backend issue?
- Is this a database issue?
- Is this an infrastructure issue?
- Is this an agent/LLM issue?

### 2. Narrow Down the Location

**Use debugging techniques**:

```python
# Add logging
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Variable value: {variable}")
logger.info(f"Function called with: {args}")
logger.error(f"Error occurred: {error}")

# Add breakpoints (if using debugger)
import pdb; pdb.set_trace()

# Add assertions
assert condition, "Expected condition not met"
```

### 3. Check Related Code

**Search for related code**:

```bash
# Find where error occurs
grep -r "function_name" app/

# Find similar patterns
grep -r "similar_pattern" app/

# Check imports
grep -r "import.*module" app/
```

### 4. Review Recent Changes

**Check what changed**:

```bash
# Git history
git log --oneline -10
git diff HEAD~1

# Check recent commits
git show HEAD

# Check specific file changes
git log -p -- path/to/file.py
```

## Phase 3: Analyze Root Cause

### 1. Form Hypotheses

**Based on evidence, form hypotheses**:

- Hypothesis 1: [Description]
- Hypothesis 2: [Description]
- Hypothesis 3: [Description]

### 2. Test Hypotheses

**Test each hypothesis**:

```python
# Test hypothesis 1
# Add test code or modify existing code
# Run and observe

# Test hypothesis 2
# ...

# Test hypothesis 3
# ...
```

### 3. Identify Root Cause

**Once root cause is identified, document**:

```markdown
## Root Cause Analysis

**Issue**: [Brief description]

**Root Cause**: [What actually caused it]

**Why it happened**: [Context and explanation]

**Impact**: [What was affected]
```

## Phase 4: Fix the Issue

### 1. Plan the Fix

**Before fixing, plan**:

- What needs to change?
- What are the side effects?
- What tests need updating?
- What documentation needs updating?

### 2. Implement Fix

**Make the fix**:

```python
# Fix the code
# Follow TDD if possible:
# 1. Write test that reproduces issue
# 2. Fix code to pass test
# 3. Ensure other tests still pass
```

### 3. Test the Fix

**Verify the fix works**:

```bash
# Run specific test
pytest tests/test_specific.py::test_name -v

# Run all related tests
pytest tests/ -k "keyword" -v

# Run full test suite
pytest tests/ -v

# Manual testing
# Test the specific scenario that failed
```

### 4. Check for Regressions

**Ensure nothing else broke**:

```bash
# Run full test suite
pytest tests/ -v

# Check related functionality
# Manually test related features
```

## Phase 5: Document and Learn

### 1. Update Error Logs

**Document in `docs/working/error-logs.md`**:

```markdown
## [Date] - [Error Name]

**Error**: [Error message]

**Root Cause**: [What caused it]

**Fix**: [How it was fixed]

**Prevention**: [How to prevent in future]

**Related**: [Links to related issues/docs]
```

### 2. Update Tests

**Add tests to prevent regression**:

```python
def test_prevents_specific_bug():
    """Test that prevents the bug we just fixed."""
    # Test code that would have caught the bug
    pass
```

### 3. Update Documentation

**If needed, update**:
- API contracts (if API changed)
- Feature docs (if behavior changed)
- Architecture docs (if design changed)

### 4. Share Learnings

**Document patterns**:
- Common pitfalls to avoid
- Debugging techniques that worked
- Tools that helped

## Debugging Techniques by Issue Type

### Backend/API Issues

```python
# Check request/response
logger.debug(f"Request: {request.json()}")
logger.debug(f"Response: {response.json()}")

# Check database queries
logger.debug(f"Query: {query}")
logger.debug(f"Result: {result}")

# Check authentication
logger.debug(f"User: {current_user}")
logger.debug(f"Permissions: {permissions}")
```

### Frontend Issues

```javascript
// Browser console
console.log('Variable:', variable);
console.trace('Call stack');

// Network tab
// Check API calls and responses

// React DevTools
// Inspect component state and props
```

### Agent/LLM Issues

```python
# Log agent state
logger.debug(f"Agent state: {state}")

# Log tool calls
logger.debug(f"Tool called: {tool_name}")
logger.debug(f"Tool input: {tool_input}")
logger.debug(f"Tool output: {tool_output}")

# Log LLM calls
logger.debug(f"LLM prompt: {prompt}")
logger.debug(f"LLM response: {response}")
```

### Database Issues

```python
# Check queries
logger.debug(f"SQL: {query}")

# Check connections
logger.debug(f"DB connection: {db.is_connected}")

# Check transactions
logger.debug(f"Transaction: {transaction}")
```

## Debugging Checklist

**Understanding**:
- [ ] Reproduced the issue
- [ ] Gathered error information
- [ ] Checked error logs

**Isolation**:
- [ ] Identified scope
- [ ] Narrowed down location
- [ ] Checked related code
- [ ] Reviewed recent changes

**Analysis**:
- [ ] Formed hypotheses
- [ ] Tested hypotheses
- [ ] Identified root cause

**Fix**:
- [ ] Planned the fix
- [ ] Implemented fix
- [ ] Tested fix
- [ ] Checked for regressions

**Documentation**:
- [ ] Updated error logs
- [ ] Updated tests
- [ ] Updated documentation
- [ ] Shared learnings

## Common Debugging Tools

```bash
# Python debugging
python -m pdb script.py
ipdb  # Enhanced pdb

# Logging
tail -f logs/app.log | grep ERROR

# Network debugging
curl -v http://localhost:8000/api/endpoint

# Database debugging
psql -d database_name -c "SELECT * FROM table;"

# Process debugging
ps aux | grep python
lsof -i :8000
```
