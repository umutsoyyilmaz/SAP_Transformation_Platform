"""
SAP Transformation Management Platform
Integration Factory domain models — Sprint 9 scope.

Models:
    - Interface: SAP integration interface object (inbound / outbound / bidirectional)
    - Wave: deployment wave for grouping interfaces by go-live phase
    - ConnectivityTest: connectivity test result per interface
    - SwitchPlan: cutover switch-plan entry per interface
    - InterfaceChecklist: readiness checklist item per interface (12-item SAP standard)

SAP Context:
    In SAP S/4HANA transformations, the Integration Factory manages all
    technical interfaces between SAP and external systems. Interfaces are
    categorised by direction (inbound/outbound/bidirectional), protocol
    (RFC, IDoc, OData, SOAP, REST, File, PI/PO, CPI), and middleware.
    Each interface goes through planning → development → connectivity test →
    switch-plan rehearsal → go-live waves.
"""

from datetime import datetime, timezone

from app.models import db


# ── Shared constants ─────────────────────────────────────────────────────

INTERFACE_DIRECTIONS = {"inbound", "outbound", "bidirectional"}

INTERFACE_PROTOCOLS = {
    "rfc", "idoc", "odata", "soap", "rest", "file",
    "pi_po", "cpi", "bapi", "ale", "other",
}

INTERFACE_STATUSES = {
    "identified", "designed", "developed", "unit_tested",
    "connectivity_tested", "integration_tested",
    "go_live_ready", "live", "decommissioned",
}

WAVE_STATUSES = {"planning", "in_progress", "completed", "cancelled"}

CONNECTIVITY_RESULTS = {"pending", "success", "partial", "failed"}

SWITCH_ACTIONS = {
    "activate", "deactivate", "redirect", "verify", "rollback",
}

# SAP standard 12-item readiness checklist
DEFAULT_CHECKLIST_ITEMS = [
    "Interface specification document approved",
    "Source/target system identified and accessible",
    "Authentication & authorization configured",
    "Network connectivity verified (firewall, ports)",
    "Message mapping / transformation defined",
    "Error handling & retry logic implemented",
    "Monitoring & alerting configured",
    "Unit test completed in DEV",
    "Integration test completed in QAS",
    "Performance / volume test passed",
    "Cutover switch plan documented",
    "Go-live approval obtained",
]


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE
# ═════════════════════════════════════════════════════════════════════════════

class Interface(db.Model):
    """
    SAP integration interface — represents a single integration point
    between SAP and an external system (or SAP-to-SAP).
    """

    __tablename__ = "interfaces"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    wave_id = db.Column(
        db.Integer, db.ForeignKey("waves.id", ondelete="SET NULL"), nullable=True,
        index=True,
    )
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
        nullable=True, comment="Link to WRICEF item (type=interface)",
        index=True,
    )

    # ── Identification
    code = db.Column(
        db.String(50), default="",
        comment="Short ID, e.g. IF-FI-001, IF-SD-042",
    )
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # ── Integration specifics
    direction = db.Column(
        db.String(20), default="outbound",
        comment="inbound | outbound | bidirectional",
    )
    protocol = db.Column(
        db.String(30), default="idoc",
        comment="rfc | idoc | odata | soap | rest | file | pi_po | cpi | bapi | ale | other",
    )
    middleware = db.Column(
        db.String(100), default="",
        comment="SAP PI/PO, SAP CPI, MuleSoft, Dell Boomi, Azure Integration, etc.",
    )
    source_system = db.Column(db.String(100), default="", comment="Source system name")
    target_system = db.Column(db.String(100), default="", comment="Target system name")
    frequency = db.Column(
        db.String(50), default="",
        comment="real-time | hourly | daily | weekly | on-demand | batch",
    )
    volume = db.Column(
        db.String(100), default="",
        comment="Expected data volume, e.g. '10K records/day', '500 IDocs/hour'",
    )

    # ── SAP specifics
    module = db.Column(db.String(50), default="", comment="SAP module: FI, MM, SD, etc.")
    transaction_code = db.Column(db.String(30), default="", comment="Related T-code")
    message_type = db.Column(db.String(50), default="", comment="IDoc message type: MATMAS, ORDERS, etc.")
    interface_type = db.Column(
        db.String(30), default="",
        comment="master_data | transactional | reference | control",
    )

    # ── Lifecycle
    status = db.Column(
        db.String(30), default="identified",
        comment="identified → designed → developed → unit_tested → connectivity_tested → integration_tested → go_live_ready → live",
    )
    priority = db.Column(db.String(20), default="medium", comment="low | medium | high | critical")
    assigned_to = db.Column(db.String(100), default="")
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    complexity = db.Column(db.String(20), default="medium", comment="low | medium | high | very_high")
    estimated_hours = db.Column(db.Float, nullable=True)
    actual_hours = db.Column(db.Float, nullable=True)

    # ── Go-live
    go_live_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    connectivity_tests = db.relationship(
        "ConnectivityTest", backref="interface", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    switch_plans = db.relationship(
        "SwitchPlan", backref="interface", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    checklist_items = db.relationship(
        "InterfaceChecklist", backref="interface", lazy="dynamic",
        cascade="all, delete-orphan", order_by="InterfaceChecklist.order",
    )
    assigned_member = db.relationship("TeamMember", foreign_keys=[assigned_to_id])

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "wave_id": self.wave_id,
            "backlog_item_id": self.backlog_item_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "direction": self.direction,
            "protocol": self.protocol,
            "middleware": self.middleware,
            "source_system": self.source_system,
            "target_system": self.target_system,
            "frequency": self.frequency,
            "volume": self.volume,
            "module": self.module,
            "transaction_code": self.transaction_code,
            "message_type": self.message_type,
            "interface_type": self.interface_type,
            "status": self.status,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_member": self.assigned_member.to_dict() if self.assigned_to_id and self.assigned_member else None,
            "complexity": self.complexity,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "go_live_date": self.go_live_date.isoformat() if self.go_live_date else None,
            "notes": self.notes,
            "checklist_progress": self._checklist_progress(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["connectivity_tests"] = [t.to_dict() for t in self.connectivity_tests]
            result["switch_plans"] = [s.to_dict() for s in self.switch_plans]
            result["checklist"] = [c.to_dict() for c in self.checklist_items]
        return result

    def _checklist_progress(self):
        """Return checklist completion fraction, e.g. '8/12'."""
        total = self.checklist_items.count()
        if total == 0:
            return "0/0"
        done = self.checklist_items.filter_by(checked=True).count()
        return f"{done}/{total}"

    def __repr__(self):
        return f"<Interface {self.id}: {self.code or self.name[:30]}>"


# ═════════════════════════════════════════════════════════════════════════════
# WAVE
# ═════════════════════════════════════════════════════════════════════════════

class Wave(db.Model):
    """
    Deployment wave — groups interfaces for phased go-live.

    Example: Wave 1 (critical FI interfaces), Wave 2 (MM/SD), Wave 3 (HR/payroll).
    """

    __tablename__ = "waves"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False,
    )

    name = db.Column(db.String(100), nullable=False, comment="e.g. Wave 1, Phase A")
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(30), default="planning",
        comment="planning | in_progress | completed | cancelled",
    )
    order = db.Column(db.Integer, default=0, comment="Sort order within program")
    planned_start = db.Column(db.Date, nullable=True)
    planned_end = db.Column(db.Date, nullable=True)
    actual_start = db.Column(db.Date, nullable=True)
    actual_end = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    interfaces = db.relationship(
        "Interface", backref="wave", lazy="dynamic",
    )

    def to_dict(self, include_interfaces=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "order": self.order,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "notes": self.notes,
            "interface_count": self.interfaces.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_interfaces:
            result["interfaces"] = [i.to_dict() for i in self.interfaces]
        return result

    def __repr__(self):
        return f"<Wave {self.id}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY TEST
# ═════════════════════════════════════════════════════════════════════════════

class ConnectivityTest(db.Model):
    """
    Connectivity test record for an interface.

    Tracks each test execution: environment, result, response time, errors.
    Multiple tests can be recorded per interface (history).
    """

    __tablename__ = "connectivity_tests"

    id = db.Column(db.Integer, primary_key=True)
    interface_id = db.Column(
        db.Integer, db.ForeignKey("interfaces.id", ondelete="CASCADE"), nullable=False,
    )

    environment = db.Column(
        db.String(30), default="dev",
        comment="dev | qas | pre_prod | prod",
    )
    result = db.Column(
        db.String(20), default="pending",
        comment="pending | success | partial | failed",
    )
    response_time_ms = db.Column(
        db.Integer, nullable=True,
        comment="Round-trip response time in milliseconds",
    )
    tested_by = db.Column(db.String(100), default="")
    tested_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    error_message = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "interface_id": self.interface_id,
            "environment": self.environment,
            "result": self.result,
            "response_time_ms": self.response_time_ms,
            "tested_by": self.tested_by,
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
            "error_message": self.error_message,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ConnectivityTest {self.id}: {self.result} ({self.environment})>"


# ═════════════════════════════════════════════════════════════════════════════
# SWITCH PLAN
# ═════════════════════════════════════════════════════════════════════════════

class SwitchPlan(db.Model):
    """
    Cutover switch-plan entry for an interface.

    During SAP cutover, each interface must be individually activated,
    deactivated, or redirected according to a precise sequence and timeline.
    """

    __tablename__ = "switch_plans"

    id = db.Column(db.Integer, primary_key=True)
    interface_id = db.Column(
        db.Integer, db.ForeignKey("interfaces.id", ondelete="CASCADE"), nullable=False,
    )

    sequence = db.Column(
        db.Integer, default=0,
        comment="Execution order in the cutover plan",
    )
    action = db.Column(
        db.String(30), default="activate",
        comment="activate | deactivate | redirect | verify | rollback",
    )
    description = db.Column(db.Text, default="")
    responsible = db.Column(db.String(100), default="")
    planned_duration_min = db.Column(
        db.Integer, nullable=True,
        comment="Planned duration in minutes",
    )
    actual_duration_min = db.Column(
        db.Integer, nullable=True,
        comment="Actual duration in minutes",
    )
    status = db.Column(
        db.String(20), default="pending",
        comment="pending | in_progress | completed | failed | skipped",
    )
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "interface_id": self.interface_id,
            "sequence": self.sequence,
            "action": self.action,
            "description": self.description,
            "responsible": self.responsible,
            "planned_duration_min": self.planned_duration_min,
            "actual_duration_min": self.actual_duration_min,
            "status": self.status,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<SwitchPlan {self.id}: #{self.sequence} {self.action}>"


# ═════════════════════════════════════════════════════════════════════════════
# INTERFACE CHECKLIST
# ═════════════════════════════════════════════════════════════════════════════

class InterfaceChecklist(db.Model):
    """
    Readiness checklist item for an interface.

    Based on SAP standard 12-item interface readiness template.
    Each item can be checked/unchecked with optional notes and evidence.
    """

    __tablename__ = "interface_checklists"

    id = db.Column(db.Integer, primary_key=True)
    interface_id = db.Column(
        db.Integer, db.ForeignKey("interfaces.id", ondelete="CASCADE"), nullable=False,
    )

    order = db.Column(db.Integer, default=0, comment="Display order")
    title = db.Column(db.String(300), nullable=False, comment="Checklist item title")
    checked = db.Column(db.Boolean, default=False)
    checked_by = db.Column(db.String(100), default="")
    checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    evidence = db.Column(db.Text, default="", comment="Evidence or reference link")
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "interface_id": self.interface_id,
            "order": self.order,
            "title": self.title,
            "checked": self.checked,
            "checked_by": self.checked_by,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "evidence": self.evidence,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<InterfaceChecklist {self.id}: {'✅' if self.checked else '⬜'} {self.title[:30]}>"


# ── Helper: seed default checklist for a new interface ───────────────────

def seed_default_checklist(interface_id):
    """Create the 12 standard checklist items for a newly created interface."""
    items = []
    for idx, title in enumerate(DEFAULT_CHECKLIST_ITEMS):
        items.append(InterfaceChecklist(
            interface_id=interface_id,
            order=idx + 1,
            title=title,
        ))
    db.session.add_all(items)
    return items
