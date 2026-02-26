# User Project Assignment Flow (Story 4.2)

Date: 2026-02-24

## API Flow
1. Onboarding direct assignment:
   - `POST /api/v1/onboarding/step/admin/{tenant_id}`
   - Optional payload:
     - `project_id`
     - `project_role` (default: `project_manager`)
     - `assignment_starts_at` (ISO datetime)
     - `assignment_ends_at` (ISO datetime)
   - Behavior:
     - User is created.
     - Project membership is added.
     - Scoped role assignment is created on `tenant/program/project`.

2. Manual project member assignment:
   - `POST /api/v1/admin/projects/{project_id}/members`
   - Payload:
     - `user_id` (required)
     - `role_in_project`
     - `role_name` (scoped RBAC role)
     - `program_id` (optional, auto-derived from project if omitted)
     - `starts_at` / `ends_at` (optional temporary authority)
   - Response includes:
     - `member`
     - `role_assignment`

3. Bulk project assignment import:
   - `GET /api/v1/admin/users/import/project-assignments/template`
   - `POST /api/v1/admin/users/import/project-assignments/validate`
   - `POST /api/v1/admin/users/import/project-assignments`
   - Query param:
     - `auto_create_users=true|false` (default `true`)
   - CSV columns:
     - `email,full_name,role,program_id,project_id,starts_at,ends_at`
   - Validation output:
     - row-level errors with `row_num`, `email`, `errors[]`.

## Automatic Expiry Handling
1. Runtime evaluation:
   - Permission evaluator ignores assignments:
     - `is_active=false`
     - `starts_at` in future
     - `ends_at` in past
2. Scheduled expiry job:
   - Job key: `rbac_assignment_expiry`
   - Marks expired assignments inactive and writes audit action `user_role.expired`.

## Audit Trail
1. Membership and role changes write immutable audit entries:
   - `project_member.assigned`
   - `project_member.removed`
   - `user_role.assigned`
   - `user_role.removed`
   - `user_role.expired`
2. Audit payload includes actor, tenant/program/project scope, user, role and effective time window.

## UI Flow
1. Admin User Management:
   - Add member to selected project with role and optional validity window.
2. Bulk Import:
   - Download template.
   - Upload CSV for dry-run validation.
   - Fix row-level errors and import.
3. Onboarding Wizard:
   - Step Admin supports optional direct project assignment fields.
