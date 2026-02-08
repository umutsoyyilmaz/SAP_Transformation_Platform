"""
SAP Transformation Management Platform
Prompt Registry — Sprint 7.

YAML-based prompt template management with:
    - Template loading from ai_knowledge/prompts/
    - Jinja2-style variable rendering
    - Version tracking
    - A/B test flag support

Usage:
    from app.ai.prompt_registry import PromptRegistry
    registry = PromptRegistry()
    prompt = registry.render("requirement_analyst", version="v1",
                             requirement_title="GL Account Posting",
                             module="FI")
"""

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Default prompts directory
_PROMPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ai_knowledge", "prompts",
)


class PromptTemplate:
    """A single prompt template with metadata."""

    def __init__(self, name: str, version: str, system: str, user: str,
                 description: str = "", ab_test: bool = False, metadata: dict | None = None):
        self.name = name
        self.version = version
        self.system = system
        self.user = user
        self.description = description
        self.ab_test = ab_test
        self.metadata = metadata or {}

    def render(self, **variables) -> list[dict]:
        """
        Render template with variables, returning chat messages.

        Variables are replaced using {{variable_name}} syntax.

        Returns:
            List of message dicts: [{"role": "system", "content": "..."}, ...]
        """
        system_rendered = self._substitute(self.system, variables)
        user_rendered = self._substitute(self.user, variables)

        messages = []
        if system_rendered.strip():
            messages.append({"role": "system", "content": system_rendered})
        if user_rendered.strip():
            messages.append({"role": "user", "content": user_rendered})
        return messages

    @staticmethod
    def _substitute(template: str, variables: dict) -> str:
        """Replace {{var}} placeholders with values."""
        def replacer(match):
            key = match.group(1).strip()
            return str(variables.get(key, f"{{{{{key}}}}}"))
        return re.sub(r'\{\{(\s*\w+\s*)\}\}', replacer, template)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "ab_test": self.ab_test,
            "system_preview": self.system[:200],
            "user_preview": self.user[:200],
        }


class PromptRegistry:
    """
    Registry for loading and managing prompt templates.

    Templates are loaded from YAML files in ai_knowledge/prompts/.
    Falls back to built-in default templates if YAML files are missing.
    """

    def __init__(self, prompts_dir: str | None = None):
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._templates: dict[str, dict[str, PromptTemplate]] = {}  # name → {version → template}
        self._load_defaults()
        self._load_from_dir()

    def _load_defaults(self):
        """Register built-in default prompt templates."""
        for tpl in _DEFAULT_TEMPLATES:
            self._register(tpl)

    def _load_from_dir(self):
        """Load prompt templates from YAML files."""
        prompts_path = Path(self._prompts_dir)
        if not prompts_path.exists():
            logger.info("Prompts directory not found: %s. Using defaults only.", self._prompts_dir)
            return

        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed. Using default prompts only.")
            return

        for yaml_file in prompts_path.glob("*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue

                tpl = PromptTemplate(
                    name=data.get("name", yaml_file.stem),
                    version=data.get("version", "v1"),
                    system=data.get("system", ""),
                    user=data.get("user", ""),
                    description=data.get("description", ""),
                    ab_test=data.get("ab_test", False),
                    metadata=data.get("metadata", {}),
                )
                self._register(tpl)
                logger.info("Loaded prompt template: %s (v%s) from %s",
                            tpl.name, tpl.version, yaml_file.name)
            except Exception as e:
                logger.error("Failed to load prompt %s: %s", yaml_file.name, e)

    def _register(self, template: PromptTemplate):
        """Add template to registry."""
        if template.name not in self._templates:
            self._templates[template.name] = {}
        self._templates[template.name][template.version] = template

    def get(self, name: str, version: str = "v1") -> PromptTemplate | None:
        """Get a prompt template by name and version."""
        versions = self._templates.get(name, {})
        return versions.get(version)

    def render(self, name: str, version: str = "v1", **variables) -> list[dict]:
        """
        Render a prompt template with variables.

        Args:
            name: Template name.
            version: Template version.
            **variables: Template variables.

        Returns:
            List of chat messages.

        Raises:
            KeyError: If template not found.
        """
        tpl = self.get(name, version)
        if not tpl:
            raise KeyError(f"Prompt template not found: {name} v{version}")
        return tpl.render(**variables)

    def list_templates(self) -> list[dict]:
        """List all registered templates."""
        result = []
        for name, versions in self._templates.items():
            for ver, tpl in versions.items():
                result.append(tpl.to_dict())
        return result

    def get_versions(self, name: str) -> list[str]:
        """Get available versions for a template."""
        return list(self._templates.get(name, {}).keys())


# ── Built-in Default Templates ────────────────────────────────────────────────

_DEFAULT_TEMPLATES = [
    PromptTemplate(
        name="system_base",
        version="v1",
        description="Base system prompt for all SAP Transformation AI assistants",
        system=(
            "You are an AI assistant specialized in SAP S/4HANA transformation projects. "
            "You have deep knowledge of SAP Activate methodology, SAP modules (FI, CO, MM, SD, PP, QM, PM, HCM, BTP), "
            "WRICEF object types (Workflows, Reports, Interfaces, Conversions, Enhancements, Forms), "
            "and enterprise project management best practices.\n\n"
            "Key principles:\n"
            "- Always reference SAP standard functionality before suggesting custom development\n"
            "- Consider SAP Best Practices and standard configurations\n"
            "- Be specific about SAP transactions, tables, and BAPIs when relevant\n"
            "- Provide confidence scores (0.0-1.0) for your recommendations\n"
            "- Return structured JSON when asked for classifications or assessments"
        ),
        user="{{user_message}}",
    ),
    PromptTemplate(
        name="requirement_analyst",
        version="v1",
        description="Classify requirements as Fit/Partial Fit/Gap and suggest SAP solutions",
        system=(
            "You are an SAP Fit/Gap Analysis specialist. Your task is to analyze business requirements "
            "and classify them against SAP S/4HANA standard capabilities.\n\n"
            "Classification rules:\n"
            "- **Fit**: Requirement fully met by SAP standard configuration (IMG/SPRO)\n"
            "- **Partial Fit**: Mostly met, but needs minor configuration changes, user exits, or BAdIs\n"
            "- **Gap**: Requires custom WRICEF development (ABAP report, interface, enhancement, etc.)\n\n"
            "For each classification, provide:\n"
            "1. classification: fit | partial_fit | gap\n"
            "2. confidence: 0.0 - 1.0\n"
            "3. reasoning: explanation of why this classification\n"
            "4. sap_solution: relevant SAP standard functionality\n"
            "5. recommended_actions: list of next steps\n"
            "6. relevant_transactions: SAP transaction codes if applicable\n"
            "7. effort_estimate: low/medium/high\n\n"
            "Return your response as valid JSON."
        ),
        user=(
            "Analyze and classify this SAP requirement:\n\n"
            "**Title:** {{requirement_title}}\n"
            "**Module:** {{module}}\n"
            "**Type:** {{requirement_type}}\n"
            "**Description:** {{description}}\n"
            "**Priority:** {{priority}}\n\n"
            "{{context}}"
        ),
    ),
    PromptTemplate(
        name="defect_triage",
        version="v1",
        description="Triage defects: severity assessment, module routing, duplicate detection",
        system=(
            "You are an SAP test defect triage specialist. Your task is to assess defect reports "
            "and recommend severity, routing, and potential duplicates.\n\n"
            "Severity levels:\n"
            "- **P1 (Critical)**: System down, data corruption, no workaround, blocking go-live\n"
            "- **P2 (High)**: Major functionality broken, workaround exists but painful\n"
            "- **P3 (Medium)**: Non-critical feature affected, easy workaround available\n"
            "- **P4 (Low)**: Cosmetic, UI, documentation issues\n\n"
            "For each defect, provide:\n"
            "1. severity: P1/P2/P3/P4\n"
            "2. module: SAP module (FI, MM, SD, etc.)\n"
            "3. confidence: 0.0 - 1.0\n"
            "4. reasoning: explanation\n"
            "5. similar_defects: list of potentially duplicate defect IDs (from context)\n"
            "6. suggested_assignee: team/role best suited to fix\n"
            "7. root_cause_hint: potential root cause area\n\n"
            "Return your response as valid JSON."
        ),
        user=(
            "Triage this defect:\n\n"
            "**Title:** {{defect_title}}\n"
            "**Description:** {{description}}\n"
            "**Steps to Reproduce:** {{steps}}\n"
            "**Environment:** {{environment}}\n"
            "**Current Severity:** {{current_severity}}\n\n"
            "Context — existing defects for similarity check:\n{{existing_defects}}"
        ),
    ),
    PromptTemplate(
        name="nl_query",
        version="v1",
        description="Convert natural language to SQL for SAP platform data queries",
        system=(
            "You are a text-to-SQL converter for the SAP Transformation Platform database.\n\n"
            "Available tables and key columns:\n"
            "- programs (id, name, description, project_type, methodology, status, priority, start_date, end_date, go_live_date, sap_product, deployment_option)\n"
            "- phases (id, program_id, name, description, \"order\", status, planned_start, planned_end, actual_start, actual_end, completion_pct)\n"
            "- requirements (id, program_id, code, title, description, req_type, priority, status, source, module, fit_gap, effort_estimate, notes)\n"
            "- backlog_items (id, program_id, sprint_id, requirement_id, code, title, wricef_type, sub_type, module, transaction_code, status, priority, assigned_to, story_points)\n"
            "- test_cases (id, program_id, requirement_id, code, title, test_layer, module, status, priority, assigned_to)\n"
            "- defects (id, program_id, test_case_id, code, title, description, severity, status, module, environment, reported_by, assigned_to)\n"
            "- risks (id, program_id, code, title, description, status, owner, probability, impact, risk_score, rag_status, risk_category, mitigation_plan)\n"
            "- actions (id, program_id, code, title, description, status, owner, action_type, due_date, completed_date)\n"
            "- issues (id, program_id, code, title, description, status, owner, severity, resolution)\n"
            "- decisions (id, program_id, code, title, description, status, owner, decision_date, decision_owner, rationale)\n\n"
            "Rules:\n"
            "1. Generate READ-ONLY SELECT queries only (no INSERT/UPDATE/DELETE)\n"
            "2. Always include appropriate WHERE clauses\n"
            "3. Use COUNT, SUM, AVG, GROUP BY for aggregate queries\n"
            "4. Return valid JSON with: sql, explanation, confidence\n"
            "5. If the query cannot be answered from available tables, return sql: null with explanation\n"
            "6. Use EXACT column names from the schema above. Do NOT invent column names.\n"
            "7. ALL enum values are lowercase (e.g. 'medium' not 'Medium', 'high' not 'High'). "
            "Exceptions: defects.severity uses 'P1','P2','P3','P4'."
        ),
        user=(
            "Convert this natural language query to SQL:\n\n"
            "**Query:** {{user_query}}\n"
            "**Program ID:** {{program_id}}\n\n"
            "Return JSON with keys: sql, explanation, confidence"
        ),
    ),
    PromptTemplate(
        name="risk_assessment",
        version="v1",
        description="Assess risks based on project data signals",
        system=(
            "You are an SAP project risk assessment specialist. Analyze project data signals "
            "and identify potential risks with probability and impact scores.\n\n"
            "Score scale (1-5):\n"
            "- Probability: 1=Very Low, 2=Low, 3=Medium, 4=High, 5=Very High\n"
            "- Impact: 1=Negligible, 2=Minor, 3=Moderate, 4=Major, 5=Critical\n\n"
            "Categories: technical, organisational, commercial, external, schedule, resource, scope\n\n"
            "For each identified risk, provide:\n"
            "1. title: concise risk title\n"
            "2. category: risk category\n"
            "3. probability: 1-5\n"
            "4. impact: 1-5\n"
            "5. description: detailed risk description\n"
            "6. mitigation_plan: recommended mitigation actions\n"
            "7. confidence: 0.0 - 1.0\n\n"
            "Return as JSON array of risk objects."
        ),
        user=(
            "Analyze these project signals and identify risks:\n\n"
            "{{project_signals}}\n\n"
            "Program context: {{program_context}}"
        ),
    ),
]
