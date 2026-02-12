"""
SAP Transformation Management Platform
AI Assistants package — Sprint 19 + S21 Final.

Assistants:
    - nl_query: Natural Language → SQL query assistant
    - requirement_analyst: Fit/Gap classification + similarity search
    - defect_triage: Severity suggestion + duplicate detection
    - risk_assessment: Project signal analysis + risk identification
    - test_case_generator: Requirement → test case generation
    - change_impact: Change impact analysis across modules
    - cutover_optimizer: Cutover runbook optimization + go/no-go assessment (Sprint 15)
    - meeting_minutes: Meeting minutes generation + action item extraction (Sprint 15)
    - steering_pack: Steering committee briefing pack generator (Sprint 19)
    - wricef_spec: WRICEF functional spec drafter (Sprint 19)
    - data_quality: Data quality analysis & cleansing advisor (Sprint 19)
    - data_migration: Data migration advisor — wave planning & reconciliation (Sprint 21)
    - integration_analyst: Integration dependency analyzer & switch-plan validator (Sprint 21)
"""

from app.ai.assistants.nl_query import NLQueryAssistant, validate_sql, sanitize_sql
from app.ai.assistants.requirement_analyst import RequirementAnalyst
from app.ai.assistants.defect_triage import DefectTriage
from app.ai.assistants.risk_assessment import RiskAssessment
from app.ai.assistants.test_case_generator import TestCaseGenerator
from app.ai.assistants.change_impact import ChangeImpactAnalyzer
from app.ai.assistants.cutover_optimizer import CutoverOptimizer
from app.ai.assistants.meeting_minutes import MeetingMinutesAssistant
from app.ai.assistants.steering_pack import SteeringPackGenerator
from app.ai.assistants.wricef_spec import WRICEFSpecDrafter
from app.ai.assistants.data_quality import DataQualityGuardian
from app.ai.assistants.data_migration import DataMigrationAdvisor
from app.ai.assistants.integration_analyst import IntegrationAnalyst

__all__ = [
    "NLQueryAssistant",
    "RequirementAnalyst",
    "DefectTriage",
    "RiskAssessment",
    "TestCaseGenerator",
    "ChangeImpactAnalyzer",
    "CutoverOptimizer",
    "MeetingMinutesAssistant",
    "SteeringPackGenerator",
    "WRICEFSpecDrafter",
    "DataQualityGuardian",
    "DataMigrationAdvisor",
    "IntegrationAnalyst",
    "validate_sql",
    "sanitize_sql",
]