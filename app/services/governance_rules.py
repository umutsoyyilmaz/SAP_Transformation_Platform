"""
Governance Rules Registry — WR-1.1

Merkezi governance kuralları, threshold'lar, block/warn koşulları ve RACI template.
Lifecycle servislerine dokunmaz — üzerlerine eklenir.

Kullanım:
    from app.services.governance_rules import GovernanceRules
    result = GovernanceRules.evaluate("workshop_complete", context)
    # → {"allowed": True, "warnings": [...], "blocks": [...]}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
# Threshold Configuration — tek yerden yönetilir
# ═════════════════════════════════════════════════════════════════════════════

THRESHOLDS: dict[str, Any] = {
    # Workshop completion gates
    "ws_complete_max_open_p1_oi": 0,          # P1 OI limiti: 0 = hiç olmamalı
    "ws_complete_max_open_p2_oi": 5,          # P2 OI soft warning sınırı
    "ws_complete_min_step_assessment_pct": 100,  # Final session: %100 assessed gerekli
    "ws_complete_max_unresolved_flags": 0,    # Cross-module flag: 0 = hepsi resolved

    # Requirement approval gates
    "req_approve_blocking_oi_allowed": False,  # Blocking OI varsa onay engellenir
    "req_approve_min_description_len": 20,     # Min açıklama uzunluğu

    # L3 sign-off gates
    "signoff_require_all_l4_assessed": True,
    "signoff_require_p1_oi_closed": True,
    "signoff_require_reqs_approved": True,

    # Escalation thresholds
    "oi_aging_warn_days": 7,                  # OI 7 gün açık → warning
    "oi_aging_escalate_days": 14,             # OI 14 gün açık → escalation
    "gap_ratio_warn_pct": 30,                 # Gap ratio > %30 → warning
    "gap_ratio_escalate_pct": 50,             # Gap ratio > %50 → escalation
    "req_coverage_warn_pct": 70,              # Req coverage < %70 → warning
    "req_coverage_escalate_pct": 50,          # Req coverage < %50 → escalation

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
# Rule Definitions — gate-specific rule fonksiyonları
# ═════════════════════════════════════════════════════════════════════════════

def _rules_workshop_complete(ctx: dict) -> list[GovernanceViolation]:
    """Workshop tamamlama kuralları.

    ctx beklenen anahtarlar:
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

    # RULE-WC-01: Final session'da tüm step'ler assessed olmalı
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

    # RULE-WC-02: P1 open item'lar kapatılmış olmalı
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
    """Requirement onaylama kuralları.

    ctx beklenen anahtarlar:
        blocking_oi_ids: list[str]
        description_length: int
    """
    violations = []

    # RULE-RA-01: Blocking OI kontrolü
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
    """L3 sign-off kuralları.

    ctx beklenen anahtarlar:
        unassessed_l4_count: int
        p1_open_count: int
        unapproved_req_count: int
    """
    violations = []

    # RULE-SO-01: Tüm L4 assessed
    unassessed = ctx.get("unassessed_l4_count", 0)
    if unassessed > 0 and THRESHOLDS["signoff_require_all_l4_assessed"]:
        violations.append(GovernanceViolation(
            rule_id="RULE-SO-01",
            severity=Severity.BLOCK,
            message=f"{unassessed} L4 process level(s) not yet assessed",
            details={"unassessed_l4": unassessed},
        ))

    # RULE-SO-02: P1 OI kapalı
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

    return violations


# ═════════════════════════════════════════════════════════════════════════════
# Gate Registry — gate adlarını kural fonksiyonlarıyla eşler
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
    """Merkezi governance kural değerlendirme motoru."""

    @staticmethod
    def evaluate(gate: str, context: dict) -> GovernanceResult:
        """Belirtilen gate için tüm kuralları çalıştır.

        Args:
            gate: Gate adı (workshop_complete, requirement_approve, l3_signoff)
            context: Rule fonksiyonlarının beklediği context dict

        Returns:
            GovernanceResult — allowed=True ise işlem devam edebilir
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
        """Tek bir threshold değeri oku."""
        return THRESHOLDS.get(key, default)

    @staticmethod
    def get_all_thresholds() -> dict:
        """Tüm threshold'ları döndür."""
        return dict(THRESHOLDS)

    @staticmethod
    def update_threshold(key: str, value) -> bool:
        """Runtime'da threshold güncelle (restart'a kadar geçerli)."""
        if key in THRESHOLDS:
            THRESHOLDS[key] = value
            return True
        return False

    @staticmethod
    def get_raci(gate: str) -> dict[str, str] | None:
        """Gate için RACI template döndür."""
        template = RACI_TEMPLATES.get(gate)
        if not template:
            return None
        return {role: raci.value for role, raci in template.items()}

    @staticmethod
    def list_gates() -> list[str]:
        """Kayıtlı tüm gate'leri listele."""
        return list(_GATE_RULES.keys())

    @staticmethod
    def list_rules() -> list[dict]:
        """Tüm gate'lerin kural ID'lerini ve açıklamalarını listele."""
        rules = []
        for gate_name, rule_fn in _GATE_RULES.items():
            rules.append({
                "gate": gate_name,
                "description": (rule_fn.__doc__ or "").strip().split("\n")[0],
                "raci": GovernanceRules.get_raci(gate_name),
            })
        return rules
