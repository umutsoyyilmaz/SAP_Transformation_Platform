# Workshop Modülü — Kapsamlı Analiz Raporu

**Tarih:** 2026-02-11
**Kapsam:** Workshop Hub (490 LOC) + Workshop Detail (645 LOC) + Backend Endpoints + Data Model
**Toplam:** 1135 LOC frontend, ~1200 LOC backend, 9 API call/sayfa

---

## 1. Modül Mimarisi

```
Workshop Hub (explore_workshops.js)          Workshop Detail (explore_workshop_detail.js)
┌─────────────────────────────────┐          ┌──────────────────────────────────────────┐
│ KPI Strip (5 KPI + metricBar)   │          │ Header (status + transition buttons)     │
│ FilterBar (status/area/wave/fac)│          │ Summary Strip (6 KPI)                    │
│ View Toggle: Table|Kanban|Cap   │          │ Tabs: Steps|Dec|OI|Req|Agenda|Attendees  │
│ GroupBy selector                │          │   └─ Steps: ProcessStepCard (expand)     │
│ Workshop Table (sortable)       │  click   │       └─ FitDecisionSelector             │
│ Workshop Kanban (4 columns)     │ ──────→  │       └─ Inline Forms (Dec/OI/Req)       │
│ Capacity View (per facilitator) │          │   └─ L3 Consolidated Decision            │
│ Area Milestone Tracker          │          │                                          │
│ Create Workshop Modal           │          │ Actions: Start|Complete|Reopen|Delta|Flag │
└─────────────────────────────────┘          └──────────────────────────────────────────┘
```

**Navigasyon:** Hub → localStorage(`exp_selected_workshop`) → Detail → `App.navigate('explore-workshops')` geri

---

## 2. Data Model İlişkileri

```
ExploreWorkshop (T-002)
├── WorkshopScopeItem (N:M → ProcessLevel L3)
├── WorkshopAttendee (1:N)
├── WorkshopAgendaItem (1:N)
├── WorkshopDependency (N:N self)
├── ExploreWorkshopDocument (1:N)
│
├── ProcessStep (1:N) — workshop start'ta otomatik oluşur
│   ├── fit_decision (fit | partial_fit | gap | NULL)
│   ├── ExploreDecision (1:N)
│   ├── ExploreOpenItem (1:N)
│   └── RequirementItem (indirect via workshop_id)
│
└── Multi-session: original_workshop_id → Delta workshops
```

---

## 3. Workshop Yaşam Döngüsü (State Machine)

```
                    ┌──────────┐
                    │  draft   │
                    └────┬─────┘
                         │ Start Workshop
                         │ (auto-creates ProcessSteps from L3→L4)
                    ┌────▼─────┐
           ┌────────│scheduled │  (date/time assigned varsa)
           │        └────┬─────┘
           │             │ Start
           │        ┌────▼──────────┐
           │        │ in_progress   │
           │        └────┬──────────┘
           │             │ Complete Workshop
           │             │ (validation: all steps assessed?)
           │        ┌────▼─────┐
           │        │completed │──→ Create Delta → yeni draft workshop
           │        └────┬─────┘
           │             │ Reopen
           │             └──→ in_progress (geri)
           │
           └──────→ cancelled (eksik — backend'de yok!)
```

---

## 4. Tespit Edilen Sorunlar

### 🔴 KRİTİK — API Field Mapping Hataları (Veri Kaybı Riski)

#### Sorun 4.1: Decision Create — `process_step_id` undefined

```
Frontend gönderen:    { l4_process_step_id: stepId, text: ..., decided_by: ... }
ExploreAPI.decisions.create:  API.post(`/process-steps/${data.process_step_id}/decisions`, data)
Backend bekleyen:     /process-steps/<step_id>/decisions (route param)

SORUN: Frontend "l4_process_step_id" gönderiyor ama API "data.process_step_id" okuyor
       → URL: /process-steps/undefined/decisions → 404 hatası
```

**Fix:** `submitInlineForm('decision', stepId)` içinde:
```javascript
// YANLIŞ:
await ExploreAPI.decisions.create(_pid, _wsId, {
    l4_process_step_id: stepId,  // ← API bunu tanımıyor
    ...
});

// DOĞRU:
await ExploreAPI.decisions.create(_pid, _wsId, {
    process_step_id: stepId,     // ← API URL'de bunu kullanıyor
    ...
});
```

#### Sorun 4.2: OpenItem Create — `workshop_id` ve `l4_process_step_id` kayboluyor

```
Frontend gönderen:  { workshop_id, l4_process_step_id, title, priority, ... }
ExploreAPI:         API.post(`/open-items`, {project_id: pid, ...data})
Backend endpoint:   create_open_item_flat() — workshop_id ve l4 alanlarını kabul ETMEYOR

SORUN: OpenItem'lar workshop/step bağlantısı olmadan "orphan" olarak oluşuyor
       → Workshop detail'da filterlanınca görünmüyor
```

**Backend'de `create_open_item_flat()` şu alanları yok sayıyor:**
- `workshop_id` → eklenmeli
- `l4_process_step_id` veya `process_step_id` → eklenmeli

**Alternatif:** Step-based endpoint kullanılmalı: `POST /process-steps/<step_id>/open-items`

#### Sorun 4.3: Requirement Create — Benzer sorun

Frontend `workshop_id` ve `l4_process_step_id` gönderiyor ama `POST /requirements` flat endpoint bunları kabul ediyor mu kontrol edilmeli. Step-based endpoint var: `POST /process-steps/<step_id>/requirements`

### 🟡 ORTA — Veri Çekme Verimsizliği

#### Sorun 4.4: fetchAll() — 9 paralel API call + client-side filtering

```javascript
// Workshop Detail: 9 API çağrısı
ExploreAPI.workshops.get(p, w),          // 1. tek workshop
ExploreAPI.levels.listL4(p),             // 2. TÜM L4'ler (yüzlerce!)
ExploreAPI.decisions.list(p, w),         // 3. workshop decisions
ExploreAPI.openItems.list(p),            // 4. TÜM open items (projedeki hepsi!)
ExploreAPI.requirements.list(p),         // 5. TÜM requirements (projedeki hepsi!)
ExploreAPI.fitDecisions.list(p, w),      // 6. workshop fit decisions
ExploreAPI.agenda.list(p, w),            // 7. workshop agenda
ExploreAPI.attendees.list(p, w),         // 8. workshop attendees
ExploreAPI.sessions.list(p, w),          // 9. workshop sessions
```

**Problem:** `listL4`, `openItems.list`, `requirements.list` proje seviyesinde TÜM verileri çekip sonra client-side filtreleme yapıyor. 500+ L4, 200+ OI, 300+ requirement olan projede bu ciddi performans sorunu.

**Ayrıca:** Steps filtreleme mantığı hatalı:
```javascript
_steps = _steps.filter(s => s.workshop_id === _wsId || s.l3_scope_item_id === _workshop.l3_scope_item_id);
```
`listL4` ProcessLevel döndürüyor, ProcessStep değil. ProcessLevel'da `workshop_id` alanı yok. Bu filtre hiçbir sonuç vermez veya yanlış sonuç verir.

#### Sorun 4.5: Workshop Hub Create — Field mapping uyumsuzluğu

```javascript
// Frontend gönderen:
{
    name: "...",
    type: "initial",            // ← doğru
    date: "2026-03-01",         // ← doğru
    facilitator_id: "John",     // ← string name, backend UUID bekliyor
    process_area: "FI",         // ← doğru
    wave: 1,                    // ← doğru
    scope_item_ids: ["uuid"],   // ← backend bu alanı arıyor mu?
    notes: "..."                // ← doğru
}
```

Backend `create_workshop` endpoint'i `scope_item_ids` array'ini alıp WorkshopScopeItem kayıtları oluşturuyor mu? Kontrol edilmeli.

### 🟡 ORTA — UX / Flow Sorunları

#### Sorun 4.6: Create Workshop modal — eksik alan validasyonu

- `Name` required ama frontend validasyonu yok (boş gönderilebilir)
- `Area` text input — dropdown olmalı (mevcut alanlardan seç)
- `L3 Scope Item ID` raw UUID — kullanıcı UUID'yi nereden bilecek? Dropdown/search olmalı
- `Facilitator` text input — team member dropdown olmalı
- `Wave` number input — max değer kontrolü yok

#### Sorun 4.7: Workshop Detail — Start sonrası steps boş görünebilir

Start endpoint ProcessStep'leri oluşturuyor ama:
1. Frontend `listL4` (ProcessLevel) çekiyor, ProcessStep değil
2. Backend'deki `GET /workshops/<ws_id>/process-steps` endpoint'i yoksa steps listelenemez
3. `fetchAll` sonrası filtreleme hatalı (4.4'te açıklandı)

#### Sorun 4.8: FitDecision — API endpoint uyumsuzluğu

```javascript
// Frontend:
ExploreAPI.fitDecisions.update(_pid, _wsId, existing.id, { fit_status: status });
// Bu çağırıyor: API.put(`/process-steps/${id}`, d)

// Ama existing.id bir FitGapDecision ID'si, ProcessStep ID'si değil!
// ProcessStep update endpoint'i fit_decision alanını güncelliyor olabilir
// ama gönderilen payload { fit_status: status } iken backend "fit_decision" bekliyor olabilir
```

#### Sorun 4.9: Delta Workshop — Scope items kopyalanmıyor

```javascript
async function createDeltaWorkshop() {
    await ExploreAPI.workshops.create(_pid, {
        name: `${_workshop.name} (Delta)`,
        workshop_type: 'delta',              // ← backend "type" alanı bekliyor
        l3_scope_item_id: _workshop.l3_scope_item_id,  // ← flat field, backend scope_item_ids[] bekliyor
        area_code: _workshop.area_code,      // ← backend "process_area" bekliyor
        ...
    });
}
```
Field adları backend ile uyuşmuyor. Delta workshop oluşur ama scope items, area, type bilgileri kaybolur.

#### Sorun 4.10: Transition API uyumsuzluğu

```javascript
// Frontend:
ExploreAPI.workshops.transition(_pid, _wsId, { action });
// Bu çağırıyor:
//   action='complete' → API.post(`/workshops/${id}/complete`)
//   action='start'    → API.post(`/workshops/${id}/start`)
//   action='reopen'   → ???

// Ama reopen için ExploreAPI.workshops.reopen() ayrıca var!
// transition() fonksiyonu 'reopen' action'ını handle etmiyor
```

`transition()` sadece `complete` ve `start` destekliyor:
```javascript
transition: (pid, id, d) => {
    if (d.action === 'complete') return API.post(`${B}/workshops/${id}/complete`, d);
    return API.post(`${B}/workshops/${id}/start`, d);  // default = start, reopen kaybolur
},
```

### 🟢 DÜŞÜK — Kozmetik / İyileştirme

#### Sorun 4.11: Emoji kullanımı (F-REV ile çakışıyor)
Workshop detail header'da: `📅`, `🕐`, `👤`, `📋`, `🔄`, `🚩`
Inline form'larda: emoji icon'lar
Empty state'lerde: `⚙️`, `💬`, `⚠️`, `📝`, `📋`, `👥`

#### Sorun 4.12: Inline form'lar — UX eksiklikleri
- Save sonrası tüm sayfa re-render ediliyor (scroll position kaybolur)
- Cancel/Save butonları form'un altında — uzun formlarda görünmeyebilir
- Validation feedback yok (hangi alan eksik?)
- Loading state yok (çift tıklama riski)

#### Sorun 4.13: L3 Consolidated Decision — her zaman görünüyor
Sadece `completed` status'ta görünmeli (doğru implement edilmiş) ama active tab ne olursa olsun sayfa sonunda. Kendi tab'ı olmalı veya steps tab'ının içinde olmalı.

#### Sorun 4.14: `_sessions` state'i kullanılmıyor
`fetchAll()`'da sessions çekiliyor ama hiçbir yerde render edilmiyor. Sessions tab yok.

---

## 5. Mevcut vs Beklenen Flow Karşılaştırması

### Workshop Oluşturma Flow

| Adım | Beklenen | Mevcut | Durum |
|------|----------|--------|:-----:|
| 1. "+ New Workshop" tıkla | Modal açılır | ✅ Modal açılır | ✅ |
| 2. İsim gir | Required validation | ❌ Validation yok | 🔴 |
| 3. L3 Scope Item seç | Dropdown/search | ❌ Raw UUID input | 🔴 |
| 4. Area seç | Dropdown (FI/CO/SD...) | ❌ Free text input | 🟡 |
| 5. Facilitator seç | Team member dropdown | ❌ Free text input | 🟡 |
| 6. Kaydet | Toast + listeye ekle | ✅ Çalışıyor | ✅ |

### Workshop Start Flow

| Adım | Beklenen | Mevcut | Durum |
|------|----------|--------|:-----:|
| 1. "Start Workshop" tıkla | Confirmation dialog | ❌ Direkt başlıyor | 🟡 |
| 2. Backend L4 steps oluşturur | ProcessStep kayıtları | ✅ Backend doğru | ✅ |
| 3. Steps listesi yüklenir | ProcessStep listesi | ❌ L4 ProcessLevel çekiyor | 🔴 |
| 4. Her step için fit decision | Radio button selector | ⚠️ Çalışabilir ama data mapping hatalı | 🟡 |

### Inline Form (Decision/OI/Req Ekleme) Flow

| Adım | Beklenen | Mevcut | Durum |
|------|----------|--------|:-----:|
| 1. "+ Decision" tıkla | Form açılır (step altında) | ✅ Çalışıyor | ✅ |
| 2. Alanları doldur | Validation | ❌ Validation yok | 🟡 |
| 3. Save tıkla | Loading → Success | ❌ Loading state yok | 🟡 |
| 4. API call | Doğru endpoint + fields | ❌ Field mapping hatalı (4.1) | 🔴 |
| 5. Yenile | Sadece ilgili bölüm | ❌ Tüm sayfa re-render | 🟡 |

### Workshop Complete Flow

| Adım | Beklenen | Mevcut | Durum |
|------|----------|--------|:-----:|
| 1. "Complete" tıkla | Confirmation + summary | ❌ Direkt tamamlıyor | 🟡 |
| 2. Unassessed steps kontrolü | Warning dialog | ✅ Backend 400 dönüyor | ✅ |
| 3. Open OIs uyarısı | Informational | ✅ Backend warning dönüyor | ✅ |
| 4. L3 propagation | Fit status aggregate | ✅ Backend yapıyor | ✅ |
| 5. L3 Consolidated Decision | Panel görünür | ✅ Render ediliyor | ✅ |

---

## 6. Önerilen İyileştirme Planı (Öncelik Sırası)

### Faz 1 — Kritik Bug Fix'ler (4-5 saat)

| # | Sorun | Fix | Effort |
|---|-------|-----|:------:|
| F1.1 | Decision create field mapping (4.1) | `l4_process_step_id` → `process_step_id` | 15min |
| F1.2 | OpenItem create orphan (4.2) | Step-based endpoint kullan veya flat endpoint'e workshop_id ekle | 1h |
| F1.3 | Requirement create (4.3) | Benzer fix | 30min |
| F1.4 | Steps data fetching (4.4/4.7) | `GET /workshops/<ws_id>/steps` endpoint ekle, frontend'i değiştir | 2h |
| F1.5 | Transition reopen (4.10) | `transition()` fonksiyonuna reopen case ekle | 15min |
| F1.6 | Delta workshop fields (4.9) | Field name mapping düzelt | 30min |

### Faz 2 — UX İyileştirmeler (6-8 saat)

| # | Sorun | Fix | Effort |
|---|-------|-----|:------:|
| F2.1 | Create Workshop modal (4.6) | L3 scope dropdown, area dropdown, facilitator dropdown, validation | 3h |
| F2.2 | Start/Complete confirmation | Confirmation dialog + summary (kaç step, kaç OI) | 1h |
| F2.3 | Inline form UX (4.12) | Validation, loading state, scroll preservation | 2h |
| F2.4 | FitDecision field name (4.8) | `fit_status` → `fit_decision` veya backend'i düzelt | 30min |
| F2.5 | L3 Decision yerleşimi (4.13) | Kendi tab'ına taşı veya steps tab footer'ına al | 30min |
| F2.6 | Sessions tab (4.14) | Multi-session bilgisini Agenda veya yeni tab'da göster | 1h |

### Faz 3 — Performans + Polish (3-4 saat)

| # | Sorun | Fix | Effort |
|---|-------|-----|:------:|
| F3.1 | fetchAll 9 API call (4.4) | Server-side aggregate endpoint: `GET /workshops/<id>/full` | 2h |
| F3.2 | Emoji removal (4.11) | F-REV ile birlikte | incl. |
| F3.3 | Create modal → L3 picker | Searchable dropdown component | 1h |
| F3.4 | Partial re-render | Step expand/collapse DOM patch | 1h |

**Durum:** ✅ Tamamlandı (aggregate endpoint + emoji cleanup + partial re-render)

---

## 7. Endpoint Envanteri

### Mevcut Workshop Endpoints (Backend)

| Method | Endpoint | Durum | Frontend Kullanıyor? |
|:------:|----------|:-----:|:-------------------:|
| GET | `/workshops` | ✅ | ✅ Hub |
| GET | `/workshops/<id>` | ✅ | ✅ Detail |
| POST | `/workshops` | ✅ | ✅ Create |
| PUT | `/workshops/<id>` | ✅ | ❌ (edit yok) |
| POST | `/workshops/<id>/start` | ✅ | ✅ |
| POST | `/workshops/<id>/complete` | ✅ | ✅ |
| POST | `/workshops/<id>/reopen` | ✅ | ⚠️ Transition mapping hatalı |
| POST | `/workshops/<id>/create-delta` | ✅ | ❌ (frontend kendi create kullanıyor) |
| GET | `/workshops/stats` | ✅ | ✅ Hub KPI |
| GET | `/workshops/capacity` | ✅ | ❌ (frontend kendi hesaplıyor) |
| GET | `/workshops/<id>/sessions` | ✅ | ✅ ama render etmiyor |
| GET | `/workshops/<id>/decisions` | ✅ | ✅ |
| GET | `/workshops/<id>/fit-decisions` | ✅ | ✅ |
| POST | `/workshops/<id>/fit-decisions` | ✅ | ✅ |
| GET | `/workshops/<id>/attendees` | ✅ | ✅ |
| POST | `/workshops/<id>/attendees` | ✅ | ❌ (add attendee UI yok) |
| PUT | `/attendees/<id>` | ✅ | ❌ |
| DELETE | `/attendees/<id>` | ✅ | ❌ |
| GET | `/workshops/<id>/agenda-items` | ✅ | ✅ |
| POST | `/workshops/<id>/agenda-items` | ✅ | ❌ (add agenda UI yok) |
| PUT | `/agenda-items/<id>` | ✅ | ❌ |
| DELETE | `/agenda-items/<id>` | ✅ | ❌ |
| GET | `/workshops/<id>/dependencies` | ✅ | ❌ (read-only render) |
| POST | `/process-steps/<id>/decisions` | ✅ | ⚠️ Field mapping hatalı |
| POST | `/process-steps/<id>/open-items` | ✅ | ❌ (flat endpoint kullanılıyor) |
| POST | `/process-steps/<id>/requirements` | ✅ | ❌ (flat endpoint kullanılıyor) |

### Eksik Endpoints

| Method | Endpoint | Neden Lazım |
|:------:|----------|-------------|
| GET | `/workshops/<id>/process-steps` | Detail view steps listesi |
| GET | `/workshops/<id>/full` | Single aggregate call (performans) |
| DELETE | `/workshops/<id>` | Workshop silme |

---

## 8. Özet Skor Kartı

| Kategori | Durum | Not |
|----------|:-----:|-----|
| Data Model | ✅ | Sağlam, ilişkiler doğru |
| Backend Endpoints | ✅ | 26 endpoint, CRUD + transitions mevcut |
| API Client (explore-api.js) | ⚠️ | Field mapping uyumsuzlukları |
| Workshop Hub UI | ✅ | Table/Kanban/Capacity/Milestone — zengin |
| Workshop Detail UI | ⚠️ | Render mantığı iyi ama data fetching hatalı |
| Inline Forms | ⚠️ | UI var ama API mapping kırık |
| Create Modal | 🟡 | Çalışıyor ama UX zayıf (dropdown yok) |
| Transitions | ⚠️ | Start/Complete çalışıyor, Reopen kırık |
| Delta Workshop | 🔴 | Field mapping tamamen yanlış |
| Performans | 🟡 | 9 API call, 3'ü gereksiz büyük veri çekiyor |
| Validation | 🔴 | Frontend'de hiç yok |

**Toplam: %60 fonksiyonel — Backend güçlü, frontend-backend arası mapping sorunları ana risk.**
