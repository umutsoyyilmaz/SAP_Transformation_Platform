"""
Data Factory Module — Models for data migration lifecycle [Sprint 10]

5 models:
  - DataObject: Master data objects to migrate
  - MigrationWave: Phased migration batches
  - CleansingTask: Data quality rules per object
  - LoadCycle: ETL execution records
  - Reconciliation: Source-target reconciliation checks
"""

from datetime import datetime, timezone

from app.models import db

# ── Constants ────────────────────────────────────────────────────────────

DATA_OBJECT_STATUSES = {"draft", "profiled", "cleansed", "ready", "migrated", "archived"}
WAVE_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
CLEANSING_STATUSES = {"pending", "running", "passed", "failed", "skipped"}
LOAD_STATUSES = {"pending", "running", "completed", "failed", "aborted"}
RECONCILIATION_STATUSES = {"pending", "matched", "variance", "failed"}

RULE_TYPES = {"not_null", "unique", "range", "regex", "lookup", "custom"}
LOAD_TYPES = {"initial", "delta", "full_reload", "mock"}
ENVIRONMENTS = {"DEV", "QAS", "PRE", "PRD"}


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════
# 1. DataObject
# ═════════════════════════════════════════════════════════════════════════

class DataObject(db.Model):
    """Master data or transactional data object scheduled for migration."""

    __tablename__ = "data_objects"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source_system = db.Column(db.String(100), nullable=False, comment="ECC, Legacy, Excel, etc.")
    target_table = db.Column(db.String(100), nullable=True, comment="S/4HANA target table")
    record_count = db.Column(db.Integer, nullable=True, default=0)
    quality_score = db.Column(db.Float, nullable=True, comment="0.0–100.0")
    status = db.Column(
        db.String(20), nullable=False, default="draft",
        comment="draft | profiled | cleansed | ready | migrated | archived",
    )
    owner = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    cleansing_tasks = db.relationship("CleansingTask", backref="data_object", lazy="dynamic", cascade="all, delete-orphan")
    load_cycles = db.relationship("LoadCycle", backref="data_object", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "source_system": self.source_system,
            "target_table": self.target_table,
            "record_count": self.record_count,
            "quality_score": self.quality_score,
            "status": self.status,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<DataObject {self.name}>"


# ═════════════════════════════════════════════════════════════════════════
# 2. MigrationWave
# ═════════════════════════════════════════════════════════════════════════

class MigrationWave(db.Model):
    """Phased migration batch — groups data objects for sequential loading."""

    __tablename__ = "migration_waves"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    wave_number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    planned_start = db.Column(db.Date, nullable=True)
    planned_end = db.Column(db.Date, nullable=True)
    actual_start = db.Column(db.Date, nullable=True)
    actual_end = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default="planned",
        comment="planned | in_progress | completed | cancelled",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    load_cycles = db.relationship("LoadCycle", backref="wave", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "wave_number": self.wave_number,
            "name": self.name,
            "description": self.description,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<MigrationWave {self.wave_number}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════
# 3. CleansingTask
# ═════════════════════════════════════════════════════════════════════════

class CleansingTask(db.Model):
    """Data quality rule applied to a DataObject."""

    __tablename__ = "cleansing_tasks"

    id = db.Column(db.Integer, primary_key=True)
    data_object_id = db.Column(
        db.Integer, db.ForeignKey("data_objects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rule_type = db.Column(
        db.String(20), nullable=False,
        comment="not_null | unique | range | regex | lookup | custom",
    )
    rule_expression = db.Column(db.Text, nullable=False, comment="Column name or expression")
    description = db.Column(db.Text, nullable=True)
    pass_count = db.Column(db.Integer, nullable=True, default=0)
    fail_count = db.Column(db.Integer, nullable=True, default=0)
    status = db.Column(
        db.String(20), nullable=False, default="pending",
        comment="pending | running | passed | failed | skipped",
    )
    last_run_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "data_object_id": self.data_object_id,
            "rule_type": self.rule_type,
            "rule_expression": self.rule_expression,
            "description": self.description,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "status": self.status,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CleansingTask {self.rule_type}: {self.rule_expression[:30]}>"


# ═════════════════════════════════════════════════════════════════════════
# 4. LoadCycle
# ═════════════════════════════════════════════════════════════════════════

class LoadCycle(db.Model):
    """ETL execution record — one load attempt for a data object in a wave."""

    __tablename__ = "load_cycles"

    id = db.Column(db.Integer, primary_key=True)
    data_object_id = db.Column(
        db.Integer, db.ForeignKey("data_objects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    wave_id = db.Column(
        db.Integer, db.ForeignKey("migration_waves.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    environment = db.Column(
        db.String(10), nullable=False, default="DEV",
        comment="DEV | QAS | PRE | PRD",
    )
    load_type = db.Column(
        db.String(20), nullable=False, default="initial",
        comment="initial | delta | full_reload | mock",
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    records_loaded = db.Column(db.Integer, nullable=True, default=0)
    records_failed = db.Column(db.Integer, nullable=True, default=0)
    status = db.Column(
        db.String(20), nullable=False, default="pending",
        comment="pending | running | completed | failed | aborted",
    )
    error_log = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    reconciliations = db.relationship("Reconciliation", backref="load_cycle", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "data_object_id": self.data_object_id,
            "wave_id": self.wave_id,
            "environment": self.environment,
            "load_type": self.load_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_loaded": self.records_loaded,
            "records_failed": self.records_failed,
            "status": self.status,
            "error_log": self.error_log,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<LoadCycle obj={self.data_object_id} env={self.environment} s={self.status}>"


# ═════════════════════════════════════════════════════════════════════════
# 5. Reconciliation
# ═════════════════════════════════════════════════════════════════════════

class Reconciliation(db.Model):
    """Post-load verification comparing source and target record counts."""

    __tablename__ = "reconciliations"

    id = db.Column(db.Integer, primary_key=True)
    load_cycle_id = db.Column(
        db.Integer, db.ForeignKey("load_cycles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_count = db.Column(db.Integer, nullable=False, default=0)
    target_count = db.Column(db.Integer, nullable=False, default=0)
    match_count = db.Column(db.Integer, nullable=False, default=0)
    variance = db.Column(db.Integer, nullable=False, default=0,
                         comment="source_count - target_count")
    variance_pct = db.Column(db.Float, nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default="pending",
        comment="pending | matched | variance | failed",
    )
    notes = db.Column(db.Text, nullable=True)
    checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "load_cycle_id": self.load_cycle_id,
            "source_count": self.source_count,
            "target_count": self.target_count,
            "match_count": self.match_count,
            "variance": self.variance,
            "variance_pct": self.variance_pct,
            "status": self.status,
            "notes": self.notes,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Reconciliation lc={self.load_cycle_id} v={self.variance}>"
