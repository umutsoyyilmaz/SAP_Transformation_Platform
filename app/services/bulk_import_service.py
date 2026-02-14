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
