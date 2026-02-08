"""
SAP Transformation Management Platform
Defect Triage Assistant — Sprint 8 (Tasks 8.8 + 8.9).

Defect triage pipeline:
    1. Load defect details
    2. Search for similar/duplicate defects via RAG embeddings (Task 8.9)
    3. Build prompt from YAML template (defect_triage.yaml)
    4. Call LLM → severity, module, duplicate detection, root cause hint
    5. Push result to Suggestion Queue (human-in-the-loop)

Architecture ref:  §10.6.3 — Defect Triage Assistant
"""

import json
import logging
import re
from typing import Any

from app.models import db
from app.models.testing import Defect

logger = logging.getLogger(__name__)


# ── Duplicate Detection Thresholds ────────────────────────────────────────────

DUPLICATE_THRESHOLD = 0.88  # cosine similarity above this → probable duplicate
SIMILAR_THRESHOLD = 0.70    # above this → related/similar defect


class DefectTriage:
    """
    AI-powered defect triage assistant.

    Uses RAG embedding similarity for duplicate detection, then
    calls LLM with SAP testing context for severity + routing.
    """

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    # ── Main Triage Flow ──────────────────────────────────────────────────

    def triage(self, defect_id: int, *, create_suggestion: bool = True) -> dict:
        """
        Triage a defect: severity classification, module routing, duplicate detection.

        Args:
            defect_id: ID of the Defect to triage.
            create_suggestion: If True, push result to Suggestion Queue.

        Returns:
            dict with: severity, module, confidence, reasoning, similar_defects,
                       is_duplicate, duplicate_of, suggested_assignee,
                       root_cause_hint, suggestion_id, error
        """
        result = {
            "defect_id": defect_id,
            "severity": None,
            "module": None,
            "confidence": 0.0,
            "reasoning": "",
            "similar_defects": [],
            "is_duplicate": False,
            "duplicate_of": None,
            "suggested_assignee": "",
            "root_cause_hint": "",
            "sap_note": "",
            "suggestion_id": None,
            "error": None,
        }

        # 1. Load defect
        defect = db.session.get(Defect, defect_id)
        if not defect:
            result["error"] = f"Defect {defect_id} not found"
            return result

        # 2. Duplicate detection via RAG embeddings (Task 8.9)
        similar, probable_duplicate = self._find_duplicates(defect)
        result["similar_defects"] = similar
        if probable_duplicate:
            result["is_duplicate"] = True
            result["duplicate_of"] = probable_duplicate

        # 3. Build existing defects context for LLM
        existing_context = self._build_existing_defects_context(defect)

        # 4. Build prompt
        messages = self._build_prompt(defect, existing_context)

        # 5. Call LLM
        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="defect_triage",
                program_id=defect.program_id,
            )
            parsed = self._parse_response(llm_response["content"])
            result.update({
                "severity": parsed.get("severity", defect.severity),
                "module": parsed.get("module", defect.module),
                "confidence": parsed.get("confidence", 0.0),
                "reasoning": parsed.get("reasoning", ""),
                "suggested_assignee": parsed.get("suggested_assignee", ""),
                "root_cause_hint": parsed.get("root_cause_hint", ""),
                "sap_note": parsed.get("sap_note", ""),
            })
            # Merge LLM duplicate info with embedding-based detection
            if parsed.get("is_duplicate") and not result["is_duplicate"]:
                result["is_duplicate"] = True
                result["duplicate_of"] = parsed.get("duplicate_of")
            if parsed.get("similar_defects"):
                # Merge LLM suggestions with RAG results
                llm_similar = parsed["similar_defects"]
                existing_ids = {s.get("entity_id") for s in similar}
                for sid in llm_similar:
                    if sid not in existing_ids:
                        result["similar_defects"].append({
                            "entity_id": sid,
                            "score": 0.0,
                            "source": "llm",
                        })

        except Exception as e:
            logger.error("DefectTriage LLM call failed: %s", e)
            result["error"] = f"AI triage failed: {str(e)}"
            return result

        # 6. Create suggestion (human-in-the-loop)
        if create_suggestion:
            try:
                from app.ai.suggestion_queue import SuggestionQueue
                changes = {}
                if result["severity"] and result["severity"] != defect.severity:
                    changes["severity"] = result["severity"]
                if result["module"] and result["module"] != defect.module:
                    changes["module"] = result["module"]

                suggestion = SuggestionQueue.create(
                    suggestion_type="defect_triage",
                    entity_type="defect",
                    entity_id=defect_id,
                    program_id=defect.program_id,
                    title=f"Triage '{defect.title}' → {result['severity']}",
                    description=result["reasoning"],
                    suggestion_data={
                        "severity": result["severity"],
                        "module": result["module"],
                        "is_duplicate": result["is_duplicate"],
                        "duplicate_of": result["duplicate_of"],
                        "suggested_assignee": result["suggested_assignee"],
                        "root_cause_hint": result["root_cause_hint"],
                        "sap_note": result["sap_note"],
                    },
                    current_data={
                        "severity": defect.severity or "",
                        "module": defect.module or "",
                        "assigned_to": defect.assigned_to or "",
                    },
                    confidence=result["confidence"],
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v2",
                    reasoning=result["reasoning"],
                )
                result["suggestion_id"] = suggestion.id
            except Exception as e:
                logger.error("Failed to create triage suggestion: %s", e)

        return result

    # ── Batch Triage ──────────────────────────────────────────────────────

    def triage_batch(self, defect_ids: list[int], **kwargs) -> list[dict]:
        """Triage multiple defects sequentially."""
        return [self.triage(did, **kwargs) for did in defect_ids]

    # ── Duplicate Detection (Task 8.9) ────────────────────────────────────

    def _find_duplicates(self, defect: Defect, top_k: int = 10) -> tuple[list[dict], int | None]:
        """
        Find similar/duplicate defects using RAG embedding similarity.

        Returns:
            (similar_list, probable_duplicate_id or None)
        """
        if not self.rag:
            return [], None

        try:
            search_text = f"{defect.title} {defect.description or ''} {defect.steps_to_reproduce or ''}"
            results = self.rag.search(
                query=search_text,
                program_id=defect.program_id,
                entity_type="defect",
                top_k=top_k,
            )

            # Filter out self
            similar = [
                r for r in results
                if not (r.get("entity_type") == "defect" and r.get("entity_id") == defect.id)
            ]

            # Check for probable duplicate (highest similarity above threshold)
            probable_duplicate = None
            for s in similar:
                if s.get("score", 0) >= DUPLICATE_THRESHOLD:
                    probable_duplicate = s.get("entity_id")
                    break

            # Filter to only meaningful similarity
            similar = [s for s in similar if s.get("score", 0) >= SIMILAR_THRESHOLD]

            return similar, probable_duplicate

        except Exception as e:
            logger.warning("Duplicate detection failed: %s", e)
            return [], None

    # ── Existing Defects Context ──────────────────────────────────────────

    @staticmethod
    def _build_existing_defects_context(defect: Defect, limit: int = 10) -> str:
        """Build context string of existing defects for LLM."""
        existing = Defect.query.filter(
            Defect.program_id == defect.program_id,
            Defect.id != defect.id,
        ).order_by(Defect.created_at.desc()).limit(limit).all()

        if not existing:
            return "No existing defects in this program."

        parts = []
        for d in existing:
            parts.append(
                f"- [{d.code}] {d.title} | Severity: {d.severity} | "
                f"Module: {d.module} | Status: {d.status}"
            )
        return "\n".join(parts)

    # ── Prompt Building ───────────────────────────────────────────────────

    def _build_prompt(self, defect: Defect, existing_context: str) -> list[dict]:
        """Build chat messages for defect triage."""
        # Try YAML template
        if self.prompt_registry:
            try:
                return self.prompt_registry.render(
                    "defect_triage",
                    defect_title=defect.title,
                    description=defect.description or "No description",
                    steps=defect.steps_to_reproduce or "Not provided",
                    environment=defect.environment or "Not specified",
                    current_severity=defect.severity or "Not set",
                    module=defect.module or "Not specified",
                    existing_defects=existing_context,
                )
            except KeyError:
                pass

        # Fallback inline prompt
        system = (
            "You are an SAP test defect triage specialist for S/4HANA.\n\n"
            "Severity: P1=Critical, P2=High, P3=Medium, P4=Low.\n"
            "Determine severity, module, and check for duplicates.\n\n"
            "Return valid JSON: {\"severity\": \"P1|P2|P3|P4\", "
            "\"module\": \"...\", \"confidence\": 0-1, \"reasoning\": \"...\", "
            "\"similar_defects\": [], \"is_duplicate\": false, \"duplicate_of\": null, "
            "\"suggested_assignee\": \"...\", \"root_cause_hint\": \"...\", \"sap_note\": \"\"}"
        )

        user = (
            f"Triage this defect:\n\n"
            f"**Title:** {defect.title}\n"
            f"**Description:** {defect.description or 'N/A'}\n"
            f"**Steps to Reproduce:** {defect.steps_to_reproduce or 'N/A'}\n"
            f"**Environment:** {defect.environment or 'N/A'}\n"
            f"**Current Severity:** {defect.severity or 'Not set'}\n"
            f"**Module:** {defect.module or 'N/A'}\n\n"
            f"**Existing defects:**\n{existing_context}"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── Response Parsing ──────────────────────────────────────────────────

    @staticmethod
    def _parse_response(content: str) -> dict:
        """Parse LLM JSON response."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{[^{}]*"severity"\s*:', cleaned, re.DOTALL)
            if match:
                start = match.start()
                brace_count = 0
                for i, ch in enumerate(cleaned[start:], start):
                    if ch == '{':
                        brace_count += 1
                    elif ch == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                return json.loads(cleaned[start:i + 1])
                            except json.JSONDecodeError:
                                break
            return {
                "severity": None,
                "module": None,
                "confidence": 0.0,
                "reasoning": content[:500],
            }
