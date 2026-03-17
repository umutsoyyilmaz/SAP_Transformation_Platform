# ADR-009: Platform Identifier Model

## Status

Proposed

## Date

2026-03-10

## Context

Platform genelinde "ID" kavramı şu anda tek bir anlama gelmiyor. Farklı katmanlarda şu alanlar birlikte kullanılıyor:

- `id`: veritabanı primary key
- `code`: kullanıcıya görünen business reference
- `entity_id`: polymorphic ilişki veya event/audit/reference alanı
- `external_id` / `alm_id`: dış sistem referansları
- `legacy_requirement_id`: eski modelden taşınan referans

Bu durum özellikle şu nedenlerle kritik hale geliyor:

- Explore modelleri ağırlıklı olarak `UUID String(36)` PK kullanıyor.
- Legacy ve operasyonel modüllerin çoğu `Integer` PK kullanıyor.
- Bazı polymorphic tablolar `entity_id = Integer` varsayıyor.
- Bazı yeni tablolar `entity_id = String` kullanıyor.
- Bazı endpoint yorumları veya plan dokümanları `code` ile `id` kavramını karıştırıyor.
- Tenant / program / project scope ile birlikte düşünüldüğünde tek başına "ID" ile lookup güvenlik ve doğruluk riski yaratıyor.

ID konusu bu platform için sadece teknik bir detay değil; veri bütünlüğü, tenant isolation, API stabilitesi, traceability ve dış sistem entegrasyonlarının temelidir.

## Problem Statement

Sistem şu anda hibrit identifier yapısı ile çalışıyor, ancak bu hibrit yapı açık bir sözleşme ile tanımlanmadığı için aşağıdaki riskleri üretiyor:

- Aynı `entity_id` alanı bazı yerlerde integer PK, bazı yerlerde UUID PK, bazı yerlerde display code gibi yorumlanabiliyor.
- `code` alanı kullanıcı için asıl referans gibi görünürken backend işlem yolları `id` ile çalışıyor.
- Polymorphic helper tablolar UUID entity'leri güvenli ve tutarlı şekilde temsil edemiyor.
- Route parametrelerinde veya API query/body alanlarında hangi identifier'ın beklendiği her zaman açık değil.
- Audit, signoff, notification, AI embedding, custom fields gibi cross-cutting alanlar ortak bir identifier modeline bağlı değil.

## Decision

Platform için dört katmanlı resmi identifier modeli benimsenir:

1. `primary_id`
   Teknik canonical kimliktir. Her entity'nin tek gerçek kimliğidir. Veritabanı PK ile aynıdır.

2. `business_code`
   İnsan tarafından okunur, UI ve operasyonel iletişim için kullanılır. Unique olabilir ama teknik canonical key değildir.

3. `scoped_reference`
   Tenant, program, project gibi scope ile birlikte anlam kazanan referanstır. Güvenlik ve erişim kontrolü için lookup daima scope ile birlikte yapılır.

4. `external_reference`
   SAP Cloud ALM, Jira, ServiceNow, provider-side process ID gibi sistem dışı referanslardır.

Bu kararın pratik karşılığı aşağıdadır.

Ek karar:

- Kullanıcı tarafından takip edilen tüm ana iş nesnelerinde `code` zorunlu business tracking reference olarak ele alınır.
- `id` teknik canonical identity olarak kalır, ancak insan operasyonu, toplantı dili, raporlama ve ekran navigasyonu `code` etrafında tasarlanır.

## Official Vocabulary

### 1. Primary ID

- Alan adı: çoğunlukla `id`
- Rol: entity'nin canonical teknik kimliği
- Kullanım alanı:
  - DB foreign key
  - internal service call
  - mutation endpoint target
  - audit/signoff referansı
  - traceability canonical bağlantı
- Kural:
  - Sistem içinde "tek doğru kimlik" budur.
  - `code` hiçbir zaman `id` yerine geçmez.
  - Aynı entity için hem `id` hem `code` varsa, yazma işlemleri `id` üzerinden yapılır.

### 2. Business Code

- Alan adı: çoğunlukla `code`
- Rol: kullanıcı dostu, okunabilir operasyonel referans
- Örnekler:
  - `PGM-001`
  - `REQ-014`
  - `OI-003`
  - `WS-SD-01`
  - `WRICEF-FI-001`
  - `IF-FI-001`
  - `CUT-001`
- Kural:
  - UI'da öncelikli gösterim alanıdır.
  - Kullanıcının item'ı takip ettiği asıl referanstır.
  - Search/filter/sort için desteklenebilir.
  - API'de response içinde dönebilir.
  - Tek başına canonical mutation target olmamalıdır.

### 2A. Code-First User Tracking Principle

Platformta kullanıcılar item'ları çoğunlukla başlıkla değil, kısa referans koduyla takip eder.

Örnekler:

- "REQ-014 onaylandı mı?"
- "OI-003 hala açık mı?"
- "CUT-001 rehearsal sonrası revize edildi mi?"
- "IF-FI-001 hangi wave'de?"

Bu nedenle kullanıcı-facing artifact'larda `code` alanı opsiyonel kozmetik alan gibi değil, operasyonel takip anahtarı gibi ele alınır.

Sonuçları:

- Ekran listelerinde `code` her zaman görünür.
- Global arama `code` ile çok hızlı sonuç döndürür.
- Bildirim, e-posta, export, PDF ve dashboard kartlarında `code` öne çıkar.
- İnsanların ekran görüntüsü, toplantı notu ve Excel üzerinden konuştuğu referans `code` olur.
- Teknik operasyonlar yine `id` ile çalışır.

Kısacası:

- backend primary key = `id`
- user tracking primary key = `code`

### 3. Scoped Reference

- Bileşenler:
  - `tenant_id`
  - `program_id`
  - `project_id`
  - `entity_type`
  - `primary_id`
- Rol:
  - Access control
  - Safe lookup
  - Tenant isolation
  - Cross-context traceability
- Kural:
  - "Entity bulundu mu?" sorusu `id` ile değil, scope + `id` ile cevaplanır.
  - Public API ve service boundary'de mümkün olan her yerde scope doğrulaması zorunludur.

### 4. External Reference

- Alan adları:
  - `external_id`
  - `alm_id`
  - provider-specific `id`
- Rol:
  - Dış sistem eşleme
  - Sync/reconciliation
  - Backward compatibility
- Kural:
  - Internal canonical key yerine kullanılamaz.
  - Ayrı namespace olarak ele alınır.

## Entity Taxonomy

### A. UUID-primary entities

Bu grup Explore ağırlıklıdır. Bunlarda canonical kimlik `String(36)` UUID PK'dir.

- `ExploreRequirement`
- `ExploreOpenItem`
- `ExploreDecision`
- `ProcessLevel`
- `ProcessStep`
- `ExploreWorkshop`
- `PhaseGate`
- `CrossModuleFlag`
- `ScopeChangeRequest`
- `Attachment`
- Explore junction / link tabloları

Bu grupta:

- `code` kullanıcı referansıdır.
- `id` teknik canonical key'dir.
- `entity_id` kullanan yardımcı tablolar string-normalized referans taşımalıdır.

### B. Integer-primary entities

Bu grup legacy ve operasyonel modüllerin çoğunu kapsar.

- `Program`
- `Project`
- legacy `Requirement`
- `BacklogItem`
- `ConfigItem`
- `Risk`
- `Action`
- `Issue`
- RAID `Decision`
- `Interface`
- `Wave`
- `CutoverPlan`
- `TestPlan`
- `TestCycle`
- `TestCase`
- `Defect`
- çoğu admin / reporting / data factory entity'si

Bu grupta:

- `id` integer PK'dir.
- `code` varsa kullanıcı referansıdır.
- Polymorphic taşıma gerekiyorsa string'e normalize edilerek taşınabilir.

## Canonical Rules

### Rule 1: Canonical identifier daima PK'dir

- UUID entity için canonical identifier = UUID `id`
- Integer entity için canonical identifier = integer `id`

### Rule 2: `code` hiçbir zaman PK değildir

- `REQ-014`, `WS-SD-01`, `CUT-001` gibi değerler business code'dur.
- Bunlar route'ta veya service lookup'ta kullanılacaksa explicit "lookup by code" davranışı tanımlanmalıdır.

### Rule 2A: User-facing entity'lerde `code` zorunlu olmalıdır

Şu sınıftaki item'larda `code` bulunması beklenir:

- requirements
- open items
- workshops
- backlog/config items
- risks/actions/issues/decisions
- interfaces
- cutover artifacts
- test cases
- benzeri operasyonel olarak takip edilen tüm work items

İstisnalar:

- saf junction tabloları
- purely technical helper tablolar
- kullanıcıya listelenmeyen background/system records

### Rule 2B: `code` stabil olmalıdır

Bir item kullanıcıya gösterildikten sonra `code` mümkün olduğunca değişmemelidir.

Sebep:

- toplantı notları bozulmaz
- Excel/export referansları kırılmaz
- e-posta ve ticket geçmişi tutarlı kalır
- kullanıcı hafızası korunur

Öneri:

- `code` immutable kabul edilir
- yalnızca düzeltme amaçlı kontrollü admin flow ile değiştirilebilir
- değişirse eski değer audit'e yazılır ve mümkünse alias/history tutulur

### Rule 2C: `code` scope içinde unique olmalıdır

Uniqueness global olmak zorunda değildir; iş alanına göre doğru scope seçilmelidir.

Örnek:

- project-scoped: `REQ-014`, `WS-SD-01`
- program-scoped: `OI-003`, `CUT-001`
- tenant-scoped veya global: `PGM-001` gibi üst seviye kodlar

Kural:

- kullanıcı aynı çalışma bağlamında aynı `code` ile iki farklı item görmemelidir
- uniqueness kuralı entity bazında açık tanımlanmalıdır

### Rule 3: Cross-cutting polymorphic references string-normalized olmalıdır

`entity_type + entity_id` modeli kullanılan tüm tablolarda `entity_id` string tutulmalıdır.

Sebep:

- Integer PK entity'ler `str(id)` olarak temsil edilebilir.
- UUID PK entity'ler doğal olarak string'dir.
- Tek tip index, serialization ve audit davranışı sağlanır.

Standart:

- DB alan adı: `entity_id`
- DB tipi: `String(64)` veya üstü
- İçerik:
  - UUID entity için UUID string
  - Integer entity için digit string, örn. `"42"`

### Rule 4: Scope without PK is incomplete

Aşağıdaki lookup yanlış kabul edilir:

- `Model.query.get(id)`
- `db.session.get(Model, id)` if scope verification yoksa
- `GET /resource/<id>` where tenant/project scope implicit ama doğrulanmıyor

Doğru pattern:

- `get_scoped_or_none(Model, id, tenant_id=..., project_id=..., program_id=...)`
- route parametresindeki `id` alındıktan sonra scope doğrulaması

### Rule 5: API response'ta `id` ve `code` birlikte dönebilir, ama rolleri farklıdır

Response contract önerisi:

```json
{
  "id": "90d2d9a5-8f8c-4f4c-8e14-8d5d019e2f3b",
  "code": "REQ-014",
  "title": "Pricing exit for intercompany flow"
}
```

Anlam:

- `id`: mutation, link resolution, internal routing
- `code`: display, reporting, human conversation

### Rule 5A: User workflows code-first olmalıdır

UI ve raporlama tarafında varsayılan gösterim sırası:

1. `code`
2. `title` / `name`
3. status / owner / due date gibi operasyonel alanlar

Önerilen örnek render:

```text
REQ-014  Intercompany pricing exit
P1  Under Review  FI  12 Mar 2026
```

Kötü örnek:

```text
Intercompany pricing exit
ID: 4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58
```

Kullanıcı UUID görmemelidir; UUID sistem içindir.

### Rule 5B: Code lookup explicit olarak desteklenmelidir

Kullanıcı takibinin doğal olması için sistemde en azından aşağıdaki kabiliyetler bulunmalıdır:

- listelerde `code` gösterimi
- search box'ta `code` ile arama
- command palette / quick jump ile `code` açma
- export/import ve raporlarda `code` sütunu
- gerekiyorsa read-only `by-code` endpoint'leri

Örnek:

- `GET /api/v1/explore/requirements/by-code/REQ-014`
- `GET /api/v1/raid/risks/by-code/RSK-001`

Ancak mutation endpoint'leri yine `id` ile hedeflenir.

### Rule 6: External IDs ayrı namespace'tir

- `external_id`
- `alm_id`
- provider-specific IDs

Bu alanlar:

- sync mapping için kullanılır
- local PK yerine geçmez
- unique constraint gerekiyorsa explicit ve scoped kurulmalıdır

## Identifier Classes

### Class A: Technical PK

Örnek:

- `program.id = 12`
- `project.id = 44`
- `explore_requirement.id = "4c7f...""`

Use cases:

- CRUD target
- FK storage
- service-level joins
- canonical traceability node identity

### Class B: Human-facing Reference

Örnek:

- `program.code = "PGM-001"`
- `explore_requirement.code = "REQ-014"`
- `interface.code = "IF-FI-001"`

Use cases:

- ekran listeleri
- export
- toplantı notları
- e-posta / PDF / steering pack

### Class C: Polymorphic Entity Reference

Örnek:

```json
{
  "entity_type": "explore_requirement",
  "entity_id": "4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58"
}
```

veya

```json
{
  "entity_type": "risk",
  "entity_id": "245"
}
```

Use cases:

- audit
- signoff
- notifications
- AI suggestion / embedding / queue
- generic attachments

### Class D: Legacy Bridge Reference

Örnek:

- `legacy_requirement_id`

Use cases:

- migration bridge
- backward compatibility
- trace reconstruction

Bu alanlar geçiş amaçlıdır; canonical değil.

## API Modeling Standard

### Read endpoints

Varsayılan:

- `GET /api/v1/<resource>/<id>`

Kurallar:

- Path'teki `<id>` her zaman primary ID'dir.
- `code` ile lookup isteniyorsa route veya query explicit olmalıdır.

Örnek:

- Doğru: `GET /api/v1/explore/requirements/<uuid>`
- Doğru: `GET /api/v1/programs/12`
- Ayrı davranış: `GET /api/v1/explore/requirements/by-code/REQ-014`

### Mutation endpoints

- `POST`, `PUT`, `PATCH`, `DELETE` işlemlerinde target entity her zaman canonical `id` ile tanımlanır.
- UI `code` gösterse bile mutation payload veya URL `id` taşımalıdır.

### Filter/search endpoints

- `code`, `external_id`, `alm_id`, `legacy_requirement_id` filtrelenebilir.
- Bunlar lookup key olabilir, fakat canonical target değildir.

## UI Modeling Standard

UI tarafında her item için şu ayrım korunmalıdır:

- `id`: invisible technical handle
- `code`: visible primary label
- `title` / `name`: descriptive label

Önerilen render pattern:

- Liste satırı: `REQ-014` + title
- Internal actions: `data-id="<uuid or int>"`
- Copy/share action:
  - "Copy item link" → canonical route with `id`
  - "Copy business reference" → `code`

Ek UX kuralı:

- Kullanıcının göreceği yerde ham PK gösterilmez.
- Detay sayfası başlığında `code` sabit olarak görünür.
- Breadcrumb, page title, modal title, toast ve success message içinde mümkünse `code` kullanılır.

Örnek:

- Doğru: `REQ-014 saved`
- Doğru: `RSK-001 escalated`
- Zayıf: `Item saved`
- Yanlış: `Entity 245 updated`

## Traceability Standard

Traceability graph node identity:

- node key = `(entity_type, primary_id)`

Display:

- label = `code || title || name`

Kural:

- Traceability motoru display amaçlı `code` taşıyabilir.
- Graph node equality veya traversal `id` ile yapılmalıdır.

Not:

- Explore requirement için `REQ-014` business code'dur; canonical node ID değildir.

## Audit / Signoff / Notification Standard

Bu üç alan platformun identifier standardını ilk benimsemesi gereken yerlerdir.

### Audit

- `entity_type: String`
- `entity_id: String`
- her zaman canonical PK'nin string normalize edilmiş hali saklanır

### Signoff

- Aynı standardı kullanır
- Zaten hibrit PK dünyasını destekleyecek şekilde string taşıma mantığına yakındır

### Notification

- `entity_id` integer olmamalı
- string-normalized canonical PK taşımalıdır

## AI / RAG / Custom Fields Standard

Bu alanlar bugün en riskli bölgedir çünkü generic entity referansı taşırlar.

Standart:

- `entity_type: String`
- `entity_id: String`

Sebep:

- UUID entity'ler de first-class citizen olur
- Tek schema ile tüm platform support edilir
- API contract sadeleşir

## Database Type Policy

### Entity PK

- Yeni entity eklerken PK tipi domain kararıdır:
  - Explore-style distributed, merge-prone, offline/import-heavy alanlar için UUID uygundur
  - Geleneksel operasyonel tablolar için Integer sürdürülebilir

Bu ADR tüm PK'leri tek tipe zorlamaz.

Bu ADR'nin hedefi:

- PK tipleri hibrit kalsa da identifier semantics tekleşsin

### Polymorphic references

- Yeni tüm polymorphic `entity_id` kolonları string olmalıdır.
- Yeni generic helper tablolar integer `entity_id` ile tasarlanmamalıdır.

## Invariants

Sistemde şu invariants korunmalıdır:

1. Her entity'nin exactly one canonical technical identity'si vardır: PK `id`.
2. `code` varsa kullanıcı referansıdır; PK değildir.
3. Generic `entity_type + entity_id` kayıtlarında `entity_id` canonical PK'nin string formudur.
4. Scope-sensitive lookup hiçbir zaman çıplak `id` ile yapılmaz.
5. External IDs local canonical ID yerine geçmez.
6. Bir API route parametresi `id` diyorsa `code` kabul etmez.

## Anti-Patterns

Kaçınılacak örnekler:

- `traceability/<entity_type>/<code>` ama parametre adı `entity_id`
- `entity_id = Integer` generic helper tablo
- UI'da `code` gösterip mutation'da da `code` yollamak
- `db.session.get(Model, id)` yapıp tenant/project check yapmamak
- comment veya doc içinde `REQ-014` gibi business code'u "ID" diye adlandırmak

## Migration Strategy

### Phase 1: Semantics alignment

- Kod ve dokümanlarda `id` vs `code` ayrımı netleştirilir
- Response schema açıklamaları düzeltilir
- Route docstring'leri netleştirilir

### Phase 2: Polymorphic schema convergence

Aşağıdaki alanlar string'e taşınır:

- `notifications.entity_id`
- `custom_field_values.entity_id`
- `ai_embeddings.entity_id`
- benzer generic helper alanlar

Geçiş yöntemi:

- yeni nullable string kolon ekle
- backfill yap
- read path dual-read
- write path yeni kolona yaz
- testler geçince eski integer kolonu kaldır

### Phase 3: API normalization

- generic API endpoint'lerde `entity_id` string kabul edilir
- integer-only parse edilen helper endpoint'ler entity-type aware hale getirilir

### Phase 4: Tooling and linting

- yeni generic model tanımlarında `entity_id = Integer` kullanımını yasaklayan test veya lint kuralı eklenir
- serializer contract testleri eklenir

## Consequences

### Positive

- UUID ve integer PK'ler birlikte ama tutarlı yaşar
- API semantics netleşir
- traceability, audit, signoff ve AI katmanları ortak bir identifier modeli kullanır
- tenant isolation ve scoped lookup daha güvenli hale gelir
- UI/business ref ile technical ref karışmaz

### Negative

- Kısa vadede migration maliyeti vardır
- bazı endpoint ve testlerde type değişimi gerekir
- polymorphic indekslerde migration planı dikkat ister

## Non-Goals

Bu ADR şunları zorunlu kılmaz:

- tüm PK'lerin UUID'ye çevrilmesi
- tüm PK'lerin integer'a çevrilmesi
- `code` alanlarının kaldırılması
- mevcut tüm route'ların tek seferde değiştirilmesi

## Decision Summary

Platformun resmi identifier modeli şudur:

- `id` = canonical technical identity
- `code` = human/business tracking reference
- `entity_type + entity_id(string)` = cross-cutting polymorphic reference
- `tenant/program/project + id` = secure scoped reference
- `external_id/alm_id/...` = external namespace

Bu model hem hibrit PK gerçekliğini kabul eder hem de semantic karmaşayı ortadan kaldırır.
En önemli UX ilkesi şudur:

- sistem item'ı `id` ile işler
- kullanıcı item'ı `code` ile takip eder

## Follow-up Work

1. `notification`, `custom_fields`, `ai` tablolarındaki generic `entity_id` alanlarını audit et.
2. `traceability` ve benzeri endpoint yorumlarında `id` ve `code` terminolojisini düzelt.
3. Generic entity reference kullanan service ve blueprint'ler için string-normalized contract testleri yaz.
4. Yeni generic model eklenmesini denetleyen küçük bir architecture test ekle.
