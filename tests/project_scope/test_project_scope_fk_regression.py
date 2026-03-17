"""FK target regression tests for Program/Project scope migration.

Validates that every model's project_id and program_id columns reference
the correct table (projects vs programs).  This test suite establishes
the baseline and tracks migration progress across phases.

Phase 0: Tests document the CURRENT state (some will xfail for known bugs).
Phase 1+: As FK targets are fixed, xfail markers are removed.
"""

import pytest

from app.models import db


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_fk_target(model_class, column_name: str) -> str | None:
    """Return the FK target table.column for a given model column.

    Returns e.g. 'programs.id' or 'projects.id', or None if no FK.
    """
    col = getattr(model_class, column_name, None)
    if col is None:
        return None
    prop = col.property
    for c in prop.columns:
        for fk in c.foreign_keys:
            return fk.target_fullname
    return None


def _has_column(model_class, column_name: str) -> bool:
    """Check if a model has a given column."""
    return hasattr(model_class, column_name) and hasattr(
        getattr(model_class, column_name), "property"
    )


# ── Tests: Models where project_id CORRECTLY points to projects.id ──────────


class TestCorrectProjectIdFK:
    """Models whose project_id already correctly references projects.id."""

    def test_user_role_project_id(self, app):
        from app.models.auth import UserRole
        with app.app_context():
            assert _get_fk_target(UserRole, "project_id") == "projects.id"

    def test_audit_log_project_id(self, app):
        from app.models.audit import AuditLog
        with app.app_context():
            assert _get_fk_target(AuditLog, "project_id") == "projects.id"

    def test_process_step_project_id(self, app):
        """ProcessStep has dual FKs: program_id -> programs, project_id -> projects."""
        from app.models.explore.process import ProcessStep
        with app.app_context():
            assert _get_fk_target(ProcessStep, "project_id") == "projects.id"
            assert _get_fk_target(ProcessStep, "program_id") == "programs.id"

    def test_workshop_scope_item_dual_fks(self, app):
        from app.models.explore.workshop import WorkshopScopeItem
        with app.app_context():
            assert _get_fk_target(WorkshopScopeItem, "project_id") == "projects.id"
            assert _get_fk_target(WorkshopScopeItem, "program_id") == "programs.id"

    def test_workshop_attendee_dual_fks(self, app):
        from app.models.explore.workshop import WorkshopAttendee
        with app.app_context():
            assert _get_fk_target(WorkshopAttendee, "project_id") == "projects.id"
            assert _get_fk_target(WorkshopAttendee, "program_id") == "programs.id"

    def test_workshop_agenda_item_dual_fks(self, app):
        from app.models.explore.workshop import WorkshopAgendaItem
        with app.app_context():
            assert _get_fk_target(WorkshopAgendaItem, "project_id") == "projects.id"
            assert _get_fk_target(WorkshopAgendaItem, "program_id") == "programs.id"

    def test_requirement_open_item_link_dual_fks(self, app):
        from app.models.explore.requirement import RequirementOpenItemLink
        with app.app_context():
            assert _get_fk_target(RequirementOpenItemLink, "project_id") == "projects.id"
            assert _get_fk_target(RequirementOpenItemLink, "program_id") == "programs.id"

    def test_requirement_dependency_dual_fks(self, app):
        from app.models.explore.requirement import RequirementDependency
        with app.app_context():
            assert _get_fk_target(RequirementDependency, "project_id") == "projects.id"
            assert _get_fk_target(RequirementDependency, "program_id") == "programs.id"

    def test_open_item_comment_dual_fks(self, app):
        from app.models.explore.requirement import OpenItemComment
        with app.app_context():
            assert _get_fk_target(OpenItemComment, "project_id") == "projects.id"
            assert _get_fk_target(OpenItemComment, "program_id") == "programs.id"


# ── Tests: Models where project_id was FIXED in Faz 1.4 ─────────────────────
# These models had project_id FK → programs.id (naming bug).
# Faz 1.4 Migration B re-pointed them to projects.id.


class TestFixedProjectIdFK:
    """Models whose project_id was fixed from programs.id → projects.id (Faz 1.4)."""

    def test_process_level_project_id(self, app):
        from app.models.explore.process import ProcessLevel
        with app.app_context():
            assert _get_fk_target(ProcessLevel, "project_id") == "projects.id"

    def test_explore_workshop_project_id(self, app):
        from app.models.explore.workshop import ExploreWorkshop
        with app.app_context():
            assert _get_fk_target(ExploreWorkshop, "project_id") == "projects.id"

    def test_explore_decision_project_id(self, app):
        from app.models.explore.requirement import ExploreDecision
        with app.app_context():
            assert _get_fk_target(ExploreDecision, "project_id") == "projects.id"

    def test_explore_open_item_project_id(self, app):
        from app.models.explore.requirement import ExploreOpenItem
        with app.app_context():
            assert _get_fk_target(ExploreOpenItem, "project_id") == "projects.id"

    def test_explore_requirement_project_id(self, app):
        from app.models.explore.requirement import ExploreRequirement
        with app.app_context():
            assert _get_fk_target(ExploreRequirement, "project_id") == "projects.id"

    def test_attachment_project_id(self, app):
        from app.models.explore.infrastructure import Attachment
        with app.app_context():
            assert _get_fk_target(Attachment, "project_id") == "projects.id"

    def test_project_role_project_id(self, app):
        from app.models.explore.governance import ProjectRole
        with app.app_context():
            assert _get_fk_target(ProjectRole, "project_id") == "projects.id"

    def test_phase_gate_project_id(self, app):
        from app.models.explore.governance import PhaseGate
        with app.app_context():
            assert _get_fk_target(PhaseGate, "project_id") == "projects.id"

    def test_scope_change_request_project_id(self, app):
        from app.models.explore.governance import ScopeChangeRequest
        with app.app_context():
            assert _get_fk_target(ScopeChangeRequest, "project_id") == "projects.id"

    def test_scope_change_log_project_id(self, app):
        from app.models.explore.governance import ScopeChangeLog
        with app.app_context():
            assert _get_fk_target(ScopeChangeLog, "project_id") == "projects.id"

    def test_process_variant_import_project_id(self, app):
        from app.models.process_mining import ProcessVariantImport
        with app.app_context():
            assert _get_fk_target(ProcessVariantImport, "project_id") == "projects.id"


# ── Tests: Models that need program_id added (Faz 1.1) ─────────────────────
# These models currently only have project_id (which actually means program_id).
# After Faz 1, they should have a proper program_id column.


class TestMissingProgramId:
    """Models that now have a program_id column (Faz 1.1 complete)."""

    def test_process_level_has_program_id(self, app):
        from app.models.explore.process import ProcessLevel
        with app.app_context():
            assert _has_column(ProcessLevel, "program_id")
            assert _get_fk_target(ProcessLevel, "program_id") == "programs.id"

    def test_explore_workshop_has_program_id(self, app):
        from app.models.explore.workshop import ExploreWorkshop
        with app.app_context():
            assert _has_column(ExploreWorkshop, "program_id")
            assert _get_fk_target(ExploreWorkshop, "program_id") == "programs.id"

    def test_explore_decision_has_program_id(self, app):
        from app.models.explore.requirement import ExploreDecision
        with app.app_context():
            assert _has_column(ExploreDecision, "program_id")
            assert _get_fk_target(ExploreDecision, "program_id") == "programs.id"

    def test_explore_open_item_has_program_id(self, app):
        from app.models.explore.requirement import ExploreOpenItem
        with app.app_context():
            assert _has_column(ExploreOpenItem, "program_id")
            assert _get_fk_target(ExploreOpenItem, "program_id") == "programs.id"

    def test_explore_requirement_has_program_id(self, app):
        from app.models.explore.requirement import ExploreRequirement
        with app.app_context():
            assert _has_column(ExploreRequirement, "program_id")
            assert _get_fk_target(ExploreRequirement, "program_id") == "programs.id"

    def test_attachment_has_program_id(self, app):
        from app.models.explore.infrastructure import Attachment
        with app.app_context():
            assert _has_column(Attachment, "program_id")
            assert _get_fk_target(Attachment, "program_id") == "programs.id"

    def test_project_role_has_program_id(self, app):
        from app.models.explore.governance import ProjectRole
        with app.app_context():
            assert _has_column(ProjectRole, "program_id")
            assert _get_fk_target(ProjectRole, "program_id") == "programs.id"

    def test_phase_gate_has_program_id(self, app):
        from app.models.explore.governance import PhaseGate
        with app.app_context():
            assert _has_column(PhaseGate, "program_id")
            assert _get_fk_target(PhaseGate, "program_id") == "programs.id"

    def test_scope_change_request_has_program_id(self, app):
        from app.models.explore.governance import ScopeChangeRequest
        with app.app_context():
            assert _has_column(ScopeChangeRequest, "program_id")
            assert _get_fk_target(ScopeChangeRequest, "program_id") == "programs.id"

    def test_scope_change_log_has_program_id(self, app):
        from app.models.explore.governance import ScopeChangeLog
        with app.app_context():
            assert _has_column(ScopeChangeLog, "program_id")
            assert _get_fk_target(ScopeChangeLog, "program_id") == "programs.id"

    def test_process_variant_import_has_program_id(self, app):
        from app.models.process_mining import ProcessVariantImport
        with app.app_context():
            assert _has_column(ProcessVariantImport, "program_id")
            assert _get_fk_target(ProcessVariantImport, "program_id") == "programs.id"


# ── Tests: Program-scoped models that should stay at program level ──────────


class TestProgramScopedModels:
    """Models that correctly use program_id -> programs.id and should stay that way."""

    def test_phase_program_id(self, app):
        from app.models.program import Phase
        with app.app_context():
            assert _get_fk_target(Phase, "program_id") == "programs.id"

    def test_workstream_program_id(self, app):
        from app.models.program import Workstream
        with app.app_context():
            assert _get_fk_target(Workstream, "program_id") == "programs.id"

    def test_team_member_program_id(self, app):
        from app.models.program import TeamMember
        with app.app_context():
            assert _get_fk_target(TeamMember, "program_id") == "programs.id"

    def test_committee_program_id(self, app):
        from app.models.program import Committee
        with app.app_context():
            assert _get_fk_target(Committee, "program_id") == "programs.id"

    def test_project_charter_program_id(self, app):
        from app.models.program import ProjectCharter
        with app.app_context():
            assert _get_fk_target(ProjectCharter, "program_id") == "programs.id"

    def test_system_landscape_program_id(self, app):
        from app.models.program import SystemLandscape
        with app.app_context():
            assert _get_fk_target(SystemLandscape, "program_id") == "programs.id"

    def test_scope_assessment_program_id(self, app):
        from app.models.program import ScopeAssessment
        with app.app_context():
            assert _get_fk_target(ScopeAssessment, "program_id") == "programs.id"

    def test_raci_activity_program_id(self, app):
        from app.models.program import RaciActivity
        with app.app_context():
            assert _get_fk_target(RaciActivity, "program_id") == "programs.id"

    def test_raci_entry_program_id(self, app):
        from app.models.program import RaciEntry
        with app.app_context():
            assert _get_fk_target(RaciEntry, "program_id") == "programs.id"

    def test_stakeholder_program_id(self, app):
        from app.models.program import Stakeholder
        with app.app_context():
            assert _get_fk_target(Stakeholder, "program_id") == "programs.id"

    def test_communication_plan_program_id(self, app):
        from app.models.program import CommunicationPlanEntry
        with app.app_context():
            assert _get_fk_target(CommunicationPlanEntry, "program_id") == "programs.id"


# ── Tests: Operational models needing project_id (Faz 3) ───────────────────


class TestOperationalModelsHaveProjectId:
    """Models that gained project_id -> projects.id in Faz 3."""

    # ── Grup A: program.py models ──

    def test_phase_has_project_id(self, app):
        from app.models.program import Phase
        with app.app_context():
            assert _has_column(Phase, "project_id")
            assert _get_fk_target(Phase, "project_id") == "projects.id"

    def test_workstream_has_project_id(self, app):
        from app.models.program import Workstream
        with app.app_context():
            assert _has_column(Workstream, "project_id")
            assert _get_fk_target(Workstream, "project_id") == "projects.id"

    def test_team_member_has_project_id(self, app):
        from app.models.program import TeamMember
        with app.app_context():
            assert _has_column(TeamMember, "project_id")
            assert _get_fk_target(TeamMember, "project_id") == "projects.id"

    def test_committee_has_project_id(self, app):
        from app.models.program import Committee
        with app.app_context():
            assert _has_column(Committee, "project_id")
            assert _get_fk_target(Committee, "project_id") == "projects.id"

    def test_raci_activity_has_project_id(self, app):
        from app.models.program import RaciActivity
        with app.app_context():
            assert _has_column(RaciActivity, "project_id")
            assert _get_fk_target(RaciActivity, "project_id") == "projects.id"

    def test_raci_entry_has_project_id(self, app):
        from app.models.program import RaciEntry
        with app.app_context():
            assert _has_column(RaciEntry, "project_id")
            assert _get_fk_target(RaciEntry, "project_id") == "projects.id"

    # ── Grup B: scenario.py ──

    def test_scenario_has_project_id(self, app):
        from app.models.scenario import Scenario
        with app.app_context():
            assert _has_column(Scenario, "project_id")
            assert _get_fk_target(Scenario, "project_id") == "projects.id"

    # ── Grup C: backlog.py ──

    def test_sprint_has_project_id(self, app):
        from app.models.backlog import Sprint
        with app.app_context():
            assert _has_column(Sprint, "project_id")
            assert _get_fk_target(Sprint, "project_id") == "projects.id"

    def test_backlog_item_has_project_id(self, app):
        from app.models.backlog import BacklogItem
        with app.app_context():
            assert _has_column(BacklogItem, "project_id")
            assert _get_fk_target(BacklogItem, "project_id") == "projects.id"

    def test_config_item_has_project_id(self, app):
        from app.models.backlog import ConfigItem
        with app.app_context():
            assert _has_column(ConfigItem, "project_id")
            assert _get_fk_target(ConfigItem, "project_id") == "projects.id"

    # ── Grup D: testing.py ──

    def test_test_plan_has_project_id(self, app):
        from app.models.testing import TestPlan
        with app.app_context():
            assert _has_column(TestPlan, "project_id")
            assert _get_fk_target(TestPlan, "project_id") == "projects.id"

    def test_test_case_has_project_id(self, app):
        from app.models.testing import TestCase
        with app.app_context():
            assert _has_column(TestCase, "project_id")
            assert _get_fk_target(TestCase, "project_id") == "projects.id"

    def test_test_suite_has_project_id(self, app):
        from app.models.testing import TestSuite
        with app.app_context():
            assert _has_column(TestSuite, "project_id")
            assert _get_fk_target(TestSuite, "project_id") == "projects.id"

    def test_defect_has_project_id(self, app):
        from app.models.testing import Defect
        with app.app_context():
            assert _has_column(Defect, "project_id")
            assert _get_fk_target(Defect, "project_id") == "projects.id"

    def test_approval_workflow_has_project_id(self, app):
        from app.models.testing import ApprovalWorkflow
        with app.app_context():
            assert _has_column(ApprovalWorkflow, "project_id")
            assert _get_fk_target(ApprovalWorkflow, "project_id") == "projects.id"

    def test_test_daily_snapshot_has_project_id(self, app):
        from app.models.testing import TestDailySnapshot
        with app.app_context():
            assert _has_column(TestDailySnapshot, "project_id")
            assert _get_fk_target(TestDailySnapshot, "project_id") == "projects.id"

    # ── Grup E: cutover.py ──

    def test_cutover_plan_has_project_id(self, app):
        from app.models.cutover import CutoverPlan
        with app.app_context():
            assert _has_column(CutoverPlan, "project_id")
            assert _get_fk_target(CutoverPlan, "project_id") == "projects.id"

    def test_post_golive_change_request_has_project_id(self, app):
        from app.models.cutover import PostGoliveChangeRequest
        with app.app_context():
            assert _has_column(PostGoliveChangeRequest, "project_id")
            assert _get_fk_target(PostGoliveChangeRequest, "project_id") == "projects.id"

    # ── Grup F: raid.py ──

    def test_risk_has_project_id(self, app):
        from app.models.raid import Risk
        with app.app_context():
            assert _has_column(Risk, "project_id")
            assert _get_fk_target(Risk, "project_id") == "projects.id"

    def test_action_has_project_id(self, app):
        from app.models.raid import Action
        with app.app_context():
            assert _has_column(Action, "project_id")
            assert _get_fk_target(Action, "project_id") == "projects.id"

    def test_issue_has_project_id(self, app):
        from app.models.raid import Issue
        with app.app_context():
            assert _has_column(Issue, "project_id")
            assert _get_fk_target(Issue, "project_id") == "projects.id"

    def test_decision_has_project_id(self, app):
        from app.models.raid import Decision
        with app.app_context():
            assert _has_column(Decision, "project_id")
            assert _get_fk_target(Decision, "project_id") == "projects.id"

    # ── Grup G: requirement.py ──

    def test_requirement_has_project_id(self, app):
        from app.models.requirement import Requirement
        with app.app_context():
            assert _has_column(Requirement, "project_id")
            assert _get_fk_target(Requirement, "project_id") == "projects.id"


# ── Tests: Project model relationships (Faz 3) ─────────────────────────────


class TestProjectRelationships:
    """Project should have relationships to operational entities after Faz 3."""

    def test_project_has_program_fk(self, app):
        from app.models.project import Project
        with app.app_context():
            assert _get_fk_target(Project, "program_id") == "programs.id"

    def test_project_has_tenant_fk(self, app):
        from app.models.project import Project
        with app.app_context():
            assert _get_fk_target(Project, "tenant_id") == "tenants.id"

    def test_project_has_phases_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "phases")

    def test_project_has_workstreams_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "workstreams")

    def test_project_has_team_members_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "team_members")

    def test_project_has_committees_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "committees")

    def test_project_has_scenarios_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "scenarios")

    def test_project_has_sprints_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "sprints")

    def test_project_has_backlog_items_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "backlog_items")

    def test_project_has_config_items_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "config_items")

    def test_project_has_test_plans_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "test_plans")

    def test_project_has_test_cases_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "test_cases")

    def test_project_has_test_suites_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "test_suites")

    def test_project_has_defects_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "defects")

    def test_project_has_cutover_plans_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "cutover_plans")

    def test_project_has_requirements_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "requirements")

    def test_project_has_risks_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "risks")

    def test_project_has_raid_decisions_relationship(self, app):
        from app.models.project import Project
        with app.app_context():
            assert hasattr(Project, "raid_decisions")
