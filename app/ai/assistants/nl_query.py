"""
SAP Transformation Management Platform
NL Query Assistant — Sprint 8 (Tasks 8.1 + 8.2).

Natural Language → SQL converter with:
    - SAP glossary term resolution (e.g. "O2C" → workstream, "WRICEF" → backlog_items)
    - DB schema context injection
    - SQL validation & sanitization (read-only enforcement)
    - Result formatting with natural-language explanation
    - Suggestion Queue integration for high-complexity queries

Architecture ref:  §10.6.1 — Natural Language Query Assistant
"""

import json
import logging
import re
from typing import Any

from app.models import db

logger = logging.getLogger(__name__)

# ── SAP Glossary (Term → DB mapping) ─────────────────────────────────────────

SAP_GLOSSARY = {
    # Process areas
    "o2c": {"column": "module", "values": ["SD"], "alias": "Order to Cash"},
    "p2p": {"column": "module", "values": ["MM"], "alias": "Procure to Pay"},
    "r2r": {"column": "module", "values": ["FI", "CO"], "alias": "Record to Report"},
    "hire to retire": {"column": "module", "values": ["HCM"], "alias": "Hire to Retire"},
    "plan to produce": {"column": "module", "values": ["PP", "QM"], "alias": "Plan to Produce"},

    # Object types
    "wricef": {"table": "backlog_items", "alias": "WRICEF development objects"},
    "workflow": {"table": "backlog_items", "filter": "wricef_type = 'workflow'"},
    "report": {"table": "backlog_items", "filter": "wricef_type = 'report'"},
    "interface": {"table": "backlog_items", "filter": "wricef_type = 'interface'"},
    "conversion": {"table": "backlog_items", "filter": "wricef_type = 'conversion'"},
    "enhancement": {"table": "backlog_items", "filter": "wricef_type = 'enhancement'"},
    "form": {"table": "backlog_items", "filter": "wricef_type = 'form'"},

    # Severity shortcuts
    "critical": {"column": "severity", "values": ["P1"]},
    "high": {"column": "severity", "values": ["P2"]},
    "medium severity": {"column": "severity", "values": ["P3"]},
    "low severity": {"column": "severity", "values": ["P4"]},
    "p1": {"column": "severity", "values": ["P1"]},
    "p2": {"column": "severity", "values": ["P2"]},
    "p3": {"column": "severity", "values": ["P3"]},
    "p4": {"column": "severity", "values": ["P4"]},

    # Status shortcuts
    "open defect": {"table": "defects", "filter": "status NOT IN ('closed', 'rejected')"},
    "open risk": {"table": "risks", "filter": "status NOT IN ('closed', 'mitigated')"},
    "blocked": {"column": "status", "values": ["blocked"]},
    "overdue": {"column": "status", "values": ["overdue"]},

    # SAP modules
    "fi": {"column": "module", "values": ["FI"]},
    "co": {"column": "module", "values": ["CO"]},
    "mm": {"column": "module", "values": ["MM"]},
    "sd": {"column": "module", "values": ["SD"]},
    "pp": {"column": "module", "values": ["PP"]},
    "qm": {"column": "module", "values": ["QM"]},
    "pm": {"column": "module", "values": ["PM"]},
    "hcm": {"column": "module", "values": ["HCM"]},
    "basis": {"column": "module", "values": ["BASIS"]},
    "btp": {"column": "module", "values": ["BTP"]},

    # Turkish shortcuts
    "gereksinim": {"table": "requirements", "alias": "requirement"},
    "hata": {"table": "defects", "alias": "defect"},
    "risk": {"table": "risks", "alias": "risk"},
    "test": {"table": "test_cases", "alias": "test case"},
    "görev": {"table": "actions", "alias": "action item"},
    "karar": {"table": "decisions", "alias": "decision"},
    "sorun": {"table": "issues", "alias": "issue"},
}

# ── DB Schema context for the LLM ────────────────────────────────────────────

DB_SCHEMA_CONTEXT = """
Available tables and key columns:

-- Program Management
programs (id, name, description, project_type, methodology, status, priority, start_date, end_date, go_live_date, sap_product, deployment_option, created_at, updated_at)
phases (id, program_id, name, description, "order", status, planned_start, planned_end, actual_start, actual_end, completion_pct, created_at)
gates (id, phase_id, name, description, gate_type, status, planned_date, actual_date, criteria, created_at)
workstreams (id, program_id, name, description, ws_type, lead_name, status, created_at)
team_members (id, program_id, name, email, role, raci, workstream_id, organization, is_active, created_at)
committees (id, program_id, name, description, committee_type, meeting_frequency, chair_name, created_at)

-- Scope & Requirements
scenarios (id, program_id, name, description, sap_module, process_area, status, priority, owner, workstream, total_workshops, total_requirements, notes, created_at, updated_at)
workshops (id, scenario_id, title, description, session_type, status, session_date, duration_minutes, location, facilitator, attendees, agenda, notes, decisions, action_items, fit_count, gap_count, partial_fit_count, created_at, updated_at)
processes (id, scenario_id, parent_id, name, description, level, process_id_code, code, module, scope_decision, fit_gap, sap_tcode, sap_reference, priority, notes, "order", created_at, updated_at)
analyses (id, process_id, name, description, analysis_type, status, fit_gap_result, decision, attendees, date, notes, created_at, updated_at)
requirements (id, program_id, process_id, workshop_id, req_parent_id, code, title, description, req_type, priority, status, source, module, effort_estimate, acceptance_criteria, notes, created_at, updated_at)
requirement_traces (id, requirement_id, target_type, target_id, trace_type, notes, created_at)
open_items (id, requirement_id, title, description, item_type, owner, due_date, status, resolution, priority, blocker, created_at, updated_at)
requirement_process_mappings (id, requirement_id, process_id, coverage_type, notes, created_at)

-- Backlog & Development
sprints (id, program_id, name, goal, status, start_date, end_date, capacity_points, velocity, "order", created_at, updated_at)
backlog_items (id, program_id, sprint_id, requirement_id, explore_requirement_id, code, title, description, wricef_type, sub_type, module, transaction_code, package, transport_request, status, priority, assigned_to, story_points, estimated_hours, actual_hours, complexity, board_order, acceptance_criteria, technical_notes, notes, created_at, updated_at)
config_items (id, program_id, requirement_id, code, title, description, module, config_key, transaction_code, transport_request, status, priority, assigned_to, complexity, estimated_hours, actual_hours, acceptance_criteria, notes, created_at, updated_at)
functional_specs (id, backlog_item_id, config_item_id, title, description, content, version, status, author, reviewer, approved_by, approved_at, created_at, updated_at)
technical_specs (id, functional_spec_id, title, description, content, version, status, author, reviewer, approved_by, approved_at, objects_list, unit_test_evidence, created_at, updated_at)

-- Testing
test_plans (id, program_id, name, description, status, test_strategy, entry_criteria, exit_criteria, start_date, end_date, created_at, updated_at)
test_cycles (id, plan_id, name, description, status, test_layer, start_date, end_date, "order", created_at, updated_at)
test_cases (id, program_id, requirement_id, backlog_item_id, config_item_id, code, title, description, test_layer, module, preconditions, test_steps, expected_result, test_data_set, status, priority, is_regression, assigned_to, created_at, updated_at)
test_executions (id, cycle_id, test_case_id, result, executed_by, executed_at, duration_minutes, notes, evidence_url, created_at, updated_at)
defects (id, program_id, test_case_id, backlog_item_id, config_item_id, code, title, description, steps_to_reproduce, severity, status, module, environment, reported_by, assigned_to, found_in_cycle, reported_at, resolved_at, reopen_count, resolution, root_cause, transport_request, notes, created_at, updated_at)

-- RAID (Risk, Action, Issue, Decision)
risks (id, program_id, code, title, description, status, owner, priority, probability, impact, risk_score, rag_status, risk_category, risk_response, mitigation_plan, contingency_plan, trigger_event, workstream_id, phase_id, created_at, updated_at)
actions (id, program_id, code, title, description, status, owner, priority, action_type, due_date, completed_date, linked_entity_type, linked_entity_id, workstream_id, phase_id, created_at, updated_at)
issues (id, program_id, code, title, description, status, owner, priority, severity, escalation_path, root_cause, resolution, resolution_date, workstream_id, phase_id, created_at, updated_at)
decisions (id, program_id, code, title, description, status, owner, priority, decision_date, decision_owner, alternatives, rationale, impact_description, reversible, workstream_id, phase_id, created_at, updated_at)

-- Notifications
notifications (id, program_id, recipient, title, message, category, severity, entity_type, entity_id, is_read, read_at, created_at)

Key relationships:
- phases.program_id → programs.id
- gates.phase_id → phases.id
- workstreams.program_id → programs.id
- team_members.workstream_id → workstreams.id
- scenarios.program_id → programs.id
- workshops.scenario_id → scenarios.id
- requirements.workshop_id → workshops.id
- processes.scenario_id → scenarios.id
- backlog_items.explore_requirement_id → explore_requirements.id
- analyses.process_id → processes.id
- requirements.process_id → processes.id
- requirement_process_mappings.requirement_id → requirements.id
- requirement_process_mappings.process_id → processes.id
- open_items.requirement_id → requirements.id
- requirements.program_id → programs.id
- requirement_traces.requirement_id → requirements.id
- backlog_items.program_id → programs.id
- backlog_items.sprint_id → sprints.id
- backlog_items.requirement_id → requirements.id
- config_items.requirement_id → requirements.id
- functional_specs.backlog_item_id → backlog_items.id
- functional_specs.config_item_id → config_items.id
- technical_specs.functional_spec_id → functional_specs.id
- test_plans.program_id → programs.id
- test_cycles.plan_id → test_plans.id
- test_cases.requirement_id → requirements.id
- test_cases.backlog_item_id → backlog_items.id
- test_cases.config_item_id → config_items.id
- test_executions.cycle_id → test_cycles.id
- test_executions.test_case_id → test_cases.id
- defects.test_case_id → test_cases.id
- defects.backlog_item_id → backlog_items.id
- defects.config_item_id → config_items.id
- risks/actions/issues/decisions.program_id → programs.id
- risks/actions/issues/decisions.workstream_id → workstreams.id
- risks/actions/issues/decisions.phase_id → phases.id

Common enum values:
- fit_gap: 'fit', 'partial_fit', 'gap', '' (empty = not classified)
- wricef_type: 'workflow', 'report', 'interface', 'conversion', 'enhancement', 'form'
- severity (defects): 'P1', 'P2', 'P3', 'P4'
- test_layer: 'unit', 'sit', 'uat', 'regression', 'performance'
- rag_status: 'red', 'amber', 'green'
""".strip()

# ── SQL Validation (Task 8.2) ─────────────────────────────────────────────────

# Forbidden SQL keywords / patterns
_FORBIDDEN_PATTERNS = [
    r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', r'\bDROP\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bEXEC\b',
    r'\bEXECUTE\b', r'\bGRANT\b', r'\bREVOKE\b', r'\bATTACH\b',
    r'\bDETACH\b', r'\bPRAGMA\b', r'\bVACUUM\b', r'\bREINDEX\b',
    r'\bREPLACE\b', r';\s*\w',  # multiple statements
    r'--',  # SQL comments (potential injection)
    r'/\*',  # block comments
]
_FORBIDDEN_RE = re.compile('|'.join(_FORBIDDEN_PATTERNS), re.IGNORECASE)

# Allowed table names
_ALLOWED_TABLES = {
    "programs", "phases", "gates", "workstreams", "team_members", "committees",
    "scenarios", "workshops",
    "processes", "analyses",
    "open_items", "requirement_process_mappings",
    "requirements", "requirement_traces",
    "sprints", "backlog_items", "config_items",
    "functional_specs", "technical_specs",
    "test_plans", "test_cycles", "test_cases", "test_executions",
    "defects",
    "risks", "actions", "issues", "decisions",
    "notifications",
}

# ── Known Enum Values (for SQL auto-correction) ──────────────────────────────
# Maps lowercase canonical value → exact DB value.
# LLM often generates 'Medium' instead of 'medium' or 'In Progress' instead of 'in_progress'.
# We build a lookup from every known value, so we can fix them in SQL string literals.

_KNOWN_ENUM_VALUES: dict[str, str] = {}  # normalized_lower → exact_db_value

_ENUM_DEFINITIONS: dict[str, list[str]] = {
    # Program management
    "programs.project_type": ["greenfield", "brownfield", "bluefield", "selective_data_transition"],
    "programs.methodology": ["sap_activate", "agile", "waterfall", "hybrid"],
    "programs.status": ["planning", "active", "on_hold", "completed", "cancelled"],
    "programs.priority": ["low", "medium", "high", "critical"],
    "programs.deployment_option": ["on_premise", "cloud", "hybrid"],
    "phases.status": ["not_started", "in_progress", "completed", "skipped"],
    "gates.gate_type": ["quality_gate", "milestone", "decision_point"],
    "gates.status": ["pending", "passed", "failed", "waived"],
    "workstreams.ws_type": ["functional", "technical", "cross_cutting"],
    "workstreams.status": ["active", "on_hold", "completed"],
    "committees.committee_type": ["steering", "advisory", "review", "working_group"],
    "committees.meeting_frequency": ["daily", "weekly", "biweekly", "monthly", "ad_hoc"],
    # Requirements
    "requirements.req_type": ["business", "functional", "technical", "non_functional", "integration"],
    "requirements.priority": ["must_have", "should_have", "could_have", "wont_have"],
    "requirements.status": ["draft", "approved", "in_progress", "implemented", "verified", "deferred", "rejected"],
    "requirements.fit_gap": [],
    "requirements.effort_estimate": ["xs", "s", "m", "l", "xl"],
    # Scenarios
    "scenarios.status": ["draft", "in_analysis", "analyzed", "approved", "on_hold"],
    "scenarios.priority": ["critical", "high", "medium", "low"],
    "scenarios.sap_module": ["FI", "CO", "SD", "MM", "PP", "QM", "PM", "HR", "WM", "LE", "PS", "BW", "BASIS"],
    "scenarios.process_area": ["order_to_cash", "procure_to_pay", "record_to_report", "plan_to_produce", "hire_to_retire", "warehouse_management", "project_management", "quality_management", "plant_maintenance", "general"],
    # Workshops
    "workshops.session_type": ["requirement_gathering", "process_mapping", "fit_gap_workshop", "design_workshop", "review", "demo", "sign_off", "training"],
    "workshops.status": ["planned", "in_progress", "completed", "cancelled"],
    # Scope
    "processes.scope_decision": ["in_scope", "out_of_scope", "deferred"],
    "processes.fit_gap": ["fit", "gap", "partial_fit", "standard"],
    "processes.priority": ["low", "medium", "high", "critical"],
    "analyses.analysis_type": ["workshop", "fit_gap", "demo", "prototype", "review"],
    "analyses.status": ["planned", "in_progress", "completed", "cancelled"],
    "analyses.fit_gap_result": ["fit", "partial_fit", "gap"],
    # Backlog
    "sprints.status": ["planning", "active", "completed", "cancelled"],
    "backlog_items.wricef_type": ["workflow", "report", "interface", "conversion", "enhancement", "form"],
    "backlog_items.status": ["new", "design", "build", "test", "deploy", "closed", "blocked", "cancelled"],
    "backlog_items.priority": ["low", "medium", "high", "critical"],
    "backlog_items.complexity": ["low", "medium", "high", "very_high"],
    "config_items.status": ["new", "design", "build", "test", "deploy", "closed", "blocked", "cancelled"],
    "config_items.priority": ["low", "medium", "high", "critical"],
    "functional_specs.status": ["draft", "in_review", "approved", "rework"],
    "technical_specs.status": ["draft", "in_review", "approved", "rework"],
    # Testing
    "test_plans.status": ["draft", "active", "completed", "cancelled"],
    "test_cycles.status": ["planning", "in_progress", "completed", "cancelled"],
    "test_cycles.test_layer": ["unit", "sit", "uat", "regression", "performance", "cutover_rehearsal"],
    "test_cases.test_layer": ["unit", "sit", "uat", "regression", "performance", "cutover_rehearsal"],
    "test_cases.status": ["draft", "ready", "approved", "deprecated"],
    "test_cases.priority": ["low", "medium", "high", "critical"],
    "test_executions.result": ["not_run", "pass", "fail", "blocked", "deferred"],
    "defects.severity": ["P1", "P2", "P3", "P4"],
    "defects.status": ["new", "open", "in_progress", "fixed", "retest", "closed", "rejected", "reopened"],
    # RAID
    "risks.status": ["identified", "analysed", "mitigating", "accepted", "closed", "expired"],
    "risks.priority": ["critical", "high", "medium", "low"],
    "risks.rag_status": ["green", "amber", "orange", "red"],
    "risks.risk_category": ["technical", "organisational", "commercial", "external", "schedule", "resource", "scope"],
    "risks.risk_response": ["avoid", "transfer", "mitigate", "accept", "escalate"],
    "actions.status": ["open", "in_progress", "completed", "cancelled", "overdue"],
    "actions.priority": ["critical", "high", "medium", "low"],
    "actions.action_type": ["preventive", "corrective", "detective", "improvement", "follow_up"],
    "issues.status": ["open", "investigating", "escalated", "resolved", "closed"],
    "issues.priority": ["critical", "high", "medium", "low"],
    "issues.severity": ["critical", "major", "moderate", "minor"],
    "decisions.status": ["proposed", "pending_approval", "approved", "rejected", "superseded"],
    "decisions.priority": ["critical", "high", "medium", "low"],
}

# Build the fast lookup: "medium" → "medium", "in progress" → "in_progress", etc.
for _vals in _ENUM_DEFINITIONS.values():
    for _v in _vals:
        _KNOWN_ENUM_VALUES[_v.lower()] = _v
        # Also map common LLM mistakes: "in_progress" → "in progress" (without underscore)
        _KNOWN_ENUM_VALUES[_v.lower().replace("_", " ")] = _v


def normalize_sql_enums(sql: str) -> str:
    """Fix case/format of string literals in SQL to match actual DB enum values.

    LLMs often produce 'Medium', 'In Progress', 'Partial Fit' instead of
    'medium', 'in_progress', 'partial_fit'. This function finds all single-quoted
    string literals and corrects them if a known enum value matches.
    """
    def _replace_literal(match: re.Match) -> str:
        original = match.group(1)
        key = original.lower().strip()
        if key in _KNOWN_ENUM_VALUES:
            return f"'{_KNOWN_ENUM_VALUES[key]}'"
        # Try underscore variant: "In Progress" → "in_progress"
        underscore_key = key.replace(" ", "_")
        if underscore_key in _KNOWN_ENUM_VALUES:
            return f"'{_KNOWN_ENUM_VALUES[underscore_key]}'"
        return match.group(0)  # No match, keep original

    return re.sub(r"'([^']*)'", _replace_literal, sql)


def validate_sql(sql: str) -> dict:
    """
    Validate SQL for safety: read-only enforcement + table whitelist.

    Returns:
        {"valid": bool, "error": str|None, "cleaned_sql": str}
    """
    if not sql or not sql.strip():
        return {"valid": False, "error": "Empty SQL query", "cleaned_sql": ""}

    cleaned = sql.strip().rstrip(";")

    # Must start with SELECT (or WITH for CTEs)
    upper = cleaned.upper().lstrip()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return {"valid": False, "error": "Only SELECT queries are allowed", "cleaned_sql": cleaned}

    # Check for forbidden patterns
    match = _FORBIDDEN_RE.search(cleaned)
    if match:
        return {"valid": False, "error": f"Forbidden SQL pattern detected: {match.group()}", "cleaned_sql": cleaned}

    # Check referenced tables against whitelist
    # Simple heuristic: find words after FROM / JOIN
    # Also extract CTE names (WITH name AS ...) to allow them
    cte_names = {m.lower() for m in re.findall(
        r'WITH\s+(\w+)\s+AS', cleaned, re.IGNORECASE
    )}
    table_refs = re.findall(
        r'(?:FROM|JOIN)\s+([a-zA-Z_]\w*)', cleaned, re.IGNORECASE
    )
    for tbl in table_refs:
        if tbl.lower() not in _ALLOWED_TABLES and tbl.lower() not in cte_names:
            return {
                "valid": False,
                "error": f"Table '{tbl}' is not in the allowed list",
                "cleaned_sql": cleaned,
            }

    # Add LIMIT if not present
    if "LIMIT" not in cleaned.upper():
        cleaned += " LIMIT 100"

    return {"valid": True, "error": None, "cleaned_sql": cleaned}


def sanitize_sql(sql: str) -> str:
    """Remove potentially dangerous characters and normalize whitespace."""
    # Remove inline/block comments 
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    # Collapse whitespace
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql


# ── NL Query Assistant ────────────────────────────────────────────────────────

class NLQueryAssistant:
    """
    Natural Language → SQL query assistant.

    Flow (per architecture §10.6.1):
        1. Enrich query with SAP glossary terms
        2. Build prompt with schema context + glossary
        3. Call LLM Gateway → get SQL + explanation + confidence
        4. Validate & sanitize SQL (read-only enforcement)
        5. Execute query on DB (if confidence ≥ threshold)
        6. Return results with natural-language explanation
    """

    CONFIDENCE_THRESHOLD = 0.6  # Below this → ask for confirmation
    HIGH_COMPLEXITY_THRESHOLD = 0.4  # Very low confidence → Suggestion Queue

    def __init__(self, gateway=None, prompt_registry=None):
        self.gateway = gateway
        self.prompt_registry = prompt_registry

    def process_query(
        self,
        user_query: str,
        program_id: int | None = None,
        auto_execute: bool = True,
    ) -> dict:
        """
        Process a natural-language query end-to-end.

        Args:
            user_query: User's question in natural language (TR/EN).
            program_id: Optional program filter.
            auto_execute: If True, execute SQL automatically when confident.

        Returns:
            dict with keys: sql, explanation, confidence, results, row_count, 
                            glossary_matches, executed, error
        """
        result = {
            "original_query": user_query,
            "program_id": program_id,
            "sql": None,
            "explanation": "",
            "confidence": 0.0,
            "results": [],
            "columns": [],
            "row_count": 0,
            "glossary_matches": [],
            "executed": False,
            "error": None,
        }

        # 1. Glossary enrichment
        glossary_matches = self._resolve_glossary(user_query)
        result["glossary_matches"] = glossary_matches

        # 2. Build prompt via registry or fallback
        messages = self._build_prompt(user_query, program_id, glossary_matches)

        # 3. Call LLM
        try:
            llm_response = self.gateway.chat(
                messages=messages,
                purpose="nl_query",
                program_id=program_id,
            )
            parsed = self._parse_llm_response(llm_response["content"])
            result["sql"] = parsed.get("sql")
            result["explanation"] = parsed.get("explanation", "")
            result["confidence"] = parsed.get("confidence", 0.0)
        except Exception as e:
            logger.error("NL Query LLM call failed: %s", e)
            result["error"] = f"AI query failed: {str(e)}"
            return result

        # 4. Validate SQL
        if not result["sql"]:
            result["error"] = "Could not generate SQL for this query"
            return result

        cleaned_sql = sanitize_sql(result["sql"])
        validation = validate_sql(cleaned_sql)
        if not validation["valid"]:
            result["error"] = f"SQL validation failed: {validation['error']}"
            result["sql"] = cleaned_sql
            return result

        # 4b. Auto-correct enum values (e.g. 'Medium' → 'medium')
        result["sql"] = normalize_sql_enums(validation["cleaned_sql"])

        # 5. Execute if confident enough
        if auto_execute and result["confidence"] >= self.CONFIDENCE_THRESHOLD:
            try:
                exec_result = self._execute_sql(result["sql"])
                result["results"] = exec_result["rows"]
                result["columns"] = exec_result["columns"]
                result["row_count"] = exec_result["row_count"]
                result["executed"] = True
            except Exception as e:
                logger.error("SQL execution failed: %s", e)
                result["error"] = f"Query execution failed: {str(e)}"
                result["executed"] = False
        else:
            result["executed"] = False
            if result["confidence"] < self.CONFIDENCE_THRESHOLD:
                result["error"] = (
                    "Low confidence — please confirm this SQL before executing. "
                    f"Confidence: {result['confidence']:.0%}"
                )

        return result

    # ── Glossary Resolution ───────────────────────────────────────────────

    @staticmethod
    def _resolve_glossary(query: str) -> list[dict]:
        """Find SAP glossary terms in the user query."""
        matches = []
        lower = query.lower()
        for term, info in SAP_GLOSSARY.items():
            if term in lower:
                matches.append({"term": term, **info})
        return matches

    # ── Prompt Building ───────────────────────────────────────────────────

    def _build_prompt(
        self, user_query: str, program_id: int | None,
        glossary_matches: list[dict],
    ) -> list[dict]:
        """Build chat messages for the LLM."""
        # Try YAML template first
        if self.prompt_registry:
            try:
                return self.prompt_registry.render(
                    "nl_query",
                    user_query=user_query,
                    program_id=program_id or "any",
                )
            except KeyError:
                pass

        # Fallback: inline prompt
        glossary_ctx = ""
        if glossary_matches:
            glossary_ctx = "\n\nDetected SAP terms:\n" + "\n".join(
                f"- \"{m['term']}\": {m.get('alias', m.get('table', m.get('column', '')))}"
                for m in glossary_matches
            )

        # Detect DB engine for SQL dialect
        from flask import current_app
        db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
        if db_uri.startswith("postgresql"):
            sql_dialect = "PostgreSQL-compatible syntax"
        else:
            sql_dialect = "SQLite-compatible syntax"

        system = (
            "You are a text-to-SQL converter for the SAP Transformation Platform.\n\n"
            f"{DB_SCHEMA_CONTEXT}\n\n"
            "Rules:\n"
            "1. SELECT queries ONLY (no INSERT/UPDATE/DELETE/DROP)\n"
            "2. Always filter by program_id when provided\n"
            "3. Use COUNT, SUM, AVG, GROUP BY for aggregate queries\n"
            f"4. {sql_dialect}\n"
            "5. LIMIT 100 maximum\n"
            "6. ALL enum values are lowercase (e.g. 'medium' not 'Medium'). Exception: defects.severity uses 'P1','P2','P3','P4'.\n"
            "7. Return valid JSON: {\"sql\": \"...\", \"explanation\": \"...\", \"confidence\": 0.0-1.0}\n"
            f"{glossary_ctx}"
        )

        user = f"Convert to SQL:\n\nQuery: {user_query}"
        if program_id:
            user += f"\nProgram ID: {program_id}"

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    # ── LLM Response Parsing ──────────────────────────────────────────────

    @staticmethod
    def _parse_llm_response(content: str) -> dict:
        """Parse LLM JSON response, handling markdown code fences."""
        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (possibly with language tag)
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed text
            match = re.search(r'\{[^{}]*"sql"\s*:', cleaned, re.DOTALL)
            if match:
                # Find the matching closing brace
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
            # Last resort
            return {"sql": None, "explanation": content[:500], "confidence": 0.0}

    # ── SQL Execution ─────────────────────────────────────────────────────

    @staticmethod
    def _execute_sql(sql: str) -> dict:
        """Execute validated read-only SQL and return results."""
        result = db.session.execute(db.text(sql))
        columns = list(result.keys()) if result.returns_rows else []
        rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
