# Test Management Audit

**Tarih:** 2026-03-11
**Kapsam:** Test Planning, Test Plan Detail, Execution Center, Defect Management, Evidence Capture, Testing blueprint/service/model katmanlari
**Yontem:** Statik kod incelemesi, UI/route bag analizi, hedefli pytest ve syntax dogrulamasi

## Durum Guncellemesi - 2026-03-12

Bu audit dokumani 11 Mart tarihli baseline bulgulari korur. Ancak 12 Mart itibariyla asagidaki alanlarda anlamli remediation uygulanmistir; dolayisiyla bu dokuman "mevcut canli risk listesi" olarak degil, "baseline + remediation history" olarak okunmalidir.

### Kapanan veya buyuk olcude kapanan bulgular

- row-level scope izolasyonu ve cross-project relation guard'lari testing read/write akislarinda sertlestirildi
- `project_id` / `program_id` drift'i planning, analytics ve traceability turevlerinde temizlendi
- defect lifecycle `resolved/retest` kanonik akisa normaliz edildi
- suite -> quick run -> execution bulunurluk problemi kapatildi
- Evidence Capture render/root sorunu giderildi
- testing route/service katmani moduler bounded-context yapisina ayrildi
- TM Playwright smoke izole DB ile tekrar kurulup green hale getirildi
- project-aware TM fixture pack'i ve FK-on integrity gate'i release test zemininin varsayilani haline getirildi
- TM migration smoke EPIC-5 operasyonel readiness revision'i (`b7p8q9r0n026`) seviyesinde green hale getirildi; gate sirasinda bulunan gercek SQLite/Alembic uyumsuzluklari kapatildi
- TM smoke expansion sirasinda bulunan `test-case-detail` hash deep-link ve `openExecutionEvidence` runtime/export sorunlari giderildi
- Explore Playwright smoke da izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- Governance Playwright smoke da izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- Dashboard Playwright smoke da izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- Project Setup ve Program Launchpad smoke'lari da izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- Cutover/Integration/Scope smoke pack'i de izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- Backlog Kanban live-move smoke pack'i de izole DB ile calisacak sekilde guncellendi ve green hale getirildi
- API/light-UI smoke paketi (`01`, `04`, `05`, `08`, `09`) icin ayri izole Playwright config eklendi ve green hale getirildi; `05` ve `08` seeded program varsayimindan cikarildi
- Phase-3 Traceability smoke pack'i (`07`) de izole DB ile calisacak sekilde guncellendi, self-seeded hale getirildi ve green hale getirildi
- FE Sprint 3 smoke pack'i (`06`) de izole DB ile calisacak sekilde guncellendi; auth/program-1 bagimliliklarindan cikarildi ve green hale getirildi
- Cross-module Traceability smoke pack'i (`12`) de izole DB ile calisacak sekilde guncellendi; seeded login bagimliligi kaldirildi ve green hale getirildi
- Test Overview, Execution Center ve Test Case Detail execution history ekranlari toplu read-model endpoint'lerine tasindi; request fan-out kapatildi
- ortak `playwright.shared.ts` factory ile tum config'ler tek izole DB desenine toplandi
- ortak `e2e/tests/helpers/active-context.ts` helper'i ile aktif program/project bootstrap tekrarları konsolide edildi; ilgili smoke pack'ler bunun uzerinden yeniden green dogrulandi
- ortak `e2e/tests/helpers/seed-factory.ts` helper'i ile base `program/default-project` ve `L1/L2/L3 hierarchy` seed tekrarları konsolide edildi
- ortak `e2e/tests/helpers/testing-seed.ts` helper'i ile `plan/cycle/case/suite/execution/defect/backlog` self-seed graph'leri konsolide edildi
- ortak `e2e/tests/helpers/traceability-seed.ts` helper'i ile requirement -> backlog -> test -> defect seed zinciri konsolide edildi
- ortak `e2e/tests/helpers/program-setup-seed.ts` helper'i ile `project/workstream/wave/team` seed graph'leri konsolide edildi
- ortak `e2e/tests/helpers/approval-seed.ts` helper'i ile approval workflow ve approval lifecycle seed/operation tekrarları konsolide edildi
- ortak `e2e/tests/helpers/governance-seed.ts` helper'i ile governance/reporting bootstrap tekrarları konsolide edildi
- governance reports workspace acilisi, AI Steering Pack modal girisi, save-to-library modal akisi ve SteerCo report form payload'i helper katmanina indirildi
- governance reports helper seti bir kademe daha genisletildi; AI Steering Pack generate ve SteerCo report card assertion adimlari da helper owner'a alindi
- governance reports helper seti bir kademe daha genisletildi; AI Steering Pack generate+summary assertion ve SteerCo create+card assertion adimlari da helper owner'a alindi
- governance shell helper seti de genisletildi; reports shell, program snapshot, RAID shell ve AI risk assessment adimlari da helper owner'a alindi
- governance reporting helper'lari preset-secimli save-to-library kontratiyla genisletildi; report preset secimi spec seviyesinden kaldirildi
- governance reporting helper'lari saved-report definition akisini da owner seviyesine aldi; preset sonucu artik UI uzerinden kaydedilip reusable library'de dogrulaniyor
- governance reporting helper'lari saved-report rerun akisini da owner seviyesine aldi; kaydedilen definition reusable library'den tekrar calistirilip preset sonucu dogrulaniyor
- governance smoke bootstrap tekrarları da helper katmanina alindi; context create+open akisi tek owner helper'da toplandi
- governance reporting helper kontrati bir adim daha genisletildi; save-to-library + reusable-library rerun zinciri tek owner helper'da toplandi
- governance reporting helper kontrati bir adim daha genisletildi; `coverage_by_module` saved-report akisi preset/draft literal'lariyla birlikte tek owner helper'a indirildi
- governance reporting helper kontrati bir adim daha genisletildi; SteerCo create akisi de default draft literal'ini spec seviyesinden helper owner'a tasidi
- governance shell helper kontrati bir adim daha genisletildi; reports shell + snapshot + RAID + AI risk assessment zinciri tek owner helper'da toplandi
- governance smoke spec'i bir tur daha inceltildi; artik kullanilmayan reports-shell import'u da temizlenerek helper owner kontrati disina cikilmadi
- traceability smoke'lari icin ortak `openTraceabilityContext` helper'i eklendi; phase-3 ve cross-module spec'lerdeki active-context bootstrap tekrari konsolide edildi
- aktif smoke spec'lerinde dogrudan `/api/v1/programs` seed sahipligi artik helper katmaninda; test dosyalarindaki kopya create-program bloklari kaldirildi
- `06`, `07`, `08`, `09`, `11`, `12` spec'leri domain helper'lara tasindigi icin self-seeded setup bloklari kuculdu ve daha okunur hale geldi
- `14`, `15`, `16` spec'leri de `program-setup-seed` helper'ina tasindigi icin `projects/workstreams/waves/team` create tekrarları spec seviyesinden kalkti
- `09`, `11`, `13` spec'leri de `approval-seed` ve `governance-seed` helper'larina tasindigi icin approval/governance bootstrap tekrarları spec seviyesinden kalkti
- deprecated compat facade dosyalari (`testing_service.py`, `testing_execution_service.py`, `test_planning_service.py`) repo'dan kaldirildi; runtime owner modulleri artik tek dogrudan servis girisleri
- `playwright.shared.ts` run/config bazli ayri artifact klasorleri urettigi icin paralel smoke reporter collision'i kapatildi
- genel `playwright.config.ts` de artik dev DB fallback kullanmiyor; default E2E girisi guvenli hale geldi
- governance smoke sirasinda gorulen AI risk assessment backend 500'u duzeltildi
- cycle operasyon metadata modeli (`environment`, `build_tag`, `transport_request`, `deployment_batch`, `release_train`, `owner`) tamamlandi ve release zincirine baglandi
- approval, retest/sign-off ve cutover go/no-go aksiyonlari operasyonel rol matrisi ile guard edildi; negatif/pozitif gate coverage eklendi
- `release-readiness` aggregate endpoint'i ve Overview/Execution Center/Test Plan Detail UI yuzeyleri SAP operasyonel readiness zincirini gorunur hale getirdi

### Acik kalan ana riskler

- **EPIC-8 - Analytics and Read-Model Optimization** aktif backlog haline getirildi; analytics/read-model tarafinda buyuk veri hacmi icin ek performans sertlestirmesi hala acik. Aggregate endpoint gecisi tamamlandi ancak dashboard/traceability/overview/execution shaping follow-up optimizasyonu suruyor
- TM ozel CI/test harness backlog'u buyuk olcude kapandi; acik kalan migration riski artik platform-geneli ve TM disi Explore/project-scope Alembic zincirine ait
- dokuman/ADR backlog'u acik: yeni owner service yapisi ve guncel aktif risk listesi tum dokumanlara tam yansimis degil

## Ozet

Test Management modulu fonksiyon olarak genis, ancak ana risk artik CRUD eksigi degil. En buyuk problemler:

- row-level scope izolasyonunun kirik olmasi
- entity iliskilerinin yeterince dogrulanmamasi
- project/program scope karisikliklari nedeniyle bazi UI akislarinin sessizce bos veya yanlis veri gostermesi
- defect lifecycle ve retest akisinin durum semantiginde ayrismasi
- bazi ekranlarda dogrudan kullanici deneyimini bozan runtime/UI hatalari

Bugun kullanici tarafinda bildirilen en kritik UX problemi olan "suite'e bagli unit test case'i execute edecek yeri bulamama" akisi duzeltildi. Quick Run artik dogru layer ile cycle uretiyor ve kullaniciyi dogrudan ilgili execution listesine indiriyor.

## Bugun Dogrulanan ve Kapatilan Kullanici Problemi

### 1. Suite -> Execution gecisi bulunurluk problemi

**Kok neden:**

- `Quick Run` backend'de hep `sit` cycle aciyordu: `app/blueprints/testing/catalog.py`
- frontend kullaniciyi ilgili cycle'a degil sadece `Execution Center` ana ekranina goturuyordu: `static/js/views/testing/test_planning.js`
- test case detail ekraninda dogrudan execution CTA yoktu: `static/js/views/testing/test_case_detail.js`

**Bugun yapilan duzeltmeler:**

- suite icindeki case layer'larindan `unit/sit/uat/...` tureten quick-run layer secimi eklendi: `app/blueprints/testing/catalog.py`
- quick-run sonrasi olusan cycle execution modalini dogrudan acan helper eklendi: `static/js/views/testing/test_execution.js`
- suite listesine dogrudan `Run` butonu eklendi: `static/js/views/testing/test_planning.js`
- test case detail header ve executions tab'ina `Execute` girisi eklendi: `static/js/views/testing/test_case_detail.js`
- UI'da `UNIT` plan type gorunur hale getirildi: `static/js/views/testing/test_planning.js`, `static/js/views/testing/test_execution.js`, `static/js/views/testing/test_plan_detail.js`, `app/models/testing.py`

## Kritik Bulgular

### 2. Row-level scope izolasyonu kirik

Detay endpoint'leri kayitlari scope'suz `_get_or_404()` / `db.session.get()` ile cekiyor. Bu nedenle izin kontrolu kategori bazinda gecse bile ID bilen kullanici scope disi plan/case/execution/defect kayitlarina ulasabilir.

- `app/blueprints/testing/catalog.py`
- `app/blueprints/testing/planning.py`
- `app/blueprints/testing/execution.py`
- `app/blueprints/testing/defect.py`
- `app/utils/helpers.py:18`
- scoped helper mevcut: `app/services/helpers/scoped_queries.py:52`

**Etki:** cross-project / cross-tenant veri sizmasi, yetki asimi, audit guvenilmezligi.

### 3. Iliski butunlugu eksik

Plan/cycle/suite/case baglari olusturulurken entity'lerin ayni program/proje kapsaminda oldugu dogrulanmiyor.

- execution olusturma: `app/blueprints/testing/execution.py`
- suite'e case baglama: `app/blueprints/testing/catalog.py`
- plan'a case baglama: `app/blueprints/testing/planning.py`

**Etki:** coverage, traceability, dashboard ve execution metrikleri sessizce kirlenir.

## Yuksek Oncelikli Uygulama Hatalari

### 4. Project/program scope karisikligi nedeniyle Explore tabanli seciciler bozulabiliyor

Test Management ekranlari aktif `project_id` yerine `TestingShared.pid` kullanip bunu `project_id` gibi Explore endpoint'lerine gonderiyor.

- `static/js/views/test_plan_detail.js:218`
- `static/js/views/test_plan_detail.js:227`
- `static/js/views/testing/test_planning.js`
- `static/js/views/testing/test_planning.js`
- `static/js/views/testing/test_planning.js`

Explore service bu endpoint'lerde `program_id` de kabul ediyor ama cogunlukla onu dogrudan `project_id` gibi yorumluyor:

- requirements: `app/services/explore_service.py:163`
- process levels: `app/services/explore_service.py:1889`

**Etki:** `project.id != program.id` oldugunda:

- L3 scope secicileri bos gelebilir
- process/workshop tabanli test case generation eksik veri gosterebilir
- plan scope modalinda Explore secimleri yanlis/eksik olabilir

### 5. Retest kuyrugu kanonik defect status ile uyumsuz

Backend FSM `resolved -> retest` akisini kanonik kabul ediyor; retest dashboard ve UI ise hala `fixed` bekliyor.

- kanonik durum modeli: `app/models/testing.py:61`, `app/models/testing.py:69`
- backend retest dashboard: `app/services/testing/analytics.py`
- execution UI fallback retest queue: `static/js/views/testing/test_execution.js`
- E2E de `fixed` seed ediyor: `e2e/tests/11-test-management-workflows.spec.ts:255`

**Etki:** `resolved` durumundaki defect'ler kullaniciya retest icin gorunmeyebilir veya kuyruk eksik gorunur.

### 6. Evidence Capture ekrani yanlis DOM kokune render ediyor

Evidence view `#mainContent` yerine `#main-content` ariyor, bulamayinca `document.body` ustune render ediyor.

- yanlis root secimi: `static/js/views/testing/evidence_capture.js`
- gercek SPA root: `templates/index.html:221`
- router evidence route'u buraya bagliyor: `static/js/app.js:53`

**Etki:** evidence ekraninda layout bozulmasi, modal/side nav ustune yazma, sayfa butunlugunun kaybi.

### 7. Execution/Overview/Case detail ekranlarinda N+1 API fan-out var

Uc ekran da acilirken planlari, sonra her planin detayini, sonra her cycle'in detayini tek tek yukluyor.

- Execution Center: `static/js/views/testing/test_execution.js`
- Test Case Detail executions tab: `static/js/views/testing/test_case_detail.js`
- Test Overview: `static/js/views/test_overview.js:14`

**Etki:** plan/cycle sayisi artisinda ekran gec acilir, browser thread'i bloklanir, kullanici "uygulama takiliyor" hissi yasar.

## Orta Oncelikli Bulgular

### 8. TestCase detail deep-link acilisi cached pid'e bagli

`TestCaseDetailView.render()` diger TM ekranlari gibi `TestingShared.getProgram()` cagirmiyor; sadece cache'lenmis `TestingShared.pid` bekliyor.

- `static/js/views/testing/test_case_detail.js`

**Etki:** ilk acilis veya deep-link senaryosunda aktif program secili olsa bile ekran gereksiz sekilde `programs` ekranina atabilir.

### 9. L3 scope coverage bug'i suruyor

Requirement coverage hesaplamasi `pid` degerini program id olarak alip `ExploreRequirement.project_id == pid` ile filtreliyor.

- `app/blueprints/testing/analytics.py`

**Etki:** gercek project/program ayrisinda coverage eksik hesaplanir.

### 10. Test zemini bu hatalarin bir kismini yakalayamiyor

- UI contract testleri sadece string/route varligini kontrol ediyor, runtime context ve render root sorunlarini yakalamiyor: `tests/ui_contracts/test_test_management_ui_contract.py:1`
- testlerde FK enforcement kapali: `tests/conftest.py:25`
- E2E suite retest icin hala `fixed` seed ediyor: `e2e/tests/11-test-management-workflows.spec.ts:255`

**Etki:** mevcut green test sonucu, kullanicinin gercek yasadigi problemleri oldugundan az gosterebilir.

## Mimari Degerlendirme

- `app/blueprints/testing/` paketi halen yogun bir orchestration yuzeyi; route sayisi arttikca scope, permission ve transaction davranisi module bazinda izlenmeli.
- service extraction ilerlemis olsa da testing modulu hala tutarli bounded-context sinirlarina sahip degil.
- frontend tarafinda program ve project context ayrimi tam normalize edilmemis; bu problem Explore ile Test Management baglandigi noktalarda tekrar ediyor.

## Dogrulama

Calistirilan hedefli kontroller:

- `pytest tests/test_management/test_api_testing.py -k "quick_run_infers_unit_layer_from_suite_cases"` -> **1 passed**
- `pytest tests/test_management/test_api_testing.py -k "add_case_to_multiple_suites or remove_case_from_suite_keeps_other_links"` -> **2 passed**
- `pytest tests/ui_contracts/test_test_management_ui_contract.py` -> **6 passed**
- `node --check static/js/views/testing/test_execution.js` -> **OK**
- `node --check static/js/views/testing/test_planning.js` -> **OK**
- `node --check static/js/views/testing/test_case_detail.js` -> **OK**
- `node --check static/js/views/testing/evidence_capture.js` -> **OK**

Not: browser tabanli tam E2E regression kosulmedi; uygulama hatalari agirlikla statik inceleme + hedefli test kombinasyonuyla cikarildi.

## Oncelikli Aksiyon Plani

### P0

- `_get_or_404()` yerine scoped entity resolve helper'lari ile tum detail endpoint'leri kapat
- suite/plan/cycle/case baglarinda ayni project/program scope dogrulamasini zorunlu kil

### P1

- Test Management frontend'inde `project_id` gereken tum Explore cagrilarini aktif project context ile degistir
- retest queue'yi `resolved` ile uyumlu hale getir; `fixed` yalnizca backward-compat mapping ise adapter katmanina tasi
- Evidence Capture root selector'ini `#mainContent` olarak duzelt

### P2

- Execution Center / Test Overview / Test Case Detail icin toplu summary endpoint'leri ekleyip N+1 fan-out'u kaldir
- test management UI contract paketine runtime-context ve DOM-root kontrolleri ekle
- project-aware test fixture'larda `project.id != program.id` senaryosunu standard hale getir

## Sonuc

Modul islevsel olarak guclu, ancak bugun kullanici tarafinda gorulen problem izole bir UX detayi degildi; ayni alanda daha genel bir desen var. Test Management'in bir sonraki kalite asamasi yeni ozellik eklemek degil, scope dogrulugu, context tutarliligi, runtime akis butunlugu ve olcekte performans konularini sertlestirmek olmali.
