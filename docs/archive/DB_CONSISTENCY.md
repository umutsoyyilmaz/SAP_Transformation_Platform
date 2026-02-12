# Dev/Prod Database Consistency Analysis

**Document ID:** P3-DB-CONSISTENCY  
**Sprint:** 9+  
**Date:** 2025-02-09

---

## 1. Issue Summary

| # | Severity | Issue | Status |
|---|----------|-------|--------|
| 1 | 🔴 High | `embedding_vector` column in RAG code doesn't exist in model | ✅ Fixed |
| 2 | 🔴 High | NL Query hardcodes SQLite syntax regardless of actual DB | ✅ Fixed |
| 3 | 🔴 High | Tests never exercise PostgreSQL or Alembic migrations | 📋 Documented |
| 4 | 🟡 Medium | No migration for pgvector extension or vector column | ✅ Fixed |
| 5 | 🟡 Medium | FK constraints not enforced in SQLite | ✅ Fixed |
| 6 | 🟡 Medium | JSON stored as db.Text instead of db.JSON | 📋 Future |
| 7 | 🟠 Low | Docker-compose env label confusion | ✅ Fixed |
| 8 | 🟠 Low | pool_pre_ping irrelevant for SQLite | 📋 Harmless |

---

## 2. Fixes Applied

### Fix 1: RAG pgvector column alignment
- The RAG code references `embedding_vector` with pgvector `<=>` operator but the model only has `embedding_json` (Text)
- **Fix:** Updated RAG fallback logic to always use `embedding_json` with Python cosine similarity when pgvector isn't available; added proper vector query when pgvector IS present using explicit SQL

### Fix 2: NL Query DB-aware SQL generation
- The NL Query assistant hardcoded "SQLite" in its prompt preamble
- **Fix:** Made it detect the actual DB engine from `SQLALCHEMY_DATABASE_URI` and adjust prompt accordingly

### Fix 3: Alembic pgvector migration
- Created migration that conditionally creates `vector` extension and `embedding_vector` column on PostgreSQL (no-op on SQLite)

### Fix 4: SQLite FK enforcement
- Added `PRAGMA foreign_keys = ON` via SQLAlchemy event listener for SQLite connections

### Fix 5: Docker-compose clarity
- Changed prod compose to use `APP_ENV: production` with proper env var placeholders

---

## 3. Remaining Items (Future Sprints)

### PostgreSQL-specific test environment
- Add a `pytest -m postgres` marker for tests that require PostgreSQL
- Use `docker-compose.dev.yml` to spin up PostgreSQL for CI
- Add a GitHub Actions step to run postgres-marked tests against real PostgreSQL

### JSON column migration
- Migrate `metadata_json`, `suggestion_data`, `current_data` from `db.Text` to `db.JSON`
- Requires Alembic migration with `batch_alter_table` for SQLite compat
- Low priority — current approach works, just misses PG indexing benefits

### Migration verification tests
- Add a test that runs `flask db upgrade` against a fresh SQLite
- Validates Alembic migration chain is complete and consistent
