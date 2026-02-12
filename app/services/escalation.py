"""
Escalation & Alert Service — WR-1.3

Threshold aşımında alert üretir, dedup key ile spam engeller.
Mevcut NotificationService üzerinden notification oluşturur.

Kullanım:
    from app.services.escalation import EscalationService
    alerts = EscalationService.check_and_alert(project_id=1)
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Any

from app.models import db
from app.models.notification import Notification
from app.services.notification import NotificationService
from app.services.governance_rules import GovernanceRules, THRESHOLDS
from app.services.metrics import (
    compute_gap_ratio,
    compute_oi_aging,
    compute_requirement_coverage,
)


# ═════════════════════════════════════════════════════════════════════════════
# Dedup — prevent duplicate alerts within same day
# ═════════════════════════════════════════════════════════════════════════════

def _dedup_key(project_id: int, alert_type: str, entity_id: str = "") -> str:
    """Generate deterministic dedup key for an alert.

    Format: gov-{project_id}-{alert_type}-{entity_id}-{date}
    Same key within a day → duplicate → skip.
    """
    today = date.today().isoformat()
    raw = f"gov-{project_id}-{alert_type}-{entity_id}-{today}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _alert_exists(dedup_key: str) -> bool:
    """Aynı dedup key ile bugün notification var mı?"""
    today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    return (
        Notification.query
        .filter(
            Notification.message.contains(dedup_key),
            Notification.created_at >= today_start,
        )
        .first()
    ) is not None


# ═════════════════════════════════════════════════════════════════════════════
# Alert Generators
# ═════════════════════════════════════════════════════════════════════════════

def _check_oi_aging_alerts(project_id: int) -> list[dict]:
    """OI aging threshold aşımı kontrolü."""
    alerts = []
    oi_data = compute_oi_aging(project_id)

    # Escalation candidates (14+ days)
    for candidate in oi_data.get("escalation_candidates", []):
        alert_type = "oi_aging_escalate"
        entity_id = str(candidate["id"])
        dk = _dedup_key(project_id, alert_type, entity_id)

        if not _alert_exists(dk):
            alerts.append({
                "type": alert_type,
                "severity": "error",
                "category": "gate",
                "title": f"ESCALATION: Open Item {candidate.get('code', entity_id)} — {candidate['age_days']} days open",
                "message": f"[{dk}] {candidate['title']} has been open for {candidate['age_days']} days "
                           f"(threshold: {THRESHOLDS['oi_aging_escalate_days']}d). Priority: {candidate['priority']}",
                "entity_type": "open_item",
                "entity_id": candidate["id"],
            })

    # P1 open items warning
    if oi_data["p1_open"] > 0:
        dk = _dedup_key(project_id, "p1_oi_open")
        if not _alert_exists(dk):
            alerts.append({
                "type": "p1_oi_open",
                "severity": "warning",
                "category": "gate",
                "title": f"WARNING: {oi_data['p1_open']} P1 open item(s) unresolved",
                "message": f"[{dk}] {oi_data['p1_open']} P1 open items remain open. "
                           f"Total open: {oi_data['total_open']}, Overdue: {oi_data['overdue']}",
                "entity_type": "project",
                "entity_id": project_id,
            })

    # Overdue batch warning
    if oi_data["overdue"] > 0:
        dk = _dedup_key(project_id, "oi_overdue_batch")
        if not _alert_exists(dk):
            alerts.append({
                "type": "oi_overdue_batch",
                "severity": "warning",
                "category": "deadline",
                "title": f"WARNING: {oi_data['overdue']} overdue open item(s)",
                "message": f"[{dk}] {oi_data['overdue']} open items past due date. Avg age: {oi_data['avg_age_days']} days",
                "entity_type": "project",
                "entity_id": project_id,
            })

    return alerts


def _check_gap_ratio_alerts(project_id: int) -> list[dict]:
    """Gap ratio threshold kontrolü."""
    alerts = []
    gap_data = compute_gap_ratio(project_id)
    gap_ratio = gap_data["gap_ratio"]

    if gap_ratio >= THRESHOLDS["gap_ratio_escalate_pct"]:
        dk = _dedup_key(project_id, "gap_ratio_escalate")
        if not _alert_exists(dk):
            alerts.append({
                "type": "gap_ratio_escalate",
                "severity": "error",
                "category": "gate",
                "title": f"ESCALATION: Gap ratio {gap_ratio}% exceeds {THRESHOLDS['gap_ratio_escalate_pct']}%",
                "message": f"[{dk}] {gap_data['gap']} gaps out of {gap_data['assessed']} assessed steps. "
                           f"Fit: {gap_data['fit']}, Partial: {gap_data['partial_fit']}",
                "entity_type": "project",
                "entity_id": project_id,
            })
    elif gap_ratio >= THRESHOLDS["gap_ratio_warn_pct"]:
        dk = _dedup_key(project_id, "gap_ratio_warn")
        if not _alert_exists(dk):
            alerts.append({
                "type": "gap_ratio_warn",
                "severity": "warning",
                "category": "gate",
                "title": f"WARNING: Gap ratio {gap_ratio}% exceeds {THRESHOLDS['gap_ratio_warn_pct']}%",
                "message": f"[{dk}] {gap_data['gap']} gaps out of {gap_data['assessed']} assessed steps",
                "entity_type": "project",
                "entity_id": project_id,
            })

    return alerts


def _check_req_coverage_alerts(project_id: int) -> list[dict]:
    """Requirement coverage threshold kontrolü."""
    alerts = []
    req_data = compute_requirement_coverage(project_id)
    coverage = req_data["coverage_pct"]

    if coverage < THRESHOLDS["req_coverage_escalate_pct"]:
        dk = _dedup_key(project_id, "req_coverage_escalate")
        if not _alert_exists(dk):
            alerts.append({
                "type": "req_coverage_escalate",
                "severity": "error",
                "category": "gate",
                "title": f"ESCALATION: Requirement coverage {coverage}% below {THRESHOLDS['req_coverage_escalate_pct']}%",
                "message": f"[{dk}] {req_data['covered']}/{req_data['total']} requirements covered",
                "entity_type": "project",
                "entity_id": project_id,
            })
    elif coverage < THRESHOLDS["req_coverage_warn_pct"]:
        dk = _dedup_key(project_id, "req_coverage_warn")
        if not _alert_exists(dk):
            alerts.append({
                "type": "req_coverage_warn",
                "severity": "warning",
                "category": "gate",
                "title": f"WARNING: Requirement coverage {coverage}% below {THRESHOLDS['req_coverage_warn_pct']}%",
                "message": f"[{dk}] {req_data['covered']}/{req_data['total']} requirements covered",
                "entity_type": "project",
                "entity_id": project_id,
            })

    return alerts


# ═════════════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════════════

class EscalationService:
    """Threshold aşımı kontrolü ve alert üretimi."""

    @staticmethod
    def check_and_alert(project_id: int, *, commit: bool = True) -> dict:
        """Tüm threshold'ları kontrol et ve gerekli alert'leri üret.

        Args:
            project_id: Program/project ID
            commit: True ise notification'ları commit'le, False ise sadece döndür

        Returns:
            {"alerts_generated": int, "alerts_skipped": int, "alerts": [...]}
        """
        all_alerts = []
        all_alerts.extend(_check_oi_aging_alerts(project_id))
        all_alerts.extend(_check_gap_ratio_alerts(project_id))
        all_alerts.extend(_check_req_coverage_alerts(project_id))

        generated = []
        for alert in all_alerts:
            notif = NotificationService.create(
                title=alert["title"],
                message=alert["message"],
                category=alert["category"],
                severity=alert["severity"],
                program_id=project_id,
                entity_type=alert["entity_type"],
                entity_id=alert.get("entity_id"),
            )
            generated.append({
                "id": notif.id,
                "type": alert["type"],
                "title": alert["title"],
                "severity": alert["severity"],
            })

        if commit and generated:
            db.session.commit()

        return {
            "project_id": project_id,
            "alerts_generated": len(generated),
            "alerts_skipped": 0,  # skipped are already filtered by dedup
            "alerts": generated,
        }

    @staticmethod
    def check_only(project_id: int) -> dict:
        """Alert üretmeden sadece threshold durumunu kontrol et.

        Returns:
            {"oi_aging": {...}, "gap_ratio": {...}, "req_coverage": {...}, "violations": [...]}
        """
        oi = compute_oi_aging(project_id)
        gap = compute_gap_ratio(project_id)
        req = compute_requirement_coverage(project_id)

        violations = []
        if oi["p1_open"] > 0:
            violations.append({"type": "p1_oi_open", "severity": "warning", "value": oi["p1_open"]})
        if oi["overdue"] > 0:
            violations.append({"type": "oi_overdue", "severity": "warning", "value": oi["overdue"]})
        if gap["gap_ratio"] >= THRESHOLDS["gap_ratio_escalate_pct"]:
            violations.append({"type": "gap_ratio_high", "severity": "error", "value": gap["gap_ratio"]})
        elif gap["gap_ratio"] >= THRESHOLDS["gap_ratio_warn_pct"]:
            violations.append({"type": "gap_ratio_warn", "severity": "warning", "value": gap["gap_ratio"]})
        if req["coverage_pct"] < THRESHOLDS["req_coverage_escalate_pct"]:
            violations.append({"type": "req_coverage_low", "severity": "error", "value": req["coverage_pct"]})
        elif req["coverage_pct"] < THRESHOLDS["req_coverage_warn_pct"]:
            violations.append({"type": "req_coverage_warn", "severity": "warning", "value": req["coverage_pct"]})

        for cand in oi.get("escalation_candidates", []):
            violations.append({
                "type": "oi_aging_escalate",
                "severity": "error",
                "value": cand["age_days"],
                "entity_id": cand["id"],
            })

        return {
            "project_id": project_id,
            "oi_aging": {"total_open": oi["total_open"], "overdue": oi["overdue"], "p1_open": oi["p1_open"], "rag": oi["rag"]},
            "gap_ratio": {"value": gap["gap_ratio"], "rag": gap["rag"]},
            "req_coverage": {"value": req["coverage_pct"], "rag": req["rag"]},
            "violations": violations,
        }
