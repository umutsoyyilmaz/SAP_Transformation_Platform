"""
SAP Transformation Management Platform
Scenario domain models — Sprint 3 scope.

Models:
    - Scenario: what-if analysis container for comparing transformation approaches
    - ScenarioParameter: key/value parameters that define a scenario variant
"""

from datetime import datetime, timezone

from app.models import db


class Scenario(db.Model):
    """
    What-if analysis scenario for SAP transformation programs.

    Allows teams to compare different transformation approaches:
    e.g. "Greenfield vs Brownfield", "Cloud vs On-Premise",
    "Big-Bang vs Phased Rollout".
    """

    __tablename__ = "scenarios"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    scenario_type = db.Column(
        db.String(50),
        default="approach",
        comment="approach | timeline | scope | cost | resource",
    )
    status = db.Column(
        db.String(30),
        default="draft",
        comment="draft | under_review | approved | rejected | archived",
    )
    is_baseline = db.Column(
        db.Boolean, default=False,
        comment="Mark one scenario as the baseline / recommended option",
    )

    # Estimation fields
    estimated_duration_weeks = db.Column(db.Integer, nullable=True)
    estimated_cost = db.Column(db.Float, nullable=True)
    estimated_resources = db.Column(db.Integer, nullable=True)
    risk_level = db.Column(
        db.String(20),
        default="medium",
        comment="low | medium | high | critical",
    )
    confidence_pct = db.Column(
        db.Integer, default=50,
        comment="Confidence level 0-100 for the estimate",
    )

    # Pros / Cons / Assumptions
    pros = db.Column(db.Text, default="", comment="Advantages — newline separated")
    cons = db.Column(db.Text, default="", comment="Disadvantages — newline separated")
    assumptions = db.Column(db.Text, default="", comment="Key assumptions — newline separated")

    # Recommendation
    recommendation = db.Column(db.Text, default="")

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
    parameters = db.relationship(
        "ScenarioParameter", backref="scenario", lazy="dynamic",
        cascade="all, delete-orphan", order_by="ScenarioParameter.key",
    )

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type,
            "status": self.status,
            "is_baseline": self.is_baseline,
            "estimated_duration_weeks": self.estimated_duration_weeks,
            "estimated_cost": self.estimated_cost,
            "estimated_resources": self.estimated_resources,
            "risk_level": self.risk_level,
            "confidence_pct": self.confidence_pct,
            "pros": self.pros,
            "cons": self.cons,
            "assumptions": self.assumptions,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["parameters"] = [p.to_dict() for p in self.parameters]
        return result

    def __repr__(self):
        return f"<Scenario {self.id}: {self.name}>"


class ScenarioParameter(db.Model):
    """
    Key/value parameter that defines a scenario variant.
    E.g. key="deployment_model", value="Cloud (RISE)", category="technical".
    """

    __tablename__ = "scenario_parameters"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer, db.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    key = db.Column(db.String(100), nullable=False, comment="Parameter name")
    value = db.Column(db.Text, default="", comment="Parameter value")
    category = db.Column(
        db.String(50),
        default="general",
        comment="general | technical | financial | organizational | timeline",
    )
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ScenarioParameter {self.id}: {self.key}={self.value}>"
