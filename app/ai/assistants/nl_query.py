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
from dataclasses import dataclass
from typing import Any

from app.models import db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryContext:
    """Normalized query analysis used by deterministic SQL generation."""

    original_query: str
    normalized_query: str
    program_id: int | None
    project_id: int | None
    glossary_matches: list[dict]
    module_values: list[str]
    intent: str
    entity: str | None
    workshop_scope: bool
    wants_grouping: bool

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
    "rfc": {"table": "change_requests", "alias": "RFC change request"},
    "change request": {"table": "change_requests", "alias": "RFC change request"},
    "change requests": {"table": "change_requests", "alias": "RFC change requests"},

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

    # Entity shortcuts
    "config item": {"table": "config_items", "alias": "configuration item"},
    "config items": {"table": "config_items", "alias": "configuration items"},
    "configuration item": {"table": "config_items", "alias": "configuration item"},
    "backlog item": {"table": "backlog_items", "alias": "backlog/WRICEF item"},
    "backlog items": {"table": "backlog_items", "alias": "backlog/WRICEF items"},
    "action item": {"table": "actions", "alias": "action item"},
    "action items": {"table": "actions", "alias": "action items"},
    "issue": {"table": "issues", "alias": "issue"},
    "issues": {"table": "issues", "alias": "issues"},

    # Localized shortcuts (Turkish)
    "gereksinim": {"table": "requirements", "alias": "requirement"},
    "hata": {"table": "defects", "alias": "defect"},
    "risk": {"table": "risks", "alias": "risk"},
    "test": {"table": "test_cases", "alias": "test case"},
    "gorev": {"table": "actions", "alias": "action item"},
    "karar": {"table": "decisions", "alias": "decision"},
    "sorun": {"table": "issues", "alias": "issue"},
}

_WORKSHOP_COUNT_FALLBACKS: dict[str, dict[str, str]] = {
    "open_items": {
        "table": "explore_open_items eoi",
        "join": "JOIN explore_workshops ew ON ew.id = eoi.workshop_id",
        "scope_alias": "eoi",
        "count_alias": "workshop_open_item_count",
        "extra_filter": "\n  AND eoi.status IN ('open', 'in_progress', 'blocked')",
        "explanation": "Counts open workshop follow-up items for the selected program.",
    },
    "requirements": {
        "table": "explore_requirements er",
        "join": "JOIN explore_workshops ew ON ew.id = er.workshop_id",
        "scope_alias": "er",
        "count_alias": "workshop_requirement_count",
        "extra_filter": "",
        "explanation": "Counts workshop requirements for the selected program.",
    },
}

_MODULE_COUNT_FALLBACKS: dict[str, dict[str, str]] = {
    "test_cases": {
        "table": "test_cases tc",
        "scope_alias": "tc",
        "module_column": "module",
        "count_alias": "test_case_count",
        "explanation": "Counts test cases for the selected SAP module in the selected program.",
    },
}

_ENTITY_QUERY_FALLBACKS: dict[str, dict[str, str | bool | list[str]]] = {
    "defects": {
        "table": "defects d",
        "scope_alias": "d",
        "module_column": "module",
        "count_alias": "defect_count",
        "supports_project_scope": False,
        "explanation": "Counts defects for the selected program.",
        "singular_label": "defect",
        "plural_label": "defects",
        "list_columns": ["d.code", "d.title", "d.status", "d.severity", "d.module", "d.assigned_to", "d.reported_at"],
        "default_order": "d.reported_at DESC, d.code ASC",
        "status_enum_key": "defects.status",
        "severity_enum_key": "defects.severity",
    },
    "test_cases": {
        "table": "test_cases tc",
        "scope_alias": "tc",
        "module_column": "module",
        "count_alias": "test_case_count",
        "supports_project_scope": False,
        "explanation": "Counts test cases for the selected program.",
        "singular_label": "test case",
        "plural_label": "test cases",
        "list_columns": ["tc.code", "tc.title", "tc.status", "tc.priority", "tc.module", "tc.test_layer"],
        "default_order": "tc.updated_at DESC, tc.code ASC",
        "status_enum_key": "test_cases.status",
    },
    "requirements": {
        "table": "explore_requirements req",
        "scope_alias": "req",
        "module_column": "sap_module",
        "count_alias": "requirement_count",
        "supports_project_scope": False,
        "explanation": "Counts requirements (explore) for the selected program.",
        "singular_label": "requirement",
        "plural_label": "requirements",
        "list_columns": ["req.code", "req.title", "req.status", "req.priority", "req.sap_module", "req.fit_status"],
        "default_order": "req.updated_at DESC, req.code ASC",
        "status_enum_key": "requirements.status",
    },
    "change_requests": {
        "table": "change_requests cr",
        "scope_alias": "cr",
        "module_column": "source_module",
        "count_alias": "rfc_count",
        "supports_project_scope": True,
        "explanation": "Counts RFC change requests for the selected project or program.",
        "singular_label": "RFC change request",
        "plural_label": "RFC change requests",
        "list_columns": ["cr.code", "cr.title", "cr.status", "cr.change_model", "cr.change_domain"],
        "default_order": "cr.updated_at DESC, cr.code ASC",
        "status_enum_key": "change_requests.status",
    },
    "risks": {
        "table": "risks r",
        "scope_alias": "r",
        "count_alias": "risk_count",
        "supports_project_scope": False,
        "explanation": "Counts risk items for the selected program.",
        "singular_label": "risk item",
        "plural_label": "risk items",
        "list_columns": ["r.code", "r.title", "r.status", "r.priority", "r.rag_status", "r.owner"],
        "default_order": "r.risk_score DESC, r.updated_at DESC, r.code ASC",
        "status_enum_key": "risks.status",
    },
    "config_items": {
        "table": "config_items ci",
        "scope_alias": "ci",
        "module_column": "module",
        "count_alias": "config_item_count",
        "supports_project_scope": False,
        "explanation": "Counts configuration items for the selected program.",
        "singular_label": "config item",
        "plural_label": "config items",
        "list_columns": ["ci.code", "ci.title", "ci.status", "ci.priority", "ci.module", "ci.assigned_to"],
        "default_order": "ci.updated_at DESC, ci.code ASC",
        "status_enum_key": "config_items.status",
    },
    "backlog_items": {
        "table": "backlog_items bi",
        "scope_alias": "bi",
        "module_column": "module",
        "count_alias": "backlog_item_count",
        "supports_project_scope": False,
        "explanation": "Counts backlog/WRICEF items for the selected program.",
        "singular_label": "backlog item",
        "plural_label": "backlog items",
        "list_columns": ["bi.code", "bi.title", "bi.status", "bi.priority", "bi.wricef_type", "bi.module", "bi.assigned_to"],
        "default_order": "bi.updated_at DESC, bi.code ASC",
        "status_enum_key": "backlog_items.status",
    },
    "actions": {
        "table": "actions a",
        "scope_alias": "a",
        "count_alias": "action_count",
        "supports_project_scope": False,
        "explanation": "Counts action items for the selected program.",
        "singular_label": "action item",
        "plural_label": "action items",
        "list_columns": ["a.code", "a.title", "a.status", "a.priority", "a.owner", "a.due_date"],
        "default_order": "a.due_date ASC, a.code ASC",
        "status_enum_key": "actions.status",
    },
    "issues": {
        "table": "issues i",
        "scope_alias": "i",
        "count_alias": "issue_count",
        "supports_project_scope": False,
        "explanation": "Counts issues for the selected program.",
        "singular_label": "issue",
        "plural_label": "issues",
        "list_columns": ["i.code", "i.title", "i.status", "i.priority", "i.severity", "i.owner"],
        "default_order": "i.updated_at DESC, i.code ASC",
        "status_enum_key": "issues.status",
    },
}

_LIST_SORT_KEYWORDS: dict[str, str] = {
    "priority": "priority",
    "status": "status",
    "severity": "severity",
    "module": "module",
    "updated": "updated_at",
    "updated at": "updated_at",
    "created": "created_at",
    "created at": "created_at",
    "date": "updated_at",
    "title": "title",
    "code": "code",
}

_LIST_PRIORITY_VALUES: dict[str, str] = {
    "critical priority": "critical",
    "high priority": "high",
    "medium priority": "medium",
    "low priority": "low",
    "must have": "must_have",
    "must-have": "must_have",
    "should have": "should_have",
    "should-have": "should_have",
    "could have": "could_have",
    "could-have": "could_have",
    "wont have": "wont_have",
    "won't have": "wont_have",
}

_FALLBACK_QUERY_PATTERNS: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (
        re.compile(r"\brequirements?\b.*\bfit(?:/|\s+to\s+)?gap\b|\bfit(?:/|\s+to\s+)?gap\b.*\brequirements?\b", re.IGNORECASE),
        (
            """
            SELECT
                COALESCE(fit_status, 'unclassified') AS fit_status,
                COUNT(*) AS requirement_count
            FROM explore_requirements
            WHERE {scope_column} = {scope_value}
            GROUP BY COALESCE(fit_status, 'unclassified')
            ORDER BY requirement_count DESC, fit_status ASC
            """.strip(),
            "Groups explore requirements by fit/gap status for the selected scope.",
        ),
    ),
    (
        re.compile(r"\bhow many\b.*\bopen\b.*\bdefects?\b|\bopen\b.*\bdefects?\b", re.IGNORECASE),
        (
            """
            SELECT COUNT(*) AS open_defect_count
            FROM defects
            WHERE {scope_column} = {scope_value}
              AND status NOT IN ('closed', 'rejected')
            """.strip(),
            "Counts open defects for the selected program.",
        ),
    ),
    (
        re.compile(
            r"\bhow many\b.*\bopen\s+items?\b.*\bworkshops?\b|"
            r"\bopen\s+items?\b.*\bunder\b.*\bworkshops?\b|"
            r"\bkaç\b.*\baçık\s+madd(e|eler)\b.*\bworkshop\b",
            re.IGNORECASE,
        ),
        (
            """
            SELECT COUNT(*) AS workshop_open_item_count
                        FROM explore_open_items eoi
                        JOIN explore_workshops ew ON ew.id = eoi.workshop_id
                        WHERE eoi.{scope_column} = {scope_value}
                            AND eoi.workshop_id IS NOT NULL
                            AND eoi.status IN ('open', 'in_progress', 'blocked'){explore_process_area_filter}
            """.strip(),
            "Counts open workshop follow-up items for the selected program.",
        ),
    ),
    (
        re.compile(
            r"\bhow many\b.*\brequirements?\b.*\bworkshops?\b|"
            r"\brequirements?\b.*\bunder\b.*\bworkshops?\b|"
            r"\bkaç\b.*\bgereksinim\b.*\bworkshop\b",
            re.IGNORECASE,
        ),
        (
            """
            SELECT COUNT(*) AS workshop_requirement_count
            FROM explore_requirements er
            JOIN explore_workshops ew ON ew.id = er.workshop_id
            WHERE er.{scope_column} = {scope_value}
              AND er.workshop_id IS NOT NULL{explore_process_area_filter}
            """.strip(),
            "Counts workshop requirements for the selected program.",
        ),
    ),
    (
        re.compile(r"\bp1\b.*\bdefects?\b.*\bfi\b|\bfi\b.*\bp1\b.*\bdefects?\b", re.IGNORECASE),
        (
            """
            SELECT code, title, status, severity, module, assigned_to, reported_at
            FROM defects
            WHERE {scope_column} = {scope_value}
              AND severity = 'P1'
              AND module = 'FI'
            ORDER BY reported_at DESC, code ASC
            """.strip(),
            "Lists P1 FI defects for the selected program.",
        ),
    ),
    (
        re.compile(r"\bwricef\b.*\bmodule\b|\bmodule\b.*\bwricef\b", re.IGNORECASE),
        (
            """
            SELECT COALESCE(module, 'unassigned') AS module, COUNT(*) AS wricef_count
            FROM backlog_items
            WHERE {scope_column} = {scope_value}
            GROUP BY COALESCE(module, 'unassigned')
            ORDER BY wricef_count DESC, module ASC
            """.strip(),
            "Summarizes WRICEF backlog items by SAP module.",
        ),
    ),
    (
        re.compile(r"\btest\b.*\b(pass rate|execution pass rate)\b|\bpass rate\b.*\btest\b", re.IGNORECASE),
        (
            """
            SELECT
                COUNT(*) AS total_executions,
                SUM(CASE WHEN result = 'pass' THEN 1 ELSE 0 END) AS passed_executions,
                ROUND(
                    100.0 * SUM(CASE WHEN result = 'pass' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                    2
                ) AS pass_rate_pct
            FROM test_executions te
            JOIN test_cycles tc ON tc.id = te.cycle_id
            JOIN test_plans tp ON tp.id = tc.plan_id
            WHERE tp.{scope_column} = {scope_value}
            """.strip(),
            "Calculates overall test execution pass rate for the selected program.",
        ),
    ),
    (
        re.compile(r"\bhow many\b.*\bdecisions?\b|\bcount\b.*\bdecisions?\b|\bkaç\b.*\bkarar\b", re.IGNORECASE),
        (
            """
            SELECT
                (SELECT COUNT(*) FROM decisions WHERE {scope_column} = {scope_value}) AS governance_decision_count,
                (SELECT COUNT(*) FROM explore_decisions WHERE {scope_column} = {scope_value}) AS workshop_decision_count,
                (
                    (SELECT COUNT(*) FROM decisions WHERE {scope_column} = {scope_value}) +
                    (SELECT COUNT(*) FROM explore_decisions WHERE {scope_column} = {scope_value})
                ) AS total_decision_count
            """.strip(),
            "Counts governance and workshop decisions together for the selected program.",
        ),
    ),
]

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

-- Change Management
change_requests (id, program_id, project_id, code, title, description, change_model, change_domain, status, priority, risk_level, environment, source_module, source_entity_type, source_entity_id, planned_start, planned_end, actual_start, actual_end, approved_at, validated_at, closed_at, created_at, updated_at)

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
- change_requests.program_id → programs.id
- change_requests.project_id → projects.id

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
    "change_requests",
    "notifications",
    "explore_workshops", "explore_requirements", "explore_open_items", "explore_decisions",
    "process_levels", "process_steps", "workshop_attendees", "workshop_agenda_items",
    "explore_workshop_documents", "workshop_scope_items", "projects",
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
    "change_requests.status": ["draft", "submitted", "approved", "in_progress", "validated", "closed", "rejected", "cancelled"],
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
        project_id: int | None = None,
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
            "project_id": project_id,
            "sql": None,
            "explanation": "",
            "confidence": 0.0,
            "results": [],
            "columns": [],
            "row_count": 0,
            "glossary_matches": [],
            "executed": False,
            "error": None,
            "answer": "",
        }

        # 1. Build deterministic query context up front.
        query_context = self._build_query_context(user_query, program_id, project_id)
        result["glossary_matches"] = query_context.glossary_matches

        # 2. Prefer deterministic SQL before calling the LLM.
        deterministic = self._fallback_sql(query_context)
        if deterministic:
            result["sql"] = deterministic["sql"]
            result["explanation"] = deterministic["explanation"]
            result["confidence"] = deterministic["confidence"]
        else:
            messages = self._build_prompt(query_context)

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
                guidance = self._build_guidance_response(query_context, str(e))
                result.update(guidance)
                return result

            if not result["sql"]:
                guidance = self._build_guidance_response(query_context)
                result.update(guidance)
                return result

        # 4. Validate SQL
        if not result["sql"]:
            guidance = self._build_guidance_response(query_context)
            result.update(guidance)
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
                result["answer"] = self._build_answer(query_context, result)
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
            pattern = re.compile(rf"(?<!\w){re.escape(term.lower())}(?!\w)")
            if pattern.search(lower):
                matches.append({"term": term, **info})
        return matches

    @staticmethod
    def _build_query_context(user_query: str, program_id: int | None, project_id: int | None = None) -> QueryContext:
        """Analyze a natural-language query into deterministic routing signals."""
        glossary_matches = NLQueryAssistant._resolve_glossary(user_query)
        normalized_query = re.sub(r"\s+", " ", user_query.lower()).strip()
        module_values: list[str] = []
        for match in glossary_matches:
            if match.get("column") != "module":
                continue
            for value in match.get("values", []):
                if isinstance(value, str):
                    module_values.append(value)

        return QueryContext(
            original_query=user_query,
            normalized_query=normalized_query,
            program_id=program_id,
            project_id=project_id,
            glossary_matches=glossary_matches,
            module_values=sorted(set(module_values)),
            intent=NLQueryAssistant._detect_query_intent(user_query),
            entity=NLQueryAssistant._detect_primary_entity(user_query),
            workshop_scope=bool(re.search(r"\bworkshops?\b|\bworkshop\b", user_query, re.IGNORECASE)),
            wants_grouping=bool(re.search(r"\bby\b|\bdistribution\b|\bgroup\b|\bstatus\b", user_query, re.IGNORECASE)),
        )

    @staticmethod
    def _fallback_sql(query_context: QueryContext) -> dict | None:
        """Return deterministic SQL for common assistant hints when the LLM cannot."""
        scope_column = "program_id"
        scope_value = str(query_context.program_id) if query_context.program_id is not None else "1=1"
        explore_process_area_filter = NLQueryAssistant._build_explore_process_area_filter(query_context.glossary_matches, "ew")

        workshop_metric_sql = NLQueryAssistant._fallback_workshop_metric_sql(
            query_context,
        )
        if workshop_metric_sql is not None:
            return workshop_metric_sql

        module_metric_sql = NLQueryAssistant._fallback_module_metric_sql(
            query_context,
        )
        if module_metric_sql is not None:
            return module_metric_sql

        entity_metric_sql = NLQueryAssistant._fallback_entity_metric_sql(
            query_context,
        )
        if entity_metric_sql is not None:
            return entity_metric_sql

        for pattern, (template, explanation) in _FALLBACK_QUERY_PATTERNS:
            if not pattern.search(query_context.original_query):
                continue
            if query_context.program_id is None:
                sql = template.replace("WHERE {scope_column} = {scope_value}\n", "WHERE ")
                sql = sql.replace("WHERE {scope_column} = {scope_value}", "")
                sql = sql.replace("WHERE eoi.{scope_column} = {scope_value}\n", "WHERE ")
                sql = sql.replace("WHERE eoi.{scope_column} = {scope_value}", "")
                sql = sql.replace("WHERE er.{scope_column} = {scope_value}\n", "WHERE ")
                sql = sql.replace("WHERE er.{scope_column} = {scope_value}", "")
                sql = sql.replace("tp.{scope_column} = {scope_value}", "1=1")
            else:
                sql = template.format(
                    scope_column=scope_column,
                    scope_value=scope_value,
                    explore_process_area_filter=explore_process_area_filter,
                )

            sql = sql.replace("{explore_process_area_filter}", explore_process_area_filter)

            sql = re.sub(r"\n\s+", "\n", sql).strip()
            return {
                "sql": sql,
                "explanation": explanation,
                "confidence": 0.82,
            }

        return None

    @staticmethod
    def _fallback_module_metric_sql(
        query_context: QueryContext,
    ) -> dict | None:
        """Return generic SQL for module-scoped count queries on domain entities."""
        if query_context.intent != "count":
            return None

        metric_key = NLQueryAssistant._detect_module_metric(query_context.original_query)
        if metric_key is None:
            return None

        metric = _MODULE_COUNT_FALLBACKS[metric_key]
        module_filter = NLQueryAssistant._build_module_column_filter(
            query_context.glossary_matches,
            metric["scope_alias"],
            metric["module_column"],
        )
        if not module_filter:
            return None

        scope_alias = metric["scope_alias"]
        scope_filter = "1=1" if query_context.program_id is None else f"{scope_alias}.program_id = {query_context.program_id}"
        sql = (
            f"SELECT COUNT(*) AS {metric['count_alias']}\n"
            f"FROM {metric['table']}\n"
            f"WHERE {scope_filter}"
            f"{module_filter}"
        )
        sql = re.sub(r"\n\s+", "\n", sql).strip()
        return {
            "sql": sql,
            "explanation": metric["explanation"],
            "confidence": 0.84,
        }

    @staticmethod
    def _fallback_entity_metric_sql(
        query_context: QueryContext,
    ) -> dict | None:
        """Return generic SQL for entity count/list queries such as RFC or risk totals."""
        if query_context.intent not in {"count", "list"}:
            return None
        if query_context.entity not in _ENTITY_QUERY_FALLBACKS:
            return None

        metric = _ENTITY_QUERY_FALLBACKS[query_context.entity]
        scope_filter = NLQueryAssistant._build_scope_filter(
            scope_alias=str(metric["scope_alias"]),
            program_id=query_context.program_id,
            project_id=query_context.project_id,
            supports_project_scope=bool(metric.get("supports_project_scope", False)),
        )
        status_filter = NLQueryAssistant._build_entity_status_filter(query_context, metric)
        module_column = metric.get("module_column")
        if isinstance(module_column, str):
            module_filter = NLQueryAssistant._build_module_column_filter(
                query_context.glossary_matches,
                str(metric["scope_alias"]),
                module_column,
            )
        else:
            module_filter = ""
        priority_filter = NLQueryAssistant._build_entity_priority_filter(query_context, metric)
        severity_filter = NLQueryAssistant._build_entity_severity_filter(query_context, metric)
        scope_phrase = "project or program" if bool(metric.get("supports_project_scope", False)) else "program"
        if query_context.intent == "list":
            list_columns = ", ".join(str(column) for column in metric.get("list_columns", []))
            order_by = NLQueryAssistant._build_list_order_by(query_context, metric)
            limit_clause = NLQueryAssistant._build_list_limit_clause(query_context)
            sql = (
                f"SELECT {list_columns}\n"
                f"FROM {metric['table']}\n"
                f"WHERE {scope_filter}{status_filter}{module_filter}{priority_filter}{severity_filter}\n"
                f"ORDER BY {order_by}\n"
                f"LIMIT {limit_clause}"
            )
            confidence = 0.8
            explanation = f"Lists {metric['plural_label']} for the selected {scope_phrase}."
        else:
            sql = (
                f"SELECT COUNT(*) AS {metric['count_alias']}\n"
                f"FROM {metric['table']}\n"
                f"WHERE {scope_filter}{status_filter}{module_filter}{priority_filter}{severity_filter}"
            )
            confidence = 0.84
            explanation = str(metric["explanation"])
        sql = re.sub(r"\n\s+", "\n", sql).strip()
        return {
            "sql": sql,
            "explanation": explanation,
            "confidence": confidence,
        }

    @staticmethod
    def _fallback_workshop_metric_sql(
        query_context: QueryContext,
    ) -> dict | None:
        """Return generic SQL for workshop-scoped count queries with optional module filters."""
        if query_context.intent != "count":
            return None
        if not query_context.workshop_scope:
            return None

        metric_key = NLQueryAssistant._detect_workshop_metric(query_context.original_query)
        if metric_key is None:
            return None

        metric = _WORKSHOP_COUNT_FALLBACKS[metric_key]
        scope_alias = metric["scope_alias"]
        scope_filter = "1=1" if query_context.program_id is None else f"{scope_alias}.program_id = {query_context.program_id}"
        explore_process_area_filter = NLQueryAssistant._build_explore_process_area_filter(query_context.glossary_matches, "ew")
        sql = (
            f"SELECT COUNT(*) AS {metric['count_alias']}\n"
            f"FROM {metric['table']}\n"
            f"{metric['join']}\n"
            f"WHERE {scope_filter}\n"
            f"  AND {scope_alias}.workshop_id IS NOT NULL"
            f"{metric['extra_filter']}"
            f"{explore_process_area_filter}"
        )
        sql = re.sub(r"\n\s+", "\n", sql).strip()
        return {
            "sql": sql,
            "explanation": metric["explanation"],
            "confidence": 0.84,
        }

    @staticmethod
    def _detect_workshop_metric(user_query: str) -> str | None:
        """Identify which workshop metric the user wants counted."""
        lowered_query = user_query.lower()
        if re.search(r"\bopen\s+items?\b|\baçık\s+madd(e|eler)\b", lowered_query):
            return "open_items"
        if re.search(r"\brequirements?\b|\bgereksinim\b", lowered_query):
            return "requirements"
        return None

    @staticmethod
    def _detect_module_metric(user_query: str) -> str | None:
        """Identify which module-scoped entity the user wants counted."""
        lowered_query = user_query.lower()
        if re.search(r"\btest\s+cases?\b|\btest\b", lowered_query):
            return "test_cases"
        return None

    @staticmethod
    def _detect_query_intent(user_query: str) -> str:
        """Classify the query into a pragmatic intent bucket."""
        lowered_query = user_query.lower()
        if NLQueryAssistant._is_count_like_query(user_query):
            return "count"
        if re.search(r"\blist\b|\bshow\b|\bhangi\b|\blistele\b|\btop\s+\d+\b|\bfirst\s+\d+\b|\bsort(?:ed)?\s+by\b|\border\s+by\b", lowered_query):
            return "list"
        if re.search(r"\bdistribution\b|\bgroup(?:ed)?\b|\bgroup\s+by\b|\bby\s+status\b|\bby\s+module\b|\bby\s+priority\b", lowered_query):
            return "distribution"
        return "unknown"

    @staticmethod
    def _detect_primary_entity(user_query: str) -> str | None:
        """Detect the main business entity being queried."""
        lowered_query = user_query.lower()
        if re.search(r"\brfcs?\b|\bchange\s+requests?\b", lowered_query):
            return "change_requests"
        if re.search(r"\bconfig(?:uration)?\s+items?\b|\bconfig\s+items?\b", lowered_query):
            return "config_items"
        if re.search(r"\bbacklog\s+items?\b", lowered_query):
            return "backlog_items"
        if re.search(r"\brisks?\b|\brisk\s+items?\b", lowered_query):
            return "risks"
        if re.search(r"\bopen\s+items?\b|\baçık\s+madd", lowered_query):
            return "open_items"
        if re.search(r"\brequirements?\b|\bgereksinim", lowered_query):
            return "requirements"
        if re.search(r"\btest\s+cases?\b|\btest\b", lowered_query):
            return "test_cases"
        if re.search(r"\bdefects?\b|\bhata\b", lowered_query):
            return "defects"
        if re.search(r"\bdecisions?\b|\bkarar\b", lowered_query):
            return "decisions"
        if re.search(r"\bactions?\b|\baction\s+items?\b|\bgorev\b", lowered_query):
            return "actions"
        if re.search(r"\bissues?\b|\bsorun\b", lowered_query):
            return "issues"
        if re.search(r"\bwricef\b", lowered_query):
            return "backlog_items"
        return None

    @staticmethod
    def _is_count_like_query(user_query: str) -> bool:
        """Detect count-style phrasing, including minor typos in 'how many'."""
        return bool(re.search(r"\bhow\s+ma\w*\b|\bcount\b|\bkaç\b", user_query, re.IGNORECASE))

    @staticmethod
    def _build_explore_process_area_filter(glossary_matches: list[dict], table_alias: str) -> str:
        """Map detected SAP module glossary terms to Explore process-area filters."""
        process_areas: list[str] = []
        for match in glossary_matches:
            if match.get("column") != "module":
                continue
            for value in match.get("values", []):
                if value in {"FI", "CO", "MM", "SD", "PP", "QM", "PM", "HCM", "BASIS", "BTP", "HR"}:
                    process_areas.append("HR" if value == "HCM" else value)

        if not process_areas:
            return ""

        unique_values = sorted(set(process_areas))
        quoted_values = ", ".join(f"'{value}'" for value in unique_values)
        return f"\n  AND {table_alias}.process_area IN ({quoted_values})"

    @staticmethod
    def _build_module_column_filter(glossary_matches: list[dict], table_alias: str, column_name: str = "module") -> str:
        """Build a SQL filter for detected SAP module glossary terms."""
        modules: list[str] = []
        for match in glossary_matches:
            if match.get("column") != "module":
                continue
            modules.extend(value for value in match.get("values", []) if isinstance(value, str))

        if not modules:
            return ""

        unique_values = sorted(set(modules))
        quoted_values = ", ".join(f"'{value}'" for value in unique_values)
        return f"\n  AND {table_alias}.{column_name} IN ({quoted_values})"

    @staticmethod
    def _build_scope_filter(
        scope_alias: str,
        program_id: int | None,
        project_id: int | None,
        supports_project_scope: bool = False,
    ) -> str:
        """Build a scope filter using project when available, otherwise program."""
        filters: list[str] = []
        if program_id is not None:
            filters.append(f"{scope_alias}.program_id = {program_id}")
        if supports_project_scope and project_id is not None:
            filters.append(f"{scope_alias}.project_id = {project_id}")
        return " AND ".join(filters) if filters else "1=1"

    @staticmethod
    def _build_entity_status_filter(query_context: QueryContext, metric: dict[str, str | bool | list[str]]) -> str:
        """Add pragmatic status filters based on query wording and entity enums."""
        normalized_query = query_context.normalized_query
        scope_alias = str(metric["scope_alias"])
        status_column = f"{scope_alias}.status"

        if "open" in normalized_query:
            if query_context.entity == "defects":
                return f"\n  AND {status_column} NOT IN ('closed', 'rejected')"
            if query_context.entity == "risks":
                return f"\n  AND {status_column} NOT IN ('closed', 'mitigated')"
            if query_context.entity == "change_requests":
                return f"\n  AND {status_column} NOT IN ('closed', 'rejected', 'cancelled')"
            if query_context.entity == "requirements":
                return f"\n  AND {status_column} NOT IN ('implemented', 'verified', 'rejected')"

        status_enum_key = metric.get("status_enum_key")
        if not isinstance(status_enum_key, str):
            return ""

        matched_status = NLQueryAssistant._detect_status_value(normalized_query, _ENUM_DEFINITIONS.get(status_enum_key, []))
        if matched_status is None:
            return ""
        return f"\n  AND {status_column} = '{matched_status}'"

    @staticmethod
    def _build_entity_priority_filter(query_context: QueryContext, metric: dict[str, str | bool | list[str]]) -> str:
        """Add pragmatic priority filters for list queries."""
        normalized_query = query_context.normalized_query
        scope_alias = str(metric["scope_alias"])
        priority_column = f"{scope_alias}.priority"

        matched_priority = NLQueryAssistant._detect_priority_value(normalized_query)
        if matched_priority is None:
            return ""
        return f"\n  AND {priority_column} = '{matched_priority}'"

    @staticmethod
    def _build_entity_severity_filter(query_context: QueryContext, metric: dict[str, str | bool | list[str]]) -> str:
        """Add pragmatic severity filters for entity queries when supported."""
        severity_enum_key = metric.get("severity_enum_key")
        if not isinstance(severity_enum_key, str):
            return ""

        scope_alias = str(metric["scope_alias"])
        severity_column = f"{scope_alias}.severity"

        severities: list[str] = []
        for match in query_context.glossary_matches:
            if match.get("column") != "severity":
                continue
            severities.extend(value for value in match.get("values", []) if isinstance(value, str))

        if severities:
            unique_values = sorted(set(severities))
            if len(unique_values) == 1:
                return f"\n  AND {severity_column} = '{unique_values[0]}'"
            quoted_values = ", ".join(f"'{value}'" for value in unique_values)
            return f"\n  AND {severity_column} IN ({quoted_values})"

        matched_severity = NLQueryAssistant._detect_status_value(
            query_context.normalized_query,
            _ENUM_DEFINITIONS.get(severity_enum_key, []),
        )
        if matched_severity is None:
            return ""
        return f"\n  AND {severity_column} = '{matched_severity}'"

    @staticmethod
    def _detect_priority_value(normalized_query: str) -> str | None:
        """Find a concrete priority value mentioned in the query."""
        for phrase, mapped_value in _LIST_PRIORITY_VALUES.items():
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized_query):
                return mapped_value
        return None

    @staticmethod
    def _build_list_order_by(query_context: QueryContext, metric: dict[str, str | bool | list[str]]) -> str:
        """Build ORDER BY for deterministic list queries."""
        normalized_query = query_context.normalized_query
        scope_alias = str(metric["scope_alias"])
        for phrase, column_name in _LIST_SORT_KEYWORDS.items():
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized_query) and re.search(r"\bsort(?:ed)?\s+by\b|\border\s+by\b", normalized_query):
                direction = "ASC" if re.search(r"\basc|ascending\b", normalized_query) else "DESC"
                return f"{scope_alias}.{column_name} {direction}"
        return str(metric["default_order"])

    @staticmethod
    def _build_list_limit_clause(query_context: QueryContext) -> int:
        """Build LIMIT for deterministic list queries."""
        match = re.search(r"\b(?:top|first|limit)\s+(\d{1,3})\b", query_context.normalized_query)
        if not match:
            return 100
        return max(1, min(int(match.group(1)), 100))

    @staticmethod
    def _detect_status_value(normalized_query: str, allowed_values: list[str]) -> str | None:
        """Find a concrete status name mentioned in the query."""
        for allowed_value in allowed_values:
            patterns = {allowed_value.lower(), allowed_value.lower().replace("_", " ")}
            for pattern in patterns:
                if re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", normalized_query):
                    return allowed_value
        return None

    @staticmethod
    def _build_answer(query_context: QueryContext, result: dict[str, Any]) -> str:
        """Summarize executed results in a chat-friendly sentence."""
        if not result.get("executed"):
            return ""

        rows = result.get("results") or []
        if not rows:
            return "I did not find any matching records in the current scope."

        entity_metric = _ENTITY_QUERY_FALLBACKS.get(query_context.entity or "")
        if (
            query_context.intent == "count"
            and entity_metric is not None
            and len(rows) == 1
            and str(entity_metric["count_alias"]) in rows[0]
        ):
            count_value = rows[0][str(entity_metric["count_alias"])]
            label = str(entity_metric["singular_label"] if count_value == 1 else entity_metric["plural_label"])
            scope_label = "selected project" if query_context.project_id is not None else "selected program"
            return f"There {'is' if count_value == 1 else 'are'} {count_value} {label} in the {scope_label}."

        if query_context.intent == "list":
            scope_label = "current scope"
            return f"I found {result.get('row_count', len(rows))} matching rows in the {scope_label}."

        if query_context.intent == "count" and len(rows) == 1 and len(rows[0]) == 1:
            count_value = next(iter(rows[0].values()))
            return f"The current query returned {count_value}."

        return f"I found {result.get('row_count', len(rows))} matching rows."

    # ── Prompt Building ───────────────────────────────────────────────────

    def _build_prompt(self, query_context: QueryContext) -> list[dict]:
        """Build chat messages for the LLM using the canonical in-code schema context."""
        glossary_ctx = ""
        if query_context.glossary_matches:
            glossary_ctx = "\n\nDetected SAP terms:\n" + "\n".join(
                f"- \"{m['term']}\": {m.get('alias', m.get('table', m.get('column', '')))}"
                for m in query_context.glossary_matches
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
            "7. Prefer exact existing table and column names from the schema context.\n"
            "8. If the query looks like a simple count/list/filter question, generate the simplest valid SQL that answers it.\n"
            "7. Return valid JSON: {\"sql\": \"...\", \"explanation\": \"...\", \"confidence\": 0.0-1.0}\n"
            f"{glossary_ctx}"
        )

        user = f"Convert to SQL:\n\nQuery: {query_context.original_query}"
        if query_context.program_id:
            user += f"\nProgram ID: {query_context.program_id}"
        if query_context.project_id:
            user += f"\nProject ID: {query_context.project_id}"

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    @staticmethod
    def _build_guidance_response(query_context: QueryContext, reason: str | None = None) -> dict:
        """Return a non-failing response for unsupported or noisy questions."""
        base_suggestions = [
            "How many open defects are there?",
            "Requirements by fit/gap status",
            "How many requirements are under SD workshops?",
            "How many test cases are related to MM module?",
            "How many RFCs do we have in this project?",
        ]
        entity_hint = query_context.entity.replace("_", " ") if query_context.entity else "program data"
        explanation = (
            f"I could not map this question to a safe SQL pattern yet. Try rephrasing it as a count, list, or distribution query about {entity_hint}."
        )
        if reason:
            explanation += f" Technical detail: {reason}."

        return {
            "sql": None,
            "explanation": explanation,
            "confidence": 0.2,
            "error": None,
            "answer": explanation,
            "suggestions": base_suggestions,
        }

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
