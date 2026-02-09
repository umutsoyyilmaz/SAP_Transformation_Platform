"""
Tests for KB Versioning — Sprint 9.5 (P9).

Tests:
    - KBVersion model CRUD & lifecycle
    - AIEmbedding versioning columns
    - Content-hash-based staleness detection
    - Non-destructive re-indexing
    - KB management API endpoints
    - Version diff endpoint
"""

import json
import pytest

from app import create_app
from app.models import db
from app.models.ai import AIEmbedding, KBVersion, AISuggestion, compute_content_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    a = create_app("testing")
    yield a


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()


@pytest.fixture()
def client(app):
    return app.test_client()


# ══════════════════════════════════════════════════════════════════════════════
# MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestKBVersionModel:
    """KBVersion model CRUD and lifecycle."""

    def test_create_kb_version(self, session):
        kbv = KBVersion(version="1.0.0", description="Initial version")
        session.add(kbv)
        session.flush()
        assert kbv.id is not None
        assert kbv.status == "building"
        assert kbv.version == "1.0.0"

    def test_activate_archives_previous(self, session):
        v1 = KBVersion(version="1.0.0", status="active")
        v2 = KBVersion(version="2.0.0", status="building")
        session.add_all([v1, v2])
        session.flush()

        v2.activate()
        session.flush()

        assert v2.status == "active"
        assert v2.activated_at is not None
        # v1 should be archived
        session.refresh(v1)
        assert v1.status == "archived"

    def test_archive(self, session):
        kbv = KBVersion(version="1.0.0", status="building")
        session.add(kbv)
        session.flush()

        kbv.archive()
        session.flush()
        assert kbv.status == "archived"
        assert kbv.archived_at is not None

    def test_to_dict(self, session):
        kbv = KBVersion(version="1.0.0", description="Test")
        session.add(kbv)
        session.flush()
        d = kbv.to_dict()
        assert d["version"] == "1.0.0"
        assert d["status"] == "building"
        assert "created_at" in d


class TestAIEmbeddingVersioning:
    """AIEmbedding versioning columns."""

    def test_new_columns_defaults(self, session):
        emb = AIEmbedding(
            entity_type="requirement",
            entity_id=1,
            chunk_text="test chunk",
        )
        session.add(emb)
        session.flush()
        assert emb.kb_version == "1.0.0"
        assert emb.is_active is True
        assert emb.content_hash is None
        assert emb.embedding_model is None

    def test_versioned_embedding(self, session):
        emb = AIEmbedding(
            entity_type="requirement",
            entity_id=1,
            chunk_text="test chunk",
            kb_version="2.0.0",
            content_hash="abc123",
            embedding_model="gemini-embedding-001",
            embedding_dim=1536,
            is_active=True,
        )
        session.add(emb)
        session.flush()
        d = emb.to_dict()
        assert d["kb_version"] == "2.0.0"
        assert d["content_hash"] == "abc123"
        assert d["embedding_model"] == "gemini-embedding-001"
        assert d["embedding_dim"] == 1536
        assert d["is_active"] is True


class TestContentHash:
    """compute_content_hash utility."""

    def test_same_text_same_hash(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_different_text_different_hash(self):
        h1 = compute_content_hash("hello world")
        h2 = compute_content_hash("hello world!")
        assert h1 != h2

    def test_hash_length(self):
        h = compute_content_hash("test")
        assert len(h) == 64  # SHA-256 hex digest


class TestAISuggestionKBVersion:
    """AISuggestion kb_version field."""

    def test_suggestion_has_kb_version(self, session):
        s = AISuggestion(
            suggestion_type="defect_triage",
            entity_type="defect",
            entity_id=1,
            title="Test suggestion",
            kb_version="2.0.0",
        )
        session.add(s)
        session.flush()
        d = s.to_dict()
        assert d["kb_version"] == "2.0.0"


# ══════════════════════════════════════════════════════════════════════════════
# RAG PIPELINE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRAGVersionedIndexing:
    """Non-destructive content-hash indexing."""

    def test_index_entity_sets_version_and_hash(self, app, session):
        from app.ai.rag import RAGPipeline
        rag = RAGPipeline()

        records = rag.index_entity(
            "requirement", 99,
            {"id": 99, "title": "Payment", "description": "Process payments"},
            embed=False,
            kb_version="1.0.0",
        )
        assert len(records) >= 1
        assert records[0].kb_version == "1.0.0"
        assert records[0].content_hash is not None
        assert records[0].is_active is True

    def test_index_entity_skips_unchanged(self, app, session):
        from app.ai.rag import RAGPipeline
        rag = RAGPipeline()

        data = {"id": 100, "title": "Invoice", "description": "Process invoices"}
        first = rag.index_entity("requirement", 100, data, embed=False, kb_version="1.0.0")
        assert len(first) >= 1

        # Same content → should skip
        second = rag.index_entity("requirement", 100, data, embed=False, kb_version="1.0.0")
        assert len(second) == 0, "Should skip unchanged content"

    def test_index_entity_replaces_on_change(self, app, session):
        from app.ai.rag import RAGPipeline
        rag = RAGPipeline()

        data_v1 = {"id": 101, "title": "Payment", "description": "V1 description"}
        first = rag.index_entity("requirement", 101, data_v1, embed=False, kb_version="1.0.0")
        assert len(first) >= 1

        data_v2 = {"id": 101, "title": "Payment", "description": "V2 updated description with more detail"}
        second = rag.index_entity("requirement", 101, data_v2, embed=False, kb_version="2.0.0")
        assert len(second) >= 1
        assert second[0].kb_version == "2.0.0"

        # Old version should be deactivated
        old = AIEmbedding.query.filter_by(
            entity_type="requirement", entity_id=101, is_active=False,
        ).count()
        assert old >= 1

    def test_search_filters_active_only(self, app, session):
        from app.ai.rag import RAGPipeline
        rag = RAGPipeline()

        # Create active and inactive embeddings
        active = AIEmbedding(
            entity_type="requirement", entity_id=200,
            chunk_text="active payment processing", is_active=True,
        )
        inactive = AIEmbedding(
            entity_type="requirement", entity_id=201,
            chunk_text="inactive payment processing", is_active=False,
        )
        session.add_all([active, inactive])
        session.flush()

        results = rag.search("payment processing", top_k=10)
        result_ids = {r["entity_id"] for r in results}
        assert 200 in result_ids
        assert 201 not in result_ids

    def test_find_stale_embeddings(self, app, session):
        from app.ai.rag import RAGPipeline

        # Embedding without content_hash = potentially stale
        stale = AIEmbedding(
            entity_type="risk", entity_id=300,
            chunk_text="stale risk", is_active=True, content_hash=None,
        )
        fresh = AIEmbedding(
            entity_type="risk", entity_id=301,
            chunk_text="fresh risk", is_active=True, content_hash="abc123",
        )
        session.add_all([stale, fresh])
        session.flush()

        results = RAGPipeline.find_stale_embeddings()
        stale_keys = {(r["entity_type"], r["entity_id"]) for r in results}
        assert ("risk", 300) in stale_keys
        assert ("risk", 301) not in stale_keys


class TestGetIndexStats:
    """Index stats include versioning info."""

    def test_stats_include_version_counts(self, app, session):
        from app.ai.rag import RAGPipeline

        session.add_all([
            AIEmbedding(entity_type="requirement", entity_id=400,
                        chunk_text="v1", is_active=True, kb_version="1.0.0"),
            AIEmbedding(entity_type="requirement", entity_id=401,
                        chunk_text="v2", is_active=True, kb_version="2.0.0"),
            AIEmbedding(entity_type="risk", entity_id=402,
                        chunk_text="v2r", is_active=True, kb_version="2.0.0"),
            AIEmbedding(entity_type="risk", entity_id=403,
                        chunk_text="archived", is_active=False, kb_version="1.0.0"),
        ])
        session.flush()

        stats = RAGPipeline.get_index_stats()
        assert "by_kb_version" in stats
        assert stats["archived_chunks"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestKBVersionAPI:
    """KB version management endpoints."""

    def test_create_version(self, client):
        r = client.post("/api/v1/ai/kb/versions", json={
            "version": "1.0.0",
            "description": "Initial KB",
        })
        assert r.status_code == 201
        assert r.get_json()["version"] == "1.0.0"

    def test_create_duplicate_version(self, client):
        client.post("/api/v1/ai/kb/versions", json={"version": "1.0.0"})
        r = client.post("/api/v1/ai/kb/versions", json={"version": "1.0.0"})
        assert r.status_code == 409

    def test_create_version_missing_version(self, client):
        r = client.post("/api/v1/ai/kb/versions", json={"description": "No version"})
        assert r.status_code == 400

    def test_list_versions(self, client):
        client.post("/api/v1/ai/kb/versions", json={"version": "1.0.0"})
        r = client.get("/api/v1/ai/kb/versions")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_version_detail(self, client):
        r1 = client.post("/api/v1/ai/kb/versions", json={"version": "5.0.0"})
        assert r1.status_code == 201, r1.get_json()
        vid = r1.get_json()["id"]
        r2 = client.get(f"/api/v1/ai/kb/versions/{vid}")
        assert r2.status_code == 200
        assert "live_chunks" in r2.get_json()

    def test_get_version_not_found(self, client):
        r = client.get("/api/v1/ai/kb/versions/9999")
        assert r.status_code == 404

    def test_activate_version(self, client):
        r1 = client.post("/api/v1/ai/kb/versions", json={"version": "6.0.0"})
        assert r1.status_code == 201, r1.get_json()
        vid = r1.get_json()["id"]
        r2 = client.patch(f"/api/v1/ai/kb/versions/{vid}/activate")
        assert r2.status_code == 200
        assert r2.get_json()["status"] == "active"

    def test_archive_building_version(self, client):
        r1 = client.post("/api/v1/ai/kb/versions", json={"version": "7.0.0"})
        assert r1.status_code == 201, r1.get_json()
        vid = r1.get_json()["id"]
        r2 = client.patch(f"/api/v1/ai/kb/versions/{vid}/archive")
        assert r2.status_code == 200
        assert r2.get_json()["status"] == "archived"

    def test_archive_active_version_fails(self, client):
        r1 = client.post("/api/v1/ai/kb/versions", json={"version": "8.0.0"})
        assert r1.status_code == 201, r1.get_json()
        vid = r1.get_json()["id"]
        client.patch(f"/api/v1/ai/kb/versions/{vid}/activate")
        r2 = client.patch(f"/api/v1/ai/kb/versions/{vid}/archive")
        assert r2.status_code == 400


class TestKBStaleAPI:
    """Staleness detection endpoint."""

    def test_stale_endpoint(self, client, session):
        session.add(AIEmbedding(
            entity_type="defect", entity_id=500,
            chunk_text="stale", is_active=True, content_hash=None,
        ))
        session.flush()

        r = client.get("/api/v1/ai/kb/stale")
        assert r.status_code == 200
        data = r.get_json()
        assert "stale_entities" in data
        assert data["total"] >= 1


class TestKBDiffAPI:
    """Version diff endpoint."""

    def test_diff_versions(self, client, session):
        # v1 entities
        session.add_all([
            AIEmbedding(entity_type="requirement", entity_id=601,
                        chunk_text="v1 req", kb_version="1.0.0", content_hash="aaa"),
            AIEmbedding(entity_type="requirement", entity_id=602,
                        chunk_text="v1 common", kb_version="1.0.0", content_hash="bbb"),
        ])
        # v2 entities
        session.add_all([
            AIEmbedding(entity_type="requirement", entity_id=602,
                        chunk_text="v2 common changed", kb_version="2.0.0", content_hash="ccc"),
            AIEmbedding(entity_type="risk", entity_id=603,
                        chunk_text="v2 new", kb_version="2.0.0", content_hash="ddd"),
        ])
        session.flush()

        r = client.get("/api/v1/ai/kb/diff/1.0.0/2.0.0")
        assert r.status_code == 200
        data = r.get_json()
        assert data["summary"]["added_count"] >= 1     # risk/603 added
        assert data["summary"]["removed_count"] >= 1   # req/601 removed
        assert data["summary"]["changed_count"] >= 1   # req/602 hash changed
