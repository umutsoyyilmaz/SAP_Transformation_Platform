# FDD-I04: Lessons Learned / Knowledge Base Modülü

**Öncelik:** P3
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-04
**Effort:** M (1 sprint)
**Faz Etkisi:** Run — Proje kapanışı ve kurumsal hafıza
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform bir proje kapandığında tüm bilgi birikimi kaybolur. Run/Hypercare fazında yaşanan sorunlar, yapılmasını istediğimiz ama yapamadığımız şeyler, bir sonraki proje için tavsiyeler hiçbir yerde kayıt altına alınmaz.

SAP SI firmaları için kurumsal hafıza oluşturmak kritik: aynı hatalar farklı projelerde tekrar yapılmamalı.

---

## 2. İş Değeri

- SI firmaları multi-tenant yapıda birden fazla proje yürütüyor — cross-project learning kritik.
- "Bu modülde daha önce ne tür WRICEF'ler çıktı?" sorusu yanıtlanabilir.
- Yeni proje başlarken scope assessment'ı destekler (Discover fazı FDD-B02 ile entegrasyon).
- Müşteri retention: proje bittikten sonra da platforma değer katılıyor.

---

## 3. Veri Modeli

### 3.1 Yeni Model: `LessonLearned`
**Dosya:** `app/models/run_sustain.py` içine ekle

```python
class LessonLearned(db.Model):
    """
    Proje sonrası lessons learned kaydı.

    Bir projeden çıkarılan ders, ilgili SAP modülü ve faz ile etiketlenerek
    Knowledge Base'e eklenir. Her tenant'ın kendi KB'si var (tenant_id izolasyonu),
    ancak tenant izin verirse 'public' paylaşıma açılabilir.
    """
    __tablename__ = "lessons_learned"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        comment="Proje silinse de ders kayıtları korunur (nullable)"
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    title = db.Column(db.String(255), nullable=False)
    category = db.Column(
        db.String(30),
        nullable=False,
        comment="what_went_well | what_went_wrong | improve_next_time | risk_realized | best_practice"
    )
    description = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.Text, nullable=True, comment="Bir sonraki proje için tavsiye")
    impact = db.Column(
        db.String(10),
        nullable=True,
        comment="high | medium | low — bu dersin önemi"
    )

    # Etiketler — arama ve filtre için
    sap_module = db.Column(db.String(10), nullable=True, comment="FI, MM, SD, ...")
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | prepare | explore | realize | deploy | run"
    )
    tags = db.Column(
        db.String(500),
        nullable=True,
        comment="CSV etiketler: data-migration,interface,authorization"
    )

    # Kaynağa bağlantı (opsiyonel)
    linked_incident_id = db.Column(
        db.Integer,
        db.ForeignKey("hypercare_incidents.id", ondelete="SET NULL"),
        nullable=True
    )
    linked_risk_id = db.Column(
        db.Integer,
        db.ForeignKey("risks.id", ondelete="SET NULL"),
        nullable=True
    )

    # Paylaşım
    is_public = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True ise tüm tenant'lara görünür (cross-tenant KB)"
    )

    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    upvote_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_ll_tenant_phase", "tenant_id", "sap_activate_phase"),
        db.Index("ix_ll_tenant_module", "tenant_id", "sap_module"),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### 3.2 Migration
```
flask db migrate -m "add lessons_learned table"
```

---

## 4. Servis Katmanı

### 4.1 Yeni Servis: `app/services/knowledge_base_service.py`

```python
def create_lesson(tenant_id: int, project_id: int, author_id: int, data: dict) -> dict:

def search_lessons(
    tenant_id: int,
    query: str | None = None,
    sap_module: str | None = None,
    phase: str | None = None,
    category: str | None = None,
    include_public: bool = True,
) -> list[dict]:
    """
    Full-text search (title + description + recommendation + tags).
    include_public=True → kendi tenant'ı + public kaydlar.

    SQLite: LIKE-based search.
    PostgreSQL: tsvector full-text veya ilike.
    """

def upvote_lesson(tenant_id: int, lesson_id: int, user_id: int) -> dict:
    """Dersi oy ver (upvote). Duplicate vote koruması yok — basit sayaç."""

def get_kb_summary(tenant_id: int) -> dict:
    """
    Returns:
        {
          "total": 45,
          "by_category": {"what_went_well": 20, "what_went_wrong": 15, ...},
          "by_module": {"FI": 15, "MM": 10, ...},
          "top_voted": [{"id": ..., "title": ..., "upvotes": 8}]
        }
    """

def export_lessons_to_pdf(tenant_id: int, project_id: int | None = None) -> bytes:
    """Lessons learned raporu PDF export (proje kapanış raporu için)."""
```

---

## 5. API Endpoint'leri

**Yeni Dosya:** `app/blueprints/knowledge_base_bp.py`

```
# Knowledge Base
GET    /api/v1/kb/lessons
       Query params: q (search), module, phase, category, project_id
       Permission: kb.view
       Note: Public lessons tüm tenant'lara görünür

POST   /api/v1/kb/lessons
       Permission: kb.create

GET    /api/v1/kb/lessons/<id>
       Permission: kb.view

PUT    /api/v1/kb/lessons/<id>
       Permission: kb.edit (sadece kendi tenant'ı)

POST   /api/v1/kb/lessons/<id>/upvote
       Permission: kb.view

GET    /api/v1/kb/summary
       Permission: kb.view

GET    /api/v1/projects/<proj_id>/kb/export-pdf
       Permission: kb.export
```

---

## 6. Frontend Değişiklikleri

### 6.1 Yeni View: `static/js/views/knowledge_base.js`

```
Knowledge Base 📚
─────────────────────────────────────────────────────────
[🔍 Search lessons...         ] [Module ▾] [Phase ▾] [Category ▾]

Top Lessons (by votes):
┌────────────────────────────────────────────────────────────────────┐
│ ▲ 8  [Best Practice] FI Closing Period Setup                       │
│       Phase: Realize  Module: FI  Tags: period-close, customizing  │
│       Recommendation: Her sprint'te period status kontrol edilmeli │
│                                               2026-01-15 • A.Koç   │
├────────────────────────────────────────────────────────────────────┤
│ ▲ 5  [Risk Realized] Interface cutover weekendinde timeout         │
│       Phase: Deploy  Module: MM  Tags: interface,timeout           │
└────────────────────────────────────────────────────────────────────┘

[+ Add Lesson]
```

### 6.2 Hızlı "Add Lesson" Shortcut
- `hypercare.js` incident close flow'una: "Add to Knowledge Base" butonu.
- `raid.js` RAID risk close flow'una: "Add to Knowledge Base" opsiyonu.

### 6.3 Navigation
Sidebar'a "Knowledge Base" sabit linki ekle (tüm projeler üzerinde çalışır).

---

## 7. Test Gereksinimleri

```python
def test_create_lesson_returns_201():
def test_search_lessons_by_title_text():
def test_search_lessons_filter_by_sap_module():
def test_search_lessons_includes_public_lessons_from_other_tenants():
def test_private_lesson_not_visible_to_other_tenants():
def test_upvote_increments_count():
def test_export_pdf_returns_bytes():
def test_kb_summary_returns_by_category_counts():
def test_tenant_isolation_edit_blocked_cross_tenant():
```

---

## 8. Kabul Kriterleri

- [ ] Lesson oluşturulabiliyor ve KB'de listseleniyor.
- [ ] Metin araması (q parametresi) çalışıyor.
- [ ] `is_public=True` olan lesson'lar diğer tenant'lara görünüyor.
- [ ] Upvote sayacı çalışıyor.
- [ ] `knowledge_base.js` view search + list + add form ile çalışıyor.
- [ ] Incident ve RAID close flow'larında "Add to KB" butonu görünüyor.
- [ ] Tenant isolation: kendi private lesson'ları başka tenant'a görünmüyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P3 — I-04 · Sprint 6 · Effort M
**Reviewer Kararı:** 🔵 KABUL EDİLİR — Cross-tenant veri paylaşımı güvenlik mekanizması eksik

### Tespit Edilen Bulgular

1. **`is_public=True` — cross-tenant paylaşım güvenlik mekanizması eksik.**
   `is_public=True` olan lesson'ların diğer tenant'lara görünmesi kabul kriterlerinde var. Ancak hangi alanların public paylaşımda maskeleneceği belirtilmemiş. Örneğin `project_id`, müşteri şirket adı, proje detayları başka tenant'a görünmemeli. Public paylaşımda `to_dict_public()` metodu ayrıca tanımlanmalı — hassas alanlar maskelenmeli.

2. **Upvote — aynı kullanıcı birden fazla upvote yapabilir mi?**
   `upvote_count` integer sayaç. Kullanıcı başına 1 upvote sınırı yoksa sayaç manipüle edilebilir. DB-level unique constraint (`user_id, lesson_id`) veya upvote kayıt tablosu eklenmeli.

3. **B-02 Discover fazı ile entegrasyon noktası.**
   FDD §2 içinde "Discover fazı FDD-B02 ile entegrasyon" potansiyel'inden bahsediliyor. Bu entegrasyon için `ScopeAssessment` oluştururken ilgili lesson'ları önermek anlamlı olur. Bu otomatik öneri AI feature gerektirir — LLMGateway üzerinden FDD-F07-benzeri bir gateway ile yapılmalı, yoksa audit log eksik kalır.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `to_dict_public()` metodu ekle — hassas alanları maskele (project_id, tenant_id) | Coder | Sprint 6 |
| A2 | Upvote unique constraint (user + lesson) DB level'da ekle | Coder | Sprint 6 |
| A3 | B-02 entegrasyon noktasını AI feature olarak backlog'a ekle | Architect | Sprint 6+ |
