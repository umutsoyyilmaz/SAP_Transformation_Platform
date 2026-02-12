"""
Sprint WR-2 — Audit + Traceability Tests (~20 tests)

Covers:
  - AuditLog model basics (write_audit, to_dict, diff property)
  - Audit API (list, filter, single, 404)
  - Audit integration (requirement transition, OI transition, workshop)
  - AI execution log bridge
  - Traceability service (trace_explore_requirement, batch, depth)
  - Traceability API endpoint
"""

import json

import pytest

from app.models import db
from app.models.audit import AuditLog, write_audit
from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    ExploreWorkshop,
    ProcessLevel,
    RequirementOpenItemLink,
    _uuid,
)
from app.models.backlog import BacklogItem, ConfigItem
from app.models.testing import TestCase, Defect
from app.models.program import Program


# ── Helpers ──────────────────────────────────────────────────────────────────

_seq = iter(range(1, 9999))


def _make_program():
    p = Program(name="WR2-Test", methodology="agile")
    db.session.add(p)
    db.session.flush()
    return p


def _make_requirement(pid, **kw):
    n = next(_seq)
    req = ExploreRequirement(
        id=kw.get("id", _uuid()),
        project_id=pid,
        code=kw.get("code", f"REQ-{n:03d}"),
        title=kw.get("title", f"Test Req {n}"),
        created_by_id="user-1",
        status=kw.get("status", "draft"),
    )
    db.session.add(req)
    db.session.flush()
    return req


def _make_open_item(pid, **kw):
    n = next(_seq)
    oi = ExploreOpenItem(
        id=kw.get("id", _uuid()),
        project_id=pid,
        code=kw.get("code", f"OI-{n:03d}"),
        title=kw.get("title", f"Test OI {n}"),
        created_by_id="user-1",
        status=kw.get("status", "open"),
    )
    db.session.add(oi)
    db.session.flush()
    return oi


def _make_workshop(pid, **kw):
    n = next(_seq)
    ws = ExploreWorkshop(
        id=kw.get("id", _uuid()),
        project_id=pid,
        code=kw.get("code", f"WS-{n:03d}"),
        name=kw.get("name", f"Test WS {n}"),
        process_area=kw.get("process_area", "FI"),
        status=kw.get("status", "in_progress"),
        session_number=kw.get("session_number", 1),
        total_sessions=kw.get("total_sessions", 1),
    )
    db.session.add(ws)
    db.session.flush()
    return ws


# ═══════════════════════════════════════════════════════════════════════════════
# A — AuditLog Model
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditLogModel:
    """AuditLog creation, serialisation, diff property."""

    def test_write_audit_creates_row(self):
        p = _make_program()
        log = write_audit(
            entity_type="requirement",
            entity_id="abc-123",
            action="requirement.approve",
            actor="user-1",
            program_id=p.id,
            diff={"status": {"old": "draft", "new": "approved"}},
        )
        assert log.id is not None
        assert log.entity_type == "requirement"
        assert log.action == "requirement.approve"
        assert AuditLog.query.count() == 1

    def test_to_dict_fields(self):
        write_audit(
            entity_type="open_item",
            entity_id="oi-1",
            action="open_item.close",
            actor="user-2",
            diff={"status": {"old": "open", "new": "closed"}},
        )
        log = AuditLog.query.first()
        d = log.to_dict()
        assert d["entity_type"] == "open_item"
        assert d["actor"] == "user-2"
        assert "timestamp" in d
        assert d["diff"]["status"]["old"] == "open"

    def test_diff_property_handles_bad_json(self):
        log = AuditLog(
            entity_type="x", entity_id="1", action="test",
            diff_json="NOT-JSON",
        )
        assert log.diff == {}

    def test_diff_property_handles_none(self):
        log = AuditLog(
            entity_type="x", entity_id="1", action="test",
            diff_json=None,
        )
        assert log.diff == {}

    def test_repr(self):
        log = AuditLog(
            entity_type="requirement", entity_id="r1",
            action="requirement.approve",
        )
        assert "requirement.approve" in repr(log)


# ═══════════════════════════════════════════════════════════════════════════════
# B — Audit API
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditAPI:
    """Audit list/filter/single endpoints."""

    def _seed(self, pid):
        for i in range(5):
            write_audit(
                entity_type="requirement" if i < 3 else "open_item",
                entity_id=f"e-{i}",
                action=f"requirement.approve" if i < 3 else "open_item.close",
                actor="user-1" if i % 2 == 0 else "user-2",
                program_id=pid,
            )
        db.session.commit()

    def test_list_returns_all(self, client):
        p = _make_program()
        self._seed(p.id)
        res = client.get("/api/v1/audit")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 5
        assert len(data["audit_logs"]) == 5

    def test_filter_by_entity_type(self, client):
        p = _make_program()
        self._seed(p.id)
        res = client.get("/api/v1/audit?entity_type=open_item")
        data = res.get_json()
        assert data["total"] == 2

    def test_filter_by_action_prefix(self, client):
        p = _make_program()
        self._seed(p.id)
        res = client.get("/api/v1/audit?action=requirement")
        data = res.get_json()
        assert data["total"] == 3

    def test_filter_by_actor(self, client):
        p = _make_program()
        self._seed(p.id)
        res = client.get("/api/v1/audit?actor=user-2")
        data = res.get_json()
        assert data["total"] == 2

    def test_pagination(self, client):
        p = _make_program()
        self._seed(p.id)
        res = client.get("/api/v1/audit?page=1&per_page=2")
        data = res.get_json()
        assert len(data["audit_logs"]) == 2
        assert data["pages"] == 3

    def test_single_entry(self, client):
        p = _make_program()
        log = write_audit(
            entity_type="workshop", entity_id="ws-1",
            action="workshop.complete", actor="user-1", program_id=p.id,
        )
        db.session.commit()
        res = client.get(f"/api/v1/audit/{log.id}")
        assert res.status_code == 200
        assert res.get_json()["action"] == "workshop.complete"

    def test_single_404(self, client):
        res = client.get("/api/v1/audit/99999")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# C — Audit Integration (lifecycle hooks)
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuditIntegration:
    """Requirement / OI transitions write audit rows."""

    def test_requirement_transition_creates_audit(self):
        from app.services.requirement_lifecycle import transition_requirement

        p = _make_program()
        req = _make_requirement(p.id, status="draft")
        db.session.commit()

        transition_requirement(
            requirement_id=req.id,
            action="submit_for_review",
            user_id="user-1",
            project_id=p.id,
            skip_permission=True,
        )
        db.session.commit()

        logs = AuditLog.query.filter_by(entity_type="requirement").all()
        assert len(logs) == 1
        assert logs[0].action == "requirement.submit_for_review"
        assert logs[0].diff["status"]["old"] == "draft"
        assert logs[0].diff["status"]["new"] == "under_review"

    def test_oi_transition_creates_audit(self):
        from app.services.open_item_lifecycle import transition_open_item

        p = _make_program()
        oi = _make_open_item(p.id, status="open")
        db.session.commit()

        transition_open_item(
            open_item_id=oi.id,
            action="start_progress",
            user_id="user-2",
            project_id=p.id,
            skip_permission=True,
        )
        db.session.commit()

        logs = AuditLog.query.filter_by(entity_type="open_item").all()
        assert len(logs) == 1
        assert logs[0].action == "open_item.start_progress"
        assert logs[0].actor == "user-2"

    def test_workshop_complete_creates_audit(self, client):
        p = _make_program()
        ws = _make_workshop(p.id, status="in_progress")
        db.session.commit()

        res = client.post(
            f"/api/v1/explore/workshops/{ws.id}/complete",
            json={"completed_by": "user-3", "force": True},
        )
        assert res.status_code == 200

        logs = AuditLog.query.filter_by(entity_type="workshop", action="workshop.complete").all()
        assert len(logs) == 1
        assert logs[0].actor == "user-3"


# ═══════════════════════════════════════════════════════════════════════════════
# D — AI Execution Log Bridge
# ═══════════════════════════════════════════════════════════════════════════════


class TestAIExecutionLog:
    """AI gateway _log_audit bridges to general audit_logs."""

    def test_ai_log_audit_writes_general_audit(self):
        from app.ai.gateway import LLMGateway

        p = _make_program()
        LLMGateway._log_audit(
            action="llm_call",
            provider="openai",
            model="gpt-4",
            user="ai-user",
            program_id=p.id,
            prompt_hash="abc123",
            prompt_summary="Test prompt",
            tokens_used=500,
            cost_usd=0.015,
            latency_ms=1200,
            response_summary="Test response",
            success=True,
        )
        db.session.commit()

        logs = AuditLog.query.filter_by(entity_type="ai_call").all()
        assert len(logs) == 1
        d = logs[0].diff
        assert d["prompt_name"] == "llm_call"
        assert d["tokens_used"] == 500
        assert d["model"] == "gpt-4"
        assert logs[0].action == "ai.llm_call"


# ═══════════════════════════════════════════════════════════════════════════════
# E — Traceability Service
# ═══════════════════════════════════════════════════════════════════════════════


class TestTraceabilityService:
    """trace_explore_requirement FK chain traversal."""

    def test_requirement_only(self):
        from app.services.traceability import trace_explore_requirement

        p = _make_program()
        req = _make_requirement(p.id)
        db.session.commit()

        graph = trace_explore_requirement(req.id)
        assert graph["requirement"]["id"] == req.id
        assert graph["chain_depth"] == 1
        assert graph["coverage"]["backlog"] == 0

    def test_with_backlog(self):
        from app.services.traceability import trace_explore_requirement

        p = _make_program()
        req = _make_requirement(p.id)
        bi = BacklogItem(
            program_id=p.id, title="BI-1", status="new",
            explore_requirement_id=req.id,
        )
        db.session.add(bi)
        db.session.commit()

        graph = trace_explore_requirement(req.id)
        assert graph["coverage"]["backlog"] == 1
        assert graph["chain_depth"] == 2
        assert len(graph["backlog_items"]) == 1

    def test_full_chain_depth_4(self):
        from app.services.traceability import trace_explore_requirement

        p = _make_program()
        req = _make_requirement(p.id)
        bi = BacklogItem(
            program_id=p.id, title="BI-2", status="new",
            explore_requirement_id=req.id,
        )
        db.session.add(bi)
        db.session.flush()

        tc = TestCase(
            program_id=p.id, title="TC-1", status="not_run",
            backlog_item_id=bi.id,
        )
        db.session.add(tc)
        db.session.flush()

        defect = Defect(
            program_id=p.id, title="DEF-1", status="open",
            test_case_id=tc.id,
        )
        db.session.add(defect)
        db.session.commit()

        graph = trace_explore_requirement(req.id)
        assert graph["chain_depth"] == 4
        assert graph["coverage"]["test"] == 1
        assert graph["coverage"]["defect"] == 1

    def test_open_items_in_trace(self):
        from app.services.traceability import trace_explore_requirement

        p = _make_program()
        req = _make_requirement(p.id)
        oi = _make_open_item(p.id)
        link = RequirementOpenItemLink(
            id=_uuid(),
            requirement_id=req.id,
            open_item_id=oi.id,
        )
        db.session.add(link)
        db.session.commit()

        graph = trace_explore_requirement(req.id)
        assert graph["coverage"]["open_item"] == 1
        assert len(graph["open_items"]) == 1

    def test_not_found_raises(self):
        from app.services.traceability import trace_explore_requirement

        with pytest.raises(ValueError, match="not found"):
            trace_explore_requirement("nonexistent")

    def test_batch(self):
        from app.services.traceability import trace_explore_batch

        p = _make_program()
        r1 = _make_requirement(p.id)
        r2 = _make_requirement(p.id)
        db.session.commit()

        results = trace_explore_batch([r1.id, r2.id, "bad-id"])
        assert len(results) == 3
        assert results[0]["requirement"]["id"] == r1.id
        assert results[2]["error"] == "not_found"


# ═══════════════════════════════════════════════════════════════════════════════
# F — Traceability API
# ═══════════════════════════════════════════════════════════════════════════════


class TestTraceabilityAPI:
    """GET /api/v1/trace/requirement/<id>."""

    def test_trace_endpoint(self, client):
        p = _make_program()
        req = _make_requirement(p.id)
        db.session.commit()

        res = client.get(f"/api/v1/trace/requirement/{req.id}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["requirement"]["id"] == req.id
        assert "coverage" in data

    def test_trace_endpoint_404(self, client):
        res = client.get("/api/v1/trace/requirement/nonexistent")
        assert res.status_code == 404
