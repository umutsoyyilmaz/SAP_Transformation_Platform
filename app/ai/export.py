"""
SAP Transformation Management Platform
AI Document Export Service — Sprint 21.

Exports AI-generated content to Markdown and JSON formats.
Combines templates with AI output for download-ready documents.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Supported document types
EXPORTABLE_TYPES = {
    "steering_pack",
    "wricef_spec",
    "meeting_minutes",
    "data_migration_strategy",
    "integration_dependency_map",
    "risk_assessment",
    "change_impact",
    "test_cases",
    "reconciliation_checklist",
}


class AIDocExporter:
    """Exports AI-generated content to downloadable formats."""

    def export_markdown(self, doc_type: str, content: dict, title: str = "") -> str:
        """
        Convert an AI output dict into styled Markdown.

        Args:
            doc_type: One of EXPORTABLE_TYPES.
            content: The AI-generated content dict.
            title: Optional document title override.

        Returns:
            Markdown string.
        """
        if doc_type not in EXPORTABLE_TYPES:
            return f"# Unsupported document type: {doc_type}\n"

        renderer = getattr(self, f"_render_{doc_type}", None)
        if renderer:
            return renderer(content, title)
        return self._render_generic(content, title or doc_type)

    def export_json(self, doc_type: str, content: dict, title: str = "") -> str:
        """Export as formatted JSON string."""
        export = {
            "document_type": doc_type,
            "title": title or doc_type.replace("_", " ").title(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "content": content,
        }
        return json.dumps(export, indent=2, default=str)

    def list_exportable_types(self) -> list[dict]:
        """List all supported export types with descriptions."""
        descriptions = {
            "steering_pack": "Executive steering committee briefing pack",
            "wricef_spec": "WRICEF functional specification document",
            "meeting_minutes": "Meeting minutes with action items",
            "data_migration_strategy": "Data migration strategy and wave plan",
            "integration_dependency_map": "Integration dependency analysis",
            "risk_assessment": "Project risk assessment report",
            "change_impact": "Change impact analysis document",
            "test_cases": "Generated test case specifications",
            "reconciliation_checklist": "Data reconciliation checklist",
        }
        return [
            {"type": t, "description": descriptions.get(t, t.replace("_", " ").title())}
            for t in sorted(EXPORTABLE_TYPES)
        ]

    # ── Renderers ─────────────────────────────────────────────────────────

    def _render_steering_pack(self, content: dict, title: str) -> str:
        md = f"# {title or content.get('title', 'Steering Committee Pack')}\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        md += "---\n\n"

        md += "## Executive Summary\n\n"
        md += content.get("executive_summary", "N/A") + "\n\n"

        if content.get("workstream_status"):
            md += "## Workstream Status\n\n"
            md += "| Workstream | Status | Progress | Highlights |\n"
            md += "|-----------|--------|----------|------------|\n"
            for ws in content["workstream_status"]:
                md += f"| {ws.get('name', '')} | {ws.get('status', '')} | "
                md += f"{ws.get('progress_pct', '')}% | {ws.get('highlights', '')} |\n"
            md += "\n"

        if content.get("risk_escalations"):
            md += "## Risk Escalations\n\n"
            for r in content["risk_escalations"]:
                md += f"- **{r.get('risk', '')}** ({r.get('severity', '')}): "
                md += f"{r.get('mitigation', '')}\n"
            md += "\n"

        if content.get("decisions_needed"):
            md += "## Decisions Needed\n\n"
            for d in content["decisions_needed"]:
                md += f"- **{d.get('decision', '')}**: {d.get('recommendation', '')}\n"
            md += "\n"

        return md

    def _render_wricef_spec(self, content: dict, title: str) -> str:
        md = f"# {title or content.get('title', 'WRICEF Specification')}\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        md += "---\n\n"

        md += "## Overview\n\n" + content.get("overview", "N/A") + "\n\n"

        if content.get("functional_requirements"):
            md += "## Functional Requirements\n\n"
            for fr in content["functional_requirements"]:
                md += f"### {fr.get('id', 'FR')}: {fr.get('description', '')}\n"
                md += f"- **Priority:** {fr.get('priority', 'N/A')}\n"
                md += f"- **Acceptance Criteria:** {fr.get('acceptance_criteria', 'N/A')}\n\n"

        md += "## Technical Details\n\n" + content.get("technical_details", "N/A") + "\n\n"
        md += "## Test Approach\n\n" + content.get("test_approach", "N/A") + "\n"
        return md

    def _render_data_migration_strategy(self, content: dict, title: str) -> str:
        md = f"# {title or 'Data Migration Strategy'}\n\n"
        md += f"**Scope:** {content.get('scope', 'full')}\n"
        md += f"**Est. Duration:** {content.get('estimated_duration_hours', 'TBD')} hours\n\n"
        md += "---\n\n"

        md += "## Strategy\n\n" + content.get("strategy", "N/A") + "\n\n"

        if content.get("wave_sequence"):
            md += "## Wave Sequence\n\n"
            for i, w in enumerate(content["wave_sequence"], 1):
                md += f"{i}. {w if isinstance(w, str) else json.dumps(w)}\n"
            md += "\n"

        if content.get("risk_areas"):
            md += "## Risk Areas\n\n"
            for r in content["risk_areas"]:
                md += f"- {r if isinstance(r, str) else json.dumps(r)}\n"
            md += "\n"

        return md

    def _render_generic(self, content: dict, title: str) -> str:
        md = f"# {title.replace('_', ' ').title()}\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        md += "---\n\n"

        for key, value in content.items():
            if key in ("confidence", "suggestion_id", "error", "program_id"):
                continue
            heading = key.replace("_", " ").title()
            if isinstance(value, list):
                md += f"## {heading}\n\n"
                for item in value:
                    md += f"- {json.dumps(item) if isinstance(item, dict) else item}\n"
                md += "\n"
            elif isinstance(value, dict):
                md += f"## {heading}\n\n"
                md += f"```json\n{json.dumps(value, indent=2)}\n```\n\n"
            else:
                md += f"## {heading}\n\n{value}\n\n"

        return md
