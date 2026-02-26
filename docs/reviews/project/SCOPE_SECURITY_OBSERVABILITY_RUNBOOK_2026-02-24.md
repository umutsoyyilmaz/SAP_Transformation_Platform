# Scope Security Observability Runbook (Story 5.1)

Date: 2026-02-24  
Owner: Platform + Security Operations

## 1. Purpose
Tenant/program/project scope ihlallerini erken tespit etmek, triage etmek ve etkisini sınırlamak.

## 2. Covered Signals
1. `cross_scope_access_attempt`: Permission guard tarafından bloke edilen erişim denemeleri.
2. `scope_mismatch_error`: Eksik/yanlış scope ile yapılan kritik çağrılar.
3. Request log scope fields: `tenant_id`, `program_id`, `project_id`, `request_id`.
4. Audit scope fields: `tenant_id`, `program_id`, `project_id`.

## 3. Alert Rules
1. `SEC-CROSS-SCOPE-001`  
Threshold: 5 dakikada >= 3 `cross_scope_access_attempt`  
Severity: High
2. `SEC-SCOPE-MISMATCH-001`  
Threshold: 5 dakikada >= 5 `scope_mismatch_error`  
Severity: Medium

## 4. Triage Procedure
1. Affected tenant/program/project alanlarını çıkar:
   - `GET /api/v1/metrics/security/events?window=300`
2. İlk ve son `request_id` değerlerini al, request log ile join et.
3. Kaynak endpoint ve actor pattern’i doğrula:
   - sistematik tarama mı (`/api/v1/.../<id>` pattern), yoksa client regression mı.
4. Eğer cross-tenant şüphesi varsa geçici containment:
   - ilgili token/session revoke
   - tenant-level rate-limit sıkılaştırma
5. RCA aç:
   - eksik scope filter veya yanlış ownership check path’i çıkar.
6. Patch + test:
   - regression test mandatory (`security alerts + scope guard`).

## 5. Sample Structured Log Events
```json
{
  "level": "WARNING",
  "logger": "app.middleware.blueprint_permissions",
  "message": "Blueprint permission denied: user=42 required=projects.view endpoint=program.list_my_projects",
  "request_id": "f3ad01bc91aa",
  "tenant_id": 7,
  "program_id": 11,
  "project_id": 22,
  "event_type": "cross_scope_access_attempt",
  "security_code": "SEC-CROSS-SCOPE-001"
}
```

```json
{
  "level": "WARNING",
  "logger": "app.middleware.timing",
  "message": "Request: GET /api/v1/programs/11/projects 403 (12ms)",
  "request_id": "f3ad01bc91aa",
  "tenant_id": 7,
  "program_id": 11,
  "project_id": null
}
```

## 6. Dashboard Queries
1. Top blocked endpoints (last 1h):
```sql
SELECT details->>'required_permission' AS permission,
       path,
       COUNT(*) AS blocked_count
FROM security_events
WHERE event_type = 'cross_scope_access_attempt'
  AND ts >= NOW() - INTERVAL '1 hour'
GROUP BY 1,2
ORDER BY blocked_count DESC;
```

2. Scope mismatch trend (5m buckets):
```sql
SELECT DATE_TRUNC('minute', to_timestamp(ts)) AS minute_bucket,
       COUNT(*) AS mismatch_count
FROM security_events
WHERE event_type = 'scope_mismatch_error'
  AND ts >= EXTRACT(EPOCH FROM NOW() - INTERVAL '24 hour')
GROUP BY 1
ORDER BY 1;
```

3. Audit scope completeness check:
```sql
SELECT COUNT(*) AS missing_scope_rows
FROM audit_logs
WHERE tenant_id IS NULL
   OR (action LIKE '%.%' AND program_id IS NULL AND project_id IS NULL);
```

## 7. Escalation Matrix
1. High (SEC-CROSS-SCOPE-001): Security on-call + Platform lead, immediate triage (<15 min).
2. Medium (SEC-SCOPE-MISMATCH-001): Platform on-call, same-day fix target.
3. Repeated alerts (>=3/day same endpoint): release gate blocker.

