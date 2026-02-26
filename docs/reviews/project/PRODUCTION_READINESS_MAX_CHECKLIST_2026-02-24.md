# PRODUCTION READINESS MAX CHECKLIST

Date: 2026-02-24  
Scope: Full production readiness gates for PERGA / SAP Transformation Platform  
Decision Rule: `GO` only if all `P0` are complete and evidenced.

## Status Legend
- `Done`: Completed and evidenced
- `Gap`: Not completed / insufficient evidence
- `In Progress`: Work started, not yet complete
- `Risk Accepted`: Explicit approval with owner and expiry date

## P0 - Release Blockers (Mandatory)

| ID | Control | Status | Owner | ETA | Evidence |
|---|---|---|---|---|---|
| P0-001 | Same-origin admin fallback removed | TBD | TBD | TBD | TBD |
| P0-002 | All API endpoints require auth + authorization | TBD | TBD | TBD | TBD |
| P0-003 | `API_AUTH_ENABLED=true` in production | TBD | TBD | TBD | TBD |
| P0-004 | API key via query param disabled in production | TBD | TBD | TBD | TBD |
| P0-005 | `db.create_all()` disabled in production startup | TBD | TBD | TBD | TBD |
| P0-006 | Auto schema ALTER on startup disabled | TBD | TBD | TBD | TBD |
| P0-007 | Alembic-only migration flow enforced | TBD | TBD | TBD | TBD |
| P0-008 | Migration rollback tested | TBD | TBD | TBD | TBD |
| P0-009 | `/health/db-diag` and `/health/db-columns` restricted | TBD | TBD | TBD | TBD |
| P0-010 | No exception details in API 500 responses | TBD | TBD | TBD | TBD |
| P0-011 | `SECRET_KEY` mandatory and rotated policy defined | TBD | TBD | TBD | TBD |
| P0-012 | JWT secret and expiry hardened | TBD | TBD | TBD | TBD |
| P0-013 | CSP removes `unsafe-eval` | TBD | TBD | TBD | TBD |
| P0-014 | CSP nonce/hash strategy for inline scripts | TBD | TBD | TBD | TBD |
| P0-015 | HSTS validated behind HTTPS termination | TBD | TBD | TBD | TBD |
| P0-016 | CORS wildcard removed, strict allowlist active | TBD | TBD | TBD | TBD |
| P0-017 | TLS enforced and HTTP redirects to HTTPS | TBD | TBD | TBD | TBD |
| P0-018 | Hardcoded secrets removed from repo/scripts | TBD | TBD | TBD | TBD |
| P0-019 | Smoke scripts require env credentials only | TBD | TBD | TBD | TBD |
| P0-020 | Production fail-fast on missing critical env vars | TBD | TBD | TBD | TBD |
| P0-021 | Rate limits active with Redis backend | TBD | TBD | TBD | TBD |
| P0-022 | Audit logs for privileged actions enabled | TBD | TBD | TBD | TBD |
| P0-023 | Backup and restore tested successfully | TBD | TBD | TBD | TBD |
| P0-024 | RPO/RTO targets defined and drill completed | TBD | TBD | TBD | TBD |
| P0-025 | DB pool and timeout validated under load | TBD | TBD | TBD | TBD |
| P0-026 | Liveness/readiness semantics validated | TBD | TBD | TBD | TBD |
| P0-027 | Deploy script health check endpoint validated | TBD | TBD | TBD | TBD |
| P0-028 | Runtime containers run as non-root | TBD | TBD | TBD | TBD |
| P0-029 | No critical findings in SAST/dep/container scans | TBD | TBD | TBD | TBD |
| P0-030 | Runbook + rollback runbook approved | TBD | TBD | TBD | TBD |

## P1 - High Priority (Should Be >=95% Before Go-Live)

| ID | Control | Status | Owner | ETA | Evidence |
|---|---|---|---|---|---|
| P1-001 | RBAC matrix documented and validated | TBD | TBD | TBD | TBD |
| P1-002 | DB least-privilege user model applied | TBD | TBD | TBD | TBD |
| P1-003 | DB credentials managed via secrets manager | TBD | TBD | TBD | TBD |
| P1-004 | Key rotation procedure operational | TBD | TBD | TBD | TBD |
| P1-005 | JWT/session revoke/logout flow tested | TBD | TBD | TBD | TBD |
| P1-006 | Brute-force and lockout protections active | TBD | TBD | TBD | TBD |
| P1-007 | CSRF model documented and tested | TBD | TBD | TBD | TBD |
| P1-008 | Security headers full-set validated | TBD | TBD | TBD | TBD |
| P1-009 | Upload size/MIME validation enforced | TBD | TBD | TBD | TBD |
| P1-010 | Centralized input validation coverage complete | TBD | TBD | TBD | TBD |
| P1-011 | Negative tests for SQLi/XSS/SSRF passed | TBD | TBD | TBD | TBD |
| P1-012 | Dependency pinning + SBOM available | TBD | TBD | TBD | TBD |
| P1-013 | CI quality gates mandatory | TBD | TBD | TBD | TBD |
| P1-014 | Branch protection + required reviews active | TBD | TBD | TBD | TBD |
| P1-015 | Release artifacts immutable/tagged | TBD | TBD | TBD | TBD |
| P1-016 | Stage-prod parity verified | TBD | TBD | TBD | TBD |
| P1-017 | IaC drift checks operational | TBD | TBD | TBD | TBD |
| P1-018 | Canary or blue/green strategy ready | TBD | TBD | TBD | TBD |
| P1-019 | Feature flags support safe rollback | TBD | TBD | TBD | TBD |
| P1-020 | API compatibility/versioning tested | TBD | TBD | TBD | TBD |
| P1-021 | API contract docs current | TBD | TBD | TBD | TBD |
| P1-022 | Idempotency on critical POST endpoints | TBD | TBD | TBD | TBD |
| P1-023 | Retry/backoff/circuit breaker defined | TBD | TBD | TBD | TBD |
| P1-024 | Async failure policy documented | TBD | TBD | TBD | TBD |
| P1-025 | Scheduler overlap/locking protections validated | TBD | TBD | TBD | TBD |
| P1-026 | Failed job/DLQ handling defined | TBD | TBD | TBD | TBD |
| P1-027 | Redis outage degrade mode tested | TBD | TBD | TBD | TBD |
| P1-028 | DB failover behavior tested | TBD | TBD | TBD | TBD |
| P1-029 | Cache invalidation strategy validated | TBD | TBD | TBD | TBD |
| P1-030 | Timezone/locale correctness validated | TBD | TBD | TBD | TBD |
| P1-031 | Retention/purge policy operational | TBD | TBD | TBD | TBD |
| P1-032 | PII masking + log redaction active | TBD | TBD | TBD | TBD |
| P1-033 | Audit trail tamper-resistance controls | TBD | TBD | TBD | TBD |
| P1-034 | Privacy delete/export request flow ready | TBD | TBD | TBD | TBD |
| P1-035 | DR environment validated | TBD | TBD | TBD | TBD |
| P1-036 | On-call rota + escalation matrix published | TBD | TBD | TBD | TBD |
| P1-037 | Incident response templates available | TBD | TBD | TBD | TBD |
| P1-038 | SLO/SLI and alert thresholds defined | TBD | TBD | TBD | TBD |
| P1-039 | Alert noise reduction and routing tuned | TBD | TBD | TBD | TBD |
| P1-040 | Ops/business dashboards complete | TBD | TBD | TBD | TBD |
| P1-041 | Correlation ID propagated end-to-end | TBD | TBD | TBD | TBD |
| P1-042 | Centralized log search operational | TBD | TBD | TBD | TBD |
| P1-043 | Distributed tracing configured | TBD | TBD | TBD | TBD |
| P1-044 | Cost observability active (DB/Redis/AI) | TBD | TBD | TBD | TBD |
| P1-045 | Capacity plan + autoscaling thresholds defined | TBD | TBD | TBD | TBD |
| P1-046 | Load test meets p95/p99 targets | TBD | TBD | TBD | TBD |
| P1-047 | Soak test passes without leak/degradation | TBD | TBD | TBD | TBD |
| P1-048 | Spike test resilience validated | TBD | TBD | TBD | TBD |
| P1-049 | Cold start and recovery time acceptable | TBD | TBD | TBD | TBD |
| P1-050 | Frontend cache-busting and asset immutability verified | TBD | TBD | TBD | TBD |

## P2 - Operational Excellence (Planned)

| ID | Control | Status | Owner | ETA | Evidence |
|---|---|---|---|---|---|
| P2-001 | Regular chaos tests scheduled | TBD | TBD | TBD | TBD |
| P2-002 | GameDay program active | TBD | TBD | TBD | TBD |
| P2-003 | Standardized postmortem and RCA process | TBD | TBD | TBD | TBD |
| P2-004 | Technical debt backlog with SLA | TBD | TBD | TBD | TBD |
| P2-005 | Runtime upgrade policy (Python/DB/Redis) | TBD | TBD | TBD | TBD |
| P2-006 | Zero-trust secret access model maturity | TBD | TBD | TBD | TBD |
| P2-007 | Multi-region strategy assessed | TBD | TBD | TBD | TBD |
| P2-008 | Archive/cold storage cost optimization | TBD | TBD | TBD | TBD |
| P2-009 | Synthetic monitoring from multiple regions | TBD | TBD | TBD | TBD |
| P2-010 | UX telemetry and funnel observability | TBD | TBD | TBD | TBD |
| P2-011 | Release train and freeze policy | TBD | TBD | TBD | TBD |
| P2-012 | Third-party dependency contingency plans | TBD | TBD | TBD | TBD |
| P2-013 | Compliance evidence automation | TBD | TBD | TBD | TBD |
| P2-014 | FinOps budget alarms and controls | TBD | TBD | TBD | TBD |
| P2-015 | Periodic external penetration test plan | TBD | TBD | TBD | TBD |

## Evidence Pack (Audit Bundle)

| ID | Artifact | Status | Owner | Link |
|---|---|---|---|---|
| E-001 | 30-day vulnerability report | TBD | TBD | TBD |
| E-002 | SAST/DAST/container scan results | TBD | TBD | TBD |
| E-003 | Migration dry-run + rollback logs | TBD | TBD | TBD |
| E-004 | Backup/restore drill report | TBD | TBD | TBD |
| E-005 | Load/soak/spike test reports | TBD | TBD | TBD |
| E-006 | Liveness/readiness verification outputs | TBD | TBD | TBD |
| E-007 | Alerting/pager test outputs | TBD | TBD | TBD |
| E-008 | Runbook approval records | TBD | TBD | TBD |
| E-009 | CAB/change approval evidence | TBD | TBD | TBD |
| E-010 | Post-deploy smoke test results | TBD | TBD | TBD |

## Go/No-Go Rule

- `GO`: All `P0` = Done with evidence, `P1` completion >= 95%
- `CONDITIONAL GO`: All `P0` = Done, `P1` completion 85-95%, explicit risk acceptance
- `NO-GO`: Any `P0` not complete or rollback/restore unproven

