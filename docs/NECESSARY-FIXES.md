# Necessary Fixes - Critical Issues Requiring Immediate Attention

This document outlines critical architectural issues that must be fixed before production deployment or significant scaling.

## Priority: CRITICAL

### 1. Remove Duplicate Database Directory

**Issue**: Two identical database directories exist:
- `core/database/` (actively used)
- `database/` (legacy, still referenced)

**Location**: Root directory

**Impact**:
- Code duplication and maintenance overhead
- Import confusion
- Risk of inconsistent changes
- Unclear source of truth

**Evidence**:
```python
# main.py uses core.database
from core.database.engine import engine, Base

# database/models/credential.py uses database
from database.engine import Base
```

**Fix Required**:
1. Search entire codebase for `from database.` imports
2. Replace all with `from core.database.`
3. Delete `database/` directory
4. Verify no references remain
5. Update any documentation

**Files to Update**:
- `database/models/credential.py`
- `database/models/user.py`
- `database/models/memory.py`
- `database/models/activity_log.py`
- `database/models/__init__.py`
- `database/__init__.py`
- `database/engine.py`

**Testing**:
- Run full test suite
- Verify all imports resolve
- Check for runtime errors

---

### 2. Fix Database Configuration for Production

**Issue**: Production database configuration is commented out, forcing SQLite in all environments.

**Location**: `core/database/engine.py` lines 25-35

**Impact**:
- Cannot deploy to production without code changes
- SQLite doesn't scale horizontally
- No connection pooling
- Risk of data loss in containerized environments
- Violates 12-factor app principles

**Current Code**:
```python
# === PRODUCTION: Uncomment for Supabase/PostgreSQL ===
# DATABASE_URL = os.getenv("DATABASE_URL")
# if not DATABASE_URL:
#     raise ValueError("DATABASE_URL environment variable is required for production")
# if DATABASE_URL.startswith("postgresql://"):
#     DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# === DEVELOPMENT: SQLite (default) ===
DATABASE_URL = "sqlite+aiosqlite:///zstyle.db"
```

**Fix Required**:
```python
# Get DATABASE_URL from environment, default to SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///zstyle.db")

# Convert postgresql:// to postgresql+asyncpg:// for async support
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Optional: Validate DATABASE_URL format
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set for production")
```

**Environment Variables**:
- Development: No `DATABASE_URL` → uses SQLite
- Production: `DATABASE_URL=postgresql://user:pass@host:5432/dbname`

**Testing**:
- Test with SQLite (no DATABASE_URL)
- Test with PostgreSQL (DATABASE_URL set)
- Verify connection pooling works
- Test connection recovery

---

### 3. Implement Webhook Verification

**Issue**: Telegram webhook verification is not implemented (placeholder returns False).

**Location**: `core/security.py` lines 87-105

**Impact**:
- Webhook endpoint accepts unverified requests
- Security vulnerability (injection attacks possible)
- No authentication for webhook calls

**Current Code**:
```python
def verify_telegram_webhook(data: dict, secret: str) -> bool:
    # TODO: Implement actual Telegram webhook HMAC verification
    return False
```

**Fix Required**:
```python
import hmac
import hashlib

def verify_telegram_webhook(data: dict, secret: str) -> bool:
    """
    Verify Telegram webhook signature using HMAC-SHA256.
    
    Telegram sends webhook secret token in X-Telegram-Bot-Api-Secret-Token header.
    This should match the secret configured in webhook setup.
    """
    if not secret:
        return False
    
    # Telegram webhook verification uses secret token in header
    # Compare against configured secret
    # Note: Actual implementation depends on Telegram's webhook format
    # This is a placeholder - verify against Telegram documentation
    
    # For now, check if secret matches configured webhook secret
    from core.config import settings
    configured_secret = settings.TELEGRAM_WEBHOOK_SECRET
    
    if not configured_secret:
        logger.warning("TELEGRAM_WEBHOOK_SECRET not configured - webhook verification disabled")
        return False
    
    return hmac.compare_digest(secret, configured_secret)
```

**Usage in Webhook Endpoint**:
```python
# In interface/telegram_webhook.py
secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
if not verify_telegram_webhook({}, secret_token):
    raise HTTPException(status_code=401, detail="Invalid webhook secret")
```

**Testing**:
- Test with valid secret token
- Test with invalid secret token
- Test with missing secret token
- Verify webhook endpoint rejects invalid requests

---

### 4. Initialize Alembic Migrations

**Issue**: Alembic is in requirements but no migrations directory exists.

**Location**: Root directory (needs creation)

**Impact**:
- No version-controlled schema changes
- Manual migrations required
- Cannot roll back changes
- Team coordination issues
- Production deployment risk

**Fix Required**:

1. **Initialize Alembic**:
```bash
alembic init alembic
```

2. **Configure `alembic/env.py`**:
```python
from core.database.engine import Base
from core.database.models import User, ActivityLog, Credential, UserMemory

# Set target metadata
target_metadata = Base.metadata

# Configure database URL from environment
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", "sqlite+aiosqlite:///zstyle.db"))
```

3. **Create Initial Migration**:
```bash
alembic revision --autogenerate -m "Initial schema"
```

4. **Review and Edit Migration**:
- Check generated migration
- Remove any unwanted changes
- Add data migrations if needed

5. **Test Migration**:
```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1
```

**Files to Create**:
- `alembic/` directory
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/` directory

**Testing**:
- Create fresh database
- Run migrations
- Verify schema matches models
- Test rollback

---

## Priority: HIGH

### 5. Replace In-Memory Session Storage

**Issue**: ADK sessions stored in memory, preventing horizontal scaling.

**Location**: `main.py` line 134, `channels/router.py` line 73

**Impact**:
- Sessions lost on restart
- Cannot scale horizontally
- No session persistence
- Poor user experience after deployments

**Current Code**:
```python
# main.py
bridge_session_service = InMemorySessionService()

# channels/router.py
self._user_sessions: Dict[str, str] = {}
```

**Fix Required**:

**Option A: Redis-backed Session Service** (Recommended)

1. Create RedisSessionService:
```python
# core/sessions/redis_session_service.py
from google.adk.sessions import BaseSessionService
import redis.asyncio as redis
import json

class RedisSessionService(BaseSessionService):
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
    
    async def create_session(self, app_name: str, user_id: str):
        # Create session and store in Redis
        session = Session(...)
        key = f"session:{app_name}:{user_id}:{session.id}"
        await self.redis.setex(key, 3600, json.dumps(session.to_dict()))
        return session
    
    async def get_session(self, app_name: str, user_id: str, session_id: str):
        key = f"session:{app_name}:{user_id}:{session_id}"
        data = await self.redis.get(key)
        if data:
            return Session.from_dict(json.loads(data))
        return None
```

2. Update main.py:
```python
from core.sessions.redis_session_service import RedisSessionService

bridge_session_service = RedisSessionService(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379")
)
```

**Option B: PostgreSQL-backed Session Service**

Similar approach but using PostgreSQL instead of Redis.

**Testing**:
- Test session creation
- Test session retrieval
- Test session expiration
- Test with multiple instances
- Test session persistence across restarts

---

### 6. Fix Encryption Key Derivation

**Issue**: Salt derived from SECRET_KEY weakens security.

**Location**: `core/security.py` lines 18-39

**Impact**:
- Reduced security strength
- No key rotation mechanism
- Single point of failure

**Current Code**:
```python
salt = hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:16]
```

**Fix Required**:

**Option A: Separate Salt Storage** (Recommended for new deployments)
```python
# Store salt separately (environment variable or secure storage)
SALT = os.getenv("ENCRYPTION_SALT", "").encode()
if not SALT:
    raise ValueError("ENCRYPTION_SALT must be set in production")

salt = SALT[:16] if len(SALT) >= 16 else SALT.ljust(16, b'0')
```

**Option B: Key Derivation with Random Salt** (Requires migration)
```python
# Store salt with each encrypted value
# Requires database migration to add salt column
```

**Option C: Use Key Management Service** (Best for production)
- AWS KMS, Azure Key Vault, or similar
- Automatic key rotation
- Hardware security modules

**Testing**:
- Test encryption/decryption roundtrip
- Test with different salts
- Verify backward compatibility (if keeping current approach)

---

## Implementation Order

1. **Week 1**: Fixes 1-4 (Database cleanup, config, webhooks, migrations)
2. **Week 2**: Fix 5 (Session storage)
3. **Week 3**: Fix 6 (Encryption) + Testing

## Testing Checklist

For each fix:
- [ ] Unit tests updated/added
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Code review completed
- [ ] Deployed to staging
- [ ] Production deployment plan created
