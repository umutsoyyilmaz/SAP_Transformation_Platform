"""Bölüm 3 — workshop_docs + minutes_generator tenant isolation tests.

Tests the P0 security gap in WorkshopDocumentService (workshop_docs.py)
and MinutesGeneratorService (minutes_generator.py): both services accept
arbitrary workshop_id values without verifying the caller owns the project.

A caller who knows a workshop UUID from another project can:
  1. READ that workshop's meeting minutes, summary, or traceability data.
  2. WRITE a new ExploreWorkshopDocument associated with that workshop.

Tests marked @pytest.mark.xfail document DESIRED post-fix behavior:
  - RED today (no project_id enforcement → assertion fails)
  - Turn GREEN once project_id parameter + ownership check is added.

Happy-path, error-handling, and denormalization-correctness tests are
standard asserts (no xfail) — they must pass both before and after the fix.
"""

from datetime import date, time

import pytest

from app.models import db
from app.models.explore import ExploreWorkshop, ExploreWorkshopDocument
from app.models.program import Program
from app.services.minutes_generator import MinutesGeneratorService
from app.services.workshop_docs import WorkshopDocumentService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_program(name: str) -> Program:
    """Create and flush a minimal Program (the top-level project entity)."""
    prog = Program(name=name, status="active", methodology="agile")
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_workshop(project_id: int, code: str, **kw) -> ExploreWorkshop:
    """Create and flush an ExploreWorkshop with all NOT NULL fields populated.

    Matches the canonical factory pattern from tests/test_explore.py#_make_workshop.
    """
    defaults = dict(
        project_id=project_id,
        code=code,
        name=f"Workshop {code}",
        type="fit_to_standard",
        status="draft",
        date=date(2026, 3, 1),
        start_time=time(9, 0),
        end_time=time(12, 0),
        process_area="FI",
        wave=1,
        session_number=1,
        total_sessions=1,
    )
    defaults.update(kw)
    ws = ExploreWorkshop(**defaults)
    db.session.add(ws)
    db.session.flush()
    return ws


def _make_document(
    workshop: ExploreWorkshop,
    doc_type: str = "meeting_minutes",
    title: str | None = None,
) -> ExploreWorkshopDocument:
    """Insert an ExploreWorkshopDocument directly (bypassing the service).

    Used to set up preconditions for read/update/delete isolation tests.
    project_id is copied from the parent workshop — this is the correct
    denormalization pattern that all service methods must also follow.
    """
    doc = ExploreWorkshopDocument(
        workshop_id=workshop.id,
        project_id=str(workshop.project_id),
        type=doc_type,
        format="markdown",
        title=title or f"Test {doc_type.replace('_', ' ').title()}",
        content="# Test content",
        generated_by="manual",
    )
    db.session.add(doc)
    db.session.flush()
    return doc


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def two_projects():
    """Two isolated projects each with their own workshop and pre-created document.

    Returns dict:
        prog_a_id, prog_b_id  — Program (project) integer PKs
        ws_a_id,   ws_b_id    — ExploreWorkshop string UUIDs
        doc_a_id,  doc_b_id   — ExploreWorkshopDocument string UUIDs
    """
    prog_a = _make_program("Alpha Corp SAP Project")
    prog_b = _make_program("Beta Corp SAP Project")

    ws_a = _make_workshop(prog_a.id, code="WS-DOC-A01", process_area="FI")
    ws_b = _make_workshop(prog_b.id, code="WS-DOC-B01", process_area="MM")

    doc_a = _make_document(ws_a, title="Alpha Meeting Minutes")
    doc_b = _make_document(ws_b, title="Beta Meeting Minutes")

    return {
        "prog_a_id": prog_a.id,
        "prog_b_id": prog_b.id,
        "ws_a_id": ws_a.id,
        "ws_b_id": ws_b.id,
        "doc_a_id": doc_a.id,
        "doc_b_id": doc_b.id,
    }


# ── TestWorkshopDocumentServiceGenerate ──────────────────────────────────────


class TestWorkshopDocumentServiceGenerate:
    """WorkshopDocumentService.generate() isolation and correctness tests."""

    # ── Happy path ───────────────────────────────────────────────────────

    def test_generate_meeting_minutes_returns_document_dict(self, two_projects):
        """Generating meeting_minutes for own workshop succeeds."""
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "meeting_minutes"
        )

        assert result["type"] == "meeting_minutes"
        assert result["format"] == "markdown"
        assert result["workshop_id"] == two_projects["ws_a_id"]

    def test_generate_workshop_summary_returns_document_dict(self, two_projects):
        """Generating workshop_summary for own workshop succeeds."""
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "workshop_summary"
        )

        assert result["type"] == "workshop_summary"
        assert result["workshop_id"] == two_projects["ws_a_id"]

    def test_generate_traceability_report_returns_document_dict(self, two_projects):
        """Generating traceability_report for own workshop succeeds."""
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "traceability_report"
        )

        assert result["type"] == "traceability_report"
        assert result["workshop_id"] == two_projects["ws_a_id"]

    # ── Denormalization correctness ───────────────────────────────────────

    def test_generated_document_project_id_matches_parent_workshop(self, two_projects):
        """The document's project_id MUST be inherited from its workshop.

        This verifies the denormalization is correct: doc.project_id must equal
        the owning workshop's project_id, not be hardcoded or left NULL.
        """
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "meeting_minutes"
        )

        assert result["project_id"] == str(two_projects["prog_a_id"])

    def test_generated_document_is_persisted_to_db(self, two_projects):
        """Document persisted by generate() must be retrievable from DB."""
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "meeting_minutes"
        )
        doc_id = result["id"]

        doc = db.session.get(ExploreWorkshopDocument, doc_id)
        assert doc is not None
        assert doc.workshop_id == two_projects["ws_a_id"]

    def test_generated_document_has_non_empty_content(self, two_projects):
        """Generated documents must have actual content (not empty strings)."""
        result = WorkshopDocumentService.generate(
            two_projects["ws_a_id"], "meeting_minutes"
        )
        assert result["content"] is not None
        assert len(result["content"]) > 0

    # ── Error handling ────────────────────────────────────────────────────

    def test_generate_invalid_doc_type_raises_value_error(self, two_projects):
        """Unknown doc_type must raise ValueError with helpful message."""
        with pytest.raises(ValueError, match="Unknown document type"):
            WorkshopDocumentService.generate(two_projects["ws_a_id"], "unknown_type")

    def test_generate_nonexistent_workshop_raises_value_error(self):
        """Non-existent workshop_id must raise ValueError, never return None."""
        with pytest.raises(ValueError, match="Workshop not found"):
            WorkshopDocumentService.generate(
                "00000000-0000-0000-0000-000000000000", "meeting_minutes"
            )

    # ── Isolation (xfail — documents desired post-fix behavior) ───────────

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: WorkshopDocumentService.generate has no project_id "
            "parameter. A caller that knows ws_b_id can generate and persist a "
            "document tagged to project_b without any authorization check. "
            "Fix: add project_id param + reject when ws.project_id != project_id."
        ),
    )
    def test_cross_project_generate_is_blocked(self, two_projects):
        """Project A MUST NOT generate documents for project B's workshop.

        VULNERABILITY TODAY: generate(ws_b_id) succeeds, writes a document
        with project_id=prog_b_id — a cross-tenant write with no auth check.
        EXPECTED AFTER FIX: raise ValueError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            WorkshopDocumentService.generate(
                two_projects["ws_b_id"], "meeting_minutes"
            )

    @pytest.mark.xfail(
        strict=False,
        reason="P0 isolation gap: see test_cross_project_generate_is_blocked.",
    )
    def test_cross_project_traceability_report_is_blocked(self, two_projects):
        """Traceability report for project_b's workshop must be rejected by project_a caller."""
        with pytest.raises((ValueError, PermissionError)):
            WorkshopDocumentService.generate(
                two_projects["ws_b_id"], "traceability_report"
            )


# ── TestMinutesGeneratorServiceGenerate ──────────────────────────────────────


class TestMinutesGeneratorServiceGenerate:
    """MinutesGeneratorService.generate() isolation and correctness tests."""

    # ── Happy path ───────────────────────────────────────────────────────

    def test_generate_returns_document_dict(self, two_projects):
        """Generating minutes for own workshop returns a document dict."""
        result = MinutesGeneratorService.generate(two_projects["ws_a_id"])

        assert isinstance(result, dict)
        assert result["type"] == "meeting_minutes"
        assert result["format"] == "markdown"
        assert result["workshop_id"] == two_projects["ws_a_id"]

    def test_generate_content_is_non_empty_markdown(self, two_projects):
        """Generated content must be a non-empty string."""
        result = MinutesGeneratorService.generate(two_projects["ws_a_id"])

        assert result["content"] is not None
        assert len(result["content"]) > 0

    def test_generate_title_includes_workshop_code(self, two_projects):
        """Document title must reference the workshop code for traceability."""
        result = MinutesGeneratorService.generate(two_projects["ws_a_id"])

        assert "WS-DOC-A01" in result["title"]

    def test_generate_with_session_number_adds_session_to_title(self, two_projects):
        """session_number=1 causes 'Session 1' to appear in the title."""
        result = MinutesGeneratorService.generate(
            two_projects["ws_a_id"], session_number=1
        )

        assert "Session 1" in result["title"]

    # ── Denormalization correctness ───────────────────────────────────────

    def test_generated_document_project_id_matches_workshop(self, two_projects):
        """Document project_id must be inherited from parent workshop, not caller."""
        result = MinutesGeneratorService.generate(two_projects["ws_a_id"])

        assert result["project_id"] == str(two_projects["prog_a_id"])

    def test_generated_document_persisted_with_correct_workshop_id(self, two_projects):
        """Document in DB must reference the correct workshop."""
        result = MinutesGeneratorService.generate(two_projects["ws_a_id"])

        doc = db.session.get(ExploreWorkshopDocument, result["id"])
        assert doc is not None
        assert doc.workshop_id == two_projects["ws_a_id"]
        assert doc.project_id == str(two_projects["prog_a_id"])

    # ── Error handling ────────────────────────────────────────────────────

    def test_nonexistent_workshop_raises_value_error(self):
        """Non-existent workshop UUID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            MinutesGeneratorService.generate(
                "deadbeef-dead-beef-dead-beefdeadbeef"
            )

    # ── Isolation (xfail) ────────────────────────────────────────────────

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: MinutesGeneratorService.generate has no project_id "
            "parameter. Any caller that knows ws_b_id can trigger minutes "
            "generation for project_b's workshop and read the output. "
            "Fix: add project_id parameter + ownership verification."
        ),
    )
    def test_cross_project_minutes_generation_is_blocked(self, two_projects):
        """Project A caller MUST NOT generate minutes for project B's workshop.

        VULNERABILITY TODAY: call succeeds, returns project_b data.
        EXPECTED AFTER FIX: raise ValueError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            MinutesGeneratorService.generate(two_projects["ws_b_id"])


# ── TestMinutesGeneratorServiceGenerateAiSummary ─────────────────────────────


class TestMinutesGeneratorServiceGenerateAiSummary:
    """MinutesGeneratorService.generate_ai_summary() isolation tests.

    Note: generate_ai_summary currently does NOT call an external AI provider —
    it produces a structured JSON summary from local DB data. Safe to run in tests.
    """

    def test_generate_ai_summary_own_workshop_returns_dict(self, two_projects):
        """AI summary for own workshop returns a document dict."""
        result = MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"])

        assert isinstance(result, dict)
        assert result["type"] == "ai_summary"
        assert result["workshop_id"] == two_projects["ws_a_id"]

    def test_ai_summary_project_id_matches_workshop(self, two_projects):
        """project_id on AI summary document must match workshop's project."""
        result = MinutesGeneratorService.generate_ai_summary(two_projects["ws_a_id"])

        assert result["project_id"] == str(two_projects["prog_a_id"])

    def test_ai_summary_nonexistent_workshop_raises_value_error(self):
        """Non-existent workshop_id raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            MinutesGeneratorService.generate_ai_summary(
                "00000000-0000-0000-0000-000000000000"
            )

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: generate_ai_summary has no project_id parameter. "
            "Any caller can retrieve AI-aggregated data for another project's workshop."
        ),
    )
    def test_cross_project_ai_summary_is_blocked(self, two_projects):
        """Project A must not receive AI summary data for project B's workshop."""
        with pytest.raises((ValueError, PermissionError)):
            MinutesGeneratorService.generate_ai_summary(two_projects["ws_b_id"])


# ── TestDocumentProjectIsolationAtModel ──────────────────────────────────────


class TestDocumentProjectIsolationAtModel:
    """Low-level model + query isolation correctness tests.

    These tests verify that the data model enforces correct project_id
    denormalization and that scoped queries cannot cross project boundaries.
    These MUST pass regardless of service-layer isolation status.
    """

    def test_document_project_id_matches_parent_workshop_project_id(self, two_projects):
        """Data invariant: doc.project_id == str(doc.workshop.project_id)."""
        doc_a = db.session.get(ExploreWorkshopDocument, two_projects["doc_a_id"])
        ws_a = db.session.get(ExploreWorkshop, two_projects["ws_a_id"])

        assert doc_a is not None
        assert doc_a.project_id == str(ws_a.project_id)

    def test_documents_from_different_projects_have_distinct_project_ids(self, two_projects):
        """Isolation invariant: project_ids must differ across tenants."""
        doc_a = db.session.get(ExploreWorkshopDocument, two_projects["doc_a_id"])
        doc_b = db.session.get(ExploreWorkshopDocument, two_projects["doc_b_id"])

        assert doc_a.project_id != doc_b.project_id

    def test_scoped_query_for_project_a_does_not_return_project_b_docs(self, two_projects):
        """Correctly-scoped query for project_a must never return project_b documents.

        This tests the query pattern that all service CRUD functions must use:
        filter by BOTH workshop_id AND project_id.
        """
        from sqlalchemy import select

        # Attempt to find project_b's document using project_a's project_id scope
        stmt = select(ExploreWorkshopDocument).where(
            ExploreWorkshopDocument.workshop_id == two_projects["ws_b_id"],
            ExploreWorkshopDocument.project_id == str(two_projects["prog_a_id"]),
        )
        results = db.session.execute(stmt).scalars().all()

        assert results == [], (
            "Cross-project document must not be visible through project_a's scope. "
            "If this fails, a document has been incorrectly tagged with a "
            "mismatched project_id."
        )

    def test_scoped_query_returns_only_own_project_documents(self, two_projects):
        """Scoped query for project_a returns project_a docs only, not project_b's."""
        from sqlalchemy import select

        stmt = select(ExploreWorkshopDocument).where(
            ExploreWorkshopDocument.project_id == str(two_projects["prog_a_id"])
        )
        docs = db.session.execute(stmt).scalars().all()

        doc_ids = {d.id for d in docs}
        assert two_projects["doc_a_id"] in doc_ids
        assert two_projects["doc_b_id"] not in doc_ids, (
            "project_b document must not appear in project_a's scoped query."
        )

    def test_workshop_document_workshop_id_references_correct_workshop(self, two_projects):
        """FK integrity: doc.workshop_id must point to the correct workshop row."""
        doc_a = db.session.get(ExploreWorkshopDocument, two_projects["doc_a_id"])

        assert doc_a.workshop_id == two_projects["ws_a_id"]
        assert doc_a.workshop_id != two_projects["ws_b_id"]
