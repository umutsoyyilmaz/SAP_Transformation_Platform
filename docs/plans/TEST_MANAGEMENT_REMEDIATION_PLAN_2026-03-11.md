# Test Management Remediation Plan

**Tarih:** 2026-03-11
**Kaynak:** `docs/reviews/project/TEST_MANAGEMENT_AUDIT_2026-03-11.md`
**Uygulama Backlogu:** `docs/plans/TEST_MANAGEMENT_SPRINT_BACKLOG_2026-03-11.md`
**Amac:** Test Management modulunu bulgu kapatma odakli sekilde sertlestirmek ve gercek bir SAP projesinde kullanilabilir, denetlenebilir, role/scoped, operasyonel olarak guvenilir hale getirmek.

## 0. Durum Ozeti - 2026-03-12

11 Mart audit'i sonrasi planlanan kritik remediations'in buyuk kismi uygulandi. Bu dokuman artik yalnizca "hedef plan" degil, ayni zamanda kapanan islerin ve kalan backlog'un baseline'i olarak okunmalidir.

### Tamamlanan ana basliklar

- scoped read/write resolver katmani ile Test Management detail ve collection endpoint'leri project-aware hale getirildi
- cross-project relation/integrity guard'lari `plan/cycle/suite/case/execution/defect` akislarinda kapatildi
- defect lifecycle kanonik `resolved/retest` semantigine normaliz edildi
- suite -> quick run -> execution bulunurluk problemi ve Evidence root/render sorunu giderildi
- planning, analytics, execution ve defect route/service katmanlari bounded-context modullerine ayrildi
- TM Playwright smoke izole DB ile deterministic hale getirildi ve guncel smoke seti gecti
- Explore Playwright smoke da izole DB modeline tasindi ve green hale getirildi
- Governance Playwright smoke da izole DB modeline tasindi ve green hale getirildi
- Dashboard Playwright smoke da izole DB modeline tasinip baseURL-aware hale getirildi
- Project Setup ve Program Launchpad smoke'lari da izole DB modeline tasinip green hale getirildi
- Cutover/Integration/Scope smoke pack'i de izole DB modeline tasinip green hale getirildi
- Backlog Kanban live-move smoke pack'i de izole DB modeline tasinip green hale getirildi
- API/light-UI smoke paketi (`01`, `04`, `05`, `08`, `09`) icin ayri izole Playwright config eklendi ve green hale getirildi; `05` ve `08` seeded program varsayimindan cikarildi
- Phase-3 Traceability smoke pack'i (`07`) de izole DB modeline tasinip self-seeded hale getirildi ve green hale getirildi
- FE Sprint 3 smoke pack'i (`06`) de izole DB modeline tasinip auth/program-1 bagimliliklarindan cikarildi ve green hale getirildi
- Cross-module Traceability smoke pack'i (`12`) de izole DB modeline tasinip seeded login bagimliligindan cikarildi ve green hale getirildi
- Test Overview, Execution Center ve Test Case Detail execution history icin aggregate/read-model endpoint'leri eklendi; ilgili ekranlardaki request fan-out kaldirildi
- ortak `playwright.shared.ts` factory eklendi; tum Playwright config'leri tek izole DB desenine toplandi
- ortak `e2e/tests/helpers/active-context.ts` helper'i eklendi; Explore, Traceability, Governance, Project Setup, Launchpad ve Cutover smoke'larindaki aktif program/project bootstrap tekrarları tek noktada toplandi
- ortak `e2e/tests/helpers/seed-factory.ts` helper'i eklendi; base `program/default-project` ve `L1/L2/L3 hierarchy` seed zincirleri tek noktada toplandi
- ortak `e2e/tests/helpers/testing-seed.ts` helper'i eklendi; `plan/cycle/case/suite/execution/defect/backlog` seed graph'leri tek noktada toplandi
- ortak `e2e/tests/helpers/traceability-seed.ts` helper'i eklendi; requirement -> backlog -> test -> defect zinciri ve traceability seed graph'i tek noktaya indirildi
- ortak `e2e/tests/helpers/program-setup-seed.ts` helper'i eklendi; `project/workstream/wave/team` sahiplik graph'leri tek noktaya indirildi
- ortak `e2e/tests/helpers/approval-seed.ts` helper'i eklendi; `approval workflow + submit/pending/decide/status` akis owner'lari tek noktaya indirildi
- ortak `e2e/tests/helpers/governance-seed.ts` helper'i eklendi; governance/reporting bootstrap ve user-context owner'i tek noktaya indirildi
- governance reports workspace acilisi, AI Steering Pack modal girisi, save-to-library modal akisi ve SteerCo report form payload'i helper owner'larina indirildi
- governance reports helper seti bir kademe daha genisletildi; AI Steering Pack generate ve SteerCo report card assertion adimlari da owner helper'a alindi
- governance reports helper seti bir kademe daha genisletildi; AI Steering Pack generate+summary assertion ve SteerCo create+card assertion adimlari da owner helper'a alindi
- governance shell helper seti de genisletildi; reports shell, program snapshot, RAID shell ve AI risk assessment adimlari da owner helper'a alindi
- governance reporting helper'lari preset-secimli save-to-library kontratiyla genisletildi; report preset secimi spec'ten helper'a alindi
- governance reporting helper'lari saved-report definition akisini da owner seviyesine aldi; preset sonucu artik UI uzerinden kaydedilip reusable library'de dogrulaniyor
- governance reporting helper'lari saved-report rerun akisini da owner seviyesine aldi; kaydedilen definition reusable library'den tekrar calistirilip preset sonucu dogrulaniyor
- governance smoke bootstrap tekrarları da helper katmanina alindi; context create+open akisi tek owner helper'da toplandi
- governance reporting helper kontrati bir adim daha genisletildi; save-to-library + reusable-library rerun zinciri tek owner helper'da toplandi
- governance reporting helper kontrati bir adim daha genisletildi; `coverage_by_module` saved-report akisi preset/draft literal'lariyla birlikte tek owner helper'a indirildi
- governance reporting helper kontrati bir adim daha genisletildi; SteerCo create akisi de default draft literal'ini spec'ten helper owner'a tasidi
- governance shell helper kontrati bir adim daha genisletildi; reports shell + snapshot + RAID + AI risk assessment zinciri tek owner helper'da toplandi
- governance smoke spec'i bir tur daha inceltildi; artik kullanilmayan reports-shell import'u da temizlenerek helper owner kontrati disina cikilmadi
- traceability smoke'lari icin ortak `openTraceabilityContext` helper'i eklendi; cross-module ve phase-3 spec'lerindeki active-context bootstrap tekrari kapandi
- aktif smoke spec'lerinde dogrudan `/api/v1/programs` seed tekrarları kaldirildi; owner helper'a indirildi
- `06`, `07`, `08`, `09`, `11`, `12` smoke/spec setleri yeni domain helper'lara tasindi; self-seeded setup bloklari belirgin sekilde kuculdu
- `14`, `15`, `16` smoke/spec setleri de `program-setup-seed` owner helper'ina tasindi; `project/workstream/wave/team` create tekrarları spec seviyesinden kalkti
- `09`, `11`, `13` smoke/spec setleri de `approval-seed` ve `governance-seed` helper'larina tasindi; approval/governance bootstrap tekrarları spec seviyesinden kalkti
- deprecated compat facade dosyalari (`testing_service.py`, `testing_execution_service.py`, `test_planning_service.py`) tamamen kaldirildi; runtime import yuzeyi artik dogrudan owner servis modullerine bagli
- `playwright.shared.ts` artik run/config bazli ayri `playwright-report` ve `test-results` klasorleri uretir; paralel smoke kosularinda reporter collision kapatildi
- genel `playwright.config.ts` artik dev DB fallback kullanmiyor; `npm run test:e2e` ve kritik smoke hedefleri de izole config uzerinden calisiyor
- governance smoke sirasinda bulunan AI risk assessment backend 500'u kapatildi
- TM icin project-aware pytest fixture pack'i varsayilan hale getirildi; `project.id != program.id` ve SQLite FK-on davranisi release gate testlerinde sabitlendi
- `tm-integrity-gate`, `tm-migration-smoke`, `tm-ui-smoke` ve `tm-release-gate` komutlari eklendi; CI'da TM integrity + migration smoke adimlari aktif hale getirildi
- TM migration smoke, tarihsel olarak Alembic disinda kalan auth/project bootstrap tablolarini minimal baseline olarak kurup EPIC-5 operasyonel readiness revision'i `b7p8q9r0n026` seviyesine kadar upgrade edecek sekilde netlestirildi
- TM migration smoke sirasinda bulunan gercek migration uyumsuzluklari (`o3c4d5e6f712`, `q5e6f7g8b914`, `r6f7g8h9c015`, `s7g8h9i0d116`) SQLite/TM gate ile uyumlu hale getirildi
- TM smoke genisletmesi sirasinda bulunan `test-case-detail` hash deep-link ve `openExecutionEvidence` export/runtime sorunlari giderildi; TM Playwright smoke yeniden green hale getirildi
- cycle operasyon metadata modeli (`environment`, `build_tag`, `transport_request`, `deployment_batch`, `release_train`, `owner`) `TestCycle` seviyesinde tamamlandi ve UI/read-model'e yansitildi
- approval, retest/sign-off ve cutover go/no-go aksiyonlari operasyonel rol matrisiyle guard edildi; negatif role coverage eklendi
- `release-readiness` aggregate endpoint'i, Overview/Execution Center/Test Plan Detail ekranlari ve hedefli API/UI contract testleri ile SAP operational readiness zinciri tamamlandi

### Kalan ana backlog

#### Aktif is listesi

EPIC-6 kapsami kapanmistir. Acik kalan analytics isleri artik aggregate endpoint ihtiyacindan degil, buyuk hacim read-model optimizasyonundan kaynaklanan follow-up backlog'dur.

1. **EPIC-8 - Analytics and Read-Model Optimization**
   - `compute_dashboard`, `compute_traceability_matrix`, `overview-summary` ve `execution-center` tarafinda kalan aggregate/shaping sadeleştirmeleri tamamlanacak.
   - Hedef: buyuk hacimde daha az query, daha kucuk payload, daha net summary semantigi ve olculebilir perf budget.
2. **Platform-geneli migration/harness follow-up**
   - TM slice green olsa da repo-wide Alembic zincirinde TM disi Explore/project-scope migrasyon drift'leri ayrica toparlanacak.
   - Hedef: TM release gate'i scope creep olmadan korurken platform geneli tam-head upgrade yolunu ayri backlog olarak kapatmak.
3. **Dokuman senkronizasyonu**
   - remediation plan, audit, sprint backlog ve ilgili ADR/dokumanlar yeni owner service yapisi ve guncel risk listesi ile senkronize edilecek.

#### Siradaki uygulama sirasi

1. **EPIC-8.1 - Dashboard aggregate ve summary shaping**
2. **EPIC-8.2 - Traceability matrix payload ve summary optimization**
3. **EPIC-8.3 - Overview / Execution Center read-model alignment**
4. **EPIC-8.4 - Perf budget, olcum ve regression gate**

#### Park edilmis / tekrar acilmayacak isler

- governance/reporting helper mikro-konsolidasyonlari artik ana backlog degil; yeni bir runtime bug veya spec kirilmasi olursa tekrar acilacak
- izole Playwright config migration'i kritik smoke pack'ler icin tamamlandi; bu alan artik rutin bakim seviyesinde

### Son dogrulama sinyali

- hedefli TM backend regresyon setleri gecti
- scoped lookup guard seti gecti
- TM release gate pytest setleri (`test_tm_release_gate`, planning/services, TM UI contract, hedefli overview/execution/traceability/dashboard API paketi) gecti
- TM migration smoke (`scripts/testing/tm_migration_smoke.py`) gecti
- izole TM Playwright smoke (`10-test-management-ops`, `11-test-management-workflows`) gecti
- active-context helper refactor'u sonrasi izole Explore (`03`), FE Sprint 3 (`06`), Phase-3 Traceability (`07`), Cross Traceability (`12`), Governance (`13`), Project Setup + Launchpad (`14`, `15`) ve Cutover (`16`) smoke pack'leri yeniden gecti
- `seed-factory` refactor'u sonrasi izole Dashboard (`02`), Explore (`03`), API/light-UI (`04`, `05`), FE Sprint 3 (`06`), Phase-3 Traceability (`07`), TM (`10`, `11`), Cross Traceability (`12`), Governance (`13`), Project Setup + Launchpad (`14`, `15`), Cutover (`16`) ve Backlog (`17`) smoke pack'leri yeniden gecti
- `testing-seed` / `traceability-seed` refactor'u sonrasi izole API/light-UI (`08`, `09` dahil), FE Sprint 3 (`06`), Phase-3 Traceability (`07`), TM (`10`, `11`) ve Cross Traceability (`12`) smoke pack'leri yeniden gecti
- `program-setup-seed` refactor'u sonrasi izole Project Setup + Launchpad (`14`, `15`) ve Cutover (`16`) smoke pack'leri yeniden gecti
- `approval-seed` / `governance-seed` refactor'u sonrasi izole Approval (`09`), TM workflow (`11`) ve Governance (`13`) smoke pack'leri yeniden gecti
- compat facade kaldirma sonrasi scoped lookup guard seti facade dosyalarinin yoklugunu ve yeni import yasağini dogruladi
- governance/report payload helper refactor'u sonrasi izole Governance (`13`) smoke yeniden gecti
- `openTraceabilityContext` refactor'u sonrasi izole Phase-3 Traceability (`07`) ve Cross Traceability (`12`) smoke pack'leri yeniden gecti
- analytics batching sertlestirmesi sonrasi L3 coverage / dashboard / traceability analytics regresyon seti yeniden gecti
- dashboard + go/no-go aggregate batching sonrasi analytics regresyon seti yeniden gecti
- cycle-risk + retest-readiness batching sonrasi hedefli analytics regresyon seti yeniden gecti
- governance helper sadeleştirmesi sonrasi izole Governance (`13`) smoke yeniden gecti
- governance helper konsolidasyonu sonrasi izole Governance (`13`) smoke yeniden gecti
- traceability matrix lightweight row-query refactor'u sonrasi hedefli analytics regresyon seti yeniden gecti
- governance shell helper genislemesi sonrasi izole Governance (`13`) smoke yeniden gecti
- dashboard read-shaping refactor'u sonrasi hedefli analytics regresyon seti yeniden gecti
- overview-summary, execution-center ve case execution-history endpoint'leri sonrasi hedefli Epic-6 regresyon seti ve TM smoke yeniden gecti
- governance preset-helper refactor'u sonrasi izole Governance (`13`) smoke yeniden gecti
- traceability matrix shaping cleanup sonrasi hedefli analytics regresyon seti yeniden gecti
- governance saved-report helper refactor'u sonrasi izole Governance (`13`) smoke yeniden gecti
- dashboard count-query cleanup sonrasi hedefli analytics regresyon seti yeniden gecti
- governance saved-report rerun helper refactor'u sonrasi izole Governance (`13`) smoke yeniden gecti
- traceability summary cleanup sonrasi hedefli analytics regresyon seti yeniden gecti
- governance bootstrap helper refactor'u sonrasi izole Governance (`13`) smoke yeniden gecti
- traceability requirement-stat cleanup sonrasi hedefli analytics regresyon seti yeniden gecti
- traceability payload prebuild refactor'u sonrasi hedefli analytics regresyon seti yeniden gecti

---

## 1. Hedef Durum

Bu plan tamamlandiginda modul su ozelliklere sahip olmali:

- project-aware ve tenant-safe veri erisimi
- SAP test fazlari icin net domain: `unit`, `string`, `sit`, `uat`, `regression`, `cutover_rehearsal`, `performance`
- reusable suite + plan-specific scope + cycle-specific execution yapisi
- defect -> retest -> approval zincirinde tekil durum semantigi
- kullanici acisindan dogrudan ve acik execute akisleri
- buyuk plan/cycle hacminde kabul edilebilir performans
- gercek proje nesnelerine bagli izlenebilirlik:
  requirement, process L3/L4, WRICEF, config item, transport/build tag, environment
- release oncesi kanitlanmis test zemini:
  API, contract, UI smoke, role/scope, performance ve migration kontrolleri

---

## 2. Tasarim Prensipleri

### 2.1 Scope once gelir

- Tum testing entity'leri `tenant -> program -> project` zincirinde resolve edilir.
- `id` bilmek erisim icin asla yeterli olmaz.
- Detail endpoint'leri scoped helper disinda entity resolve etmez.

### 2.2 Project, programdan ayri birinci sinif context'tir

- Frontend `TestingShared.pid` uzerinden `project_id` tahmin etmez.
- Explore ve Testing baglantilarinda aktif project context zorunludur.

### 2.3 Execution ana gercektir

- Dashboard, readiness, sign-off ve go/no-go her zaman `TestExecution` odakli hesaplanir.
- Step-level kayitlar execution sonucunu destekler; override etmez.

### 2.4 Suite reusable, plan operational, cycle executable

- `TestSuite` katalog/reuse birimidir.
- `TestPlan` scope, environment ve governance birimidir.
- `TestCycle` execution dalgasidir.

### 2.5 Domain vocabulary tek olmalidir

- Bir kavramin tek kanonik adi olur.
- `fixed` vs `resolved`, `plan_type` vs `test_layer`, `project_id` vs `program_id` gibi drift'ler adapter katmaninda tutulur, domainin icine sizmaz.

---

## 3. Program Yapisi

Plan 6 is akisi ve 4 release dalgasi halinde ilerlemelidir.

| Dalga | Sure | Hedef | Cikis |
|------|------|-------|-------|
| R1 | 2 hafta | Stabilizasyon ve guvenlik | Scope leak kapali, execute akislari net |
| R2 | 2-3 hafta | Domain normalization | Status/layer/scope semantigi tutarli |
| R3 | 2 hafta | SAP operasyonel readiness | Environment, evidence, approvals, retest operasyonlari saglam |
| R4 | 2 hafta | Performance, test zemini, release hardening | Buyuk veri hacmi ve release gate'leri tamam |

Toplam tahmini sure: **8-9 hafta**

---

## 4. Workstream'ler

### WS1 - Security, Scope and Data Integrity

**Amac:** Cross-project/cross-tenant erisim riskini ve sessiz veri kirlenmesini kapatmak.

#### Kapsam

- tum `_get_or_404()` / `db.session.get()` kullanimlarini scoped helper'a tasimak
- `TestPlan`, `TestCycle`, `TestCase`, `TestExecution`, `Defect`, `TestSuite` detail endpoint'lerini scope-aware yapmak
- `create_test_execution`, `add_case_to_suite`, `add_case_to_plan`, `import_from_suite`, `quick_run` akilarinda project/program tutarlilik kontrolu eklemek
- nullable `tenant_id` davranisini normalize etmek
- create/update path'lerinde `project_id` ve `tenant_id` populate edilmesini zorunlu hale getirmek

#### Teslimatlar

- scoped entity resolver helper seti
- blueprint seviyesinde route audit checklist
- integrity guard unit/integration testleri

#### Kabul Kriterleri

- baska project'e ait plan/case/execution/defect detail'i 404 veya 403 doner
- foreign plan/suite/cycle/case baglari 400 ile reddedilir
- tum testing create path'lerinde `project_id` zorunlu ve testle korunur

#### Tahmini Efor

**8-10 gun**

---

### WS2 - Domain Model Normalization

**Amac:** Test management dilini ve state machine'lerini SAP proje gercegine uygun, tutarli hale getirmek.

#### Kapsam

- defect lifecycle'i kanonik hale getirmek:
  `new -> assigned -> in_progress -> resolved -> retest -> closed/reopened/rejected/deferred`
- `fixed` durumunu backward-compat adapter'a indirmek veya migration ile kaldirmak
- `plan_type` ve `test_layer` iliskisini netlestirmek
- `unit` ve mumkunse `string` layer destegini UI + backend + docs + tests'te standardize etmek
- `l3_scope_coverage()` bug'ini project-aware filtre ile duzeltmek
- model comment/docstring/enum sabitlerini gercek domain ile senkronize etmek

#### Teslimatlar

- updated model constants
- migration/compat notlari
- normalized API contract

#### Kabul Kriterleri

- retest queue `resolved` / `retest` defect'leri dogru gosterir
- UI'da plan type ve cycle layer vocabulary tutarlidir
- `project.id != program.id` fixture'larinda coverage dogru calisir

#### Tahmini Efor

**6-8 gun**

---

### WS3 - User Journeys and UX Repair

**Amac:** Kullanici icin ana akislari tek bakista bulunur ve hataya dayanikli hale getirmek.

#### Kapsam

- suite -> quick run -> cycle executions akisini resmi bir pattern yapmak
- test case detail, suite list, plan detail ve defect panel'lerinde deep-link CTA standardi tanimlamak
- Evidence Capture root/render sorununu gidermek
- project context eksikliginde anlamli yonlendirme ve banner davranisi eklemek
- deep-link acilislarinda `TestingShared.getProgram()` / aktif project senkronizasyonu
- execute, retest, evidence ve approval giris noktalarini test overview/cockpit'te gorunur hale getirmek

#### Teslimatlar

- "Execution Entry Standard" UI guideline
- guncellenmis TM navigation ve CTA map'i
- evidence ekraninda SPA uyumlu render

#### Kabul Kriterleri

- suite'e bagli bir test case 3 tik icinde execution'a ulasir
- defect panel'den execution chain acilisi calisir
- evidence route layout bozmaz
- test case detail deep-link'te gereksiz program redirect'i olmaz

#### Tahmini Efor

**5-6 gun**

---

### WS4 - SAP Project Operational Readiness

**Amac:** Modulu "demo" seviyesinden cikarip gercek SAP delivery operasyonlarina oturtmak.

#### Kapsam

- environment ve landscape semantigini netlestirmek:
  `DEV`, `QAS`, `PRE`, `PRD`, gerekiyorsa multiple logical test env
- `build_tag` / transport / deployment batch referanslarini execution ve cycle seviyesinde standardize etmek
- wave, release train, cutover rehearsal, dry-run gibi SAP operasyon kavramlarini plan/cycle metadata'da netlestirmek
- UAT sign-off, evidence, defect, approval ve go/no-go iliskilerini release readiness akisi olarak baglamak
- role mapping:
  Test Manager, SIT Lead, UAT Lead, Business Tester, BPO, PMO, Release Manager

#### Teslimatlar

- SAP role matrix
- release readiness data contract
- cycle metadata standardi

#### Kabul Kriterleri

- her cycle icin environment + build/transport + owner + readiness durumu gorulebilir
- UAT sign-off verisi release kararinda kullanilir
- cutover rehearsal ve regression gibi fazlar ayni altyapida ama farkli guard'larla isler

#### Tahmini Efor

**5-7 gun**

---

### WS5 - Performance and Read Model Hardening

**Amac:** Plan/cycle sayisi arttiginda ekranlarin operasyonel hizini korumak.

#### Kapsam

- Execution Center, Test Overview ve Test Case Detail icin toplu read endpoint'leri
- N+1 API fan-out yerine aggregate/read-model endpoint
- dashboard ve retest queue icin ozel summary payload'lari
- lazy loading / windowing / pagination stratejisi
- gerekiyorsa lightweight cache ve invalidation kurallari

#### Teslimatlar

- read-model endpoint backlog
- response budget hedefleri
- high-volume smoke dataset

#### Kabul Kriterleri

- 100+ plan / 500+ cycle / 10k+ execution senaryosunda ekranlar kabul edilebilir surede yuklenir
- overview ve execution center ilk render'da coklu chained request firtinasi uretmez

#### Tahmini Efor

**5-6 gun**

---

### WS6 - Test Harness, CI and Release Governance

**Amac:** Bug'larin geri gelmesini engellemek ve release kararini testlerle desteklemek.

#### Kapsam

- `project.id != program.id` fixture seti standard hale getirilecek
- SQLite FK enforcement testte acilacak veya Postgres tabanli CI slice eklenecek
- scope/permission negatif testleri eklenecek
- UI contract testlerine runtime-context, root selector ve deep-link kontrolleri eklenecek
- Playwright testlerinde stateful dev DB yerine izolasyonlu seed/teardown duzeni
- test management icin release gate:
  API, contract, smoke, scope, migration, perf

#### Teslimatlar

- CI gate matrisi
- isolated TM smoke config
- negative security test paketi

#### Kabul Kriterleri

- cross-scope erisim bug'i test olmadan merge edilemez
- evidence root, quick-run deep-link ve retest queue status drift'i testlerle yakalanir
- TM smoke suite deterministic calisir

#### Tahmini Efor

**6-8 gun**

---

## 5. Release Dalgalari

### R1 - Stabilizasyon ve Guvenlik

**Sure:** 2 hafta
**Icinde:** WS1 + WS3'un kritik kismi

#### Cikislar

- scope leak kapatilmis
- integrity guard'lar eklenmis
- quick-run / execute / evidence / deep-link kullanici akislari net

#### R1 Exit Criteria

- P0 bulgu kalmaz
- TM kritik smoke akislari green
- user-facing dead CTA kalmaz

---

### R2 - Domain Normalization

**Sure:** 2-3 hafta
**Icinde:** WS2 + WS6'nin domain testleri

#### Cikislar

- canonical defect lifecycle
- project/program context duzgun ayrilmis
- coverage ve retest hesaplari dogru

#### R2 Exit Criteria

- `fixed/resolved` drift kapali
- `project.id != program.id` testleri green
- API contract dokumani guncel

---

### R3 - SAP Operational Readiness

**Sure:** 2 hafta
**Icinde:** WS4 + WS3'un operasyonel UX katmani

#### Cikislar

- environment/build/release metadata standart
- role-based operasyon ekranlari tutarli
- sign-off, approval, evidence ve go/no-go zinciri tamam

#### R3 Exit Criteria

- UAT sign-off ve readiness karar akisi demo degil, operasyonel olarak tamam
- release manager / test lead / business tester akislari net

---

### R4 - Performance and Release Hardening

**Sure:** 2 hafta
**Icinde:** WS5 + WS6

#### Cikislar

- aggregate endpoint'ler ve read model'ler canli
- isolated CI ve smoke pack tamam
- release checklist ve rollback plan'i hazir

#### R4 Exit Criteria

- high-volume dataset smoke green
- perf budget ve CI gates saglanmis
- modul production hardening checklist'ini gecmis

---

## 6. Epic Seviyesinde Backlog

| Epic | Baslik | Oncelik | Dalga |
|------|--------|---------|-------|
| E1 | Scoped entity resolution retrofit | P0 | R1 |
| E2 | Testing relation integrity guards | P0 | R1 |
| E3 | Project context normalization across TM frontend | P0 | R2 |
| E4 | Defect lifecycle canonicalization | P0 | R2 |
| E5 | Evidence capture SPA compliance | P1 | R1 |
| E6 | Execution entry point standardization | P1 | R1 |
| E7 | Coverage and traceability correctness fixes | P1 | R2 |
| E8 | SAP environment/build/release metadata model | P1 | R3 |
| E9 | Retest, sign-off and readiness flow hardening | P1 | R3 |
| E10 | Read-model and performance optimization | P1 | R4 |
| E11 | TM isolated CI/smoke/perf harness | P1 | R4 |
| E12 | Documentation, runbook and operating model refresh | P2 | tum dalgalar |

---

## 7. Mimari Sonuc Resmi

Plan sonunda hedeflenen sade yapı:

```text
Project
  -> TestPlan
      -> PlanScope
      -> PlanTestCase
      -> TestCycle
          -> TestExecution
              -> TestStepResult
              -> Evidence
              -> Defect
                  -> Retest
                  -> Approval / Sign-off
```

Kurallar:

- `Project` canonical operational scope'tur.
- `TestSuite` katalog ve reuse katmanidir, execution giris noktasi olabilir ama scope gercegi degildir.
- `PlanScope` ve `PlanTestCase` release-level governance'in ana katmanidir.
- `TestExecution` operasyonel gercektir.

---

## 8. KPI ve Basari Metrikleri

| Metrik | Baslangic | Hedef |
|--------|-----------|-------|
| Scope leak bulgusu | Var | 0 |
| Cross-project integrity bug | Var | 0 |
| User-visible dead CTA | Var | 0 |
| `project != program` senaryosunda TM bug | Var | 0 |
| Retest state drift | Var | 0 |
| N+1 opening pattern | Var | kritik ekranlarda yok |
| TM smoke determinism | zayif | deterministic |
| SAP readiness metadata completeness | parcali | tam |

---

## 9. Uygulama Stratejisi

Bu planin uygulanma sirasi:

1. Once P0 guvenlik ve kullanici akislari kapatilacak.
2. Ardindan domain normalization yapilacak; bu adimdan once buyuk UI redesign yapilmayacak.
3. Sonra SAP operasyon katmani ve release metadata guclendirilecek.
4. En son performans/read model ve CI hardening tamamlanacak.

Bu siralama bozulmamali. Aksi halde UI polish yapilirken temel scope ve domain kusurlari tekrar uretilecektir.

---

## 10. Onerilen Calisma Modu

Teslimat sekli feature bazli degil, vertical slice bazli olmalidir.

Her epic su 6 parcayi birlikte kapatmali:

1. model / service / blueprint degisikligi
2. UI akisi
3. negatif test
4. smoke veya contract test
5. dokumantasyon
6. release note / migration notu

Bu disiplin uygulanmazsa modul tekrar dokuman-kod-test drift'i uretir.

---

## 11. Ilk 10 Gun Icin Onerilen Somut Is Listesi

### Gun 1-2

- scoped helper retrofit envanteri
- tum testing detail route'larin audit tablosu
- P0 route fix backlog'u

### Gun 3-4

- plan/case/cycle/execution/defect detail scoped fetch refactor
- integrity guard'lar
- negatif API testleri

### Gun 5

- project context normalization tasarimi
- frontend Explore cagrilarinin envanteri

### Gun 6-7

- TM frontend `project_id` gecisi
- evidence root fix
- test case detail deep-link fix

### Gun 8

- retest lifecycle canonicalization tasarimi
- `fixed` compatibility karari

### Gun 9-10

- retest queue + dashboard normalization
- E2E ve contract test update
- R1/R2 gate review

---

## 12. Sonuc

Bu planin hedefi sadece bulgu kapatmak degil, Test Management'i SAP delivery operasyonunun guvenilir bir parcasi haline getirmektir. Bunun icin once guvenlik ve scope, sonra domain dili, sonra operasyon akislari, en son performans ve release hardening kapatilmalidir.

En kritik karar sunudur:

**Testing modulu yeniden "feature-first" degil, "operational correctness first" mantigiyla ilerlemelidir.**
