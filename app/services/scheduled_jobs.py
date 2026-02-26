"""
SAP Transformation Management Platform
Scheduled Jobs — Sprint 16.

Concrete job implementations that run on a schedule.

Jobs:
    - overdue_scanner: Scans for overdue RAID actions and open items
    - escalation_check: Runs governance escalation checks
    - daily_digest: Sends daily notification digest emails
    - weekly_digest: Sends weekly summary emails
    - stale_notification_cleanup: Archives old read notifications
    - sla_compliance_check: Checks Hypercare SLA compliance
    - data_quality_guard_daily: Report-only project scope integrity checks
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Any

from app.models import db
from app.models.notification import Notification
from app.models.scheduling import NotificationPreference
from app.services.scheduler_service import register_job

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Job 1: Overdue Scanner
# ═══════════════════════════════════════════════════════════════════════════

@register_job("overdue_scanner")
def scan_overdue_items(app) -> dict[str, Any]:
    """Scan for overdue RAID actions and open items, create notifications."""
    from app.services.notification import NotificationService

    results = {"actions_overdue": 0, "open_items_overdue": 0, "notifications_created": 0}

    # Scan overdue RAID actions
    try:
        from app.models.raid import RaidAction
        today = date.today()
        overdue_actions = RaidAction.query.filter(
            RaidAction.due_date < today,
            RaidAction.status.notin_(["completed", "cancelled", "closed"]),
        ).all()

        for action in overdue_actions:
            results["actions_overdue"] += 1
            NotificationService.create(
                title=f"Action {action.code} is overdue",
                message=f"{action.title} — due date was {action.due_date}.",
                category="action",
                severity="warning",
                program_id=action.program_id,
                entity_type="action",
                entity_id=action.id,
                recipient="all",
            )
            results["notifications_created"] += 1
    except ImportError:
        logger.warning("RaidAction model not available, skipping action scan")
    except Exception as e:
        logger.error("Error scanning overdue actions: %s", e)

    # Scan overdue open items (Explore module)
    try:
        from app.models.explore import OpenItem
        today = date.today()
        overdue_ois = OpenItem.query.filter(
            OpenItem.due_date < today,
            OpenItem.status.notin_(["closed", "cancelled", "resolved"]),
        ).all()

        for oi in overdue_ois:
            results["open_items_overdue"] += 1
            NotificationService.create(
                title=f"Open Item {getattr(oi, 'code', '')} is overdue",
                message=f"{oi.title} — due date was {oi.due_date}.",
                category="issue",
                severity="warning",
                program_id=getattr(oi, "program_id", None),
                entity_type="open_item",
                entity_id=oi.id,
                recipient="all",
            )
            results["notifications_created"] += 1
    except ImportError:
        logger.warning("OpenItem model not available, skipping OI scan")
    except Exception as e:
        logger.error("Error scanning overdue open items: %s", e)

    db.session.commit()
    logger.info("Overdue scanner: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 2: Escalation Check
# ═══════════════════════════════════════════════════════════════════════════

@register_job("escalation_check")
def run_escalation_check(app) -> dict[str, Any]:
    """Run governance escalation checks for all active programs."""
    from app.services.escalation import EscalationService
    from app.models.program import Program

    results = {"programs_checked": 0, "alerts_created": 0}

    programs = Program.query.filter(
        Program.status.in_(["active", "in_progress", "executing"]),
    ).all()

    for program in programs:
        try:
            alerts = EscalationService.check_and_alert(project_id=program.id)
            results["programs_checked"] += 1
            results["alerts_created"] += len(alerts) if alerts else 0
        except Exception as e:
            logger.error("Escalation check failed for program %s: %s", program.id, e)

    db.session.commit()
    logger.info("Escalation check: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 3: Daily Digest
# ═══════════════════════════════════════════════════════════════════════════

@register_job("daily_digest")
def send_daily_digest(app) -> dict[str, Any]:
    """Send daily notification digest to users with digest_frequency='daily'."""
    from app.services.email_service import EmailService
    from app.services.notification import NotificationService

    results = {"users_processed": 0, "emails_sent": 0, "errors": 0}

    # Find users who want daily digests
    prefs = NotificationPreference.query.filter_by(
        digest_frequency="daily",
        is_enabled=True,
    ).all()

    # Group by user
    user_prefs: dict[str, list[NotificationPreference]] = {}
    for p in prefs:
        user_prefs.setdefault(p.user_id, []).append(p)

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    for user_id, user_pref_list in user_prefs.items():
        try:
            # Get categories this user wants in digest
            categories = [p.category for p in user_pref_list]

            # Get unread notifications since yesterday
            notifications = Notification.query.filter(
                Notification.recipient.in_([user_id, "all"]),
                Notification.created_at >= yesterday,
                Notification.category.in_(categories),
            ).order_by(Notification.created_at.desc()).limit(50).all()

            if not notifications:
                continue

            # Build notification list HTML
            notif_html_parts = []
            for n in notifications:
                color = "#ef4444" if n.severity == "error" else (
                    "#f59e0b" if n.severity == "warning" else "#3b82f6"
                )
                notif_html_parts.append(
                    f'<div style="padding: 8px 12px; border-left: 3px solid {color}; '
                    f'margin-bottom: 8px; background: white;">'
                    f'<strong>{n.title}</strong><br>'
                    f'<span style="color: #64748b; font-size: 13px;">{n.message[:200]}</span>'
                    f'</div>'
                )

            # Get email address
            email = next(
                (p.email_address for p in user_pref_list if p.email_address),
                f"{user_id}@sap-platform.local",
            )

            EmailService.send_from_template(
                to_email=email,
                to_name=user_id,
                template_name="daily_digest",
                context={
                    "date": date.today().isoformat(),
                    "unread_count": len(notifications),
                    "notification_list": "\n".join(notif_html_parts),
                },
                category="digest",
                program_id=None,
            )

            results["users_processed"] += 1
            results["emails_sent"] += 1

        except Exception as e:
            results["errors"] += 1
            logger.error("Daily digest failed for user %s: %s", user_id, e)

    db.session.commit()
    logger.info("Daily digest: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 4: Weekly Digest
# ═══════════════════════════════════════════════════════════════════════════

@register_job("weekly_digest")
def send_weekly_digest(app) -> dict[str, Any]:
    """Send weekly notification summary to users with digest_frequency='weekly'."""
    from app.services.email_service import EmailService

    results = {"users_processed": 0, "emails_sent": 0, "errors": 0}

    prefs = NotificationPreference.query.filter_by(
        digest_frequency="weekly",
        is_enabled=True,
    ).all()

    user_prefs: dict[str, list[NotificationPreference]] = {}
    for p in prefs:
        user_prefs.setdefault(p.user_id, []).append(p)

    week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)

    for user_id, user_pref_list in user_prefs.items():
        try:
            categories = [p.category for p in user_pref_list]

            # Count notifications by category for this week
            notifications = Notification.query.filter(
                Notification.recipient.in_([user_id, "all"]),
                Notification.created_at >= week_ago,
                Notification.category.in_(categories),
            ).all()

            if not notifications:
                continue

            # Build category summary
            category_counts: dict[str, int] = {}
            for n in notifications:
                category_counts[n.category] = category_counts.get(n.category, 0) + 1

            rows_html = "\n".join(
                f'<tr><td style="padding: 8px;">{cat}</td>'
                f'<td style="padding: 8px; text-align: right;">{cnt}</td></tr>'
                for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1])
            )

            unread = sum(1 for n in notifications if not n.is_read)

            # Highlights: top 3 most severe
            highlights = sorted(notifications,
                                key=lambda n: {"error": 0, "warning": 1, "info": 2,
                                               "success": 3}.get(n.severity, 4))[:3]
            highlights_html = "<h4>Top Alerts</h4>" + "".join(
                f'<p style="margin: 4px 0;"><strong>[{h.severity.upper()}]</strong> {h.title}</p>'
                for h in highlights
            ) if highlights else ""

            email = next(
                (p.email_address for p in user_pref_list if p.email_address),
                f"{user_id}@sap-platform.local",
            )

            EmailService.send_from_template(
                to_email=email,
                to_name=user_id,
                template_name="weekly_digest",
                context={
                    "week": date.today().isocalendar()[1],
                    "category_rows": rows_html,
                    "total_unread": unread,
                    "highlights": highlights_html,
                },
                category="digest",
            )

            results["users_processed"] += 1
            results["emails_sent"] += 1

        except Exception as e:
            results["errors"] += 1
            logger.error("Weekly digest failed for user %s: %s", user_id, e)

    db.session.commit()
    logger.info("Weekly digest: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 5: Stale Notification Cleanup
# ═══════════════════════════════════════════════════════════════════════════

@register_job("stale_notification_cleanup")
def cleanup_stale_notifications(app) -> dict[str, Any]:
    """Archive (delete) read notifications older than 30 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    deleted = Notification.query.filter(
        Notification.is_read.is_(True),
        Notification.read_at < cutoff,
    ).delete(synchronize_session="fetch")

    db.session.commit()
    logger.info("Stale notification cleanup: deleted %d old read notifications", deleted)
    return {"deleted": deleted, "cutoff": cutoff.isoformat()}


# ═══════════════════════════════════════════════════════════════════════════
#  Job 6: SLA Compliance Check
# ═══════════════════════════════════════════════════════════════════════════

@register_job("sla_compliance_check")
def check_sla_compliance(app) -> dict[str, Any]:
    """Check Hypercare SLA compliance and create alerts for breaches."""
    from app.services.notification import NotificationService

    results = {"slas_checked": 0, "breaches_found": 0, "notifications_created": 0}

    try:
        from app.models.cutover import HypercareSLA, HypercareIncident

        slas = HypercareSLA.query.all()

        for sla in slas:
            results["slas_checked"] += 1

            # Count open incidents that breach this SLA
            open_incidents = HypercareIncident.query.filter(
                HypercareIncident.cutover_plan_id == sla.cutover_plan_id,
                HypercareIncident.severity == sla.severity,
                HypercareIncident.status.in_(["open", "investigating", "in_progress"]),
            ).all()

            for incident in open_incidents:
                if not incident.created_at or not sla.response_target_min:
                    continue
                # Check response SLA breach (minutes)
                created = incident.created_at.replace(tzinfo=None) if incident.created_at.tzinfo else incident.created_at
                minutes_since = (datetime.now(timezone.utc).replace(tzinfo=None) - created).total_seconds() / 60
                if minutes_since > sla.response_target_min and incident.response_time_min is None:
                    results["breaches_found"] += 1
                    NotificationService.create(
                        title=f"SLA Breach: Incident {incident.code or incident.id} — response time exceeded",
                        message=(
                            f"Severity {sla.severity} incident has been open for "
                            f"{minutes_since:.0f} min without response "
                            f"(SLA: {sla.response_target_min} min)."
                        ),
                        category="hypercare",
                        severity="error",
                        program_id=None,
                        entity_type="hypercare_incident",
                        entity_id=incident.id,
                    )
                    results["notifications_created"] += 1

                # Check resolution SLA breach (minutes)
                if (sla.resolution_target_min
                        and minutes_since > sla.resolution_target_min
                        and incident.resolved_at is None):
                    results["breaches_found"] += 1
                    NotificationService.create(
                        title=f"SLA Breach: Incident {incident.code or incident.id} — resolution time exceeded",
                        message=(
                            f"Severity {sla.severity} incident has been open for "
                            f"{minutes_since:.0f} min without resolution "
                            f"(SLA: {sla.resolution_target_min} min)."
                        ),
                        category="hypercare",
                        severity="error",
                        program_id=None,
                        entity_type="hypercare_incident",
                        entity_id=incident.id,
                    )
                    results["notifications_created"] += 1

        db.session.commit()
    except ImportError:
        logger.warning("Hypercare models not available, skipping SLA check")
    except Exception as e:
        logger.error("SLA compliance check failed: %s", e)

    logger.info("SLA compliance check: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 7: Hypercare Auto-Escalation — FDD-B03-Phase-2
# ═══════════════════════════════════════════════════════════════════════════

@register_job("auto_escalate_incidents")
def auto_escalate_incidents(app) -> dict[str, Any]:
    """Evaluate escalation rules for all active hypercare plans.

    Only processes CutoverPlans with status='hypercare' to avoid evaluating
    closed/draft plans.  Uses the same lazy evaluation pattern as the API-level
    escalation engine but triggered on a schedule.
    """
    from sqlalchemy import select
    from app.models.cutover import CutoverPlan

    results = {"plans_evaluated": 0, "new_escalations": 0, "errors": 0}

    try:
        plans = db.session.execute(
            select(CutoverPlan).where(CutoverPlan.status == "hypercare")
        ).scalars().all()

        for plan in plans:
            try:
                from app.services.hypercare_service import evaluate_escalations
                new_events = evaluate_escalations(plan.tenant_id, plan.id)
                results["plans_evaluated"] += 1
                results["new_escalations"] += len(new_events)
            except Exception as e:
                results["errors"] += 1
                logger.error(
                    "Auto-escalation failed for plan %s: %s", plan.id, e,
                )

        db.session.commit()
    except Exception as e:
        logger.error("Auto-escalation job failed: %s", e)
        results["errors"] += 1

    logger.info("Auto-escalation: %s", results)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Job 8: RBAC Assignment Expiry — Story 4.2
# ═══════════════════════════════════════════════════════════════════════════

@register_job("rbac_assignment_expiry")
def expire_rbac_assignments(app) -> dict[str, Any]:
    """Deactivate time-bound role assignments whose end date has passed."""
    from app.services.permission_service import expire_temporary_assignments

    try:
        result = expire_temporary_assignments()
        logger.info("RBAC assignment expiry: %s", result)
        return result
    except Exception as exc:
        logger.error("RBAC assignment expiry failed: %s", exc)
        return {"expired_assignments": 0, "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════════
#  Job 9: Data Quality Guard (Report-Only) — Story 5.2
# ═══════════════════════════════════════════════════════════════════════════

@register_job("data_quality_guard_daily")
def run_data_quality_guard_daily(app) -> dict[str, Any]:
    """Run report-only project scope integrity checks and emit critical alerts."""
    from app.models.audit import write_audit
    from app.services.data_quality_guard_service import collect_project_scope_quality_report
    from app.services.notification import NotificationService

    report = collect_project_scope_quality_report(report_only=True)
    summary = report["summary"]

    alerts_created = 0
    if summary.get("critical_rows", 0) > 0:
        NotificationService.create(
            title="Data Quality Guard: critical project-scope anomalies detected",
            message=(
                f"Critical rows={summary['critical_rows']}, "
                f"critical tables={summary['critical_tables']}, "
                f"tables_with_issues={summary['tables_with_issues']}."
            ),
            category="system",
            severity="error",
            entity_type="data_quality_guard",
            entity_id=None,
        )
        alerts_created += 1

    write_audit(
        entity_type="data_quality_report",
        entity_id=summary.get("tables_scanned", 0),
        action="data_quality.report",
        actor="system",
        diff=summary,
    )

    db.session.commit()
    result = {
        "mode": report["mode"],
        "summary": summary,
        "alerts_created": alerts_created,
    }
    logger.info("Data quality guard: %s", result)
    return result
