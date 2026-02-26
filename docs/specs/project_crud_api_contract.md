# Project CRUD API Contract

Date: 2026-02-24
Scope: Story 2.1 (`Program -> Project`)

## Security & Scope Rules
- JWT is mandatory for all project CRUD endpoints.
- `tenant_id` is read from JWT (`g.jwt_tenant_id`) and applied on every query.
- Unscoped primary-key lookups are forbidden.
- 404: resource not found in caller tenant scope.
- 403: caller is authenticated but violates scope rules (e.g. cross-program move).

## Endpoints

### 1. `GET /api/v1/programs/{program_id}/projects`
- Returns tenant-scoped project list for the program.

Sample response:
```json
[
  {
    "id": 12,
    "tenant_id": 3,
    "program_id": 44,
    "code": "TR-WAVE-01",
    "name": "Turkey Rollout",
    "type": "rollout",
    "status": "active",
    "owner_id": 18,
    "start_date": "2026-03-01",
    "end_date": null,
    "go_live_date": null,
    "is_default": true,
    "created_at": "2026-02-24T11:30:00+00:00",
    "updated_at": "2026-02-24T11:30:00+00:00"
  }
]
```

### 2. `POST /api/v1/programs/{program_id}/projects`
Sample request:
```json
{
  "code": "TR-WAVE-02",
  "name": "Turkey Rollout Wave 2",
  "type": "rollout",
  "status": "active",
  "owner_id": 18,
  "start_date": "2026-05-01",
  "end_date": "2026-09-30",
  "go_live_date": "2026-10-15",
  "is_default": false
}
```

Sample response (`201`):
```json
{
  "id": 13,
  "tenant_id": 3,
  "program_id": 44,
  "code": "TR-WAVE-02",
  "name": "Turkey Rollout Wave 2",
  "type": "rollout",
  "status": "active",
  "owner_id": 18,
  "start_date": "2026-05-01",
  "end_date": "2026-09-30",
  "go_live_date": "2026-10-15",
  "is_default": false,
  "created_at": "2026-02-24T11:32:00+00:00",
  "updated_at": "2026-02-24T11:32:00+00:00"
}
```

### 3. `GET /api/v1/projects/{project_id}`
- Returns a single tenant-scoped project.

### 4. `PUT /api/v1/projects/{project_id}`
- Allowed fields: `code, name, type, status, owner_id, start_date, end_date, go_live_date, is_default`.
- `tenant_id` and cross-program move attempts are rejected.

Sample request:
```json
{
  "name": "Turkey Rollout Wave 2 - Updated",
  "status": "on_hold"
}
```

### 5. `DELETE /api/v1/projects/{project_id}`
- Deletes tenant-scoped project record.

## Error Semantics
- `401`: Missing/invalid JWT identity.
- `403`: Permission denied or forbidden scope transition.
- `404`: Program/project not found within current tenant scope.
- `409`: Duplicate code or default-project uniqueness conflict.
