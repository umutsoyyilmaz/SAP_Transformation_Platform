# ADR-010: Business Code Standard

## Status

Proposed

## Date

2026-03-11

## Related

- [ADR-009-IDENTIFIER-MODEL.md](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/docs/plans/ADR-009-IDENTIFIER-MODEL.md)

## Why This Exists

Platformta teknik kimlik olarak `id` kullanılır.

Ama kullanıcılar item'ları teknik `id` ile değil, kısa ve okunabilir referans kodları ile takip eder:

- `REQ-014`
- `OI-003`
- `RSK-001`
- `CUT-001`
- `IF-FI-001`

Bu nedenle `code` alanı sadece görsel bir etiket değil, kullanıcı operasyonunun ana referansıdır.

Bu ADR, `code` alanının nasıl üretileceğini, nasıl gösterileceğini, nasıl aranacağını ve nasıl korunacağını tanımlar.

## Mental Model

Sistemin çalışma mantığı iki katmanlıdır:

- Sistem item'ı `id` ile işler.
- Kullanıcı item'ı `code` ile takip eder.

Örnek:

```json
{
  "id": "4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58",
  "code": "REQ-014",
  "title": "Intercompany pricing exit"
}
```

Burada:

- `id` backend için canonical technical key'dir.
- `code` kullanıcı için business tracking key'dir.

Kullanıcı şunu söyler:

- "`REQ-014` approved mı?"

Sistem ise arkada şunu çözer:

- `REQ-014` → ilgili requirement kaydı → UUID `id`

## Core Principles

### 1. Code-first user tracking

Kullanıcı-facing tüm ana work item'larda takip referansı `code` olmalıdır.

Bu şu alanlarda görünmelidir:

- liste ekranları
- detay sayfası başlığı
- breadcrumb
- toast / success message
- bildirim
- e-posta / export / PDF
- global arama / quick jump

### 2. Technical ID stays invisible

Ham PK değeri kullanıcıya normal akışta gösterilmez.

Gösterilmesi gereken:

- `REQ-014`
- `RSK-001`
- `IF-FI-001`

Gösterilmemesi gereken:

- `245`
- `4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58`

İstisna:

- admin/debug ekranları
- audit/export içeriği
- API response inspection

### 3. Code is stable

Bir item kullanıcıya gösterildikten sonra `code` mümkün olduğunca değişmez kabul edilir.

Sebep:

- toplantı notları bozulmaz
- e-posta geçmişi kırılmaz
- Excel/export satırları referansını kaybetmez
- kullanıcı hafızası korunur

### 4. Code is not the DB primary key

`code` çok önemli bir kullanıcı referansı olsa da teknik primary key değildir.

Yani:

- read/search/by-code akışı olabilir
- mutation/doğrudan entity hedefleme yine `id` ile yapılır

## Scope

Bu standart aşağıdaki user-facing entity tipleri için geçerlidir:

- program
- project
- explore requirement
- explore open item
- explore decision
- workshop
- backlog item
- config item
- risk
- action
- issue
- decision
- interface
- cutover plan
- cutover task
- cutover incident
- war room
- test case
- defect
- scope change request
- benzeri operasyonel work item'lar

Bu standart şu kayıtlar için zorunlu değildir:

- junction tabloları
- saf teknik helper tablolar
- internal event rows
- background/system records

## Standard Syntax

Tüm business code'larda varsayılan karakter standardı:

- sadece `A-Z`
- sadece `0-9`
- sadece `-`

Kurallar:

- büyük harf kullanılır
- boşluk kullanılmaz
- underscore kullanılmaz
- slash kullanılmaz
- nokta sadece özel hiyerarşik process code'larda istisna olarak kullanılabilir
- başta veya sonda `-` olmaz
- art arda `--` olmaz

Örnek doğru formatlar:

- `REQ-014`
- `WS-SD-01`
- `IF-FI-001`
- `CUT-001-T047`
- `RSK-PGM-001`

Örnek yanlış formatlar:

- `req-14`
- `Req_014`
- `REQ 014`
- `REQ/014`

## Standard Length

Önerilen hedef:

- çoğu work item code'u `<= 30` karakter

İzin verilen istisna:

- bazı modellerde kolon genişliği nedeniyle `<= 50`

Pratik ilke:

- kod kısa okunur olmalı
- ekrana sığmalı
- konuşurken kolay telaffuz edilmeli

## Code Families

Kodlar tek tip olmak zorunda değildir. Dört ana family kullanılır.

### Family A: Pure sequential work-item code

Biçim:

```text
<PREFIX>-<SEQ>
```

Örnek:

- `REQ-014`
- `OI-003`
- `RSK-001`
- `ACT-001`
- `ISS-001`
- `DEC-001`
- `CUT-001`
- `INC-001`
- `WR-001`
- `CR-001`

Ne zaman kullanılır:

- item tipi kendi başına yeterince anlaşılırsa
- ekstra bağlam kodun içine gömülmeden de kullanıcı tarafından anlaşılabiliyorsa

### Family B: Contextual semantic code

Biçim:

```text
<PREFIX>-<CONTEXT>-<SEQ>
```

Örnek:

- `WS-SD-01`
- `WS-FI-03A`
- `IF-FI-001`
- `TC-FI-001`
- `CFG-SD-042`
- `DEF-FI-042`

Ne zaman kullanılır:

- modül/alan kodu kullanıcı için gerçekten değerli ise
- kodun konuşma sırasında bağlamı hızlı anlatması isteniyorsa

Kural:

- context bölümü sadece stabil alanlardan türetilir
- status, owner, tarih gibi değişken bilgiler code içine gömülmez

### Family C: Hierarchy code

Biçim:

```text
<LEVEL/PATH>
```

Örnek:

- `VC-001`
- `PA-FIN`
- `J58`
- `J58.01`

Ne zaman kullanılır:

- süreç hiyerarşisi veya katalog yapısı temsil ediliyorsa

### Family D: Composed child code

Biçim:

```text
<PARENT-CODE>-<CHILD-PREFIX><SEQ>
```

Örnek:

- `CUT-001-T047`

Ne zaman kullanılır:

- child item, parent item ile güçlü görsel ilişki kurmalıysa

## Prefix Standard

Her user-facing entity sabit ve kolay öğrenilebilir bir prefix ailesine sahip olmalıdır.

Önerilen/uyumlu prefix seti:

| Entity | Prefix | Örnek |
|---|---|---|
| Program | `PGM` | `PGM-001` |
| Project | serbest business shorthand | `TR-W1`, `CORE`, `DE-R1` |
| Explore Requirement | `REQ` | `REQ-014` |
| Explore Open Item | `OI` | `OI-003` |
| Explore Decision | `DEC` | `DEC-004` |
| Workshop | `WS` | `WS-SD-01` |
| Backlog Item | `WRICEF` veya subtype | `WRICEF-FI-001`, `ENH-SD-042` |
| Config Item | `CFG` | `CFG-FI-001` |
| Risk | `RSK` | `RSK-001` |
| Action | `ACT` | `ACT-001` |
| Issue | `ISS` | `ISS-001` |
| RAID Decision | `DEC` | `DEC-001` |
| Program Decision | `DEC-PGM` | `DEC-PGM-001` |
| Program Risk | `RSK-PGM` | `RSK-PGM-001` |
| Program Milestone | `MS-PGM` | `MS-PGM-001` |
| Interface | `IF` | `IF-FI-001` |
| Cutover Plan | `CUT` | `CUT-001` |
| Cutover Task | parent-composed | `CUT-001-T047` |
| Cutover Incident | `INC` | `INC-001` |
| War Room Entry | `WR` | `WR-001` |
| Scope Change Request | `SCR` | `SCR-001` |
| Test Case | `TC` | `TC-FI-001` |
| Defect | `DEF` | `DEF-0001` |

## Sequence Standard

Varsayılan sayı formatı:

- 3 haneli zero-padded sequence

Örnek:

- `REQ-001`
- `REQ-014`
- `RSK-128`

İstisnalar:

- yüksek hacimli entity'lerde 4 hane kabul edilebilir
- mevcut ürün davranışı korunuyorsa farklı genişlik desteklenebilir

Örnek:

- `DEF-0001`

Kural:

- bir entity family içinde padding stili tutarlı olmalıdır
- aynı entity için `REQ-1` ve `REQ-001` birlikte yaşamamalıdır

## Uniqueness Standard

`code` global unique olmak zorunda değildir. Doğru scope içinde unique olmalıdır.

Önerilen scope mantığı:

| Entity family | Recommended uniqueness scope |
|---|---|
| Program | tenant veya platform |
| Project | program |
| Explore Requirement | project |
| Workshop | project |
| Explore Open Item | program |
| RAID items | project veya program iş bağlamı |
| Backlog / Config / Interface / Test Case | project |
| Cutover artifacts | plan veya program |

Pratik kural:

- kullanıcı aynı çalışma bağlamında aynı `code` ile iki farklı item görmemelidir

## Immutability Standard

Varsayılan davranış:

- create anında `code` üretilir
- create sonrası normal kullanıcı akışında değişmez

İzin verilen istisna:

- yönetici düzeltmesi
- migration/backfill
- data repair

Bu durumda:

- değişiklik audit'e yazılır
- eski kod tekrar kullanılmaz
- mümkünse eski kod alias/history olarak tutulur

## Reuse Policy

Bir code bir kez yayımlandıktan sonra tekrar kullanılmaz.

Silinmiş, iptal edilmiş veya superseded item için bile reuse yapılmaz.

Yanlış:

- `REQ-014` silindi, yeni item'a tekrar verildi

Doğru:

- `REQ-014` geçmişte kaldı
- yeni item `REQ-015` veya uygun yeni numara ile oluşturuldu

## Generation Policy

Code üretimi service layer'da yapılmalıdır.

Algoritma:

1. item scope'u belirlenir
2. entity family belirlenir
3. uygun prefix belirlenir
4. scope içindeki son sequence bulunur
5. bir sonraki sequence tahsis edilir
6. kayıt transaction içinde yazılır

Concurrency kuralı:

- duplicate üretimi DB unique constraint + retry ile engellenir

## Search and Navigation Policy

Kullanıcı akışı code-first olmalıdır.

Sistem aşağıdaki davranışları desteklemelidir:

- exact code search
- prefix search
- paste-and-open akışı
- command palette quick jump
- export/import içinde code sütunu

Örnek:

Kullanıcı arama kutusuna `REQ-014` yazar.

Sistem:

1. aktif scope içinde `REQ-014` arar
2. tek eşleşme bulursa ilgili entity'yi resolve eder
3. UI detaya `id` ile gider

Yani kullanıcı code ile başlar, sistem id ile açar.

## API Policy

### Read

Canonical route target:

```http
GET /api/v1/explore/requirements/<id>
```

Opsiyonel code lookup route:

```http
GET /api/v1/explore/requirements/by-code/REQ-014
```

### Write

Mutation target her zaman `id` olmalıdır:

```http
PATCH /api/v1/explore/requirements/<id>
```

`code` ile mutation yapılmaz.

### Response

User-facing entity response'larında `code` dönmelidir.

Örnek:

```json
{
  "id": "4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58",
  "code": "REQ-014",
  "title": "Intercompany pricing exit",
  "status": "under_review"
}
```

## UX Standard

Varsayılan render düzeni:

```text
REQ-014  Intercompany pricing exit
P1  Under Review  FI
```

Başarılı message örnekleri:

- `REQ-014 saved`
- `RSK-001 escalated`
- `CUT-001 approved`

Kaçınılacak örnekler:

- `Item saved`
- `Entity updated`
- `4c7fdc8f-3b91-4a9a-8b75-6b7f7f1f0f58 updated`

## End-to-End Example 1

Create requirement:

1. User creates a new Explore Requirement.
2. Service allocates:
   - `id = "4c7fdc8f-..."`
   - `code = "REQ-014"`
3. UI listesinde item `REQ-014` olarak görünür.
4. Notification title `REQ-014 created` olur.
5. Search box'a `REQ-014` yazınca detay açılır.
6. Backend update işlemini UUID `id` ile yapar.

## End-to-End Example 2

Find from meeting note:

Toplantı notunda şu satır var:

```text
REQ-014 before UAT sign-off
```

Kullanıcı:

1. `REQ-014` aratır
2. sistem code'dan item'ı bulur
3. detay ekranı açılır
4. approval işlemi teknik `id` ile yapılır

## End-to-End Example 3

Title changes, code stays:

Başlangıç:

```json
{
  "id": "4c7fdc8f-...",
  "code": "REQ-014",
  "title": "Intercompany pricing exit"
}
```

Başlık revize edilir:

```json
{
  "id": "4c7fdc8f-...",
  "code": "REQ-014",
  "title": "Intercompany transfer pricing enhancement"
}
```

Sonuç:

- kullanıcı referansı kırılmaz
- eski toplantı notları geçerliliğini korur
- teknik hedef de değişmez

## Current System Compatibility

Bu standart mevcut model örnekleriyle uyumludur:

- Program: `PGM-001` [app/models/program.py#L77](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/program.py#L77)
- Explore Open Item: `OI-{seq}` [app/models/explore/requirement.py#L168](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/explore/requirement.py#L168)
- Workshop: `WS-{area}-{seq}{letter}` [app/models/explore/workshop.py#L78](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/explore/workshop.py#L78)
- Backlog item: `WRICEF-FI-001` [app/models/backlog.py#L176](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/backlog.py#L176)
- Risk: `RSK-001` [app/models/raid.py#L97](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/raid.py#L97)
- Interface: `IF-FI-001` [app/models/interface_factory.py#L107](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/interface_factory.py#L107)
- Cutover plan: `CUT-001` [app/models/cutover.py#L227](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/cutover.py#L227)
- Test case: `TC-FI-001` [app/models/testing.py#L419](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/models/testing.py#L419)

## Non-Goals

Bu standart şunları zorunlu kılmaz:

- tüm entity'lerin aynı code pattern kullanması
- tüm code'ların global unique olması
- `id` kullanımının kaldırılması
- eski data'nın tek seferde yeniden kodlanması

## Summary

Business code standardının özeti:

- kullanıcı item'ı `code` ile tanır
- sistem item'ı `id` ile işler
- `code` kısa, görünür, stabil ve scope içinde unique olur
- `code` arama, raporlama ve operasyonel dilin ana referansı olur
- `id` teknik güvenlik ve veri bütünlüğü için arka planda kalır
