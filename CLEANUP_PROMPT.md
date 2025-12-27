# OpenMemory Integration Cleanup & Completion Prompt

## Context
The OpenMemory integration has been refactored from Docker-based to local SDK-based, but there are several incomplete pieces and bugs that need to be fixed.

## Issues to Fix

### 1. **OpenMemoryService API Mismatch** (`services/memory/openmemory_service.py`)
   - **Line 67**: `tags = metadata.pop("tags", []) if metadata else []` - This will fail if metadata is None because you can't call `.pop()` on None. Should be: `tags = (metadata or {}).pop("tags", [])`
   - **Line 71-75**: The `Memory.add()` signature expects `user_id` as a positional parameter, not keyword. Current code passes it as keyword. Fix to: `await self.mem.add(content, user_id=user_id, tags=tags, meta=metadata)`
   - **Line 102-106**: The `Memory.search()` signature expects `user_id` as a positional parameter. Current code incorrectly uses filters dict. Should be: `await self.mem.search(query, user_id=user_id, limit=limit)`

### 2. **Missing Agent Tool Integration** (`agents/exec_func_coach/agent.py`)
   - **Lines 36-41**: Import statements missing `add_long_term_memory` and `search_long_term_memory`
   - **Lines 98-117**: `get_default_tools()` function doesn't include the new long-term memory tools. Add both `add_long_term_memory` and `search_long_term_memory` to the tools list.

### 3. **Documentation Updates**
   - **`README.md`**: Add note about OpenMemory running locally (no Docker service needed)
   - **`docs/architecture.md`**: Already updated, verify it's accurate
   - **`docs/api.md`**: Consider adding OpenMemory endpoints if exposed via API

### 4. **Error Handling**
   - **`services/memory/openmemory_service.py`**: The global instance creation (line 115) catches all exceptions silently. Consider making it more robust or at least logging the specific error type.

### 5. **Test Coverage**
   - Verify tests cover the actual Memory API calls correctly
   - Ensure tests handle the case where `openmemory_service` is None

## Verification Steps

1. Run tests: `pytest tests/services/test_openmemory_service.py -v`
2. Verify agent can import and use the new tools
3. Check that OpenMemory initializes correctly without OpenAI key (should use synthetic embeddings)
4. Verify docker-compose.yml has no references to openmemory service
5. Ensure requirements.txt has `openmemory-py` (not `openmemory`)

## Expected Final State

- OpenMemory runs locally using `openmemory-py` SDK
- No Docker service needed for OpenMemory
- Agent has access to `add_long_term_memory` and `search_long_term_memory` tools
- All tests passing
- Documentation updated
- Code follows existing patterns and style

## Files to Modify

1. `services/memory/openmemory_service.py` - Fix API calls and error handling
2. `agents/exec_func_coach/agent.py` - Add new tools to imports and tool list
3. `README.md` - Update setup instructions
4. `tests/services/test_openmemory_service.py` - Verify test mocks match actual API

