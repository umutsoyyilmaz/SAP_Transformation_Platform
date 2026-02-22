# FDD: P0 Tenant Isolation Fix — Service Layer Scoped Queries

**Tarih:** 2026-02-21
**Pipeline:** Tip 3 — Complete BP (Architect → QA → Coder → Reviewer)
**Kaynak:** EXEC-SUMMARY-tenant-isolation-2026-02-21.md
**Öncelik:** P0-BLOCKER
**Tahmini Efor:** 3 servis × ~2 saat = 1 gün

---

## 1. MİMARİ KARAR (Architect)

### Problem
78 servis fonksiyonunda `Model.query.get(pk)` pattern'i tenant/project filtresiz kullanılıyor. Bu cross-tenant veri okuma ve yazma açığı oluşturuyor.

### Çözüm Stratejisi

**Helper utility + servis servis ilerleme.**

#### Adım 1: Helper Utility Oluştur
`app/services/helpers/scoped_queries.py` — tüm servisler bunu import edecek.

> **🔍 REVIEWER AUDIT NOTU (2026-02-22):**
> Bu FDD'nin tamamlanması **B-03 (Run/Hypercare)** için sert bağımlılıktır.
> `run_sustain_service.py` ve `cutover.py` modelleri de aynı `Model.query.get(pk)` açığını taşıyor.
> B-03 Sprint 4'e planlandı — bu fix Sprint 1'de tamamlanmadan B-03 implement edilmemelidir.
> Ayrıca bu dosyadaki `get_scoped()` helper, B-04 (SignoffRecord), F-06 (RaciEntry),
> I-01 (TransportRequest), I-08 (Stakeholder) FDD'lerinde de kullanılmalı — tüm yeni model
> sorgularında `nullable=True tenant_id` pattern'i yerine bu utility standart olarak benimsenmeli.

```python
"""
Tenant-scoped query helpers.

Every get-by-id in the platform MUST use these helpers instead of
Model.query.get(pk). Direct .get() calls bypass tenant isolation.
"""
from sqlalchemy import select
from app.models import db
from app.core.exceptions import NotFoundError


def get_scoped(model, pk, *, project_id=None, program_id=None, tenant_id=None):
    """
    Fetch a single entity by PK with mandatory scope filter.

    At least one scope parameter must be provided.
    Raises NotFoundError if not found or scope mismatch.

    Usage:
        ws = get_scoped(ExploreWorkshop, ws_id, project_id=project_id)
        kt = get_scoped(KnowledgeTransfer, kt_id, program_id=program_id)
    """
    if not any([project_id, program_id, tenant_id]):
        raise ValueError("get_scoped requires at least one scope filter")

    stmt = select(model).where(model.id == pk)

    if project_id is not None and hasattr(model, 'project_id'):
        stmt = stmt.where(model.project_id == project_id)
    if program_id is not None and hasattr(model, 'program_id'):
        stmt = stmt.where(model.program_id == program_id)
    if tenant_id is not None and hasattr(model, 'tenant_id'):
        stmt = stmt.where(model.tenant_id == tenant_id)

    result = db.session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise NotFoundError(
            resource=model.__name__,
            resource_id=pk
        )
    return result


def get_scoped_or_none(model, pk, *, project_id=None, program_id=None, tenant_id=None):
    """Same as get_scoped but returns None instead of raising."""
    try:
        return get_scoped(model, pk,
                          project_id=project_id,
                          program_id=program_id,
                          tenant_id=tenant_id)
    except NotFoundError:
        return None
```

#### Adım 2: Servis Servis Fix Sırası

| Sıra | Servis | Fonksiyon Sayısı | Scope Field | Neden Bu Sıra |
|------|--------|------------------|-------------|----------------|
| 1 | `workshop_session_service.py` | 9 🔴 | `project_id` (via workshop join) | BLOCKER: carry_forward |
| 2 | `workshop_docs_service.py` | 8 🔴 | `project_id` (via workshop join) | generate_minutes 3 query |
| 3 | `explore_service.py` | 19 🔴 | `project_id` | En çok fonksiyon |
| 4 | `run_sustain_service.py` | 13 🔴 | `program_id` | Farklı scope field |

#### Adım 3: Her Servis İçin Fix Pattern

**Pattern A — Doğrudan `project_id` olan entity'ler:**
```python
# ÖNCE (🔴)
def get_workshop_service(ws_id):
    ws = ExploreWorkshop.query.get(ws_id)

# SONRA (🟢)
def get_workshop_service(ws_id, project_id):
    ws = get_scoped(ExploreWorkshop, ws_id, project_id=project_id)
```

**Pattern B — Parent FK üzerinden scope (session → workshop → project):**
```python
# ÖNCE (🔴)
def get_session_service(session_id):
    session = WorkshopSession.query.get(session_id)

# SONRA (🟢)
def get_session_service(session_id, project_id):
    stmt = (
        select(WorkshopSession)
        .join(WorkshopSession.workshop)
        .where(
            WorkshopSession.id == session_id,
            ExploreWorkshop.project_id == project_id,
        )
    )
    session = db.session.execute(stmt).scalar_one_or_none()
    if not session:
        raise NotFoundError(resource="WorkshopSession", resource_id=session_id)
    return session
```

**Pattern C — `program_id` scope (run_sustain):**
```python
# ÖNCE (🔴)
def get_knowledge_transfer(kt_id):
    kt = KnowledgeTransfer.query.get(kt_id)

# SONRA (🟢)
def get_knowledge_transfer(kt_id, program_id):
    kt = get_scoped(KnowledgeTransfer, kt_id, program_id=program_id)
```

### Blueprint Değişikliği

Her blueprint route, servis çağrısına `project_id` geçirmeli:

```python
# ÖNCE (🔴)
@bp.route("/workshops/<ws_id>", methods=["GET"])
@require_permission("explore.view")
def get_workshop(ws_id):
    return jsonify(get_workshop_service(ws_id)), 200

# SONRA (🟢)
@bp.route("/workshops/<ws_id>", methods=["GET"])
@require_permission("explore.view")
def get_workshop(ws_id):
    project_id = g.current_project_id  # veya request.args / JWT'den
    return jsonify(get_workshop_service(ws_id, project_id=project_id)), 200
```

---

## 2. QA TEST SPEC

### Test 1: carry_forward cross-tenant engelleme
```
GIVEN: Tenant A'nın session_id=1, Tenant B'nin workshop_id=99
WHEN: carry_forward_items(session_id=1, {"target_workshop_id": 99, "open_item_ids": [...]}, project_id=A_project)
THEN: NotFoundError — target workshop Tenant A'nın project'inde yok
```

### Test 2: get_scoped helper
```
GIVEN: Workshop id=5, project_id=10 (Tenant A)
WHEN: get_scoped(ExploreWorkshop, 5, project_id=99)  # wrong project
THEN: NotFoundError raised
WHEN: get_scoped(ExploreWorkshop, 5, project_id=10)  # correct project
THEN: Workshop object returned
```

### Test 3: Mevcut fonksiyonellik korunuyor
```
GIVEN: Mevcut test suite (2191 test)
WHEN: Tüm testler çalıştırılır
THEN: Mevcut testler geçiyor (regression yok)
      — Bazı testler project_id parametresi eksik olduğu için kırılabilir
      — Bu testler güncellenmeli (beklenen kırılma)
```

### Test 4: get_scoped scope olmadan çağrılamaz
```
GIVEN: get_scoped(ExploreWorkshop, 5)  # scope parametresi yok
THEN: ValueError raised — "requires at least one scope filter"
```

---

## 3. CODER PROMPT (Copilot'a Verilecek)

Aşağıdaki 3 bölümü sırayla Copilot'a ver. Her bölüm sonrası test et, commit at.

### BÖLÜM 1: Helper Utility

```
@workspace Sen Coder Agent rolündesin.

## BAĞLAM
Tenant isolation audit'inde 78 fonksiyonda `Model.query.get(pk)` pattern'inin
tenant/project filtresiz kullanıldığı tespit edildi. Bu cross-tenant veri sızıntısı
oluşturuyor.

## GÖREV: Scoped Query Helper Oluştur

1. `app/services/helpers/` klasörünü oluştur (yoksa)
2. `app/services/helpers/__init__.py` oluştur (boş)
3. `app/services/helpers/scoped_queries.py` oluştur:

İçerik:
- get_scoped(model, pk, *, project_id=None, program_id=None, tenant_id=None)
  - En az bir scope parametresi zorunlu (yoksa ValueError)
  - select(model).where(model.id == pk, model.{scope_field} == scope_value)
  - Bulamazsa NotFoundError raise et
  - app/core/exceptions.py'deki NotFoundError'ı kullan

- get_scoped_or_none() — aynı ama None döner

4. Test yaz: tests/test_scoped_queries.py
   - test_get_scoped_without_scope_raises_value_error
   - test_get_scoped_wrong_project_raises_not_found
   - test_get_scoped_correct_project_returns_entity
   - test_get_scoped_or_none_returns_none

## KRİTİK
- Mevcut hiçbir dosyayı DEĞİŞTİRME — sadece yeni dosyalar oluştur
- SQLAlchemy 2.0 select() stili kullan (coding standards)
- app/core/exceptions.py'deki mevcut exception class'ları kontrol et ve kullan
```

### BÖLÜM 2: workshop_session_service.py Fix (BLOCKER dahil)

```
@workspace Sen Coder Agent rolündesin.

## BAĞLAM
app/services/helpers/scoped_queries.py oluşturuldu (önceki adım).
Şimdi workshop_session_service.py'deki 9 🔴 fonksiyonu fix ediyoruz.

En kritik: carry_forward_items — cross-tenant veri YAZMA açığı (P0-BLOCKER).

## GÖREV: workshop_session_service.py Tenant Isolation Fix

Dosya: app/services/workshop_session_service.py

### Kural:
Her `WorkshopSession.query.get(session_id)` çağrısını şununla değiştir:
```python
from app.services.helpers.scoped_queries import get_scoped

# Session → Workshop → project_id zinciri ile scope
stmt = (
    select(WorkshopSession)
    .join(WorkshopSession.workshop)
    .where(
        WorkshopSession.id == session_id,
        ExploreWorkshop.project_id == project_id,
    )
)
session = db.session.execute(stmt).scalar_one_or_none()
if not session:
    raise NotFoundError(resource="WorkshopSession", resource_id=session_id)
```

### Değiştirilecek fonksiyonlar (9 adet):
1. get_session(session_id) → get_session(session_id, project_id)
2. update_session(session_id, data) → update_session(session_id, data, project_id)
3. delete_session(session_id) → delete_session(session_id, project_id)
4. start_session(session_id) → start_session(session_id, project_id)
5. end_session(session_id, data) → end_session(session_id, data, project_id)
6. carry_forward_items(session_id, data) → carry_forward_items(session_id, data, project_id)
   ⚠️ BLOCKER: Bu fonksiyonda source session, target workshop VE open_item_ids
   üçü de project_id ile scope edilmeli!
7. get_session_summary(session_id) → get_session_summary(session_id, project_id)
8. list_session_participants(session_id) → list_session_participants(session_id, project_id)
9. add_session_note(session_id, data) → add_session_note(session_id, data, project_id)

### carry_forward_items özel fix:
```python
def carry_forward_items(session_id, data, project_id):
    # 1. Source session — project scope ile doğrula
    stmt = (
        select(WorkshopSession)
        .join(WorkshopSession.workshop)
        .where(WorkshopSession.id == session_id,
               ExploreWorkshop.project_id == project_id)
    )
    session = db.session.execute(stmt).scalar_one_or_none()
    if not session:
        raise NotFoundError(resource="WorkshopSession", resource_id=session_id)

    # 2. Target workshop — AYNI project scope
    target_ws = get_scoped(ExploreWorkshop,
                           data["target_workshop_id"],
                           project_id=project_id)

    # 3. Open items — AYNI project scope (batch)
    oi_ids = data.get("open_item_ids", [])
    stmt = select(ExploreOpenItem).where(
        ExploreOpenItem.id.in_(oi_ids),
        ExploreOpenItem.project_id == project_id,
    )
    open_items = db.session.execute(stmt).scalars().all()
    if len(open_items) != len(oi_ids):
        raise ValidationError("One or more open items not found in this project")

    # ... devam eden kopyalama mantığı aynı kalır
```

### Blueprint güncelleme:
Bu fonksiyonları çağıran blueprint route'ları da güncelle — project_id parametresi ekle.
Mevcut blueprint dosyasını bul:
grep -rn "carry_forward\|get_session\|update_session" app/blueprints/

## KRİTİK
- Fonksiyon signature'ları değişiyor — çağıran yerleri de güncelle
- Mevcut testleri çalıştır, kırılanları project_id ekleyerek düzelt
- SQLAlchemy 2.0 select() stili kullan
```

### BÖLÜM 3: workshop_docs_service.py Fix

```
@workspace Sen Coder Agent rolündesin.

## BAĞLAM
Önceki adımda workshop_session_service.py fix edildi.
Şimdi workshop_docs_service.py'deki 8 🔴 fonksiyonu fix ediyoruz.

## GÖREV: workshop_docs_service.py Tenant Isolation Fix

Aynı pattern: her query.get(pk) → get_scoped veya join-based scoped query.

### Değiştirilecek fonksiyonlar (8 adet):
1. get_document(doc_id) → get_document(doc_id, project_id)
   — Document → Workshop → project_id join
2. update_document(doc_id, data) → update_document(doc_id, data, project_id)
3. delete_document(doc_id) → delete_document(doc_id, project_id)
4. generate_meeting_minutes(workshop_id) → generate_meeting_minutes(workshop_id, project_id)
   ⚠️ 3 ayrı query fix: Workshop lookup + AgendaItem + Attendee
   Workshop'u get_scoped ile al, sonra agenda/attendee workshop_id FK ile güvenli
5. get_document_content(doc_id) → get_document_content(doc_id, project_id)
6. publish_document(doc_id) → publish_document(doc_id, project_id)
7. archive_document(doc_id) → archive_document(doc_id, project_id)
8. list_document_versions(doc_id) → list_document_versions(doc_id, project_id)

### Document → Workshop → project_id join pattern:
```python
stmt = (
    select(ExploreWorkshopDocument)
    .join(ExploreWorkshopDocument.workshop)
    .where(
        ExploreWorkshopDocument.id == doc_id,
        ExploreWorkshop.project_id == project_id,
    )
)
doc = db.session.execute(stmt).scalar_one_or_none()
```

## KRİTİK
- Blueprint route'ları da güncelle
- generate_meeting_minutes'deki 3 query'yi düzelt
- Mevcut testleri çalıştır, kırılanları düzelt
```

---

## 4. REVIEWER CHECKLIST (Fix Sonrası)

Her servis fix'i sonrası Copilot'a şu review prompt'unu ver:

```
@workspace Sen Reviewer Agent rolündesin. POST-FIX REVIEW.

Aşağıdaki dosyaları kontrol et:
- app/services/helpers/scoped_queries.py
- app/services/workshop_session_service.py (değişen)
- app/services/workshop_docs_service.py (değişen)
- İlgili blueprint dosyaları (değişen)
- İlgili test dosyaları (değişen/eklenen)

CHECKLIST:
☐ get_scoped helper doğru çalışıyor mu?
☐ Hiçbir fonksiyonda Model.query.get(pk) kalmadı mı?
☐ Tüm fonksiyon signature'larına project_id/program_id eklendi mi?
☐ carry_forward_items — source, target, OI üçü de scoped mu?
☐ generate_meeting_minutes — 3 query de scoped mu?
☐ Blueprint'ler project_id'yi servise geçiriyor mu?
☐ Mevcut testler geçiyor mu veya güncellendi mi?
☐ Yeni testler eklendi mi (cross-tenant engelleme)?
☐ SQLAlchemy 2.0 select() stili kullanılmış mı?

Bulduğun sorunları listele.
```

---

## 5. COMMIT STRATEJİSİ

| Commit | İçerik | Mesaj |
|--------|--------|-------|
| 1 | Helper utility + testleri | `[Feat] Scoped query helper for tenant isolation` |
| 2 | workshop_session_service.py fix | `[Fix] Workshop session service tenant isolation (P0-BLOCKER carry_forward)` |
| 3 | workshop_docs_service.py fix | `[Fix] Workshop docs service tenant isolation (generate_minutes)` |
| 4 | explore_service.py fix | `[Fix] Explore service tenant isolation (19 functions)` |
| 5 | run_sustain_service.py fix | `[Fix] Run sustain service tenant isolation (13 functions)` |

Her commit bağımsız olarak test edilebilir ve revert edilebilir.

---

*FDD prepared by Architect Agent — 2026-02-21*
