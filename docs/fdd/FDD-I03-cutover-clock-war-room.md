# FDD-I03: Cutover Clock — War Room Deneyimi

**Öncelik:** P3
**Tarih:** 2026-02-22
**Kaynak:** AUDIT-PLATFORM-FUNCTIONAL-2026-02-22.md → I-03
**Effort:** L (2 sprint)
**Faz Etkisi:** Deploy — Go-live weekend cutover yönetimi
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## 1. Problem Tanımı

Mevcut `cutover.js` view'ı ve `CutoverPlan`, `RunbookTask`, `Rehearsal`, `GoNoGoItem` modelleri mevcut. Ancak gerçek bir go-live weekend'inde ihtiyaç duyulan **gerçek zamanlı war room deneyimi** yok:
- Cutover başlangıcından itibaren countdown timer yok.
- Görevler paralel akışları olan bir kritik yol üzerinde görselleştirilmiyor.
- Her görevin kim tarafından yürütüldüğü real-time görülemiyor.
- Gecikme → kritik yola etki hesabı yok.
- AI Cutover Optimizer (`app/ai/assistants/cutover_optimizer.py`) mevcut ama UI bağlantısı zayıf.

---

## 2. İş Değeri

- Go-live weekend'inin en kaotik saatlerinde proje yöneticisi tüm durumu tek ekranda görür.
- Her görev saatlik ve dakikalık plana göre renklendirilir — gecikme anında fark edilir.
- Paralel akış görselleştirmesi kim ne yapıyor, kim neyi bekliyor sorusunu yanıtlar.
- AI Optimizer'ın task sıralama önerisi somut bir UI üzerinde gösterilir.
- Post-cutover rehearsal analizi için her cutover'ın timeline'ı kayıt altında kalır.

---

## 3. Mevcut Model Durumu

`app/models/cutover.py`:
- `CutoverPlan`: start_time, status, go_live_date — temel var.
- `RunbookTask`: title, assigned_to_id, planned_start, planned_end, actual_start, actual_end, status, depends_on_ids (JSON) — zincir takibi için yeterince detaylı.
- `GoNoGoItem`: criteria, status, checked_by_id — go/no-go kontrol listesi var.
- `Rehearsal`: start_datetime, end_datetime, status, issues_found — rehearsal kaydı var.

**Model değişikliği minimumdur.** Çoğunlukla yeni servis ve frontend gerekli.

---

## 4. Veri Modeli Değişiklikleri

### 4.1 `RunbookTask` Modeli Genişletme

```python
# Mevcut alanlara EKLENECEKler:
workstream = db.Column(
    db.String(50),
    nullable=True,
    comment="technical | basis | functional | data | interface | communication"
)
planned_duration_minutes = db.Column(db.Integer, nullable=True)
actual_duration_minutes = db.Column(db.Integer, nullable=True)
delay_minutes = db.Column(db.Integer, nullable=True, comment="Otomatik hesaplanır")
is_critical_path = db.Column(db.Boolean, nullable=False, default=False)
parallel_group = db.Column(
    db.String(20),
    nullable=True,
    comment="A | B | C | ... — Aynı gruptaki görevler paralel çalışır"
)
issue_note = db.Column(db.Text, nullable=True, comment="Sorun yaşandıysa not")
```

### 4.2 Migration
```
flask db migrate -m "extend runbook_tasks with workstream, critical_path, parallel_group"
```

---

## 5. Servis Katmanı

### 5.1 `app/services/cutover_service.py` Genişletme (mevcut dosya)

```python
def start_cutover_clock(tenant_id: int, project_id: int, plan_id: int) -> dict:
    """
    Cutover başlatır: CutoverPlan.status = 'active', actual_start = now().
    Tüm RunbookTask'lar için planned_start_offset hesaplanır.
    """

def complete_task(
    tenant_id: int, project_id: int, task_id: int,
    executor_id: int, notes: str | None = None
) -> dict:
    """
    Görevi tamamlar: actual_end = now().
    delay_minutes hesaplar.
    Bağımlı taskları unlock eder (depends_on kontrolü).
    Kritik yol taskı gecikmişse uyarı döner.
    """

def get_cutover_live_status(tenant_id: int, project_id: int, plan_id: int) -> dict:
    """
    War room tablosu için gerçek zamanlı durum snapshotu.

    Returns:
        {
          "clock": {
            "started_at": "...",
            "elapsed_minutes": 185,
            "planned_total_minutes": 1440,
            "estimated_completion": "...",
            "is_behind_schedule": True,
            "delay_minutes": 30
          },
          "go_no_go": {"passed": 12, "pending": 3, "failed": 0},
          "tasks": {
            "total": 87, "completed": 32, "in_progress": 5,
            "blocked": 2, "pending": 48
          },
          "workstreams": {
            "technical": {"completed": 10, "total": 20, "current_task": "..."},
            "basis": {"completed": 5, "total": 10, "current_task": "..."}
          },
          "critical_path_tasks": [
            {
              "id": 42, "title": "...", "status": "in_progress",
              "planned_end": "...", "delay_minutes": 15,
              "assigned_to": "A.Koç"
            }
          ],
          "ai_recommendation": null  // AI Optimizer bağlantısı için placeholder
        }
    """

def calculate_critical_path(tenant_id: int, project_id: int, plan_id: int) -> list[int]:
    """
    Tüm task bağımlılıklarından kritik yol task ID listesini hesaplar.
    Sadece plan başlamadan önce çalıştırılır.
    """
```

---

## 6. API Endpoint'leri

**Dosya:** `app/blueprints/cutover_bp.py`

```
POST /api/v1/projects/<proj_id>/cutover/plans/<plan_id>/start
     Permission: cutover.manage

GET  /api/v1/projects/<proj_id>/cutover/plans/<plan_id>/live-status
     Permission: cutover.view
     Response: get_cutover_live_status() çıktısı
     (Frontend 30 saniyede bir polling yapabilir)

POST /api/v1/projects/<proj_id>/cutover/tasks/<task_id>/complete
     Body: { "notes": "..." }
     Permission: cutover.execute

POST /api/v1/projects/<proj_id>/cutover/tasks/<task_id>/start
     Permission: cutover.execute

POST /api/v1/projects/<proj_id>/cutover/tasks/<task_id>/flag-issue
     Body: { "note": "..." }
     Permission: cutover.execute

GET  /api/v1/projects/<proj_id>/cutover/plans/<plan_id>/critical-path
     Permission: cutover.view
```

---

## 7. Frontend Değişiklikleri

### 7.1 `cutover.js` Genişletme — War Room View

**Cutover Clock (üst bant):**
```
╔══════════════════════════════════════════════════════════════════╗
║ ⏱ CUTOVER CLOCK    Başlangıç: 10 Ekim 22:00   Geçen: 03:05:22  ║
║ Tahmini Bitiş: 11 Ekim 08:30   Gecikme: ⚠️ +30 DK               ║
║ Go/No-Go: ✅12  ⏳3  🔴0  │  Tasks: 32/87  │  Critical Path: ✅ 4/6 ║
╚══════════════════════════════════════════════════════════════════╝
```

**Workstream Columns (Kanban benzeri):**
```
[TECHNICAL]        [BASIS]           [FUNCTIONAL]      [DATA]
  ✅ Backend down    ✅ SID check       🔄 FI cutover     ✅ Migration done
  🔄 ABAP deploy       ✅ Clients           ⏳ CO period      ⏳ Reconcile
  ⏳ Interface up    🔄 Transport      ⏳ SD activation  ⏳ Archive
```

**Gantt Timeline (alt bant):**
```
                     22:00  00:00  02:00  04:00  06:00  08:00
ABAP Deploy        [████████]
Transport Import           [█████████]
Interface Tests                    [██████]
Period Close                              [████]
Final Go/No-Go                                  [██]◆ Go Live
```

**AI Recommendation Panel:**
```
🤖 Cutover Optimizer Önerisi:
  Transport Import 30 dk gecikmiş. Interface Tests 2 saat erkene alınabilir.
  [Apply Recommendation]
```

### 7.2 30s Auto-Refresh
`live-status` endpoint'i 30 saniyede bir polling ile canlı güncelleme.

---

## 8. Test Gereksinimleri

```python
def test_start_cutover_clock_sets_actual_start():
def test_complete_task_calculates_delay_minutes():
def test_complete_task_unlocks_dependent_tasks():
def test_live_status_returns_correct_completed_count():
def test_live_status_marks_is_behind_schedule_when_delayed():
def test_calculate_critical_path_returns_correct_task_ids():
def test_flag_issue_sets_issue_note():
def test_tenant_isolation_live_status_cross_tenant_404():
```

---

## 9. Kabul Kriterleri

- [ ] Cutover start endpoint çalışıyor — `CutoverPlan.status = 'active'`.
- [ ] Task complete endpoint delay_minutes hesaplıyor.
- [ ] `GET /live-status` çalışıyor, 30s polling ile frontend güncelleniyor.
- [ ] War room UI: clock, workstream columns, critical path görünüyor.
- [ ] Gecikmiş kritik path task'ları kırmızı renk ile işaretleniyor.
- [ ] `calculate_critical_path()` bağımlılık zincirini doğru traverse ediyor.


---

## 🔍 REVIEWER AUDIT NOTU

**Audit Tarihi:** 2026-02-22
**Öncelik Matrisi Kaydı:** P3 — I-03 · Sprint 5 · Effort L
**Reviewer Kararı:** 🔵 KABUL EDİLİR — Real-time polling stratejisi Sprint 5 başında kesinleştirilmeli

### Tespit Edilen Bulgular

1. **30 saniye polling — WebSocket mı, SSE mi, polling mi?**
   FDD `GET /live-status` için 30 saniye polling öneriyor. Go-live weekend'inde 50+ kullanıcı war room'da olursa her 30 saniyede 50 request. Alternatif: Server-Sent Events (SSE) daha verimli. WebSocket ise Railway/Heroku'da sticky session gerektirir. Bu karar infrastructure seçimine göre verilmeli.

2. **`calculate_critical_path()` — bağımlılık zinciri sonsuz döngü riski.**
   `depends_on_ids` JSON alanı ile dairesel bağımlılık (A → B → A) mümkün. `calculate_critical_path()` algoritması cycle detection içermeli, aksi halde sonsuz döngüye girer.

3. **`delay_minutes` — otomatik hesaplanıyor ama concurrent update riski.**
   İki kullanıcı aynı task'ı aynı anda complete ederse `delay_minutes` yanlış hesaplanabilir. Database-level locking veya optimistic concurrency versioning eklenmeli.

4. **AI Cutover Optimizer entegrasyonu — gateway üzerinden mi?**
   `app/ai/assistants/cutover_optimizer.py` mevcut. Bu AI entegrasyonu `LLMGateway` üzerinden mi geçiyor? Platform standardına göre tüm AI çağrıları gateway'den geçmeli ve audit log'a yazılmalı.

### Eylem Kalemleri

| # | Eylem | Sahip | Sprint |
|---|---|---|---|
| A1 | Polling vs SSE kararını infrastructure kısıtlarına göre FDD'ye yaz | Architect | Sprint 5 |
| A2 | `calculate_critical_path()` içine cycle detection ekle | Coder | Sprint 5 |
| A3 | `delay_minutes` hesabı için optimistic locking stratejisi belirle | Coder | Sprint 5 |
| A4 | `cutover_optimizer.py` → `LLMGateway` kullanımını doğrula | Reviewer | Sprint 5 |
