"""
SAP Transformation Management Platform
Meeting Minutes Assistant — Sprint 15 (AI Phase 3).

Two capabilities:
    1. generate_minutes — Raw meeting text → structured minutes with decisions, action items
    2. extract_actions  — Raw text → action items list with assignees and due dates

Pipeline:
    1. Accept raw meeting text (transcript, notes, etc.)
    2. RAG search for related project context
    3. Build prompt from YAML template (meeting_minutes.yaml)
    4. Call LLM → structured JSON response
    5. Push result to SuggestionQueue (human-in-the-loop)
"""

import json
import logging
import re

from app.models import db
from app.models.program import Program

logger = logging.getLogger(__name__)


class MeetingMinutesAssistant:
    """AI-powered meeting minutes generator and action item extractor."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    # ── Full Minutes Generation ───────────────────────────────────────────

    def generate_minutes(
        self,
        raw_text: str,
        program_id: int | None = None,
        *,
        meeting_type: str = "general",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Generate structured meeting minutes from raw text.

        Args:
            raw_text: Raw transcript, notes, or freeform text
            program_id: Optional program ID for project context
            meeting_type: "general" | "steering_committee" | "workshop" | "technical" | "status_update"
            create_suggestion: Whether to push to suggestion queue

        Returns:
            dict with keys: title, date, attendees, agenda, summary, decisions,
                  action_items, risks_raised, next_steps, confidence,
                  suggestion_id, error
        """
        result = {
            "title": "",
            "date": None,
            "attendees": [],
            "agenda": [],
            "summary": "",
            "decisions": [],
            "action_items": [],
            "risks_raised": [],
            "next_steps": [],
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        if not raw_text or not raw_text.strip():
            result["error"] = "raw_text is required"
            return result

        # Build project context from RAG if program_id given
        project_context = ""
        if program_id:
            program = db.session.get(Program, program_id)
            if program:
                project_context = f"Project: {program.name}\nStatus: {program.status or 'N/A'}\n"

            if self.rag:
                try:
                    hits = self.rag.search(
                        query=raw_text[:500],
                        program_id=program_id,
                        top_k=3,
                    )
                    if hits:
                        project_context += f"\nRelated context:\n{json.dumps(hits[:3], indent=2)}"
                except Exception as exc:
                    logger.warning("RAG search failed: %s", exc)

        # Build prompt
        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            messages = self.prompt_registry.render(
                "meeting_minutes",
                raw_text=raw_text,
                meeting_type=meeting_type,
                project_context=project_context or "No project context available",
            )
        except KeyError:
            messages = self._fallback_minutes_prompt(raw_text, meeting_type, project_context)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="meeting_minutes",
                program_id=program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "title": parsed.get("title", ""),
                "date": parsed.get("date"),
                "attendees": parsed.get("attendees", []),
                "agenda": parsed.get("agenda", []),
                "summary": parsed.get("summary", ""),
                "decisions": parsed.get("decisions", []),
                "action_items": parsed.get("action_items", []),
                "risks_raised": parsed.get("risks_raised", []),
                "next_steps": parsed.get("next_steps", []),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("MeetingMinutesAssistant LLM call failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        # Push to suggestion queue
        if create_suggestion and self.suggestion_queue and program_id:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="meeting_minutes",
                    entity_type="program",
                    entity_id=program_id,
                    program_id=program_id,
                    title=f"Meeting: {result.get('title', 'Untitled')}",
                    description=result.get("summary", "")[:200],
                    suggestion_data={
                        "title": result["title"],
                        "date": result["date"],
                        "attendees": result["attendees"],
                        "agenda": result["agenda"],
                        "summary": result["summary"],
                        "decisions": result["decisions"],
                        "action_items": result["action_items"],
                        "risks_raised": result["risks_raised"],
                        "next_steps": result["next_steps"],
                    },
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-generated meeting minutes",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    # ── Action Items Extraction ───────────────────────────────────────────

    def extract_actions(
        self,
        raw_text: str,
        program_id: int | None = None,
        *,
        create_suggestion: bool = True,
    ) -> dict:
        """
        Extract action items from raw meeting text.

        Returns:
            dict with keys: action_items (list of dicts), total_count,
                  confidence, suggestion_id, error
        """
        result = {
            "action_items": [],
            "total_count": 0,
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        if not raw_text or not raw_text.strip():
            result["error"] = "raw_text is required"
            return result

        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            messages = self.prompt_registry.render(
                "meeting_actions",
                raw_text=raw_text,
            )
        except KeyError:
            messages = self._fallback_actions_prompt(raw_text)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="meeting_actions",
                program_id=program_id,
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            items = parsed.get("action_items", [])
            result.update({
                "action_items": items,
                "total_count": len(items),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("MeetingMinutesAssistant extract_actions failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        if create_suggestion and self.suggestion_queue and program_id:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="meeting_minutes",
                    entity_type="program",
                    entity_id=program_id,
                    program_id=program_id,
                    title=f"Action items ({result['total_count']} extracted)",
                    description="; ".join(
                        a.get("action", "") for a in result["action_items"][:3]
                    ),
                    suggestion_data={"action_items": result["action_items"]},
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-extracted action items from meeting text",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    # ── Fallback prompts ──────────────────────────────────────────────────

    def _fallback_minutes_prompt(self, raw_text, meeting_type, project_context):
        system = (
            "You are an expert SAP project meeting minutes generator. "
            "Convert raw meeting text into structured, professional meeting minutes.\n\n"
            "Return valid JSON with these keys:\n"
            "{\n"
            '  "title": "Meeting title",\n'
            '  "date": "YYYY-MM-DD or null",\n'
            '  "attendees": [{"name": str, "role": str}],\n'
            '  "agenda": ["item1", "item2"],\n'
            '  "summary": "Executive summary paragraph",\n'
            '  "decisions": [{"decision": str, "rationale": str, "owner": str}],\n'
            '  "action_items": [{"action": str, "assignee": str, "due_date": str, "priority": "high"|"medium"|"low"}],\n'
            '  "risks_raised": [{"risk": str, "severity": "high"|"medium"|"low", "mitigation": str}],\n'
            '  "next_steps": ["step1", "step2"],\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )
        user = (
            f"Meeting type: {meeting_type}\n"
            f"Project context: {project_context or 'N/A'}\n\n"
            f"Raw meeting text:\n{raw_text}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _fallback_actions_prompt(self, raw_text):
        system = (
            "You are an expert at extracting action items from meeting text. "
            "Identify every action, task, or commitment mentioned.\n\n"
            "Return valid JSON:\n"
            "{\n"
            '  "action_items": [\n'
            '    {"action": str, "assignee": str|null, "due_date": str|null, '
            '"priority": "high"|"medium"|"low", "category": str}\n'
            "  ],\n"
            '  "confidence": 0.0-1.0\n'
            "}"
        )
        user = f"Extract all action items from this meeting text:\n\n{raw_text}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── Response parser ───────────────────────────────────────────────────

    @staticmethod
    def _parse_response(content: str) -> dict:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    return {}
        return {}
