"""
SAP Transformation Management Platform
AI Assistants package — Sprint 8.

Assistants:
    - nl_query: Natural Language → SQL query assistant
    - requirement_analyst: Fit/Gap classification + similarity search
    - defect_triage: Severity suggestion + duplicate detection
"""

from app.ai.assistants.nl_query import NLQueryAssistant, validate_sql, sanitize_sql
from app.ai.assistants.requirement_analyst import RequirementAnalyst
from app.ai.assistants.defect_triage import DefectTriage

__all__ = [
    "NLQueryAssistant",
    "RequirementAnalyst",
    "DefectTriage",
    "validate_sql",
    "sanitize_sql",
]