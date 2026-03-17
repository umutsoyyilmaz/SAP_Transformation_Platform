# Test Management Sprint Backlog

Date: 2026-03-11  
Owner: QA Platform + Testing Domain Team  
Source: `docs/plans/TEST_MANAGEMENT_REMEDIATION_PLAN_2026-03-11.md`  
Scope: Test Planning, Test Execution, Defect Management, Evidence, Sign-off, Traceability

## 1. Objective

Test Management modulunu:

1. scope-safe
2. project-aware
3. SAP proje operasyonlarina uygun
4. performansli
5. testlerle korunmus

hale getirmek.

Bu backlog net-new feature listesi degil; audit bulgularini kapatmak ve modulu production-grade operasyon seviyesine tasimak icin uygulanabilir delivery planidir.

## 2. Planning Assumptions

1. Sprint suresi: 2 hafta
2. Bir sprintte 2 backend engineer + 1 frontend engineer + 1 QA/shared owner varsayildi
3. Eforlar net engineering gunu olarak verildi
4. P0/P1 item'lar bitmeden genis UI/genisletme feature'lari alinmaz

## 3. Ownership Model

| Owner | Sorumluluk |
|---|---|
| Architecture | scope kurallari, domain dili, migration kararlari |
| Backend | model/service/blueprint degisiklikleri, read model, security guard |
| Frontend | context, UX akislari, CTA, render ve navigation tutarliligi |
| QA | negatif testler, smoke, contract, regression gate |
| Product/Test Lead | SAP operasyon akislari, role matrix, UAT sign-off, readiness beklentileri |

## 4. Sprint Roadmap

| Sprint | Theme | Hedef | Tahmini Yuk |
|---|---|---|---|
| TM-S1 | Security + User Blocking Fixes | Scope leak, integrity, execute/evidence acil problemler | 18-22 gun |
| TM-S2 | Context + Domain Normalization | project context, lifecycle, coverage, vocabulary | 18-21 gun |
| TM-S3 | SAP Operational Hardening | environment/build/sign-off/readiness/roles | 16-20 gun |
| TM-S4 | Performance + CI Hardening | read-model, perf, deterministic smoke, release gates | 18-22 gun |

## 4.1 Current Status - 2026-03-12

### Buyuk olcude tamamlanan epikler

- EPIC-1 Scoped Data Access Retrofit
- EPIC-2 User Blocking Journey Repair
- EPIC-3 Project Context Normalization
- EPIC-4 Domain Vocabulary and Lifecycle Cleanup
- EPIC-6 Read Model and Performance Hardening
- EPIC-7 Test Harness and Release Gates

### Aktif epikler

- EPIC-5 SAP Operational Readiness
- EPIC-12 Documentation, runbook and operating model refresh

Not: EPIC-6 kapsami tamamlandi. Kalan analytics/read-model iyilestirmeleri artik EPIC-6-sonrasi follow-up optimizasyon backlog'u olarak izleniyor.

### Park edilen dusuk oncelikli alanlar

- governance/reporting helper mikro-konsolidasyonlari
- kritik smoke kapsaminda olmayan ek Playwright helper temizligi

## 5. Epic Backlog

## EPIC-1: Scoped Data Access Retrofit

Priority: P0  
Sprint: TM-S1  
Suggested Owner: Backend + Architecture

### Story 1.1 - Testing detail endpoint scope inventory
Tasks:
1. Tum testing detail endpoint'lerini cikar ve scope davranisini tablo halinde belge.
2. `_get_or_404`, `db.session.get`, direct query kullanimlarini siniflandir.
3. Riskli endpoint'leri `read leak`, `write leak`, `integrity leak` diye etiketle.

Definition of Done:
1. Touched route inventory tamam.
2. P0 route listesi net.
3. Refactor sirasina gore uygulanabilir tablo hazir.

Effort: 1 gun  
Owner: Architecture

### Story 1.2 - Scoped resolver helper standardi
Tasks:
1. Testing entity'leri icin ortak scoped resolve helper ekle.
2. Tenant/program/project parametreleri olmadan resolve edilemeyen API tasarla.
3. Error semantics'i standardize et: `403` vs `404`.

Definition of Done:
1. Helper tek kullanim noktasi olur.
2. Scope gerektiren entity lookup'lar unscoped calismaz.
3. Unit testler helper davranisini korur.

Effort: 2 gun  
Owner: Backend

### Story 1.3 - Detail endpoint refactor
Tasks:
1. Plan, cycle, case, execution, defect, suite detail endpoint'lerini helper'a tasi.
2. Scope testlerini yaz.
3. Eski lookup pattern'lerini temizle.

Definition of Done:
1. Cross-project access negatif testleri green.
2. API behavior documented.
3. P0 read leak kalmaz.

Effort: 3 gun  
Owner: Backend

### Story 1.4 - Write path integrity guards
Tasks:
1. `create_test_execution`, `add_case_to_suite`, `add_case_to_plan`, `import_from_suite`, `quick_run` icin same-project guard ekle.
2. Hata mesajlarini kullaniciya anlasilir yap.
3. Negative API testlerini ekle.

Definition of Done:
1. Foreign entity baglama reddedilir.
2. Dashboard/coverage sessiz kirlenmez.
3. Integrity regression testleri green.

Effort: 3 gun  
Owner: Backend

## EPIC-2: User Blocking Journey Repair

Priority: P0  
Sprint: TM-S1  
Suggested Owner: Frontend + Backend

### Story 2.1 - Execution entry standardi
Tasks:
1. Suite, case detail, plan detail ve defect panel icin resmi execution entry pattern'i tanimla.
2. Buton etiketleri ve hedef ekran davranisini standardize et.
3. Dead CTA taramasini test ile koru.

Definition of Done:
1. Kullanici execute giriisini her ana ekranda bulur.
2. CTA'lar ilgili cycle/execution'a indirir.
3. UI contract testine dahil olur.

Effort: 2 gun  
Owner: Frontend

### Story 2.2 - Evidence Capture SPA compliance
Tasks:
1. Evidence view root selector'ini `mainContent` ile hizala.
2. Evidence route render + modal davranisini duzelt.
3. Execution -> Evidence deep-link smoke testi ekle.

Definition of Done:
1. Evidence sayfasi body'ye dump etmez.
2. Layout bozulmaz.
3. Smoke test green.

Effort: 1 gun  
Owner: Frontend

### Story 2.3 - Deep-link and context recovery
Tasks:
1. `TestCaseDetailView` ve ilgili ekranlarda lazy context resolve ekle.
2. `TestingShared.getProgram()` / aktif project senkronizasyonunu netlestir.
3. Hatali durumda anlasilir recovery banner ekle.

Definition of Done:
1. Deep-link acilisi gereksiz `programs` redirect'i yapmaz.
2. Case/defect/execution cross-navigation stabil calisir.
3. Manual QA checklist gecilir.

Effort: 2 gun  
Owner: Frontend

## EPIC-3: Project Context Normalization

Priority: P0  
Sprint: TM-S2  
Suggested Owner: Frontend + Architecture

### Story 3.1 - Testing project context policy
Tasks:
1. Testing modulu icin resmi context contract yaz: hangi ekran `program_id`, hangisi `project_id` kullanir.
2. Explore ve Testing baglantilarinda canonical scope kurali belirle.
3. Contract'i helper ve UI katmanina yansit.

Definition of Done:
1. Tek policy dokumani var.
2. Frontend ve backend ayni scope contract'i kullanir.
3. Audit bulgusundaki karisiklik kapatilir.

Effort: 1 gun  
Owner: Architecture

### Story 3.2 - Frontend Explore API scope fix
Tasks:
1. TM view'larinda `project_id=${pid}` ve benzeri hatali cagrilari aktif project context ile degistir.
2. Missing project durumunu kullanıcıya acik goster.
3. Project-aware contract/UI testleri ekle.

Definition of Done:
1. `project.id != program.id` fixture'larinda UI bos kalmaz.
2. Scope picker'lar dogru veri getirir.
3. Regression tests green.

Effort: 3 gun  
Owner: Frontend

### Story 3.3 - Backend scope validation hardening
Tasks:
1. Testing tarafindan cagiran Explore endpoint'leri icin explicit `project_id` validation ekle.
2. `program_id` fallback kullanilan servisleri audit et.
3. Gecis gerekiyorsa warning/metrics ekle.

Definition of Done:
1. Yanlis scope request'leri sessizce yanlis veri donmez.
2. Gecici fallback'ler izlenebilir olur.
3. Integration testler green.

Effort: 2 gun  
Owner: Backend

## EPIC-4: Domain Vocabulary and Lifecycle Cleanup

Priority: P0  
Sprint: TM-S2  
Suggested Owner: Backend + Product/Test Lead

### Story 4.1 - Defect lifecycle canonicalization
Tasks:
1. Kanonik durum kumesini kesinlestir: `new, assigned, in_progress, resolved, retest, closed, reopened, rejected, deferred`.
2. `fixed` icin adapter/migration stratejisi uygula.
3. FSM, dashboard ve UI badge/filters'i ayni vocabulary'ye cek.

Definition of Done:
1. `resolved` defect'ler retest akislariyla uyumlu.
2. UI, API ve testler tek vocabulary kullanir.
3. E2E suite canonical state ile calisir.

Effort: 3 gun  
Owner: Backend

### Story 4.2 - Test layer and plan type alignment
Tasks:
1. `unit/string/sit/uat/regression/cutover_rehearsal/performance` vocabulary kararini finalize et.
2. Model comment, UI labels, create modal ve quick-run davranisini normalize et.
3. Backward-compat notlarini belge.

Definition of Done:
1. Plan type ve cycle layer tutarli.
2. Quick-run, plan create ve dashboard ayni vocabulary'yi kullanir.
3. Contract testleri green.

Effort: 2 gun  
Owner: Backend + Frontend

### Story 4.3 - Coverage correctness fix pack
Tasks:
1. `l3_scope_coverage()` project-aware filtre bug'ini duzelt.
2. `project != program` senaryosu icin API test ekle.
3. Coverage ekrani/metrics regression check ekle.

Definition of Done:
1. Coverage dogru hesaplanir.
2. Legacy fixture maskesi kirilir.
3. Test ile korunur.

Effort: 2 gun  
Owner: Backend

## EPIC-5: SAP Operational Readiness

Priority: P1  
Sprint: TM-S3  
Suggested Owner: Product/Test Lead + Backend

Status: Completed - 2026-03-12

Completion note:
1. Cycle operasyon metadata modeli (`environment`, `build_tag`, `transport_request`, `deployment_batch`, `release_train`, `owner`) backend + UI + migration smoke ile tamamlandi.
2. Approval, retest/sign-off ve cutover go/no-go aksiyonlari operasyonel rol matrisiyle guard edildi; negatif role testleri eklendi.
3. `release-readiness` aggregate endpoint'i ve Overview/Execution Center/Test Plan Detail ekranlari SAP release governance zincirine hizalandi.

### Story 5.1 - Environment and build metadata standard
Tasks:
1. Plan/cycle/execution icin environment ve build/transport semantic modelini netlestir.
2. UI gorunumlerini ve validation'lari ekle/guncelle.
3. Reporting/readiness alanlarina yansit.

Definition of Done:
1. Her cycle icin environment ve build referansi gorulebilir.
2. SAP transport/build context execution ile baglanir.
3. Field contract dokumani guncel.

Effort: 3 gun  
Owner: Backend + Frontend

### Story 5.2 - Role matrix and operational permissions
Tasks:
1. Test Manager, SIT Lead, UAT Lead, Business Tester, BPO, Release Manager rolleri icin action matrix cikar.
2. Retest, sign-off, go/no-go ve approval aksiyonlarina role guard ekle.
3. Negatif role testlerini yaz.

Definition of Done:
1. Kritik aksiyonlar role-aware.
2. SAP operasyon rolleri dokumante.
3. Permission smoke testleri green.

Effort: 3 gun  
Owner: Architecture + Backend

### Story 5.3 - Release readiness chain hardening
Tasks:
1. Defect -> retest -> approval -> sign-off -> go/no-go veri akisini hizala.
2. Readiness panel'lerinde missing-linkage / ready-now / blocked reason'lari net goster.
3. UAT sign-off ve evidence zincirini release kararinda kullan.

Definition of Done:
1. Release readiness ekranlari gercek operasyonel anlam tasir.
2. Next action mesajlari tutarli ve dogru.
3. E2E smoke coverage var.

Effort: 4 gun  
Owner: Backend + Frontend

## EPIC-6: Read Model and Performance Hardening

Priority: P1  
Sprint: TM-S4  
Suggested Owner: Backend

Status: Completed - 2026-03-12

Completion note:
1. `overview-summary`, `execution-center` ve `case execution-history` endpoint'leri eklendi.
2. `test_overview.js`, `test_execution.js` ve `test_case_detail.js` fan-out pattern'inden cikarildi.
3. Hedefli pytest, UI contract ve TM Playwright smoke setleri green.

### Story 6.1 - Overview aggregate endpoint
Tasks:
1. Test Overview icin aggregate payload endpoint tasarla.
2. Plan/cycle detaylarini toplu hesaplayan backend path ekle.
3. Frontend fan-out'u kaldir.

Definition of Done:
1. Overview tek veya cok az request ile yuklenir.
2. Ayni metrikler korunur.
3. Perf smoke test green.

Effort: 3 gun  
Owner: Backend

### Story 6.2 - Execution Center aggregate endpoint
Tasks:
1. Execution Center queue/failed/blocked/retest icin toplu read model olustur.
2. Cycle detail fetch pattern'ini sadeleştir.
3. Frontend fetch davranisini optimize et.

Definition of Done:
1. Execution Center request firtinasi uretmez.
2. Queue ekranlari daha hizli acilir.
3. Existing ops behavior korunur.

Effort: 4 gun  
Owner: Backend + Frontend

### Story 6.3 - Test case execution history query optimization
Tasks:
1. Case detail executions tab'i icin toplu history endpoint ekle.
2. Tum plan/cycle traversal'ini kaldir.
3. UI render suresini olc.

Definition of Done:
1. Case detail execution history dogrudan gelir.
2. Buyuk veri hacminde ekran stabil kalir.
3. Perf regression testi var.

Effort: 2 gun  
Owner: Backend

## EPIC-7: Test Harness and Release Gates

Priority: P1  
Sprint: TM-S4  
Suggested Owner: QA + Backend
Status: Completed - 2026-03-12

Completion Notes:
1. Project-aware TM fixture pack devreye alindi; `project.id != program.id` ve SQLite FK-on davranisi release gate testlerinde sabitlendi.
2. `tm-integrity-gate`, `tm-migration-smoke`, `tm-ui-smoke` ve `tm-release-gate` komutlari eklendi; CI'da TM integrity + migration smoke aktif.
3. TM migration smoke, legacy auth/project bootstrap baseline'i ile son TM foundation revision'i `z4n5o6p7k823` seviyesinde green calisiyor.
4. UI contract ve TM Playwright smoke kapsaminda deep-link, quick-run, retest queue, evidence ve execution chain runtime sorunlari yakalanip kapatildi.

### Story 7.1 - Project-aware fixture pack
Tasks:
1. `project.id != program.id` fixture standardi kur.
2. Legacy fixture kullanimlarini temizle.
3. TM API testlerinde yeni fixture'i default yap.

Definition of Done:
1. Scope karisikliklari fixture ile maskelenmez.
2. Coverage/context bug'lari testte gorunur olur.
3. Test suite green.

Effort: 2 gun  
Owner: QA + Backend

### Story 7.2 - DB integrity and CI alignment
Tasks:
1. SQLite FK enforcement ac veya Postgres CI slice ekle.
2. Integrity testleri CI gate'e bagla.
3. Migration smoke komutu ekle.

Definition of Done:
1. Iliski butunlugu testte gercekci olur.
2. CI'da integrity regressions fail eder.
3. Release checklist'e baglanir.

Effort: 3 gun  
Owner: Backend + QA

### Story 7.3 - UI contract and smoke expansion
Tasks:
1. UI contract testlerine runtime root/context/deep-link kontrolleri ekle.
2. Playwright TM suite'ini isolated seed/teardown ile calistir.
3. Critical smoke pack: quick-run, retest queue, evidence, execution chain.

Definition of Done:
1. Bugun yakalanmayan runtime hatalari testte yakalanir.
2. Stateful dev DB bagimliligi kalkar.
3. Deterministic smoke suite green.

Effort: 4 gun  
Owner: QA + Frontend

## EPIC-8: Analytics and Read-Model Optimization

Priority: P1  
Sprint: TM-S5  
Suggested Owner: Backend + QA
Status: In Progress - 2026-03-12

Scope note:
1. Bu epic yeni aggregate endpoint ihtiyacindan degil, mevcut read-model'lerin buyuk hacimde daha stabil, daha ucuz ve semantik olarak daha tutarli calismasindan sorumludur.
2. Kapsam ozellikle `dashboard`, `traceability matrix`, `overview-summary` ve `execution-center` aggregate shaping katmanidir.

### Story 8.1 - Dashboard aggregate shaping
Tasks:
1. `compute_dashboard()` icindeki tekrarli count/list pass'lerini tek aggregate helper setine indir.
2. `pass`, `fail`, `blocked`, `not_run`, `deferred`, `total_executed` ve coverage summary semantigini tek yerde normalize et.
3. Dashboard summary icin project-scoped regresyon testlerini genislet.

Definition of Done:
1. Dashboard summary alanlari tekrarli sorgu ve ikinci/ucuncu shaping pass'leri olmadan hesaplanir.
2. `blocked` ve `deferred` davranisi test ile korunur.
3. Hedefli dashboard regresyon seti green.

Effort: 3 gun  
Owner: Backend

### Story 8.2 - Traceability matrix payload optimization
Tasks:
1. Requirement -> test case -> defect payload build akisinda tekrarli ORM/dict donusumlerini prebuilt map/set owner'larina indir.
2. Summary alanlari (`requirements_with_tests`, `unlinked_test_cases`, `total_defects`) matrix disi veriyi saymayacak sekilde netlestir.
3. Traceability response shape'ini buyuk veri hacminde daha hafif hale getirecek trimming kurallarini uygula.

Definition of Done:
1. Traceability matrix daha kucuk ve daha tutarli payload uretir.
2. Summary semantigi matrix icindeki gercek zincir ile birebir uyumludur.
3. Hedefli traceability regresyon seti green.

Effort: 3 gun  
Owner: Backend

### Story 8.3 - Overview and Execution aggregate alignment
Tasks:
1. `overview-summary`, `execution-center`, `cycle-risk`, `retest-readiness` ve `release-readiness` icin ortak aggregate helper sahipligini netlestir.
2. Ayni entity ayni summary mantigi ile iki farkli ekranda farkli sayilmiyorsa bunu testle sabitle.
3. UI contract seviyesinde aggregate alan adlari ve panel kontratlarini guncelle.

Definition of Done:
1. Overview ve Execution Center ayni read-model semantigini kullanir.
2. Frontend tarafinda yeni fan-out veya local summary hesaplama geri donmez.
3. API + UI contract testleri green.

Effort: 2 gun  
Owner: Backend + Frontend

### Story 8.4 - Perf budget and regression gate
Tasks:
1. `dashboard`, `traceability matrix`, `overview-summary` ve `execution-center` icin orta/yüksek hacim fixture senaryolari tanimla.
2. Query count, response size veya elapsed time uzerinden basit bir perf baseline olustur.
3. Bu baseline'i hedefli regression komutuna veya CI raporuna bagla.

Definition of Done:
1. Read-model optimizasyonu sadece sezgisel degil, olculebilir hale gelir.
2. Buyuk hacimde belirgin regresyonlar release oncesi gorunur olur.
3. Perf smoke veya benchmark komutu dokumante edilmis durumda.

Effort: 3 gun  
Owner: Backend + QA

## 6. Sprint Commit Recommendation

### TM-S1 Commit Scope

- EPIC-1 tamam
- EPIC-2 tamam

Release message:
`Testing scope leaks closed and core execution journeys stabilized.`

### TM-S2 Commit Scope

- EPIC-3 tamam
- EPIC-4 tamam

Release message:
`Testing domain semantics normalized around project-aware context and canonical lifecycle rules.`

### TM-S3 Commit Scope

- EPIC-5 tamam

Release message:
`Testing module aligned to SAP operational readiness and release governance workflows.`

### TM-S4 Commit Scope

- EPIC-6 tamam
- EPIC-7 tamam

Release message:
`Testing module hardened for scale, deterministic regression, and release-gated operation.`

### TM-S5 Commit Scope

- EPIC-8 tamam

Release message:
`Testing analytics and read-models hardened for semantic correctness and measurable scale.`

## 7. Dependency Map

| Once | Sonra |
|---|---|
| EPIC-1 | EPIC-6 |
| EPIC-2 | EPIC-5 |
| EPIC-3 | EPIC-4 |
| EPIC-4 | EPIC-5 |
| EPIC-5 | EPIC-7 smoke |
| EPIC-6 | EPIC-8 |
| EPIC-8 | performance gate |

## 8. Suggested Staffing

| Role | FTE | Sprint Focus |
|---|---:|---|
| Backend Engineer A | 1.0 | scope, integrity, lifecycle, read models |
| Backend Engineer B | 1.0 | SAP metadata, permissions, readiness, CI |
| Frontend Engineer | 1.0 | context, UX, evidence, execution chain, fetch optimization |
| QA / SDET | 0.75 | contract, smoke, negative scope tests, isolated harness |
| Architecture Lead | 0.25 | domain rules, migration review, acceptance gate |
| Product / Test Lead | 0.25 | SAP role matrix, sign-off workflow, readiness expectations |

## 9. Delivery Guardrails

1. Her story API + UI + test + docs birlikte kapanir.
2. Unscoped lookup ekleyen PR merge edilmez.
3. `project_id` gerektiren akislarda fallback sessiz calisamaz.
4. Canonical domain vocabulary disina yeni enum eklenmez.
5. Smoke suite kirmiziysa sprint item'i tamam sayilmaz.

## 10. First Sprint Candidate Board

### Must Have

- Story 1.2
- Story 1.3
- Story 1.4
- Story 2.1
- Story 2.2

### Should Have

- Story 2.3
- Story 3.1 hazirlik tasarimi

### Could Have

- Story 7.1 baslangic fixture iskeleti

## 11. Success Criteria

Bu backlog tamamlandiginda:

1. Test Management modulu SAP projesinde kullanici tarafinda "nereden execute edecegim?" sorusu dogurmaz.
2. Cross-project veri sızıntısı ve sessiz veri kirlenmesi kapanir.
3. Retest ve sign-off operasyonlari gercek release kararlarina baglanabilir.
4. Modul buyuk veri hacminde kabul edilebilir performans verir.
5. Regression test zemini production kararini destekler.
