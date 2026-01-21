# Credential Management Audit Report

## Executive Summary

This audit identifies critical issues in the OAuth and credential management system that prevent Google ADK toolsets from accessing per-user credentials. The system violates ADK credential patterns by initializing toolsets at module load without per-user credential injection.

## Phase 1 Audit Results

### 1.1 Credential Storage Locations

#### Database Storage (Working)
- **Location**: `services/credential_service.py`
- **Status**: ✅ Functional
- **Storage**: Encrypted tokens in PostgreSQL `credentials` table
- **Access Pattern**: Per-user retrieval via `credential_service.get_credentials(user_id, service)`

#### OAuth Callback Storage (Partially Working)
- **Location**: `app/main.py:537-541` (Google), `app/main.py:739-744` (TickTick)
- **Status**: ⚠️ Stores tokens but doesn't calculate `expires_at`
- **Issue**: `expires_in` stored but `expires_at` never calculated

#### Module-Level Toolset Initialization (BROKEN)
- **Location**: `agent/exec_func_coach/googtools.py:173-256`
- **Status**: ❌ Broken - Toolsets initialized without per-user credentials
- **Issue**: Google toolsets created once at module load with only `client_id`/`client_secret`
- **Impact**: Toolsets cannot access user-specific tokens stored in database

#### Session State Storage (Partial)
- **Location**: `channels/router.py:250-251`
- **Status**: ⚠️ Only stores `user_id`, not credentials
- **Issue**: Credentials never synced to `tool_context.state` as ADK expects

### 1.2 ADK Pattern Violations

#### Violation 1: Module-Level Toolset Initialization
**Current Code:**
```python
# agent/exec_func_coach/googtools.py:177-180
google_calendar_toolset = CalendarToolset(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)
```

**ADK Expected Pattern:**
- Toolsets should be created per-request with user credentials
- Credentials should come from `tool_context.state` or `request_credential()`
- No global toolset instances shared across users

#### Violation 2: Missing Credential Flow
**Current Code:**
- No `tool_context.request_credential()` calls
- No `tool_context.get_auth_response()` handling
- Credentials stored in database but never accessed by Google toolsets

**ADK Expected Pattern:**
```python
def secure_tool(..., tool_context: ToolContext):
    cred_key = "auth:google:user_id"
    cred_data = tool_context.state.get(cred_key)
    if not cred_data:
        tool_context.request_credential(auth_config)
        return {"status": "auth_required"}
    # Use credentials...
```

#### Violation 3: Token Expiration Not Handled
**Current Code:**
```python
# app/main.py:537-541
await credential_service.store_credentials(user_id, "google", {
    "token": tokens["access_token"],
    "refresh_token": tokens.get("refresh_token"),
    "expires_in": tokens.get("expires_in", 3600)  # Stored but never used
})
```

**Issue**: `expires_at` never calculated, expiration never checked

### 1.3 Security Audit Results

#### Encryption Implementation
- **Status**: ✅ Credentials encrypted at rest using Fernet
- **Issue**: Fixed salt (`b'zstyle_salt_2024'`) reduces security
- **Recommendation**: Use environment-specific salt or derive from SECRET_KEY

#### Token Storage
- **Access Tokens**: ✅ Encrypted in database
- **Refresh Tokens**: ✅ Encrypted in database
- **Expiration**: ❌ Not tracked (`expires_at` NULL for all Google credentials)

#### Credential Lifecycle
- **Creation**: ✅ OAuth callback stores tokens
- **Refresh**: ❌ Missing for Google (exists for TickTick)
- **Revocation**: ❌ No handling for revoked tokens
- **Deletion**: ✅ `delete_credentials()` exists

### 1.4 Known ADK Issues

#### Issue #267: Bearer Token Not Passed to ToolContext
- **Impact**: HTTP bearer tokens won't be available in `tool_context`
- **Workaround**: Use `tool_context.state` for credential storage
- **Status**: Not currently affected (not using bearer tokens)

#### Issue #734: SecuritySchemeType Serialization
- **Impact**: May cause issues with DatabaseSessionService
- **Workaround**: Using InMemorySessionService (not affected)
- **Status**: Not currently affected

#### Issue #3331: MCP OAuth2 Flow Defect
- **Impact**: OAuth flows may fail during tool discovery
- **Workaround**: Ensure toolsets don't require auth during discovery
- **Status**: Not currently affected (not using MCP)

### 1.5 Comparison: TickTick (Working) vs Google (Broken)

#### TickTick Pattern (✅ Works)
```python
# agent/exec_func_coach/ticktool.py:132-175
async def get_ticktick_client(user_id: str):
    # 1. Retrieve credentials per-request from database
    creds = await credential_service.get_credentials(user_id, "ticktick")
    
    # 2. Check expiration and refresh if needed
    if creds.get("refresh_token") and token_expired:
        updated_creds = await refresh_ticktick_token(user_id, creds)
    
    # 3. Create client with user-specific credentials
    auth = OAuth2(...)
    auth.token = creds.get("token")
    auth.refresh_token = creds.get("refresh_token")
    return TickTickClient(None, auth)
```

**Why It Works:**
- Credentials retrieved per-request from database
- Token refresh implemented
- User-specific client creation

#### Google Pattern (❌ Broken)
```python
# agent/exec_func_coach/googtools.py:177-180
google_calendar_toolset = CalendarToolset(
    client_id=settings.GOOGLE_CLIENT_ID,  # Global, not per-user
    client_secret=settings.GOOGLE_CLIENT_SECRET
)
```

**Why It Fails:**
- Toolset initialized once at module load
- No per-user credential injection
- Credentials in database never accessed

## Phase 1 Actions Completed

- [x] Documented all credential storage locations
- [x] Identified ADK pattern violations
- [x] Security audit completed
- [x] Documented TickTick vs Google comparison
- [x] Identified known ADK issues and workarounds

## Phase 1 Actions Remaining

- [ ] Remove broken module-level toolset initialization
- [ ] Remove unused credential callback functions
- [ ] Create test suite for credential flows
- [ ] Database migration to calculate expires_at

## Next Steps: Phase 2 Rebuild

See `docs/CREDENTIAL_REBUILD_PLAN.md` for detailed Phase 2 implementation plan.
