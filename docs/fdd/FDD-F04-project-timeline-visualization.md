# FDD-F04: Proje Timeline Görselleştirme

**Öncelik:** P2
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → F-04
**Effort:** M (1 sprint)
**Faz Etkisi:** Prepare — Proje planlama ve yönetim
**Pipeline:** Tip 2 — Architect → Coder → Reviewer

---

## 1. Problem Tanımı

Platform'da `Phase`, `Gate`, `Sprint` modelleri mevcut ama bunları görsel bir zaman çizelgesinde gösteren herhangi bir UI yok. Proje yöneticisi proje takvimini görmek için başka araçlara (MS Project, Excel) başvurmak zorunda.

---

## 2. İş Değeri

- Proje yöneticisi faz geçişlerini, sprint tarihlerini ve gate'leri tek ekranda görebilir.
- Steering committee'ye "projekt nerede?" sorusuna görsel yanıt verir.
- Geciken fazları, kritik path üzerindeki riskleri anında tespit eder.
- SAP Activate faz blokları görsel olarak haritanlanabilir.

---

## 3. Teknik Tasarım

### 3.1 Mevcut Model Durumu
`app/models/program.py`:
- `Phase`: `name`, `start_date`, `end_date`, `status`, `program_id` — timeline için yeterli.
- `Gate`: `gate_type`, `planned_date`, `actual_date`, `status`, `phase_id` — milestone olarak kullanılabilir.
- `Sprint` (`app/models/backlog.py`): `name`, `start_date`, `end_date`, `status`, `project_id` — sprint baraları için.

**Model değişikliği gerekmez.** Sadece yeni bir API endpoint ve frontend görünümü yeterli.

### 3.2 Timeline Veri Endpoint'i
**Dosya:** `app/blueprints/program_bp.py`

```python
@bp.route("/api/v1/programs/<int:program_id>/timeline", methods=["GET"])
@require_permission("program.view")
def get_timeline(program_id: int):
    """
    Program timeline datasını döner — faz barları, gate milestone'ları, sprint'ler.

    Response format özellikle frontend Gantt/Timeline kütüphanesleriyle
    (vis-timeline, frappe-gantt, dhtmlx) uyumlu olacak şekilde tasarlandı.
    """
    ...
```

Response:
```json
{
  "program": {"id": 1, "name": "S/4HANA Migration", "start_date": "2026-01-01", "end_date": "2026-12-31"},
  "phases": [
    {
      "id": 1,
      "name": "Discover",
      "sap_activate_phase": "discover",
      "start_date": "2026-01-01",
      "end_date": "2026-01-31",
      "status": "completed",
      "color": "#22c55e",
      "gates": [
        {"id": 1, "name": "Discover Gate", "planned_date": "2026-01-31", "actual_date": "2026-01-29", "status": "passed"}
      ]
    }
  ],
  "sprints": [
    {
      "id": 10,
      "name": "Sprint 1",
      "project_id": 5,
      "project_name": "FI Implementation",
      "start_date": "2026-03-01",
      "end_date": "2026-03-14",
      "status": "active",
      "velocity": 23,
      "planned_points": 30
    }
  ],
  "milestones": [
    {"id": "m1", "name": "Design Freeze", "date": "2026-05-01", "type": "gate", "status": "upcoming"},
    {"id": "m2", "name": "Go-Live", "date": "2026-11-01", "type": "go_live", "status": "upcoming"}
  ],
  "today": "2026-02-22"
}
```

---

## 4. Frontend Değişiklikleri

### 4.1 Kütüphane Seçimi: `frappe-gantt`
- Açık kaynak MIT lisanslı, vanilla JS/CSS ile çalışır.
- CDN üzerinden yüklenebilir — build pipeline değişikliği gerekmez.
- Faz barları, milestone diamond'ları, bugün çizgisi built-in.

Alternatif: `vis-timeline` (daha zengin özellik seti, daha büyük bundle).

### 4.2 Yeni View: `static/js/views/timeline.js`

```javascript
/**
 * Project Timeline View
 * frappe-gantt tabanlı program faz ve sprint görselleştirmesi.
 *
 * Gösterilen öğeler:
 * - SAP Activate fazları (renkli barlar, faz renk kodu)
 * - Gate milestone'ları (diamond ikonlar)
 * - Sprint barları (faz içinde daha ince barlar)
 * - Bugün çizgisi (kırmızı dikey)
 * - Geciken öğeler (kırmızı renk override)
 *
 * Erişim: /#/programs/{programId}/timeline
 */
```

**Görsel Tasarım:**

```
SAP Activate Timeline — S/4HANA Migration 2026
────────────────────────────────────────────────────────────────────────
             Jan    Feb    Mar    Apr    May    Jun    Jul    Aug    ...
DISCOVER    [████]◆
PREPARE            [██████]◆
EXPLORE                   [████████████████]◆
REALIZE                                   [██████████████████████]◆
DEPLOY                                                          [████]◆▲
────────────────────────────────────────────────────────────────────────
Sprint 1           [░░]
Sprint 2                 [░░]
Sprint 3                       [░░]
────────────────────────────────────────────────────────────────────────
◆ Gate   ▲ Go-Live   │ Today   ████ On track   ████ Delayed
```

### 4.3 Renk Kodu
| Faz | Renk |
|-----|------|
| Discover | #6366f1 (mor) |
| Prepare | #f59e0b (sarı) |
| Explore | #3b82f6 (mavi) |
| Realize | #8b5cf6 (violet) |
| Deploy | #ef4444 (kırmızı) |
| Run | #22c55e (yeşil) |
| Tamamlanan | #9ca3af (gri) |
| Geciken | #ef4444 (kırmızı) |

### 4.4 Navigation
`program.js` dashboard'una "View Timeline" butonu ekle.
Sidebar'a Timeline linki ekle.

---

## 5. API Endpoint'leri

```
GET /api/v1/programs/<program_id>/timeline
    Permission: program.view
    Response: Yukarıdaki JSON formatı

GET /api/v1/programs/<program_id>/timeline/critical-path
    Permission: program.view
    Response: Geciken fazlar ve etkilenen gate'ler listesi
    {
      "delayed_items": [{"phase_id": 2, "name": "Prepare", "days_late": 5}],
      "at_risk_gates": [{"gate_id": 3, "name": "Explore Gate", "risk": "high"}]
    }
```

---

## 6. Test Gereksinimleri

```python
# tests/test_timeline.py

def test_timeline_endpoint_returns_all_phases():
def test_timeline_includes_gates_nested_in_phases():
def test_timeline_includes_sprints_with_date_range():
def test_timeline_marks_delayed_phases_correctly():
def test_critical_path_returns_delayed_items():
def test_tenant_isolation_timeline_cross_tenant_404():
```

---

## 7. Kabul Kriterleri

- [ ] `GET /programs/<id>/timeline` endpoint'i phases + gates + sprints döndürüyor.
- [ ] `frappe-gantt` veya seçilen kütüphane ile timeline görünümü çalışıyor.
- [ ] Geciken fazlar kırmızı renkle işaretleniyor.
- [ ] Bugün çizgisi (today marker) görünüyor.
- [ ] Gate milestone'ları diamond ikonla görünüyor.
- [ ] `program.js` dashboardunda "Timeline" butonu çalışıyor.
- [ ] Tenant isolation korunuyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P2 — F-04 · Sprint 3 · Effort M
**Reviewer Kararı:** 🔵 KABUL EDİLİR — Sprint 3 öncesinde kütüphane seçimi kesinleştirilmeli

### Tespit Edilen Bulgular

1. **Kütüphane seçimi lisans riski — frappe-gantt MIT, dhtmlx ticari.**
   FDD `frappe-gantt`, `vis-timeline`, `dhtmlx` seçeneklerini listeliyor. `dhtmlx` ticari lisanslıdır — ücretsiz kullanılamaz. Sprint 3'te yanlış kütüphane seçilirse ticari lisans sorunu doğar. `frappe-gantt` (MIT) önerilir.

2. **Model değişikliği yok — bu iyi, ama `Phase.start_date` null kontrolü gerekiyor.**
   `Phase` modelinde `start_date` nullable olabilir. Timeline endpoint'i null date'li fazları nasıl işleyeceğini belirtmeli — null date'li fazlar görünmez mi, placeholder mı gösterir?

3. **Read-only başlangıç kararı — FDD'de belirtilmiş, iyi.**
   Drag-to-reschedule yok. Ancak frontend kütüphanesi seçimi bu sınırlamayı desteklemeli (onClick handler'ı disable etmek yeterli). Bu karar implementation'da unutulursa kullanıcı drag edip hiçbir şey olmadığında kötü UX yaşar.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | `frappe-gantt` (MIT) as seçilen kütüphane olarak FDD'ye yaz | Architect | Sprint 3 Öncesi |
| A2 | Null `start_date` / `end_date` olan fazları timeline'da nasıl gösterileceğini belirt | Coder | Sprint 3 |
| A3 | Drag-to-reschedule disable edildiğini, cursor pointer olmayacağını UX spec'e ekle | Frontend | Sprint 3 |
