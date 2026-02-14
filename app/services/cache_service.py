"""
Tenant-Aware Cache Service — Sprint 9 (Item 4.2)

Provides a thin cache wrapper with:
  - Permission cache (5 min TTL)
  - Role lookup cache (5 min TTL)
  - Manual invalidation helpers

Uses Redis in production (via REDIS_URL), falls back to
a simple in-memory dict for development/testing.
"""

import json
import logging
import time

logger = logging.getLogger(__name__)

# ── In-memory fallback ───────────────────────────────────────────────────

_memory_store: dict = {}  # key → (value_json, expire_ts)


class _MemoryBackend:
    """Simple dict cache for dev/testing."""

    def get(self, key):
        entry = _memory_store.get(key)
        if entry is None:
            return None
        val, expires = entry
        if expires and time.time() > expires:
            _memory_store.pop(key, None)
            return None
        return val

    def setex(self, key, ttl_seconds, value):
        _memory_store[key] = (value, time.time() + ttl_seconds)

    def delete(self, *keys):
        for k in keys:
            _memory_store.pop(k, None)

    def keys(self, pattern):
        """Simple glob matching for 'prefix*' patterns."""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in _memory_store if k.startswith(prefix)]
        return [k for k in _memory_store if k == pattern]

    def flushdb(self):
        _memory_store.clear()

    def ping(self):
        return True


# ── Singleton cache backend ──────────────────────────────────────────────

_backend = None


def _get_backend():
    """Lazy-initialise Redis or fall back to in-memory."""
    global _backend
    if _backend is not None:
        return _backend

    import os
    redis_url = os.getenv("REDIS_URL")
    if redis_url and not redis_url.startswith("memory://"):
        try:
            import redis as _redis
            _backend = _redis.from_url(redis_url, decode_responses=True)
            _backend.ping()
            logger.info("Cache: using Redis at %s", redis_url.split("@")[-1])
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — falling back to memory cache", exc)
            _backend = _MemoryBackend()
    else:
        _backend = _MemoryBackend()
    return _backend


# ── Default TTLs ─────────────────────────────────────────────────────────

PERMISSION_TTL = 300   # 5 minutes
ROLE_TTL = 300         # 5 minutes
DEFAULT_TTL = 300


# ── Key builders ─────────────────────────────────────────────────────────

def _perm_key(tenant_id, user_id):
    return f"perm:{tenant_id}:{user_id}"


def _role_key(tenant_id, user_id):
    return f"roles:{tenant_id}:{user_id}"


def _flag_key(tenant_id, flag_key):
    return f"ff:{tenant_id}:{flag_key}"


# ── Public API ───────────────────────────────────────────────────────────


def get_cached_permissions(tenant_id, user_id):
    """Return cached permission codenames list, or None on miss."""
    raw = _get_backend().get(_perm_key(tenant_id, user_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached_permissions(tenant_id, user_id, permissions):
    """Cache a list of permission codenames."""
    _get_backend().setex(
        _perm_key(tenant_id, user_id),
        PERMISSION_TTL,
        json.dumps(permissions),
    )


def get_cached_roles(tenant_id, user_id):
    """Return cached role names list, or None on miss."""
    raw = _get_backend().get(_role_key(tenant_id, user_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached_roles(tenant_id, user_id, roles):
    """Cache a list of role names."""
    _get_backend().setex(
        _role_key(tenant_id, user_id),
        ROLE_TTL,
        json.dumps(roles),
    )


def invalidate_user_cache(tenant_id, user_id):
    """Remove all cached data for a specific user."""
    be = _get_backend()
    be.delete(_perm_key(tenant_id, user_id), _role_key(tenant_id, user_id))


def invalidate_tenant_cache(tenant_id):
    """Remove all cached data for a tenant (e.g. after role/permission change)."""
    be = _get_backend()
    for prefix in ("perm:", "roles:", "ff:"):
        pattern = f"{prefix}{tenant_id}:*"
        keys = be.keys(pattern)
        if keys:
            be.delete(*keys)


def get_cached(key, ttl=DEFAULT_TTL, loader=None):
    """Generic cache-aside.  If *loader* is provided, it's called on miss
    and the result is cached."""
    be = _get_backend()
    raw = be.get(key)
    if raw is not None:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    if loader is None:
        return None
    value = loader()
    if value is not None:
        be.setex(key, ttl, json.dumps(value))
    return value


def set_cached(key, value, ttl=DEFAULT_TTL):
    """Generic set."""
    _get_backend().setex(key, ttl, json.dumps(value))


def delete_cached(key):
    """Generic delete."""
    _get_backend().delete(key)


def clear_all():
    """Flush entire cache (use sparingly — mainly for testing)."""
    _get_backend().flushdb()


def health_check():
    """Return cache backend status."""
    try:
        be = _get_backend()
        be.ping()
        backend_type = "redis" if not isinstance(be, _MemoryBackend) else "memory"
        return {"status": "ok", "backend": backend_type}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
