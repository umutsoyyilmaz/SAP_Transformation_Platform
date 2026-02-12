"""
SAP Transformation Management Platform
AI Response Cache — Sprint 20 (Performance).

Two-tier caching:
    1. In-memory TTLCache for hot responses (sub-millisecond reads)
    2. DB-backed AIResponseCache for persistence across restarts

Skip cache for:
    - Conversations (multi-turn context changes every message)
    - Explicitly disabled via `use_cache=False`
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from threading import Lock

from app.models import db
from app.models.ai import AIResponseCache

logger = logging.getLogger(__name__)

# Default TTL in seconds
DEFAULT_TTL_SECONDS = 300  # 5 minutes
MAX_MEMORY_ENTRIES = 500

# Purposes that should never be cached (context-dependent)
SKIP_CACHE_PURPOSES = {"conversation", "conversation_general"}


class ResponseCacheService:
    """LLM response cache with in-memory + DB tiers."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, dict] = {}  # prompt_hash → {response, expires_at}
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

    @staticmethod
    def compute_hash(messages: list, model: str) -> str:
        """Compute deterministic hash for a prompt + model combination."""
        payload = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, prompt_hash: str) -> dict | None:
        """
        Look up cached response. Check memory first, then DB.

        Returns:
            dict with cached LLM response or None if miss/expired.
        """
        now = datetime.now(timezone.utc)

        # Tier 1: in-memory
        with self._lock:
            entry = self._memory.get(prompt_hash)
            if entry and entry["expires_at"] > now:
                self._stats["hits"] += 1
                return entry["response"]
            elif entry:
                # Expired in-memory entry
                del self._memory[prompt_hash]

        # Tier 2: DB
        try:
            cached = AIResponseCache.query.filter_by(prompt_hash=prompt_hash).first()
            if cached and not cached.is_expired():
                # Promote to in-memory
                response = json.loads(cached.response_json)
                with self._lock:
                    self._memory[prompt_hash] = {
                        "response": response,
                        "expires_at": cached.expires_at,
                    }
                    self._enforce_memory_limit()

                # Update hit stats
                cached.hit_count = (cached.hit_count or 0) + 1
                cached.last_hit_at = now
                db.session.flush()

                self._stats["hits"] += 1
                return response
            elif cached:
                # Expired DB entry — clean up
                db.session.delete(cached)
                db.session.flush()
        except Exception as exc:
            logger.warning("Cache DB lookup failed: %s", exc)

        self._stats["misses"] += 1
        return None

    def set(self, prompt_hash: str, response: dict, model: str = "",
            purpose: str = "", prompt_tokens: int = 0,
            completion_tokens: int = 0, ttl_seconds: int | None = None):
        """Store a response in both memory and DB cache."""
        ttl = ttl_seconds or self.ttl_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        # Tier 1: in-memory
        with self._lock:
            self._memory[prompt_hash] = {
                "response": response,
                "expires_at": expires_at,
            }
            self._enforce_memory_limit()

        # Tier 2: DB
        try:
            existing = AIResponseCache.query.filter_by(prompt_hash=prompt_hash).first()
            if existing:
                existing.response_json = json.dumps(response)
                existing.expires_at = expires_at
                existing.model = model
            else:
                entry = AIResponseCache(
                    prompt_hash=prompt_hash,
                    model=model,
                    purpose=purpose,
                    response_json=json.dumps(response),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    expires_at=expires_at,
                )
                db.session.add(entry)
            db.session.flush()
        except Exception as exc:
            logger.warning("Cache DB write failed: %s", exc)

        self._stats["sets"] += 1

    def invalidate(self, prompt_hash: str | None = None):
        """
        Invalidate cache entries.
        If prompt_hash is None, clears everything.
        """
        with self._lock:
            if prompt_hash:
                self._memory.pop(prompt_hash, None)
            else:
                count = len(self._memory)
                self._memory.clear()
                self._stats["evictions"] += count

        try:
            if prompt_hash:
                AIResponseCache.query.filter_by(prompt_hash=prompt_hash).delete()
            else:
                AIResponseCache.query.delete()
            db.session.flush()
        except Exception as exc:
            logger.warning("Cache invalidation failed: %s", exc)

    def cleanup_expired(self) -> int:
        """Remove expired entries from DB. Returns count of deleted entries."""
        try:
            now = datetime.now(timezone.utc)
            deleted = AIResponseCache.query.filter(
                AIResponseCache.expires_at < now
            ).delete()
            db.session.flush()
            return deleted
        except Exception as exc:
            logger.warning("Cache cleanup failed: %s", exc)
            return 0

    def get_stats(self) -> dict:
        """Return cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0

        # Count DB entries
        try:
            db_count = AIResponseCache.query.count()
        except Exception:
            db_count = 0

        with self._lock:
            mem_count = len(self._memory)

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "sets": self._stats["sets"],
            "evictions": self._stats["evictions"],
            "hit_rate_pct": round(hit_rate, 2),
            "memory_entries": mem_count,
            "db_entries": db_count,
            "ttl_seconds": self.ttl_seconds,
        }

    def should_cache(self, purpose: str) -> bool:
        """Check if a given purpose should be cached."""
        return purpose not in SKIP_CACHE_PURPOSES and not purpose.startswith("conversation_")

    def _enforce_memory_limit(self):
        """Evict oldest entries if memory cache exceeds limit. Must hold lock."""
        if len(self._memory) > MAX_MEMORY_ENTRIES:
            # Sort by expires_at, evict oldest
            sorted_keys = sorted(
                self._memory.keys(),
                key=lambda k: self._memory[k]["expires_at"],
            )
            to_remove = len(self._memory) - MAX_MEMORY_ENTRIES
            for key in sorted_keys[:to_remove]:
                del self._memory[key]
                self._stats["evictions"] += 1
