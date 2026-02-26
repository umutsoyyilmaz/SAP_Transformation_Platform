# RBAC Scope Precedence (Story 4.1)

Date: 2026-02-24  
Owner: Architecture + Platform Team

## Precedence Rules
1. Deny-by-default: hiçbir eşleşen role assignment yoksa karar `deny`.
2. Scope hierarchy: `global < tenant < program < project`.
3. Assignment matching:
   - Tenant assignment, aynı tenant altındaki tüm program/project isteklerine uygulanır.
   - Program assignment, sadece ilgili program (ve o programın project’leri) için geçerlidir.
   - Project assignment, sadece ilgili project için geçerlidir.
4. Superuser bypass:
   - `platform_admin`, `tenant_admin` eşleşen scope içinde tüm permission’ları geçer.
5. Union semantics:
   - Eşleşen assignment’ların permission’ları birleşim alınır; explicit deny yoktur.
6. Deterministic evaluation:
   - Geçersiz scope kombinasyonu (`project_id` var, `program_id` yok gibi) hata üretir.

## Permission Matrix
| Role | Scope | requirements.read | requirements.create | tests.execute |
|---|---|---:|---:|---:|
| tenant_admin | tenant | allow | allow | allow |
| program_manager | program | allow | allow | deny |
| project_manager | project | allow | allow | deny |
| project_member | project | allow | deny | allow |
| readonly | tenant/program/project | allow | deny | deny |

## Notes
1. `project_member` ve `project_manager` rolleri membership tabanlı ek filtreye ihtiyaç duymadan project scope ile sınırlandırılır.
2. Legacy unscope çağrılar backward-compatible tutulur; yeni scope-aware akışlarda tenant/program/project parametreleri zorunlu kullanılmalıdır.
