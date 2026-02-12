"""
SAP Transformation Management Platform
Data Quality Guardian — Sprint 19 (AI Phase 4).

Analyzes data objects/loads and provides quality recommendations:
    - Data completeness analysis
    - Quality rule suggestions
    - Cleansing action recommendations
    - Migration readiness assessment
"""

import json
import logging

from app.models import db

logger = logging.getLogger(__name__)


class DataQualityGuardian:
    """AI-powered data quality analysis and cleansing advisor."""

    def __init__(self, gateway=None, rag=None, prompt_registry=None, suggestion_queue=None):
        self.gateway = gateway
        self.rag = rag
        self.prompt_registry = prompt_registry
        self.suggestion_queue = suggestion_queue

    def analyze(
        self,
        data_object_id: int,
        *,
        analysis_type: str = "completeness",
        create_suggestion: bool = True,
    ) -> dict:
        """
        Analyze a data object for quality issues.

        Args:
            data_object_id: DataObject ID to analyze
            analysis_type: "completeness" | "consistency" | "migration_readiness"
            create_suggestion: Whether to push to suggestion queue

        Returns:
            dict with quality_score, issues, recommendations, cleansing_actions, etc.
        """
        result = {
            "data_object_id": data_object_id,
            "analysis_type": analysis_type,
            "quality_score": 0.0,
            "completeness_pct": 0.0,
            "issues": [],
            "recommendations": [],
            "cleansing_actions": [],
            "migration_readiness": "",
            "confidence": 0.0,
            "suggestion_id": None,
            "error": None,
        }

        from app.models.data_factory import DataObject
        obj = db.session.get(DataObject, data_object_id)
        if not obj:
            result["error"] = "Data object not found"
            return result

        # Build context
        context = self._build_data_context(obj)

        # RAG context
        rag_context = ""
        if self.rag:
            try:
                hits = self.rag.search(
                    query=f"data quality rules for {obj.name} {getattr(obj, 'object_type', '')}",
                    program_id=getattr(obj, "program_id", None),
                    top_k=5,
                )
                if hits:
                    rag_context = json.dumps(hits[:5], indent=2)
            except Exception as exc:
                logger.warning("RAG search failed: %s", exc)

        # Build prompt
        if not self.prompt_registry:
            result["error"] = "Prompt registry not available"
            return result

        try:
            messages = self.prompt_registry.render(
                "data_quality",
                object_name=obj.name,
                data_context=context,
                analysis_type=analysis_type,
                rag_context=rag_context or "No additional context",
            )
        except KeyError:
            messages = self._fallback_prompt(obj, context, analysis_type)

        if not self.gateway:
            result["error"] = "LLM Gateway not available"
            return result

        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="data_quality",
                program_id=getattr(obj, "program_id", None),
            )
            parsed = self._parse_response(llm_response.get("content", ""))
            result.update({
                "quality_score": parsed.get("quality_score", 0.0),
                "completeness_pct": parsed.get("completeness_pct", 0.0),
                "issues": parsed.get("issues", []),
                "recommendations": parsed.get("recommendations", []),
                "cleansing_actions": parsed.get("cleansing_actions", []),
                "migration_readiness": parsed.get("migration_readiness", ""),
                "confidence": parsed.get("confidence", 0.0),
            })
        except Exception as exc:
            logger.error("DataQualityGuardian LLM call failed: %s", exc)
            result["error"] = f"AI analysis failed: {str(exc)}"
            return result

        # Suggestion queue
        program_id = getattr(obj, "program_id", None)
        if create_suggestion and self.suggestion_queue and program_id:
            try:
                suggestion = self.suggestion_queue.create(
                    suggestion_type="data_quality",
                    entity_type="data_object",
                    entity_id=data_object_id,
                    program_id=program_id,
                    title=f"Data Quality: {obj.name}",
                    description=f"Score: {result['quality_score']}, {len(result['issues'])} issues found",
                    suggestion_data=result,
                    confidence=result.get("confidence", 0.0),
                    model_used=self.gateway.DEFAULT_CHAT_MODEL if self.gateway else "",
                    prompt_version="v1",
                    reasoning="AI-generated data quality analysis",
                )
                result["suggestion_id"] = suggestion.id
            except Exception as exc:
                logger.warning("Failed to create suggestion: %s", exc)

        return result

    @staticmethod
    def _build_data_context(obj) -> str:
        """Build text summary of data object for prompt."""
        parts = [
            f"Object: {obj.name}",
            f"Type: {getattr(obj, 'object_type', 'N/A')}",
            f"Status: {getattr(obj, 'status', 'N/A')}",
            f"Source System: {getattr(obj, 'source_system', 'N/A')}",
            f"Target System: {getattr(obj, 'target_system', 'N/A')}",
        ]
        if getattr(obj, "description", None):
            parts.append(f"Description: {obj.description[:500]}")
        if getattr(obj, "record_count", None):
            parts.append(f"Records: {obj.record_count}")
        return "\n".join(parts)

    @staticmethod
    def _fallback_prompt(obj, context: str, analysis_type: str):
        return [
            {"role": "system", "content": (
                "You are an SAP data quality specialist. Analyze the data object and provide "
                "quality assessment in JSON format with keys: quality_score (0-100), "
                "completeness_pct (0-100), issues (list of strings), recommendations (list), "
                "cleansing_actions (list), migration_readiness (string), confidence (0-1)."
            )},
            {"role": "user", "content": (
                f"Perform a {analysis_type} analysis on this data object:\n{context}"
            )},
        ]

    @staticmethod
    def _parse_response(content: str) -> dict:
        """Parse JSON response from LLM."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
        return {"quality_score": 50, "confidence": 0.5, "issues": [content]}
