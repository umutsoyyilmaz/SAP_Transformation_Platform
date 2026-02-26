"""
Governance Rules Registry — WR-1.1

Central governance rules, thresholds, block/warn conditions, and RACI template.
Does not touch lifecycle services — layers on top of them.

Usage:
    from app.services.governance_rules import GovernanceRules
    result = GovernanceRules.evaluate("workshop_complete", context)
    # -> {"allowed": True, "warnings": [...], "blocks": [...]}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═════════════════════════════════════════════════════════════════════════════

class Severity(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    INFO = "info"


class RACIRole(str, Enum):
    """RACI role-based approval chain."""
    RESPONSIBLE = "responsible"
    ACCOUNTABLE = "accountable"
    CONSULTED = "consulted"
    INFORMED = "informed"


@dataclass
class GovernanceViolation:
    """Single governance rule violation."""
    rule_id: str
    severity: Severity
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class GovernanceResult:
    """Aggregate result of evaluating all governance rules for a gate."""
    gate: str
    allowed: bool
    violations: list[GovernanceViolation] = field(default_factory=list)

    @property
    def blocks(self) -> list[dict]:
        return [v.to_dict() for v in self.violations if v.severity == Severity.BLOCK]

    @property
    def warnings(self) -> list[dict]:
        return [v.to_dict() for v in self.violations if v.severity == Severity.WARN]

    @property
    def infos(self) -> list[dict]:
        return [v.to_dict() for v in self.violations if v.severity == Severity.INFO]

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "allowed": self.allowed,
            "blocks": self.blocks,
            "warnings": self.warnings,
            "infos": self.infos,
        }


# ═════════════════════════════════════════════════════════════════════════════
# Threshold Configuration — managed from a single location
# ═════════════════════════════════════════════════════════════════════════════

THRESHOLDS: dict[str, Any] = {
    # Workshop completion gates
    "ws_complete_max_open_p1_oi": 0,          # P1 OI limit: 0 = none allowed
    "ws_complete_max_open_p2_oi": 5,          # P2 OI soft warning threshold
    "ws_complete_min_step_assessment_pct": 100,  # Final session: 100% assessed required
    "ws_complete_max_unresolved_flags": 0,    # Cross-module flag: 0 = all must be resolved

    # Requirement approval gates
    "req_approve_blocking_oi_allowed": False,  # Approval blocked if blocking OI exists
    "req_approve_min_description_len": 20,     # Min description length

    # L3 sign-off gates
    "signoff_require_all_l4_assessed": True,
    "signoff_require_p1_oi_closed": True,
    "signoff_require_reqs_approved": True,

    # Escalation thresholds
    "oi_aging_warn_days": 7,                  # OI open 7 days -> warning
    "oi_aging_escalate_days": 14,             # OI open 14 days -> escalation
    "gap_ratio_warn_pct": 30,                 # Gap ratio > 30% -> warning
    "gap_ratio_escalate_pct": 50,             # Gap ratio > 50% -> escalation
    "req_coverage_warn_pct": 70,              # Req coverage < 70% -> warning
    "req_coverage_escalate_pct": 50,          # Req coverage < 50% -> escalation

    # Metrics health RAG thresholds
    "health_green_min_pct": 80,
    "health_amber_min_pct": 60,
}


# ═════════════════════════════════════════════════════════════════════════════
# RACI Template — role-based approval chain
# ═════════════════════════════════════════════════════════════════════════════

RACI_TEMPLATES: dict[str, dict[str, RACIRole]] = {
    "workshop_complete": {
        "process_owner": RACIRole.ACCOUNTABLE,
        "facilitator": RACIRole.RESPONSIBLE,
        "consultant": RACIRole.CONSULTED,
        "project_manager": RACIRole.INFORMED,
    },
    "requirement_approve": {
        "process_owner": RACIRole.ACCOUNTABLE,
        "business_analyst": RACIRole.RESPONSIBLE,
        "solution_architect": RACIRole.CONSULTED,
        "project_manager": RACIRole.INFORMED,
    },
    "l3_signoff": {
        "process_owner": RACIRole.ACCOUNTABLE,
        "solution_architect": RACIRole.RESPONSIBLE,
        "functional_consultant": RACIRole.CONSULTED,
        "project_manager": RACIRole.INFORMED,
    },
    "scope_change": {
        "steering_committee": RACIRole.ACCOUNTABLE,
        "project_manager": RACIRole.RESPONSIBLE,
        "process_owner": RACIRole.CONSULTED,
        "solution_architect": RACIRole.INFORMED,
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# Rule Definitions — gate-specific rule functions
# ═════════════════════════════════════════════════════════════════════════════

def _rules_workshop_complete(ctx: dict) -> list[GovernanceViolation]:
    """Workshop completion rules.

    Expected ctx keys:
        is_final_session: bool
        total_steps: int
        unassessed_steps: int
        open_p1_oi_count: int
        open_p2_oi_count: int
        unresolved_flag_count: int
        force: bool
    """
    violations = []
    is_final = ctx.get("is_final_session", False)
    force = ctx.get("force", False)

    # RULE-WC-01: All steps must be assessed in the final session
    total = ctx.get("total_steps", 0)
    unassessed = ctx.get("unassessed_steps", 0)
    if is_final and total > 0:
        assessed_pct = ((total - unassessed) / total) * 100
        min_pct = THRESHOLDS["ws_complete_min_step_assessment_pct"]
        if assessed_pct < min_pct:
            sev = Severity.WARN if force else Severity.BLOCK
            violations.append(GovernanceViolation(
                rule_id="RULE-WC-01",
                severity=sev,
                message=f"{unassessed}/{total} process steps not assessed"
                        f" ({assessed_pct:.0f}% < {min_pct}% required)",
                details={"unassessed": unassessed, "total": total,
                         "assessed_pct": round(assessed_pct, 1)},
            ))
    elif not is_final and unassessed > 0:
        violations.append(GovernanceViolation(
            rule_id="RULE-WC-01",
            severity=Severity.INFO,
            message=f"{unassessed} steps deferred to next session",
            details={"unassessed": unassessed},
        ))

    # RULE-WC-02: P1 open items must be closed
    p1_count = ctx.get("open_p1_oi_count", 0)
    max_p1 = THRESHOLDS["ws_complete_max_open_p1_oi"]
    if p1_count > max_p1:
        violations.append(GovernanceViolation(
            rule_id="RULE-WC-02",
            severity=Severity.BLOCK if not force else Severity.WARN,
            message=f"{p1_count} P1 open item(s) still unresolved",
            details={"p1_open": p1_count, "threshold": max_p1},
        ))

    # RULE-WC-03: P2 open item soft warning
    p2_count = ctx.get("open_p2_oi_count", 0)
    max_p2 = THRESHOLDS["ws_complete_max_open_p2_oi"]
    if p2_count > max_p2:
        violations.append(GovernanceViolation(
            rule_id="RULE-WC-03",
            severity=Severity.WARN,
            message=f"{p2_count} P2 open item(s) exceed threshold ({max_p2})",
            details={"p2_open": p2_count, "threshold": max_p2},
        ))

    # RULE-WC-04: Unresolved cross-module flags
    flag_count = ctx.get("unresolved_flag_count", 0)
    max_flags = THRESHOLDS["ws_complete_max_unresolved_flags"]
    if flag_count > max_flags:
        violations.append(GovernanceViolation(
            rule_id="RULE-WC-04",
            severity=Severity.WARN,
            message=f"{flag_count} unresolved cross-module flag(s)",
            details={"unresolved_flags": flag_count},
        ))

    return violations


def _rules_requirement_approve(ctx: dict) -> list[GovernanceViolation]:
    """Requirement approval rules.

    Expected ctx keys:
        blocking_oi_ids: list[str]
        description_length: int
    """
    violations = []

    # RULE-RA-01: Blocking OI check
    blocking = ctx.get("blocking_oi_ids", [])
    if blocking and not THRESHOLDS["req_approve_blocking_oi_allowed"]:
        violations.append(GovernanceViolation(
            rule_id="RULE-RA-01",
            severity=Severity.BLOCK,
            message=f"{len(blocking)} blocking open item(s) must be resolved first",
            details={"blocking_oi_ids": blocking},
        ))

    # RULE-RA-02: Minimum description length
    desc_len = ctx.get("description_length", 0)
    min_len = THRESHOLDS["req_approve_min_description_len"]
    if desc_len < min_len:
        violations.append(GovernanceViolation(
            rule_id="RULE-RA-02",
            severity=Severity.WARN,
            message=f"Requirement description too short ({desc_len} < {min_len} chars)",
            details={"description_length": desc_len, "min_required": min_len},
        ))

    return violations


def _rules_l3_signoff(ctx: dict) -> list[GovernanceViolation]:
    """L3 sign-off rules.

    Expected ctx keys:
        unassessed_l4_count: int
        p1_open_count: int
        unapproved_req_count: int
    """
    violations = []

    # RULE-SO-01: All L4 assessed
    unassessed = ctx.get("unassessed_l4_count", 0)
    if unassessed > 0 and THRESHOLDS["signoff_require_all_l4_assessed"]:
        violations.append(GovernanceViolation(
            rule_id="RULE-SO-01",
            severity=Severity.BLOCK,
            message=f"{unassessed} L4 process level(s) not yet assessed",
            details={"unassessed_l4": unassessed},
        ))

    # RULE-SO-02: P1 OI closed
    p1_open = ctx.get("p1_open_count", 0)
    if p1_open > 0 and THRESHOLDS["signoff_require_p1_oi_closed"]:
        violations.append(GovernanceViolation(
            rule_id="RULE-SO-02",
            severity=Severity.BLOCK,
            message=f"{p1_open} P1 open item(s) still unresolved",
            details={"p1_open": p1_open},
        ))

    # RULE-SO-03: Requirement'lar approved/deferred
    unapproved = ctx.get("unapproved_req_count", 0)
    if unapproved > 0 and THRESHOLDS["signoff_require_reqs_approved"]:
        violations.append(GovernanceViolation(
            rule_id="RULE-SO-03",
            severity=Severity.BLOCK,
            message=f"{unapproved} requirement(s) not yet approved or deferred",
            details={"unapproved_reqs": unapproved},
        ))

    # RULE-SO-04: Formal sign-off record must exist for this entity.
    # When callers provide tenant_id, program_id, entity_type, and entity_id in ctx,
    # we verify a SignoffRecord with action='approved' exists before allowing the gate.
    # This is backward-compatible — old callers that omit these keys skip the rule.
    tenant_id = ctx.get("tenant_id")
    program_id = ctx.get("program_id")
    entity_type = ctx.get("entity_type")
    entity_id = ctx.get("entity_id")
    if tenant_id and program_id and entity_type and entity_id:
        try:
            from app.services.signoff_service import is_entity_approved  # local import avoids circular dependency
            if not is_entity_approved(tenant_id, program_id, entity_type, str(entity_id)):
                violations.append(GovernanceViolation(
                    rule_id="RULE-SO-04",
                    severity=Severity.BLOCK,
                    message=(
                        f"{entity_type} '{entity_id}' has no formal sign-off record. "
                        "An approver must approve this entity before the gate can proceed."
                    ),
                    details={"entity_type": entity_type, "entity_id": str(entity_id)},
                ))
        except Exception:
            # Non-fatal: log and continue rather than blocking all gate evaluations
            # if the signoff table is not yet migrated (e.g., during first deploy).
            logger.warning(
                "RULE-SO-04 signoff check failed for entity_type=%s entity_id=%s — skipping",
                entity_type,
                entity_id,
                exc_info=True,
            )

    return violations


# ═════════════════════════════════════════════════════════════════════════════
# Gate Registry — maps gate names to rule functions
# ═════════════════════════════════════════════════════════════════════════════

_GATE_RULES: dict[str, callable] = {
    "workshop_complete": _rules_workshop_complete,
    "requirement_approve": _rules_requirement_approve,
    "l3_signoff": _rules_l3_signoff,
}


# ═════════════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════════════

class GovernanceRules:
    """Central governance rule evaluation engine."""

    @staticmethod
    def evaluate(gate: str, context: dict) -> GovernanceResult:
        """Run all rules for the specified gate.

        Args:
            gate: Gate name (workshop_complete, requirement_approve, l3_signoff)
            context: Context dict expected by the rule functions

        Returns:
            GovernanceResult — allowed=True means the operation can proceed
        """
        rule_fn = _GATE_RULES.get(gate)
        if not rule_fn:
            return GovernanceResult(gate=gate, allowed=True)

        violations = rule_fn(context)
        has_blocks = any(v.severity == Severity.BLOCK for v in violations)

        return GovernanceResult(
            gate=gate,
            allowed=not has_blocks,
            violations=violations,
        )

    @staticmethod
    def get_threshold(key: str, default=None):
        """Read a single threshold value."""
        return THRESHOLDS.get(key, default)

    @staticmethod
    def get_all_thresholds() -> dict:
        """Return all thresholds."""
        return dict(THRESHOLDS)

    @staticmethod
    def update_threshold(key: str, value) -> bool:
        """Update a threshold at runtime (valid until restart)."""
        if key in THRESHOLDS:
            THRESHOLDS[key] = value
            return True
        return False

    @staticmethod
    def get_raci(gate: str) -> dict[str, str] | None:
        """Return the RACI template for a gate."""
        template = RACI_TEMPLATES.get(gate)
        if not template:
            return None
        return {role: raci.value for role, raci in template.items()}

    @staticmethod
    def list_gates() -> list[str]:
        """List all registered gates."""
        return list(_GATE_RULES.keys())

    @staticmethod
    def list_rules() -> list[dict]:
        """List rule IDs and descriptions for all gates."""
        rules = []
        for gate_name, rule_fn in _GATE_RULES.items():
            rules.append({
                "gate": gate_name,
                "description": (rule_fn.__doc__ or "").strip().split("\n")[0],
                "raci": GovernanceRules.get_raci(gate_name),
            })
        return rules
