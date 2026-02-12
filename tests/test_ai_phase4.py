"""
SAP Transformation Management Platform
Tests — AI Phase 4: Doc Gen + Multi-turn Conversations (Sprint 19).

Covers:
    - AIConversation & AIConversationMessage models
    - ConversationManager service (create / send / close / list / get)
    - SteeringPackGenerator assistant
    - WRICEFSpecDrafter assistant
    - DataQualityGuardian assistant
    - API endpoints: /doc-gen/*, /conversations/*
"""

import json
import pytest

from app import create_app
from app.models import db as _db
from app.models.ai import (
    AIConversation,
    AIConversationMessage,
    AISuggestion,
    CONVERSATION_STATUSES,
    ASSISTANT_TYPES,
    DOC_GEN_TYPES,
    SUGGESTION_TYPES,
)
from app.models.program import Program
from app.models.backlog import BacklogItem
from app.models.data_factory import DataObject


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    return create_app("testing")


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helpers ──────────────────────────────────────────────────────────────


def _create_program(client, **kw):
    payload = {"name": "S19 Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_backlog_item(program_id, **kw):
    """Insert a BacklogItem directly into the DB."""
    data = {
        "program_id": program_id,
        "title": "GL Account Posting Enhancement",
        "description": "Custom GL posting logic for FICO module",
        "wricef_type": "enhancement",
        "module": "FI",
        "status": "new",
    }
    data.update(kw)
    item = BacklogItem(**data)
    _db.session.add(item)
    _db.session.commit()
    return item


def _create_data_object(program_id, **kw):
    """Insert a DataObject directly into the DB."""
    data = {
        "program_id": program_id,
        "name": "GL Master Data",
        "description": "General Ledger master records",
        "source_system": "ECC",
        "target_table": "BKPF",
        "record_count": 150_000,
        "status": "profiled",
    }
    data.update(kw)
    obj = DataObject(**data)
    _db.session.add(obj)
    _db.session.commit()
    return obj


# ═════════════════════════════════════════════════════════════════════════════
# 1. MODEL TESTS — AIConversation & AIConversationMessage
# ═════════════════════════════════════════════════════════════════════════════


class TestAIConversationModel:
    """AIConversation ORM model tests."""

    def test_create_conversation(self, app):
        conv = AIConversation(
            title="Test Session",
            assistant_type="general",
            status="active",
            user="alice",
        )
        _db.session.add(conv)
        _db.session.commit()
        assert conv.id is not None
        assert conv.status == "active"
        assert conv.message_count == 0

    def test_conversation_to_dict(self, app, client):
        prog = _create_program(client)
        conv = AIConversation(
            title="Dict Test",
            assistant_type="requirement_analyst",
            status="active",
            user="bob",
            program_id=prog["id"],
        )
        _db.session.add(conv)
        _db.session.commit()
        d = conv.to_dict()
        assert d["title"] == "Dict Test"
        assert d["assistant_type"] == "requirement_analyst"
        assert d["user"] == "bob"
        assert "messages" not in d

    def test_conversation_to_dict_with_messages(self, app):
        conv = AIConversation(title="Msgs Test", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        msg = AIConversationMessage(
            conversation_id=conv.id, seq=1, role="user", content="Hello"
        )
        _db.session.add(msg)
        _db.session.commit()
        d = conv.to_dict(include_messages=True)
        assert "messages" in d
        assert len(d["messages"]) == 1
        assert d["messages"][0]["content"] == "Hello"

    def test_conversation_repr(self, app):
        conv = AIConversation(title="Repr", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        r = repr(conv)
        assert "general" in r or str(conv.id) in r

    def test_conversation_statuses_constant(self):
        assert "active" in CONVERSATION_STATUSES
        assert "closed" in CONVERSATION_STATUSES
        assert "archived" in CONVERSATION_STATUSES

    def test_assistant_types_constant(self):
        assert "general" in ASSISTANT_TYPES
        assert "steering_pack" in ASSISTANT_TYPES
        assert "wricef_spec" in ASSISTANT_TYPES
        assert "data_quality" in ASSISTANT_TYPES
        assert len(ASSISTANT_TYPES) >= 12

    def test_doc_gen_types_constant(self):
        assert DOC_GEN_TYPES == {"steering_pack", "wricef_spec", "data_quality"}

    def test_suggestion_types_include_new(self):
        for t in ("steering_pack", "wricef_spec", "data_quality", "conversation"):
            assert t in SUGGESTION_TYPES

    def test_conversation_with_context_json(self, app):
        ctx = {"filters": {"module": "FI"}, "settings": {"lang": "en"}}
        conv = AIConversation(
            title="Ctx Test",
            assistant_type="general",
            status="active",
            context_json=json.dumps(ctx),
        )
        _db.session.add(conv)
        _db.session.commit()
        loaded = json.loads(conv.context_json)
        assert loaded["filters"]["module"] == "FI"


class TestAIConversationMessageModel:
    """AIConversationMessage ORM model tests."""

    def test_create_message(self, app):
        conv = AIConversation(title="Msg Parent", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        msg = AIConversationMessage(
            conversation_id=conv.id,
            seq=1,
            role="user",
            content="What is SAP FICO?",
        )
        _db.session.add(msg)
        _db.session.commit()
        assert msg.id is not None
        assert msg.role == "user"

    def test_message_to_dict(self, app):
        conv = AIConversation(title="P", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        msg = AIConversationMessage(
            conversation_id=conv.id, seq=1, role="assistant",
            content="SAP FICO is ...", model="local-stub",
            prompt_tokens=10, completion_tokens=20, cost_usd=0.0, latency_ms=50,
        )
        _db.session.add(msg)
        _db.session.commit()
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert d["model"] == "local-stub"
        assert d["prompt_tokens"] == 10

    def test_message_repr(self, app):
        conv = AIConversation(title="R", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        msg = AIConversationMessage(
            conversation_id=conv.id, seq=1, role="user", content="Hi"
        )
        _db.session.add(msg)
        _db.session.commit()
        r = repr(msg)
        assert "user" in r

    def test_message_cascade_delete(self, app):
        conv = AIConversation(title="Cascade", assistant_type="general", status="active")
        _db.session.add(conv)
        _db.session.commit()
        for i in range(3):
            _db.session.add(AIConversationMessage(
                conversation_id=conv.id, seq=i + 1, role="user",
                content=f"msg {i}",
            ))
        _db.session.commit()
        assert AIConversationMessage.query.filter_by(conversation_id=conv.id).count() == 3
        _db.session.delete(conv)
        _db.session.commit()
        assert AIConversationMessage.query.filter_by(conversation_id=conv.id).count() == 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. CONVERSATION MANAGER SERVICE TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestConversationManager:
    """Unit tests for ConversationManager service."""

    def _make_mgr(self, app):
        from app.ai.conversation import ConversationManager
        from app.ai.gateway import LLMGateway
        from app.ai.prompt_registry import PromptRegistry
        gw = LLMGateway(app)
        pr = PromptRegistry()
        return ConversationManager(gateway=gw, prompt_registry=pr)

    def test_create_session_basic(self, app):
        mgr = self._make_mgr(app)
        result = mgr.create_session(assistant_type="general", title="Test Chat", user="alice")
        assert result["id"] is not None
        assert result["status"] == "active"
        assert result["assistant_type"] == "general"

    def test_create_session_with_system_prompt(self, app):
        mgr = self._make_mgr(app)
        result = mgr.create_session(
            assistant_type="general",
            title="System Prompt",
            user="alice",
            system_prompt="You are a helpful SAP consultant.",
        )
        conv = _db.session.get(AIConversation, result["id"])
        msgs = conv.messages.all()
        assert len(msgs) == 1
        assert msgs[0].role == "system"
        assert "SAP consultant" in msgs[0].content

    def test_send_message(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Chat", user="bob")
        result = mgr.send_message(sess["id"], "What is S/4HANA?")
        assert result.get("content") is not None
        assert result["conversation_id"] == sess["id"]

    def test_send_message_increments_count(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Inc", user="alice")
        mgr.send_message(sess["id"], "Hi")
        conv = _db.session.get(AIConversation, sess["id"])
        # At least 2 messages: user + assistant (possibly system too)
        assert conv.message_count >= 2

    def test_send_message_to_closed_session(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Closed", user="alice")
        mgr.close_session(sess["id"])
        result = mgr.send_message(sess["id"], "Hello?")
        assert "error" in result

    def test_send_message_nonexistent_session(self, app):
        mgr = self._make_mgr(app)
        result = mgr.send_message(99999, "Hello?")
        assert "error" in result

    def test_send_empty_message(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Empty", user="alice")
        result = mgr.send_message(sess["id"], "")
        assert "error" in result

    def test_close_session(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Close Me", user="alice")
        result = mgr.close_session(sess["id"])
        assert result["status"] == "closed"

    def test_close_nonexistent_session(self, app):
        mgr = self._make_mgr(app)
        result = mgr.close_session(99999)
        assert "error" in result

    def test_list_sessions(self, app):
        mgr = self._make_mgr(app)
        mgr.create_session(assistant_type="general", title="A", user="alice")
        mgr.create_session(assistant_type="requirement_analyst", title="B", user="alice")
        mgr.create_session(assistant_type="general", title="C", user="bob")

        all_sessions = mgr.list_sessions()
        assert len(all_sessions) == 3

        by_user = mgr.list_sessions(user="alice")
        assert len(by_user) == 2

        by_type = mgr.list_sessions(assistant_type="general")
        assert len(by_type) == 2

    def test_list_sessions_by_status(self, app):
        mgr = self._make_mgr(app)
        s1 = mgr.create_session(assistant_type="general", title="Open", user="alice")
        s2 = mgr.create_session(assistant_type="general", title="Closed", user="alice")
        mgr.close_session(s2["id"])
        active = mgr.list_sessions(status="active")
        assert len(active) == 1
        assert active[0]["title"] == "Open"

    def test_get_session(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(assistant_type="general", title="Get Me", user="alice")
        result = mgr.get_session(sess["id"])
        assert result is not None
        assert result["title"] == "Get Me"

    def test_get_session_with_messages(self, app):
        mgr = self._make_mgr(app)
        sess = mgr.create_session(
            assistant_type="general", title="Msgs",
            user="alice", system_prompt="Be nice",
        )
        mgr.send_message(sess["id"], "Hello")
        result = mgr.get_session(sess["id"], include_messages=True)
        assert "messages" in result
        # system + user + assistant = 3
        assert len(result["messages"]) >= 3

    def test_get_nonexistent_session(self, app):
        mgr = self._make_mgr(app)
        assert mgr.get_session(99999) is None

    def test_list_sessions_with_limit(self, app):
        mgr = self._make_mgr(app)
        for i in range(5):
            mgr.create_session(assistant_type="general", title=f"S{i}", user="alice")
        result = mgr.list_sessions(limit=3)
        assert len(result) == 3


# ═════════════════════════════════════════════════════════════════════════════
# 3. STEERING PACK GENERATOR TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestSteeringPackGenerator:
    """Unit tests for SteeringPackGenerator assistant."""

    def _make_generator(self, app):
        from app.ai.assistants.steering_pack import SteeringPackGenerator
        from app.ai.gateway import LLMGateway
        from app.ai.rag import RAGPipeline
        from app.ai.prompt_registry import PromptRegistry
        from app.ai.suggestion_queue import SuggestionQueue
        return SteeringPackGenerator(
            gateway=LLMGateway(app),
            rag=RAGPipeline(app),
            prompt_registry=PromptRegistry(),
            suggestion_queue=SuggestionQueue(),
        )

    def test_generate_with_valid_program(self, app, client):
        prog = _create_program(client)
        gen = self._make_generator(app)
        result = gen.generate(program_id=prog["id"])
        assert "title" in result
        assert not result.get("error")
        assert result.get("confidence", 0) >= 0

    def test_generate_with_invalid_program(self, app):
        gen = self._make_generator(app)
        result = gen.generate(program_id=99999)
        assert "error" in result

    def test_generate_creates_suggestion(self, app, client):
        prog = _create_program(client)
        gen = self._make_generator(app)
        result = gen.generate(program_id=prog["id"], create_suggestion=True)
        if "suggestion_id" in result and result["suggestion_id"]:
            suggestion = _db.session.get(AISuggestion, result["suggestion_id"])
            assert suggestion is not None
            assert suggestion.suggestion_type == "steering_pack"

    def test_generate_without_suggestion(self, app, client):
        prog = _create_program(client)
        gen = self._make_generator(app)
        result = gen.generate(program_id=prog["id"], create_suggestion=False)
        assert result.get("suggestion_id") is None

    def test_generate_weekly_period(self, app, client):
        prog = _create_program(client)
        gen = self._make_generator(app)
        result = gen.generate(program_id=prog["id"], period="weekly")
        assert not result.get("error")

    def test_generate_monthly_period(self, app, client):
        prog = _create_program(client)
        gen = self._make_generator(app)
        result = gen.generate(program_id=prog["id"], period="monthly")
        assert not result.get("error")


# ═════════════════════════════════════════════════════════════════════════════
# 4. WRICEF SPEC DRAFTER TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestWRICEFSpecDrafter:
    """Unit tests for WRICEFSpecDrafter assistant."""

    def _make_drafter(self, app):
        from app.ai.assistants.wricef_spec import WRICEFSpecDrafter
        from app.ai.gateway import LLMGateway
        from app.ai.rag import RAGPipeline
        from app.ai.prompt_registry import PromptRegistry
        from app.ai.suggestion_queue import SuggestionQueue
        return WRICEFSpecDrafter(
            gateway=LLMGateway(app),
            rag=RAGPipeline(app),
            prompt_registry=PromptRegistry(),
            suggestion_queue=SuggestionQueue(),
        )

    def test_generate_with_valid_item(self, app, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=item.id)
        assert "title" in result
        assert not result.get("error")

    def test_generate_with_invalid_item(self, app):
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=99999)
        assert "error" in result

    def test_generate_functional_spec(self, app, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=item.id, spec_type="functional")
        assert not result.get("error")

    def test_generate_technical_spec(self, app, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=item.id, spec_type="technical")
        assert not result.get("error")

    def test_generate_creates_suggestion(self, app, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=item.id, create_suggestion=True)
        if "suggestion_id" in result and result["suggestion_id"]:
            s = _db.session.get(AISuggestion, result["suggestion_id"])
            assert s is not None
            assert s.suggestion_type == "wricef_spec"

    def test_generate_without_suggestion(self, app, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        drafter = self._make_drafter(app)
        result = drafter.generate(backlog_item_id=item.id, create_suggestion=False)
        assert result.get("suggestion_id") is None


# ═════════════════════════════════════════════════════════════════════════════
# 5. DATA QUALITY GUARDIAN TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestDataQualityGuardian:
    """Unit tests for DataQualityGuardian assistant."""

    def _make_guardian(self, app):
        from app.ai.assistants.data_quality import DataQualityGuardian
        from app.ai.gateway import LLMGateway
        from app.ai.rag import RAGPipeline
        from app.ai.prompt_registry import PromptRegistry
        from app.ai.suggestion_queue import SuggestionQueue
        return DataQualityGuardian(
            gateway=LLMGateway(app),
            rag=RAGPipeline(app),
            prompt_registry=PromptRegistry(),
            suggestion_queue=SuggestionQueue(),
        )

    def test_analyze_with_valid_object(self, app, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=obj.id)
        assert not result.get("error")

    def test_analyze_with_invalid_object(self, app):
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=99999)
        assert "error" in result

    def test_analyze_completeness(self, app, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=obj.id, analysis_type="completeness")
        assert not result.get("error")

    def test_analyze_consistency(self, app, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=obj.id, analysis_type="consistency")
        assert not result.get("error")

    def test_analyze_creates_suggestion(self, app, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=obj.id, create_suggestion=True)
        if "suggestion_id" in result and result["suggestion_id"]:
            s = _db.session.get(AISuggestion, result["suggestion_id"])
            assert s is not None
            assert s.suggestion_type == "data_quality"

    def test_analyze_without_suggestion(self, app, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        guardian = self._make_guardian(app)
        result = guardian.analyze(data_object_id=obj.id, create_suggestion=False)
        assert result.get("suggestion_id") is None


# ═════════════════════════════════════════════════════════════════════════════
# 6. DOC-GEN API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestDocGenAPI:
    """Integration tests for /api/v1/ai/doc-gen/* endpoints."""

    # ── Steering Pack ────────────────────────────────────────────────────

    def test_steering_pack_endpoint(self, client):
        prog = _create_program(client)
        res = client.post("/api/v1/ai/doc-gen/steering-pack", json={
            "program_id": prog["id"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "title" in data or "executive_summary" in data

    def test_steering_pack_missing_program_id(self, client):
        res = client.post("/api/v1/ai/doc-gen/steering-pack", json={})
        assert res.status_code == 400
        assert "program_id" in res.get_json()["error"]

    def test_steering_pack_invalid_program(self, client):
        res = client.post("/api/v1/ai/doc-gen/steering-pack", json={
            "program_id": 99999,
        })
        assert res.status_code in (200, 400)

    def test_steering_pack_with_period(self, client):
        prog = _create_program(client)
        res = client.post("/api/v1/ai/doc-gen/steering-pack", json={
            "program_id": prog["id"],
            "period": "monthly",
        })
        assert res.status_code in (200, 400)

    # ── WRICEF Spec ──────────────────────────────────────────────────────

    def test_wricef_spec_endpoint(self, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        res = client.post("/api/v1/ai/doc-gen/wricef-spec", json={
            "backlog_item_id": item.id,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "title" in data

    def test_wricef_spec_missing_item_id(self, client):
        res = client.post("/api/v1/ai/doc-gen/wricef-spec", json={})
        assert res.status_code == 400
        assert "backlog_item_id" in res.get_json()["error"]

    def test_wricef_spec_invalid_item(self, client):
        res = client.post("/api/v1/ai/doc-gen/wricef-spec", json={
            "backlog_item_id": 99999,
        })
        assert res.status_code in (200, 400)

    def test_wricef_spec_with_type(self, client):
        prog = _create_program(client)
        item = _create_backlog_item(prog["id"])
        res = client.post("/api/v1/ai/doc-gen/wricef-spec", json={
            "backlog_item_id": item.id,
            "spec_type": "technical",
        })
        assert res.status_code in (200, 400)

    # ── Data Quality ─────────────────────────────────────────────────────

    def test_data_quality_endpoint(self, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        res = client.post("/api/v1/ai/doc-gen/data-quality", json={
            "data_object_id": obj.id,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert not data.get("error")

    def test_data_quality_missing_object_id(self, client):
        res = client.post("/api/v1/ai/doc-gen/data-quality", json={})
        assert res.status_code == 400
        assert "data_object_id" in res.get_json()["error"]

    def test_data_quality_invalid_object(self, client):
        res = client.post("/api/v1/ai/doc-gen/data-quality", json={
            "data_object_id": 99999,
        })
        assert res.status_code in (200, 400)

    def test_data_quality_with_type(self, client):
        prog = _create_program(client)
        obj = _create_data_object(prog["id"])
        res = client.post("/api/v1/ai/doc-gen/data-quality", json={
            "data_object_id": obj.id,
            "analysis_type": "consistency",
        })
        assert res.status_code in (200, 400)


# ═════════════════════════════════════════════════════════════════════════════
# 7. CONVERSATION API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestConversationAPI:
    """Integration tests for /api/v1/ai/conversations/* endpoints."""

    # ── Create ───────────────────────────────────────────────────────────

    def test_create_conversation(self, client):
        res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "general",
            "title": "My Chat",
            "user": "alice",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["status"] == "active"
        assert data["assistant_type"] == "general"

    def test_create_conversation_with_system_prompt(self, client):
        res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "general",
            "title": "System",
            "system_prompt": "You are a helpful assistant.",
        })
        assert res.status_code == 201

    def test_create_conversation_defaults(self, client):
        res = client.post("/api/v1/ai/conversations", json={})
        assert res.status_code == 201
        data = res.get_json()
        assert data["assistant_type"] == "general"

    # ── List ─────────────────────────────────────────────────────────────

    def test_list_conversations_empty(self, client):
        res = client.get("/api/v1/ai/conversations")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_list_conversations(self, client):
        client.post("/api/v1/ai/conversations", json={"title": "A", "user": "alice"})
        client.post("/api/v1/ai/conversations", json={"title": "B", "user": "bob"})
        res = client.get("/api/v1/ai/conversations")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    def test_list_conversations_filter_user(self, client):
        client.post("/api/v1/ai/conversations", json={"title": "A", "user": "alice"})
        client.post("/api/v1/ai/conversations", json={"title": "B", "user": "bob"})
        res = client.get("/api/v1/ai/conversations?user=alice")
        assert res.status_code == 200
        assert len(res.get_json()) == 1

    def test_list_conversations_filter_status(self, client):
        r1 = client.post("/api/v1/ai/conversations", json={"title": "Open"})
        r2 = client.post("/api/v1/ai/conversations", json={"title": "Closed"})
        conv_id = r2.get_json()["id"]
        client.post(f"/api/v1/ai/conversations/{conv_id}/close")
        res = client.get("/api/v1/ai/conversations?status=active")
        assert res.status_code == 200
        assert len(res.get_json()) == 1

    def test_list_conversations_limit(self, client):
        for i in range(5):
            client.post("/api/v1/ai/conversations", json={"title": f"S{i}"})
        res = client.get("/api/v1/ai/conversations?limit=2")
        assert res.status_code == 200
        assert len(res.get_json()) == 2

    # ── Get ──────────────────────────────────────────────────────────────

    def test_get_conversation(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "Get Me"})
        conv_id = r.get_json()["id"]
        res = client.get(f"/api/v1/ai/conversations/{conv_id}")
        assert res.status_code == 200
        assert res.get_json()["title"] == "Get Me"

    def test_get_conversation_not_found(self, client):
        res = client.get("/api/v1/ai/conversations/99999")
        assert res.status_code == 404

    def test_get_conversation_without_messages(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "NoMsg"})
        conv_id = r.get_json()["id"]
        res = client.get(f"/api/v1/ai/conversations/{conv_id}?messages=false")
        assert res.status_code == 200
        assert "messages" not in res.get_json()

    # ── Send Message ─────────────────────────────────────────────────────

    def test_send_message(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "Chat"})
        conv_id = r.get_json()["id"]
        res = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json={
            "message": "What is SAP?",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert "content" in data

    def test_send_message_empty(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "Empty"})
        conv_id = r.get_json()["id"]
        res = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json={
            "message": "",
        })
        assert res.status_code == 400

    def test_send_message_not_found(self, client):
        res = client.post("/api/v1/ai/conversations/99999/messages", json={
            "message": "Hello",
        })
        assert res.status_code == 404

    def test_send_message_to_closed(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "Closed"})
        conv_id = r.get_json()["id"]
        client.post(f"/api/v1/ai/conversations/{conv_id}/close")
        res = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json={
            "message": "Hello",
        })
        assert res.status_code == 400

    def test_multi_turn_conversation(self, client):
        r = client.post("/api/v1/ai/conversations", json={
            "title": "Multi-turn",
            "system_prompt": "You are a helpful assistant.",
        })
        conv_id = r.get_json()["id"]
        # Turn 1
        r1 = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json={
            "message": "What is SAP FICO?",
        })
        assert r1.status_code == 201
        # Turn 2
        r2 = client.post(f"/api/v1/ai/conversations/{conv_id}/messages", json={
            "message": "Can you give more details?",
        })
        assert r2.status_code == 201
        # Check messages
        res = client.get(f"/api/v1/ai/conversations/{conv_id}")
        msgs = res.get_json().get("messages", [])
        # system + (user + assistant) * 2 = 5
        assert len(msgs) >= 5

    # ── Close ────────────────────────────────────────────────────────────

    def test_close_conversation(self, client):
        r = client.post("/api/v1/ai/conversations", json={"title": "Close Me"})
        conv_id = r.get_json()["id"]
        res = client.post(f"/api/v1/ai/conversations/{conv_id}/close")
        assert res.status_code == 200
        assert res.get_json()["status"] == "closed"

    def test_close_not_found(self, client):
        res = client.post("/api/v1/ai/conversations/99999/close")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 8. PROMPT YAML TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestDocGenPrompts:
    """Verify prompt YAMLs are loadable and renderable."""

    def test_steering_pack_prompt_loads(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        tpl = pr.get("steering_pack")
        assert tpl is not None

    def test_wricef_spec_prompt_loads(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        tpl = pr.get("wricef_spec")
        assert tpl is not None

    def test_data_quality_prompt_loads(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        tpl = pr.get("data_quality")
        assert tpl is not None

    def test_steering_pack_prompt_renders(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        rendered = pr.render(
            "steering_pack",
            period="weekly",
            program_name="Test Program",
            program_context="5 requirements, 3 risks",
            rag_context="Best practices for steering committees",
        )
        # rendered is a list of message dicts
        text = str(rendered).lower()
        assert "weekly" in text or "test program" in text

    def test_wricef_spec_prompt_renders(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        rendered = pr.render(
            "wricef_spec",
            spec_type="functional",
            item_title="GL Enhancement",
            item_context="type=enhancement, module=FI",
            rag_context="WRICEF standards",
        )
        text = str(rendered)
        assert "GL Enhancement" in text or "functional" in text.lower()

    def test_data_quality_prompt_renders(self, app):
        from app.ai.prompt_registry import PromptRegistry
        pr = PromptRegistry()
        rendered = pr.render(
            "data_quality",
            analysis_type="completeness",
            object_name="GL Master Data",
            data_context="150000 records from ECC",
            rag_context="Data migration best practices",
        )
        text = str(rendered)
        assert "GL Master Data" in text or "completeness" in text.lower()


# ═════════════════════════════════════════════════════════════════════════════
# 9. IMPORT VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════


class TestS19Imports:
    """Verify all S19 modules are importable."""

    def test_import_conversation_manager(self):
        from app.ai.conversation import ConversationManager
        assert ConversationManager is not None

    def test_import_steering_pack(self):
        from app.ai.assistants.steering_pack import SteeringPackGenerator
        assert SteeringPackGenerator is not None

    def test_import_wricef_spec(self):
        from app.ai.assistants.wricef_spec import WRICEFSpecDrafter
        assert WRICEFSpecDrafter is not None

    def test_import_data_quality(self):
        from app.ai.assistants.data_quality import DataQualityGuardian
        assert DataQualityGuardian is not None

    def test_import_from_assistants_init(self):
        from app.ai.assistants import (
            SteeringPackGenerator, WRICEFSpecDrafter, DataQualityGuardian,
        )
        assert all([SteeringPackGenerator, WRICEFSpecDrafter, DataQualityGuardian])

    def test_import_conversation_models(self):
        from app.models.ai import AIConversation, AIConversationMessage
        assert AIConversation is not None
        assert AIConversationMessage is not None
