# Project Scope Migration - Production Rollout & Rollback Runbook (Story 6.2)

Date: 2026-02-24  
Owner: Platform Engineering + SRE + Product Ops  
Change Type: `Tenant -> Program -> Project` scope activation in production

## 1. Objective
Project-scope migration'i tenant segment bazlı canary rollout ile güvenli aktive etmek, regresyon halinde veri kaybı olmadan traffic-safe rollback uygulamak.

## 2. Preconditions
1. EPIC-1/2/3/4/5 migration ve guard testleri green.
2. `project_scope_enabled` feature flag tenant-bazlı kontrol edilebilir durumda.
3. Gözlemlenebilirlik aktif:
   - `cross_scope_access_attempt`
   - `scope_mismatch_error`
   - 4xx/5xx, p95 latency, request throughput
4. Rollback için verified backup snapshot + restore dry-run raporu mevcut.

## 3. Canary Rollout Phases (Tenant Segment)
| Phase | Tenant Segment | Traffic Share | Duration | Entry Criteria | Exit Criteria |
|---|---|---|---|---|---|
| 0 | Internal sandbox tenants | ~1% | 4 saat | Smoke + core regression green | P0 incident yok, error budget içinde |
| 1 | Low-risk pilot tenants | ~5% | 8 saat | Phase 0 stable | 4xx/5xx baseline +10% altında, no cross-tenant incident |
| 2 | Medium-risk tenants | ~20% | 12 saat | Phase 1 stable | Scope mismatch alert seviyesi Medium altında |
| 3 | Broad production rollout | ~50% | 12 saat | Phase 2 stable | Support ticket anomalisi yok, SLO ihlali yok |
| 4 | Full rollout | 100% | 24 saat monitor | Phase 3 stable | 24 saat boyunca rollback trigger yok |

## 4. Feature Flag Activation/Deactivation
### Activation Steps (Per Phase)
1. Canary segment tenant list'ini change ticket'a ekle.
2. `project_scope_enabled=false` iken pre-check al:
   - API smoke
   - `/api/v1/me/projects` authorization checks
3. Segment için `project_scope_enabled=true` yap.
4. 15 dk yoğun gözlem:
   - 403/404 semantics
   - `scope_mismatch_error` trend
5. 60 dk stabilite onayı sonrası phase advance kararı al.

### Deactivation (Fast Safety Switch)
1. Problemli tenant segmentte `project_scope_enabled=false`.
2. In-flight istekler için 5 dakika boyunca elevated monitoring.
3. Segment-specific support duyurusu: "project-aware features temporarily disabled".
4. RCA kaydı aç, re-enable için fix criteria tanımla.

## 5. Rollback Triggers (Go -> No-Go)
1. P0 security: cross-tenant veri sızıntısı veya unauthorized data exposure.
2. P0 availability: 10 dakikada 5xx oranı baseline'a göre +50% üstü.
3. P1 functional: critical journey (project CRUD / context resolve) success < %95.
4. Guard breach: data-quality job'da critical orphan/mismatch artışı.
5. On-call + Product + Security ortak kararıyla manual rollback.

## 6. Rollback Procedure (Schema-safe + Traffic-safe, No Data Loss)
1. Immediate containment:
   - Etkilenen tenant segmentte `project_scope_enabled=false`.
   - Gerekirse write-heavy endpointlere geçici rate-limit.
2. Traffic stabilization:
   - API error oranı normalize olana kadar canary freeze.
   - Destek ekibine incident banner metni geç.
3. Data safety:
   - Migration additive olduğu için destructive schema rollback yapılmaz.
   - `project_id` yazılmış kayıtlar korunur, backward-compatible read path aktif kalır.
4. Verification:
   - Core smoke + isolation negative tests rerun.
   - `cross_scope_access_attempt` ve `scope_mismatch_error` baseline'a dönmeli.
5. Decision:
   - Root cause fix + test evidence olmadan tekrar activate edilmez.

## 7. MTTR Targets
| Severity | Definition | Detection SLA | Mitigation SLA | Recovery SLA | MTTR Target |
|---|---|---|---|---|---|
| P0 | Security leak / tenant isolation break | 5 dk | 15 dk | 60 dk | <= 60 dk |
| P1 | Core function degradation | 10 dk | 30 dk | 120 dk | <= 120 dk |
| P2 | Non-critical UX/API regressions | 30 dk | 4 saat | 24 saat | <= 24 saat |

## 8. Communication Checklist (Product / Support / Ops)
### Pre-Deploy
1. Change announcement: kapsam, tenant segment, risk, rollback plan.
2. Support briefing: beklenen semptomlar, escalation route.
3. Ops briefing: dashboard linkleri, alert threshold'lar, on-call sahipleri.

### During Rollout
1. Her phase geçişinde kısa durum güncellemesi paylaş.
2. Alert tetiklenirse 15 dk içinde incident channel aç.
3. Canary freeze/continue kararını Product + Ops birlikte logla.

### Post-Deploy
1. 24 saatlik stabilization raporu yayınla.
2. Açık aksiyonlar ve takip ETA'larını ekle.
3. Sign-off kayıtlarını release ticket'a attach et.

## 9. Go / No-Go Checklist
| Check | Owner | Go Criteria | No-Go Criteria |
|---|---|---|---|
| Security isolation tests | Security QA | %100 pass | herhangi bir fail |
| Regression pack | QA | green | fail |
| Data quality report | Data/Ops | critical=0 veya approved mitigation | critical unresolved |
| Observability dashboards | SRE | canlı + doğru veri | eksik/yanlış sinyal |
| Rollback switch test | Platform | feature flag deactivate başarıyla testli | testsiz |
| Stakeholder readiness | Product/Ops | communication complete | incomplete |

## 10. Ownership Matrix (RACI)
| Workstream | Platform Eng | SRE | Security | QA | Product | Support |
|---|---|---|---|---|---|---|
| Flag rollout execution | R | A | C | C | C | I |
| Runtime monitoring | C | R/A | C | I | I | I |
| Security triage | C | C | R/A | C | I | I |
| Regression validation | C | I | C | R/A | I | I |
| Go/No-Go decision | C | C | C | C | R/A | I |
| Customer communication | I | I | I | I | A | R |

Legend: `R=Responsible`, `A=Accountable`, `C=Consulted`, `I=Informed`

## 11. Execution Log Template
```text
Phase:
Timestamp (UTC):
Segment:
Flag State:
Key Metrics (4xx/5xx, p95, alerts):
Decision: continue / hold / rollback
Owner:
Notes:
```
