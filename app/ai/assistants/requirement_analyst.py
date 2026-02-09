"""
SAP Transformation Management Platform
Requirement Analyst Assistant — Sprint 8 (Tasks 8.5 + 8.6).

Fit/Gap classification pipeline:
    1. Load requirement details
    2. Search similar requirements via RAG (embedding similarity)
    3. Build prompt from YAML template (requirement_analyst.yaml)
    4. Call LLM → get classification + confidence + reasoning
    5. Push result to Suggestion Queue (human-in-the-loop)

Architecture ref: §10.6.2 — Requirement Analyst Assistant
"""

import json
import logging
from typing import Any

from app.models import db
from app.models.requirement import Requirement

logger = logging.getLogger(__name__)


class RequirementAnalyst:
    """
    AI-powered requirement Fit/Gap analyst.

    Uses RAG similarity search to find comparable requirements, then
    calls LLM with SAP Best Practice context for classification.
    """

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    # ── Main Classification Flow ──────────────────────────────────────────

    def classify(self, requirement_id: int, *, create_suggestion: bool = True) -> dict:
        """
        Classify a requirement as Fit / Partial Fit / Gap.

        Args:
            requirement_id: ID of the Requirement to classify.
            create_suggestion: If True, push result to Suggestion Queue.

        Returns:
            dict: classification, confidence, reasoning, similar_requirements,
                  sap_solution, effort_estimate, suggestion_id, error
        """
        result = {
            "requirement_id": requirement_id,
            "classification": None,
            "confidence": 0.0,
            "reasoning": "",
            "sap_solution": "",
            "sap_transactions": [],
            "recommended_actions": [],
            "effort_estimate": "",
            "clean_core_compliant": None,
            "similar_requirements": [],
            "suggestion_id": None,
            "error": None,
        }

        # 1. Load requirement
        req = db.session.get(Requirement, requirement_id)
        if not req:
            result["error"] = f"Requirement {requirement_id} not found"
            return result

        # 2. Similarity search via RAG (Task 8.6)
        similar = self._find_similar(req)
        result["similar_requirements"] = similar

        # 3. Build prompt
        messages = self._build_prompt(req, similar)

        # 4. Call LLM
        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="requirement_analyst",
                program_id=req.program_id,
            )
            parsed = self._parse_response(llm_response["content"])
            result.update({
                "classification": parsed.get("classification"),
                "confidence": parsed.get("confidence", 0.0),
                "reasoning": parsed.get("reasoning", ""),
                "sap_solution": parsed.get("sap_solution", ""),
                "sap_transactions": parsed.get("sap_transactions", []),
                "recommended_actions": parsed.get("recommended_actions", []),
                "effort_estimate": parsed.get("effort_estimate", ""),
                "clean_core_compliant": parsed.get("clean_core_compliant"),
            })
        except Exception as e:
            logger.error("RequirementAnalyst LLM call failed: %s", e)
            result["error"] = f"AI analysis failed: {str(e)}"
            return result

        # 5. Create suggestion (human-in-the-loop)
        if create_suggestion and result["classification"]:
            try:
                from app.ai.suggestion_queue import SuggestionQueue
                suggestion = SuggestionQueue.create(
                    suggestion_type="fit_gap_classification",
                    entity_type="requirement",
                    entity_id=requirement_id,
                    program_id=req.program_id,
                    title=f"Classify '{req.title}' as {result['classification']}",
                    description=result["reasoning"],
                    suggestion_data={
                        "fit_gap": result["classification"],
                        "effort_estimate": result["effort_estimate"],
                        "sap_solution": result["sap_solution"],
                        "sap_transactions": result["sap_transactions"],
                        "recommended_actions": result["recommended_actions"],
                        "clean_core_compliant": result["clean_core_compliant"],
                    },
                    current_data={
                        "effort_estimate": req.effort_estimate or "",
                    },
                    confidence=result["confidence"],
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v2",
                    reasoning=result["reasoning"],
                )
                result["suggestion_id"] = suggestion.id
            except Exception as e:
                logger.error("Failed to create suggestion: %s", e)

        return result

    # ── Batch Classification ──────────────────────────────────────────────

    def classify_batch(self, requirement_ids: list[int], **kwargs) -> list[dict]:
        """Classify multiple requirements sequentially."""
        return [self.classify(rid, **kwargs) for rid in requirement_ids]

    # ── Similarity Search (Task 8.6) ──────────────────────────────────────

    def _find_similar(self, req: Requirement, top_k: int = 5) -> list[dict]:
        """Find similar requirements using RAG embedding similarity."""
        if not self.rag:
            return []

        try:
            search_text = f"{req.title} {req.description or ''} {req.module or ''}"
            results = self.rag.search(
                query=search_text,
                program_id=req.program_id,
                entity_type="requirement",
                top_k=top_k,
            )
            # Filter out selbst (the requirement being classified)
            return [
                r for r in results
                if not (r.get("entity_type") == "requirement" and r.get("entity_id") == req.id)
            ]
        except Exception as e:
            logger.warning("Similarity search failed: %s", e)
            return []

    # ── Prompt Building ───────────────────────────────────────────────────

    def _build_prompt(self, req: Requirement, similar: list[dict]) -> list[dict]:
        """Build chat messages for Fit/Gap classification."""
        # Context from similar requirements
        context_parts = []
        for i, s in enumerate(similar[:5], 1):
            context_parts.append(
                f"{i}. [{s.get('entity_id', '?')}] "
                f"(score: {s.get('score', 0):.2f}) "
                f"{s.get('content', '')[:200]}"
            )
        context = "\n".join(context_parts) if context_parts else "No similar requirements found."

        # Try YAML template
        if self.prompt_registry:
            try:
                return self.prompt_registry.render(
                    "requirement_analyst",
                    requirement_title=req.title,
                    module=req.module or "N/A",
                    requirement_type=req.req_type or "functional",
                    priority=req.priority or "medium",
                    description=req.description or "No description provided",
                    context=context,
                )
            except KeyError:
                pass

        # Fallback inline prompt
        system = (
            "You are an SAP Fit/Gap Analysis specialist for S/4HANA transformation.\n\n"
            "Classify the requirement as: fit, partial_fit, or gap.\n"
            "Consider SAP S/4HANA 2023 standard. Prefer clean core (BTP extensions).\n\n"
            "Return valid JSON: {\"classification\": \"fit|partial_fit|gap\", "
            "\"confidence\": 0-1, \"reasoning\": \"...\", \"sap_solution\": \"...\", "
            "\"sap_transactions\": [], \"recommended_actions\": [], "
            "\"effort_estimate\": \"low|medium|high\", \"clean_core_compliant\": true/false}"
        )

        user = (
            f"Analyze this requirement:\n\n"
            f"**Title:** {req.title}\n"
            f"**Module:** {req.module or 'N/A'}\n"
            f"**Type:** {req.req_type or 'functional'}\n"
            f"**Priority:** {req.priority or 'medium'}\n"
            f"**Description:** {req.description or 'N/A'}\n\n"
            f"**Similar requirements:**\n{context}"
        )

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── Response Parsing ──────────────────────────────────────────────────

    @staticmethod
    def _parse_response(content: str) -> dict:
        """Parse LLM JSON response."""
        import re
        cleaned = content.strip()
        # Strip markdown code fences
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object
            match = re.search(r'\{[^{}]*"classification"\s*:', cleaned, re.DOTALL)
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
                "classification": None,
                "confidence": 0.0,
                "reasoning": content[:500],
            }
