"""
SAP Authorization Concept domain models (FDD-I02 / S7-02).

ADR-002 Decision: These models represent SAP authorization concept roles,
completely separate from the platform RBAC (app/models/user.py::Role).
Using 'SapAuth*' prefix to avoid any ambiguity with platform Role model.

Models:
    SapAuthRole   — Single or composite SAP authorization role (Einzelrolle / Sammelrolle)
    SapAuthObject — SAP authorization object with field→value assignments
    SodMatrix     — Segregation of Duties risk registry between role pairs

Architecture note (ADR-002 §2):
    Platform RBAC  → app/models/user.py::Role + permission_service.py
    SAP auth concept → SapAuthRole (this file) + sap_auth_service.py
    These two systems MUST NOT share tables or services.
"""

import os
from datetime import datetime, timezone

from app.models import db

# ── SOD Rule Constants ─────────────────────────────────────────────────────────
# Built-in SOD rule set: tuples of (auth_object, conflicting_activities).
# When two roles share the same auth_object and include both activities,
# generate_sod_matrix() flags a conflict at the given risk level.

SOD_RULES: list[dict] = [
    {
        "auth_object": "F_BKPF_BUK",
        "conflict_activities": ["01", "60"],  # 01=create, 60=approve
        "risk_level": "critical",
        "description": "FI document creation and approval on the same company code",
    },
    {
        "auth_object": "M_BEST_BSA",
        "conflict_activities": ["01", "08"],  # 01=create, 08=release/approve
        "risk_level": "critical",
        "description": "Purchase order creation and release",
    },
    {
        "auth_object": "F_LFA1_BUK",
        "conflict_activities": ["01", "02"],  # 01=create, 02=change
        "risk_level": "high",
        "description": "Vendor master data create and change (payment manipulation risk)",
    },
    {
        "auth_object": "F_KNA1_BUK",
        "conflict_activities": ["01", "02"],
        "risk_level": "high",
        "description": "Customer master data create and change",
    },
    {
        "auth_object": "F_BKPF_KOA",
        "conflict_activities": ["01", "60"],
        "risk_level": "high",
        "description": "FI posting and approval on account type",
    },
]

ROLE_TYPES = {"single", "composite"}
ROLE_STATUSES = {"draft", "in_review", "approved", "implemented"}
RISK_LEVELS = {"critical", "high", "medium", "low"}

# ── Conditional PostgreSQL partial index (ADR-002 §4.2) ──────────────────────
# SQLite does NOT support WHERE-clause partial indexes.
# Only add the partial index when running against PostgreSQL.

_sod_indexes: list = [
    db.Index("ix_sod_matrix_role_pair", "role_a_id", "role_b_id"),
]
if "postgres" in os.getenv("DATABASE_URL", "").lower():
    _sod_indexes.append(
        db.Index(
            "ix_sod_high_risk",
            "role_a_id",
            "role_b_id",
            postgresql_where=db.text("risk_level IN ('critical', 'high')"),
        )
    )


# ═════════════════════════════════════════════════════════════════════════
# SapAuthRole
# ═════════════════════════════════════════════════════════════════════════


class SapAuthRole(db.Model):
    """
    SAP authorization concept role — NOT a platform RBAC role.

    Represents a single role (Einzelrolle, e.g. Z_FI_AR_CLERK) or composite
    role (Sammelrolle, e.g. Z_FI_ACCOUNTANT) within an SAP go-live project's
    authorization concept.

    Lifecycle: draft → in_review → approved → implemented

    Platform RBAC is managed separately via app/models/user.py::Role
    and app/services/permission_service.py. These must never be confused.

    project_id references programs.id (the canonical project entity).
    """

    __tablename__ = "sap_auth_roles"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    role_name = db.Column(
        db.String(30),
        nullable=False,
        comment="SAP role name format: Z_FI_AR_CLERK",
    )
    role_type = db.Column(
        db.String(20),
        nullable=False,
        default="single",
        comment="single | composite",
    )
    description = db.Column(db.String(500), nullable=True)
    sap_module = db.Column(
        db.String(10),
        nullable=True,
        comment="SAP module code: FI, MM, SD, etc.",
    )

    # Org-level defaults for this role (JSON dict mapping field → value)
    # Example: {"BUKRS": "1000", "WERKS": "*"}
    org_levels = db.Column(
        db.JSON,
        nullable=True,
        comment="Org level defaults: {BUKRS: '1000', WERKS: '*'}",
    )

    # Composite role: ordered list of single-role IDs that make up this composite
    child_role_ids = db.Column(
        db.JSON,
        nullable=True,
        comment="[int, ...] — sap_auth_roles.id list for composite roles only",
    )

    # Business context
    business_role_description = db.Column(
        db.String(200),
        nullable=True,
        comment="Human-readable business function: Accounts Receivable Clerk",
    )
    user_count_estimate = db.Column(
        db.Integer,
        nullable=True,
        comment="Approximate number of users who will receive this role",
    )

    # L4 ProcessStep linkage (JSON list of ProcessStep IDs)
    linked_process_step_ids = db.Column(
        db.JSON,
        nullable=True,
        comment="[int, ...] references to ProcessStep.id (L4 steps this role supports)",
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="draft",
        comment="draft | in_review | approved | implemented",
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    auth_objects = db.relationship(
        "SapAuthObject",
        back_populates="auth_role",
        cascade="all, delete-orphan",
        lazy="select",
    )
    sod_risks_as_a = db.relationship(
        "SodMatrix",
        foreign_keys="SodMatrix.role_a_id",
        cascade="all, delete-orphan",
        lazy="select",
    )
    sod_risks_as_b = db.relationship(
        "SodMatrix",
        foreign_keys="SodMatrix.role_b_id",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        db.Index("ix_sap_auth_roles_tenant_project", "tenant_id", "project_id"),
        {"extend_existing": True},
    )

    def to_dict(self) -> dict:
        """Serialize to dict — no sensitive fields on this model."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ═════════════════════════════════════════════════════════════════════════
# SapAuthObject
# ═════════════════════════════════════════════════════════════════════════


class SapAuthObject(db.Model):
    """
    SAP authorization object assignment within a SapAuthRole.

    Each row represents one authorization object (e.g. F_BKPF_BUK) assigned
    to a role, together with the field→value grants (e.g. ACTVT=["01","02","03"],
    BUKRS=["1000"]).

    source field tracks provenance:
      - "su24" — auto-derived from SU24 proposal
      - "su25_template" — derived from SU25 copy
      - "manual" — manually added by consultant

    Why separate from SapAuthRole: a single role can have 20-100 authorization
    objects. Normalization allows per-object editing without full role replacement.
    """

    __tablename__ = "sap_auth_objects"

    id = db.Column(db.Integer, primary_key=True)
    auth_role_id = db.Column(
        db.Integer,
        db.ForeignKey("sap_auth_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    auth_object = db.Column(
        db.String(10),
        nullable=False,
        comment="SAP authorization object code: F_BKPF_BUK",
    )
    auth_object_description = db.Column(db.String(200), nullable=True)

    # Field→value grants as JSON dict
    # Example: {"ACTVT": ["01", "02", "03"], "BUKRS": ["1000"], "KOART": ["*"]}
    field_values = db.Column(
        db.JSON,
        nullable=False,
        comment='Field→value grants: {"ACTVT": ["01","02"], "BUKRS": ["1000"]}',
    )

    source = db.Column(
        db.String(20),
        nullable=True,
        comment="su24 | su25_template | manual",
    )

    # Relationship
    auth_role = db.relationship("SapAuthRole", back_populates="auth_objects")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ═════════════════════════════════════════════════════════════════════════
# SodMatrix
# ═════════════════════════════════════════════════════════════════════════


class SodMatrix(db.Model):
    """
    Segregation of Duties risk — conflicting SapAuthRole pairs.

    Each row represents a detected (or manually registered) conflict between
    two roles. When the same user holds both role_a and role_b they can
    perform conflicting activities (e.g. create + approve an invoice).

    Auto-generated by generate_sod_matrix() using the SOD_RULES constant.
    Rows can then be updated with mitigating_control and accepted via
    accept_sod_risk().

    Why role-pair level (not object level): SOD management in SAP projects
    is done at role level for SU10 assignment control. Object-level SOD would
    require GRC which is out of scope for this platform.

    PostgreSQL partial index on (role_a_id, role_b_id) WHERE risk_level IN
    ('critical', 'high') is created conditionally — see _sod_indexes above.
    SQLite test environment uses the plain composite index only (ADR-002 §4.2).
    """

    __tablename__ = "sod_matrix"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    role_a_id = db.Column(
        db.Integer,
        db.ForeignKey("sap_auth_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_b_id = db.Column(
        db.Integer,
        db.ForeignKey("sap_auth_roles.id", ondelete="CASCADE"),
        nullable=False,
    )

    risk_level = db.Column(
        db.String(10),
        nullable=False,
        comment="critical | high | medium | low",
    )
    risk_description = db.Column(db.String(500), nullable=True)
    conflicting_auth_object = db.Column(
        db.String(10),
        nullable=True,
        comment="The SAP auth object that triggers this SOD conflict",
    )
    mitigating_control = db.Column(
        db.Text,
        nullable=True,
        comment="Compensating control description (e.g. manual approval log)",
    )
    is_accepted = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="Risk formally accepted (residual risk acknowledged)",
    )
    accepted_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = tuple(_sod_indexes) + ({"extend_existing": True},)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
