"""
SAP Transformation Management Platform
AI Assistants package — Sprint 12.

Assistants:
    - nl_query: Natural Language → SQL query assistant
    - requirement_analyst: Fit/Gap classification + similarity search
    - defect_triage: Severity suggestion + duplicate detection
    - risk_assessment: Project signal analysis + risk identification
    - test_case_generator: Requirement → test case generation
    - change_impact: Change impact analysis across modules
"""

from app.ai.assistants.nl_query import NLQueryAssistant, validate_sql, sanitize_sql
from app.ai.assistants.requirement_analyst import RequirementAnalyst
from app.ai.assistants.defect_triage import DefectTriage
from app.ai.assistants.risk_assessment import RiskAssessment
from app.ai.assistants.test_case_generator import TestCaseGenerator
from app.ai.assistants.change_impact import ChangeImpactAnalyzer

__all__ = [
    "NLQueryAssistant",
    "RequirementAnalyst",
    "DefectTriage",
    "RiskAssessment",
    "TestCaseGenerator",
    "ChangeImpactAnalyzer",
    "validate_sql",
    "sanitize_sql",
]