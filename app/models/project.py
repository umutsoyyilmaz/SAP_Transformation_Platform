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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Project {self.id}: {self.code}>"
