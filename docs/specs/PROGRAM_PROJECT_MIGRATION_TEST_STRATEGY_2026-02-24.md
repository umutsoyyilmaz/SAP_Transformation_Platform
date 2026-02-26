# Program -> Project Migration Test Strategy (Story 6.1)

Date: 2026-02-24  
Owner: QA + Platform Engineering  
Scope: Tenant/Program/Project isolation and migration safety

## 1. Objective
Program->Project geçişinde veri izolasyonu, yetki doğruluğu ve client geriye dönük uyumluluğu için test kapsamını standardize etmek.

## 2. Test Layers
1. Unit
   - Scope resolver (`get_scoped`, fallback resolver, URL context parsing)
   - RBAC evaluator (tenant/program/project scoped permissions, deny-by-default)
2. Integration
   - API ownership checks (JWT tenant scope, program/project ownership)
   - Cross-tenant / cross-program / cross-project negative paths
3. E2E / UI Contract
   - Program+Project selector state
   - My Projects personalization and URL/state sync
4. Security
   - IDOR vectors (direct ID access with foreign tenant/project IDs)
   - Scope mismatch and forbidden access telemetry/alerts

## 3. Suite Mapping
### Unit
1. `tests/test_scoped_queries.py`
2. `tests/test_project_scope_resolver.py`
3. `tests/test_rbac_scope_aware.py`

### Integration
1. `tests/test_api_projects.py`
2. `tests/test_tenant_isolation.py`
3. `tests/test_my_projects_visibility.py`
4. `tests/test_scope_observability_story_51.py`
5. `tests/test_data_quality_guard_jobs.py`

### E2E / UI Contract
1. `tests/test_context_url_routing_contract.py`
2. `tests/test_program_projects_ui_contract.py`
3. `tests/test_my_projects_ui_contract.py`

### Security-Focused Negatives
1. Cross-tenant read/write -> 404/403 semantics
2. Missing/invalid scope args -> explicit reject + security event
3. Unscoped lookup guard -> CI fail

## 4. Explicit Negative Test Matrix
1. `tenant A` token with `tenant B` resource id -> blocked.
2. `program_id` valid, `project_id` foreign program -> blocked.
3. `project_id` without valid `program_id` context -> fallback reject.
4. `db.session.get()` style unscoped lookup introduction -> guard test fail.
5. Default project fallback when flag disabled -> reject.
6. URL `program_id/project_id` invalid combinations -> sanitize + event.

## 5. Test Data Strategy
1. Base fixtures:
   - 2 tenant
   - tenant başına 2 program
   - program başına >=2 project (1 default + 1 non-default)
2. Role fixtures:
   - `tenant_admin`, `program_manager`, `project_manager`, `project_member`, `viewer/readonly`
3. Deterministic factories:
   - UUID-suffix email/slug generation
   - explicit ownership mapping (`tenant_id`, `program_id`, `project_id`)
4. Isolation assertions:
   - same PK pattern on different tenant not leaked
   - all API assertions verify both status code and payload shape

## 6. Release Gate Criteria (Pass/Fail)
1. Unit gate:
   - `scope/rbac` suite pass rate: 100%
2. Isolation gate:
   - critical negative tests pass rate: 100%
   - cross-tenant/cross-project bypass count: 0
3. Regression gate:
   - project-scope regression pack pass rate: 100%
4. Coverage gate (target):
   - changed lines in scope-related services: >=85%
   - overall backend coverage floor: >=75%
5. Performance guard:
   - regression suite runtime PR pipeline <=20 min
6. Go/No-Go:
   - any P0/P1 security/isolation test fail => release fail

## 7. CI Execution Matrix
| Stage | Suite | Command | Trigger | Estimated Runtime |
|---|---|---|---|---|
| PR-1 | Lint | `ruff check . && ruff format --check .` | PR/Main | 2-3 min |
| PR-2 | Core test | existing `pytest tests/ ...` | PR/Main | 10-14 min |
| PR-3 | Project-scope regression pack | `bash scripts/ci_project_scope_regression.sh` | PR/Main | 6-10 min |
| Nightly-1 | Extended E2E | `python scripts/e2e_extended_test.py` | Nightly | 15-25 min |
| Nightly-2 | Security replay (IDOR corpus) | targeted negative suite rerun | Nightly | 5-8 min |

Total PR runtime estimate: 18-27 min.

## 8. Regression Pack Pipeline Integration
1. Script: `scripts/ci_project_scope_regression.sh`
2. CI step: `Project-Scope Regression Pack`
3. Fail-fast policy: any failure blocks merge.

## 9. Exit Checklist
1. Tüm listed suites green.
2. Scope security alerts baseline altında.
3. Data quality guard report kritikleri 0 veya approved remediation plan var.
4. Release gate kriterleri dokümante edilmiş ve imzalanmış.

