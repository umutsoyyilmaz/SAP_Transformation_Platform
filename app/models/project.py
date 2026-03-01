"""Project domain model for Program -> Project hierarchy."""

from datetime import datetime, timezone

from app.models import db


class Project(db.Model):
    """Execution unit under a Program (e.g., country/wave/release track)."""

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="implementation")
    status = db.Column(db.String(30), nullable=False, default="active")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    go_live_date = db.Column(db.Date, nullable=True)
    is_default = db.Column(db.Boolean, nullable=False, default=False)

    # ── Operational fields (Faz 2.2 — Project = execution unit) ──
    description = db.Column(db.Text, nullable=True)
    wave_number = db.Column(
        db.Integer, nullable=True,
        comment="Ordering within program (wave 1, 2, ...)",
    )
    sap_product = db.Column(
        db.String(50), nullable=True, default="S/4HANA",
        comment="S/4HANA | SuccessFactors | Ariba | BTP | Other",
    )
    project_type = db.Column(
        db.String(50), nullable=True, default="greenfield",
        comment="greenfield | brownfield | bluefield | selective_data_transition",
    )
    methodology = db.Column(
        db.String(50), nullable=True, default="sap_activate",
        comment="sap_activate | agile | waterfall | hybrid",
    )
    deployment_option = db.Column(
        db.String(30), nullable=True, default="on_premise",
        comment="on_premise | cloud | hybrid",
    )
    priority = db.Column(
        db.String(20), nullable=True, default="medium",
        comment="low | medium | high | critical",
    )

    # ── 5-dimensional RAG status ──
    project_rag = db.Column(
        db.String(10), nullable=True,
        comment="Overall RAG: Green | Amber | Red",
    )
    rag_scope = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_timeline = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_budget = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_quality = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_resources = db.Column(db.String(10), nullable=True, comment="Green | Amber | Red")
    rag_updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Faz 3: Relationships to operational entities ──
    phases = db.relationship("Phase", backref="project", lazy="dynamic",
                             foreign_keys="Phase.project_id")
    workstreams = db.relationship("Workstream", backref="project", lazy="dynamic",
                                  foreign_keys="Workstream.project_id")
    team_members = db.relationship("TeamMember", backref="project", lazy="dynamic",
                                   foreign_keys="TeamMember.project_id")
    committees = db.relationship("Committee", backref="project", lazy="dynamic",
                                 foreign_keys="Committee.project_id")
    scenarios = db.relationship("Scenario", backref="project", lazy="dynamic",
                                foreign_keys="Scenario.project_id")
    sprints = db.relationship("Sprint", backref="project", lazy="dynamic",
                              foreign_keys="Sprint.project_id")
    backlog_items = db.relationship("BacklogItem", backref="project", lazy="dynamic",
                                    foreign_keys="BacklogItem.project_id")
    config_items = db.relationship("ConfigItem", backref="project", lazy="dynamic",
                                   foreign_keys="ConfigItem.project_id")
    test_plans = db.relationship("TestPlan", backref="project", lazy="dynamic",
                                 foreign_keys="TestPlan.project_id")
    test_cases = db.relationship("TestCase", backref="project", lazy="dynamic",
                                 foreign_keys="TestCase.project_id")
    test_suites = db.relationship("TestSuite", backref="project", lazy="dynamic",
                                  foreign_keys="TestSuite.project_id")
    defects = db.relationship("Defect", backref="project", lazy="dynamic",
                              foreign_keys="Defect.project_id")
    cutover_plans = db.relationship("CutoverPlan", backref="project", lazy="dynamic",
                                    foreign_keys="CutoverPlan.project_id")
    requirements = db.relationship("Requirement", backref="project", lazy="dynamic",
                                   foreign_keys="Requirement.project_id")
    risks = db.relationship("Risk", backref="project", lazy="dynamic",
                            foreign_keys="Risk.project_id")
    actions = db.relationship("Action", backref="project", lazy="dynamic",
                              foreign_keys="Action.project_id")
    issues = db.relationship("Issue", backref="project", lazy="dynamic",
                             foreign_keys="Issue.project_id")
    raid_decisions = db.relationship("Decision", backref="project", lazy="dynamic",
                                     foreign_keys="Decision.project_id")

    __table_args__ = (
        db.UniqueConstraint("program_id", "code", name="uq_projects_program_code"),
        db.Index("ix_projects_tenant_program", "tenant_id", "program_id"),
        db.Index(
            "uq_projects_program_default_true",
            "program_id",
            unique=True,
            postgresql_where=db.text("is_default IS TRUE"),
            sqlite_where=db.text("is_default = 1"),
        ),
    )

    def to_dict(self) -> dict:
        """Serialize core project fields for API responses."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "code": self.code,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "owner_id": self.owner_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "go_live_date": self.go_live_date.isoformat() if self.go_live_date else None,
            "is_default": self.is_default,
            # Operational fields (Faz 2.2)
            "description": self.description,
            "wave_number": self.wave_number,
            "sap_product": self.sap_product,
            "project_type": self.project_type,
            "methodology": self.methodology,
            "deployment_option": self.deployment_option,
            "priority": self.priority,
            # 5-dimensional RAG
            "project_rag": self.project_rag,
            "rag_scope": self.rag_scope,
            "rag_timeline": self.rag_timeline,
            "rag_budget": self.rag_budget,
            "rag_quality": self.rag_quality,
            "rag_resources": self.rag_resources,
            "rag_updated_at": self.rag_updated_at.isoformat() if self.rag_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Project {self.id}: {self.code}>"
