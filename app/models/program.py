"""
SAP Transformation Management Platform
Program domain models — Sprint 1 scope.

Models:
    - Program: top-level project entity (SAP transformation program)
"""

from datetime import datetime, timezone

from app.models import db


class Program(db.Model):
    """
    Represents an SAP transformation program / project.
    Maps to ProjektCoPilot's 'projects' table.
    """

    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    project_type = db.Column(
        db.String(50),
        default="greenfield",
        comment="greenfield | brownfield | bluefield | selective_data_transition",
    )
    methodology = db.Column(
        db.String(50),
        default="sap_activate",
        comment="sap_activate | agile | waterfall | hybrid",
    )
    status = db.Column(
        db.String(30),
        default="planning",
        comment="planning | active | on_hold | completed | cancelled",
    )
    priority = db.Column(
        db.String(20),
        default="medium",
        comment="low | medium | high | critical",
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    go_live_date = db.Column(db.Date, nullable=True)

    # SAP-specific
    sap_product = db.Column(
        db.String(50),
        default="S/4HANA",
        comment="S/4HANA | SuccessFactors | Ariba | BTP | Other",
    )
    deployment_option = db.Column(
        db.String(30),
        default="on_premise",
        comment="on_premise | cloud | hybrid",
    )

    # Metadata
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
        """Serialize program to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "methodology": self.methodology,
            "status": self.status,
            "priority": self.priority,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "go_live_date": (
                self.go_live_date.isoformat() if self.go_live_date else None
            ),
            "sap_product": self.sap_product,
            "deployment_option": self.deployment_option,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Program {self.id}: {self.name}>"
