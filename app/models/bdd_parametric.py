"""F7 — BDD, Parametrization & Data-Driven Testing models."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from app.models import db


def _utcnow():
    return datetime.now(timezone.utc)


# ── 7.1 BDD / Gherkin ─────────────────────────────────────────────

class TestCaseBDD(db.Model):
    """Gherkin feature/scenario linked to a test case."""

    __tablename__ = "test_case_bdd"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_file = Column(Text, default="")  # Full .feature content
    language = Column(String(10), default="en")  # en, de, tr
    synced_from = Column(String(200), default="")  # Git URL if synced
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    test_case = relationship("TestCase", backref="bdd_spec", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "test_case_id": self.test_case_id,
            "feature_file": self.feature_file,
            "language": self.language,
            "synced_from": self.synced_from,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── 7.2 Data Parametrization ──────────────────────────────────────

class TestDataParameter(db.Model):
    """Parameterized test data for data-driven testing."""

    __tablename__ = "test_data_parameters"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(100), nullable=False)  # e.g. {{customer_id}}
    data_type = Column(String(20), default="string")  # string|number|date|boolean
    values = Column(JSON, default=list)  # ["CUST-001", "CUST-002", ...]
    source = Column(String(30), default="manual")  # manual|data_set|api
    data_set_id = Column(
        Integer,
        ForeignKey("test_data_sets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "test_case_id": self.test_case_id,
            "name": self.name,
            "data_type": self.data_type,
            "values": self.values or [],
            "source": self.source,
            "data_set_id": self.data_set_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TestDataIteration(db.Model):
    """One row of parameterized data for an execution."""

    __tablename__ = "test_data_iterations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    execution_id = Column(
        Integer,
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iteration_no = Column(Integer, nullable=False, default=1)
    parameters = Column(JSON, default=dict)  # {"customer_id": "CUST-001", …}
    result = Column(String(20), default="not_run")  # pass|fail|blocked|not_run
    executed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(String(100), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    execution = relationship("TestExecution", backref="iterations")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "execution_id": self.execution_id,
            "iteration_no": self.iteration_no,
            "parameters": self.parameters or {},
            "result": self.result,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "executed_by": self.executed_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 7.3 Shared Step Library ───────────────────────────────────────

class SharedStep(db.Model):
    """Reusable step sequence."""

    __tablename__ = "shared_steps"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    steps = Column(JSON, default=list)  # [{step_no, action, expected, data}]
    tags = Column(JSON, default=list)
    usage_count = Column(Integer, default=0)
    created_by = Column(String(100), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    references = relationship(
        "TestStepReference", backref="shared_step", lazy="dynamic"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "title": self.title,
            "description": self.description,
            "steps": self.steps or [],
            "tags": self.tags or [],
            "usage_count": self.usage_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "reference_count": self.references.count() if self.references else 0,
        }


class TestStepReference(db.Model):
    """Reference to a shared step within a test case."""

    __tablename__ = "test_step_references"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_no = Column(Integer, nullable=False, default=1)
    shared_step_id = Column(
        Integer,
        ForeignKey("shared_steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    override_data = Column(JSON, default=dict)  # Parameter overrides
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "test_case_id": self.test_case_id,
            "step_no": self.step_no,
            "shared_step_id": self.shared_step_id,
            "override_data": self.override_data or {},
            "shared_step_title": self.shared_step.title if self.shared_step else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 7.4 Test Case Data Binding ────────────────────────────────────

class TestCaseDataBinding(db.Model):
    """Link test case parameters to a data set."""

    __tablename__ = "test_case_data_bindings"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_set_id = Column(
        Integer,
        ForeignKey("test_data_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_mapping = Column(JSON, default=dict)  # {"{{customer_id}}": "col_name"}
    iteration_mode = Column(String(20), default="all")  # all|random|first_n
    max_iterations = Column(Integer, nullable=True)  # null = all rows
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "test_case_id": self.test_case_id,
            "data_set_id": self.data_set_id,
            "parameter_mapping": self.parameter_mapping or {},
            "iteration_mode": self.iteration_mode,
            "max_iterations": self.max_iterations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ── 7.5 Suite Templates ──────────────────────────────────────────

class SuiteTemplate(db.Model):
    """Reusable test suite template across programs."""

    __tablename__ = "suite_templates"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(String(50), default="regression")  # regression|smoke|integration|…
    tc_criteria = Column(JSON, default=dict)  # Filter criteria to select TCs
    created_by = Column(String(100), default="")
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tc_criteria": self.tc_criteria or {},
            "created_by": self.created_by,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
