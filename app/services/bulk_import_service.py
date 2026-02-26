"""
Bulk User Import Service — Sprint 8, Item 3.6

CSV-based bulk user import with validation and progress tracking.

Features:
  - Parse CSV with columns: email, full_name, role (optional)
  - Validate email format, duplicate check, role existence
  - Batch create users with error reporting per row
  - Template CSV generation
  - Import history tracking
"""

import csv
import io
import logging
from datetime import datetime, timezone

from email_validator import EmailNotValidError, validate_email

from app.models import db
from app.models.auth import Role, Tenant, User, UserRole
from app.models.program import Program
from app.models.project import Project
from app.services.user_service import assign_role, assign_to_project, UserServiceError
from app.utils.crypto import hash_password

logger = logging.getLogger(__name__)


class BulkImportError(Exception):
    """Bulk import error."""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════
# CSV Template
# ═══════════════════════════════════════════════════════════════

CSV_TEMPLATE_HEADER = ["email", "full_name", "role"]
CSV_TEMPLATE_EXAMPLE = [
    ["user1@example.com", "John Doe", "viewer"],
    ["user2@example.com", "Jane Smith", "functional_consultant"],
    ["user3@example.com", "Bob Wilson", ""],
]


def generate_csv_template() -> str:
    """Generate a CSV template string for bulk user import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADER)
    writer.writerows(CSV_TEMPLATE_EXAMPLE)
    return output.getvalue()


# ═══════════════════════════════════════════════════════════════
# CSV Parsing & Validation
# ═══════════════════════════════════════════════════════════════

def parse_csv(file_content: str | bytes) -> list[dict]:
    """
    Parse CSV content into a list of row dicts.
    Returns list of {"email": ..., "full_name": ..., "role": ...}
    """
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8-sig")  # Handle BOM

    reader = csv.DictReader(io.StringIO(file_content))

    # Validate headers
    fieldnames = reader.fieldnames or []
    # Normalize headers (strip whitespace, lowercase)
    normalized = [f.strip().lower() for f in fieldnames]
    if "email" not in normalized:
        raise BulkImportError(
            "CSV must have an 'email' column. "
            f"Found columns: {', '.join(fieldnames)}"
        )

    rows = []
    for i, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        # Normalize keys
        normalized_row = {}
        for k, v in row.items():
            normalized_row[k.strip().lower()] = (v or "").strip()
        rows.append({
            "row_num": i,
            "email": normalized_row.get("email", ""),
            "full_name": normalized_row.get("full_name", ""),
            "role": normalized_row.get("role", ""),
        })

    return rows


def validate_import_rows(tenant_id: int, rows: list[dict]) -> dict:
    """
    Validate all rows before import.
    Returns {"valid": [...], "errors": [...]}
    """
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise BulkImportError("Tenant not found", 404)

    # Pre-fetch existing emails for this tenant
    existing_emails = {
        u.email.lower()
        for u in User.query.filter_by(tenant_id=tenant_id).with_entities(User.email)
    }

    # Pre-fetch available roles
    available_roles = {
        r.name
        for r in Role.query.filter(
            (Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None))
        )
    }

    # Current user count for limit check
    current_count = User.query.filter_by(tenant_id=tenant_id).count()
    max_users = tenant.max_users

    valid = []
    errors = []
    seen_emails = set()

    for row in rows:
        row_errors = []
        email = row["email"].lower()

        # 1. Email required
        if not email:
            row_errors.append("Email is required")
        else:
            # 2. Email format
            try:
                result = validate_email(email, check_deliverability=False)
                email = result.normalized
            except EmailNotValidError as e:
                row_errors.append(f"Invalid email: {e}")

            # 3. Duplicate in CSV
            if email in seen_emails:
                row_errors.append(f"Duplicate email in CSV: {email}")
            seen_emails.add(email)

            # 4. Already exists in tenant
            if email in existing_emails:
                row_errors.append(f"User already exists: {email}")

        # 5. Role validation (if specified)
        role = row.get("role", "").strip()
        if role and role not in available_roles:
            row_errors.append(
                f"Unknown role '{role}'. Available: {', '.join(sorted(available_roles))}"
            )

        if row_errors:
            errors.append({
                "row_num": row["row_num"],
                "email": row["email"],
                "errors": row_errors,
            })
        else:
            valid.append({
                "row_num": row["row_num"],
                "email": email,
                "full_name": row.get("full_name", ""),
                "role": role or "viewer",
            })

    # 6. User limit check
    if current_count + len(valid) > max_users:
        remaining = max_users - current_count
        errors.append({
            "row_num": 0,
            "email": "",
            "errors": [
                f"Import would exceed user limit. "
                f"Current: {current_count}, Limit: {max_users}, "
                f"Remaining capacity: {remaining}, Attempting to add: {len(valid)}"
            ],
        })

    return {"valid": valid, "errors": errors}


# ═══════════════════════════════════════════════════════════════
# Bulk Import Execution
# ═══════════════════════════════════════════════════════════════

def execute_bulk_import(tenant_id: int, validated_rows: list[dict]) -> dict:
    """
    Execute the bulk import for validated rows.
    Returns {"created": [...], "failed": [...]}
    """
    created = []
    failed = []

    for row in validated_rows:
        try:
            user = User(
                tenant_id=tenant_id,
                email=row["email"],
                full_name=row.get("full_name", ""),
                status="active",
                auth_provider="csv_import",
            )
            db.session.add(user)
            db.session.flush()

            # Assign role
            role_name = row.get("role", "viewer")
            role = Role.query.filter(
                (Role.name == role_name)
                & ((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
            ).first()
            if role:
                db.session.add(UserRole(user_id=user.id, role_id=role.id))

            created.append({
                "row_num": row["row_num"],
                "email": row["email"],
                "user_id": user.id,
                "role": role_name,
            })

        except Exception as e:
            db.session.rollback()
            failed.append({
                "row_num": row["row_num"],
                "email": row["email"],
                "error": str(e),
            })

    if created and not failed:
        db.session.commit()

    return {
        "created": created,
        "failed": failed,
        "total_processed": len(validated_rows),
        "total_created": len(created),
        "total_failed": len(failed),
    }


def import_users_from_csv(tenant_id: int, file_content: str | bytes) -> dict:
    """
    Full pipeline: parse → validate → import.
    Returns comprehensive result with validation errors and import results.
    """
    # 1. Parse
    rows = parse_csv(file_content)
    if not rows:
        raise BulkImportError("CSV file is empty or has no data rows")

    # 2. Validate
    validation = validate_import_rows(tenant_id, rows)

    # If there are limit errors (row_num=0), don't proceed
    limit_errors = [e for e in validation["errors"] if e["row_num"] == 0]
    if limit_errors:
        return {
            "status": "error",
            "message": "Import blocked: user limit would be exceeded",
            "validation_errors": validation["errors"],
            "total_rows": len(rows),
            "valid_count": len(validation["valid"]),
            "error_count": len(validation["errors"]),
            "import_result": None,
        }

    # 3. Import valid rows
    import_result = None
    if validation["valid"]:
        import_result = execute_bulk_import(tenant_id, validation["valid"])

    return {
        "status": "completed" if not validation["errors"] else "partial",
        "message": (
            f"Imported {len(validation['valid'])} users"
            + (f", {len(validation['errors'])} rows had errors" if validation["errors"] else "")
        ),
        "total_rows": len(rows),
        "valid_count": len(validation["valid"]),
        "error_count": len(validation["errors"]),
        "validation_errors": validation["errors"],
        "import_result": import_result,
    }


# ═══════════════════════════════════════════════════════════════
# Project Assignment Import (Story 4.2)
# ═══════════════════════════════════════════════════════════════

PROJECT_ASSIGN_TEMPLATE_HEADER = [
    "email", "full_name", "role", "program_id", "project_id", "starts_at", "ends_at",
]
PROJECT_ASSIGN_TEMPLATE_EXAMPLE = [
    ["user1@example.com", "John Doe", "project_member", "1", "2", "", ""],
    ["user2@example.com", "Jane Smith", "project_manager", "1", "2", "2026-03-01T00:00:00Z", "2026-06-01T00:00:00Z"],
]


def generate_project_assignment_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(PROJECT_ASSIGN_TEMPLATE_HEADER)
    writer.writerows(PROJECT_ASSIGN_TEMPLATE_EXAMPLE)
    return output.getvalue()


def _parse_optional_dt(raw: str, field_name: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BulkImportError(f"{field_name} must be ISO datetime") from exc
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_project_assignment_csv(file_content: str | bytes) -> list[dict]:
    if isinstance(file_content, bytes):
        file_content = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(file_content))
    fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
    required = {"email", "role", "program_id", "project_id"}
    missing = sorted(required - set(fieldnames))
    if missing:
        raise BulkImportError(f"CSV missing required columns: {', '.join(missing)}")

    rows = []
    for i, row in enumerate(reader, start=2):
        normalized = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        rows.append({
            "row_num": i,
            "email": normalized.get("email", ""),
            "full_name": normalized.get("full_name", ""),
            "role": normalized.get("role", ""),
            "program_id": normalized.get("program_id", ""),
            "project_id": normalized.get("project_id", ""),
            "starts_at": normalized.get("starts_at", ""),
            "ends_at": normalized.get("ends_at", ""),
        })
    return rows


def validate_project_assignment_rows(
    tenant_id: int,
    rows: list[dict],
    *,
    auto_create_users: bool = True,
) -> dict:
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise BulkImportError("Tenant not found", 404)

    existing_users = {u.email.lower(): u for u in User.query.filter_by(tenant_id=tenant_id).all()}
    programs = {p.id: p for p in Program.query.filter_by(tenant_id=tenant_id).all()}
    projects = {p.id: p for p in Project.query.filter_by(tenant_id=tenant_id).all()}
    available_roles = {
        r.name for r in Role.query.filter((Role.tenant_id == tenant_id) | (Role.tenant_id.is_(None)))
    }

    valid = []
    errors = []
    for row in rows:
        row_errors = []
        email = (row.get("email") or "").lower().strip()
        role = (row.get("role") or "").strip()

        if not email:
            row_errors.append("Email is required")
        else:
            try:
                email = validate_email(email, check_deliverability=False).normalized
            except EmailNotValidError as exc:
                row_errors.append(f"Invalid email: {exc}")

        if not role:
            row_errors.append("role is required")
        elif role not in available_roles:
            row_errors.append(f"Unknown role '{role}'")

        try:
            program_id = int(row.get("program_id") or 0)
            project_id = int(row.get("project_id") or 0)
            if program_id <= 0 or project_id <= 0:
                raise ValueError
        except ValueError:
            row_errors.append("program_id and project_id must be positive integers")
            program_id = None
            project_id = None

        starts_at = None
        ends_at = None
        try:
            starts_at = _parse_optional_dt(row.get("starts_at", ""), "starts_at")
            ends_at = _parse_optional_dt(row.get("ends_at", ""), "ends_at")
            if starts_at and ends_at and ends_at < starts_at:
                row_errors.append("ends_at must be >= starts_at")
        except BulkImportError as exc:
            row_errors.append(exc.message)

        if program_id and program_id not in programs:
            row_errors.append(f"Program {program_id} not found in tenant")
        if project_id and project_id not in projects:
            row_errors.append(f"Project {project_id} not found in tenant")
        if project_id in projects and program_id in programs:
            if projects[project_id].program_id != program_id:
                row_errors.append("project_id does not belong to program_id")

        if email and email not in existing_users and not auto_create_users:
            row_errors.append(f"User not found for email: {email}")

        if row_errors:
            errors.append({"row_num": row["row_num"], "email": row.get("email", ""), "errors": row_errors})
            continue

        valid.append({
            "row_num": row["row_num"],
            "email": email,
            "full_name": row.get("full_name", ""),
            "role": role,
            "program_id": program_id,
            "project_id": project_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        })
    return {"valid": valid, "errors": errors}


def execute_project_assignment_import(
    tenant_id: int,
    validated_rows: list[dict],
    *,
    actor_user_id: int | None = None,
    auto_create_users: bool = True,
) -> dict:
    created = []
    failed = []
    for row in validated_rows:
        try:
            with db.session.begin_nested():
                user = User.query.filter_by(tenant_id=tenant_id, email=row["email"]).first()
                user_created = False
                if not user:
                    if not auto_create_users:
                        raise BulkImportError(f"User not found for email: {row['email']}")
                    user = User(
                        tenant_id=tenant_id,
                        email=row["email"],
                        full_name=row.get("full_name", ""),
                        status="active",
                        auth_provider="csv_import",
                    )
                    db.session.add(user)
                    db.session.flush()
                    user_created = True

                # Membership (idempotent behavior: skip if already member).
                if not UserRole.query.filter_by(
                    user_id=user.id,
                    tenant_id=tenant_id,
                    program_id=row["program_id"],
                    project_id=row["project_id"],
                ).first():
                    try:
                        assign_to_project(
                            user.id,
                            row["project_id"],
                            role_in_project=row["role"],
                            assigned_by=actor_user_id,
                        )
                    except UserServiceError as exc:
                        if "already assigned" not in exc.message.lower():
                            raise

                assign_role(
                    user.id,
                    row["role"],
                    assigned_by=actor_user_id,
                    tenant_id=tenant_id,
                    program_id=row["program_id"],
                    project_id=row["project_id"],
                    starts_at=row.get("starts_at"),
                    ends_at=row.get("ends_at"),
                )

                created.append({
                    "row_num": row["row_num"],
                    "email": row["email"],
                    "user_id": user.id,
                    "created_user": user_created,
                    "program_id": row["program_id"],
                    "project_id": row["project_id"],
                    "role": row["role"],
                })
        except Exception as exc:
            failed.append({
                "row_num": row["row_num"],
                "email": row["email"],
                "error": str(exc),
            })

    db.session.commit()
    return {
        "created": created,
        "failed": failed,
        "total_processed": len(validated_rows),
        "total_created": len(created),
        "total_failed": len(failed),
    }


def import_project_assignments_from_csv(
    tenant_id: int,
    file_content: str | bytes,
    *,
    actor_user_id: int | None = None,
    auto_create_users: bool = True,
) -> dict:
    rows = parse_project_assignment_csv(file_content)
    if not rows:
        raise BulkImportError("CSV file is empty or has no data rows")
    validation = validate_project_assignment_rows(
        tenant_id,
        rows,
        auto_create_users=auto_create_users,
    )
    import_result = None
    if validation["valid"]:
        import_result = execute_project_assignment_import(
            tenant_id,
            validation["valid"],
            actor_user_id=actor_user_id,
            auto_create_users=auto_create_users,
        )
    return {
        "status": "completed" if not validation["errors"] else "partial",
        "message": (
            f"Processed {len(rows)} rows: {len(validation['valid'])} valid, "
            f"{len(validation['errors'])} validation errors"
        ),
        "total_rows": len(rows),
        "valid_count": len(validation["valid"]),
        "error_count": len(validation["errors"]),
        "validation_errors": validation["errors"],
        "import_result": import_result,
    }
