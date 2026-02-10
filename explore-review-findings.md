# Explore Phase — End-to-End Review Findings

**Tarih:** 2025-02-11  
**Scope:** Explore Phase modülünün 9 kaynak dosyası üzerinde uçtan uca tutarlılık analizi  
**Yöntem:** D1 (FS/TS) ↔ M9 (Model) ↔ B9 (Blueprint) ↔ S (Services×8) ↔ T1 (Tests) ↔ D9 (Task List) ↔ Seed Data ↔ User Guide (TR+EN)  
**Reviewer:** Architecture Review Agent  
**Commit:** `3c331dd` (TS-Sprint 2)

---

## Kaynak Dosya Envanteri

| Kısaltma | Dosya | LOC | Durum |
|----------|-------|-----|-------|
| D1 | `explore-phase-fs-ts.md` | 2 787 | v1.2, 18 bölüm, 25 tablo, 12 GAP |
| M9 | `app/models/explore.py` | 1 890 | 25 model sınıfı |
| B9 | `app/blueprints/explore_bp.py` | 2 525 | 66 route |
| S-fit | `app/services/fit_propagation.py` | 278 | L4→L3→L2 yayılım |
| S-req | `app/services/requirement_lifecycle.py` | 244 | 10 geçiş, toplu işlem |
| S-oi | `app/services/open_item_lifecycle.py` | 280 | 6 geçiş, bloklama |
| S-sign | `app/services/signoff.py` | 279 | L3 onay, override |
| S-ws | `app/services/workshop_session.py` | 302 | carry-forward, multi-session |
| S-alm | `app/services/cloud_alm.py` | 259 | ALM push (placeholder) |
| S-code | `app/services/code_generator.py` | 92 | Otomatik kod üretimi |
| S-min | `app/services/minutes_generator.py` | 240 | Toplantı tutanağı |
| T1 | `tests/test_explore.py` | 2 091 | 192 test (4 grup) |
| D9 | `EXPLORE_PHASE_TASK_LIST.md` | 1 217 | 175/179 görev (%98) |
| Seed | `scripts/seed_data/explore.py` | 504 | 12/25 tablo |
| UG-TR | `User Guide/explore-phase-user-guide.md` | 1 048 | 13 bölüm, Türkçe |
| UG-EN | `User Guide/explore-phase-user-guide-en.md` | 1 048 | 13 bölüm, İngilizce |

**Toplam incelenen LOC:** ~13 835  
**Not:** Proje dokümanlarında referans verilen `app/services/explore_service.py (S7 — 423 LOC)` dosyası mevcut değildir. Explore servis katmanı 8 ayrı dosyaya (~1 974 LOC) bölünmüştür.

---

## Özet Tablo

| Bölüm | Kapsam | Bulgu Sayısı | SEV-1 | SEV-2 | SEV-3 |
|--------|--------|:------------:|:-----:|:-----:|:-----:|
| **A** | FS/TS → Kod Uyumu | 7 | 1 | 4 | 2 |
| **B** | Kod → Test Kapsamı | 6 | 0 | 4 | 2 |
| **C** | Kullanıcı Kılavuzu → FS/TS | 4 | 0 | 2 | 2 |
| **D** | Görev Listesi Doğruluğu | 3 | 0 | 2 | 1 |
| **E** | Seed Data Kapsamı | 4 | 0 | 2 | 2 |
| **Toplam** | | **24** | **1** | **14** | **9** |

**Severity tanımları:**
- **SEV-1:** Çalışma zamanı hatası / veri kaybı riski — acil düzeltme
- **SEV-2:** İşlevsel eksiklik / uyumsuzluk — sprint içinde düzeltme
- **SEV-3:** İyileştirme / kozmetik — backlog'a ekle

---

## Bölüm A — FS/TS → Kod Uyumu

### A-001 · minutes_generator.py — 8 Attribute Name Mismatch (Runtime Error)

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/services/minutes_generator.py` ↔ `app/models/explore.py` |
| **Tip** | Kod Hatası |
| **Severity** | **SEV-1** |
| **Mevcut Değer** | `minutes_generator.py` ORM nesnelerine aşağıdaki attribute isimlerle erişiyor: |
| **Beklenen Değer** | Model sınıflarındaki gerçek kolon isimleri kullanılmalı |
| **Etki** | `generate()` çağrıldığında **AttributeError** ile çökme |

**Detaylı Mismatch Tablosu:**

| # | minutes_generator.py (satır) | Kullanılan Attribute | Model Sınıfı | Gerçek Kolon/Erişim | Sonuç |
|---|------------------------------|---------------------|---------------|---------------------|-------|
| 1 | L49 `.order_by(WAI.order_index)` | `order_index` | WorkshopAgendaItem | `sort_order` | AttributeError |
| 2 | L54 `.order_by(PS.order_index)` | `order_index` | ProcessStep | `sort_order` | AttributeError |
| 3 | L53 `.filter_by(session_number=…)` | `session_number` | ProcessStep | Kolon yok (ExploreWorkshop'ta var) | AttributeError |
| 4 | L111 `ws.scheduled_date` | `scheduled_date` | ExploreWorkshop | `date` | AttributeError |
| 5 | L122 `a.attended` | `attended` | WorkshopAttendee | `attendance_status` | AttributeError |
| 6 | L145 `s.l4_code` | `l4_code` | ProcessStep | Yok; `s.process_level.code` ile erişilmeli | AttributeError |
| 7 | L154 `d.decision_text` | `decision_text` | ExploreDecision | `text` | AttributeError |
| 8 | L177 `r.requirement_type` | `requirement_type` | ExploreRequirement | `type` | AttributeError |

**Önerilen Aksiyon:**
1. Her bir attribute referansını model kolon ismine göre düzeltin.
2. `ProcessStep.session_number` filtresi → `ProcessStep.workshop` ilişkisi üzerinden `ExploreWorkshop.session_number` ile filtreleyin veya join yapın.
3. `s.l4_code` → Eager-load `process_level` ilişkisini ve `s.process_level.code` kullanın.
4. Bu servise en az 5 unit test yazın (B-004'e bağlı).

---

### A-002 · Backend→Frontend Alan İsmi Uyumsuzluğu: `date` vs `scheduled_date`

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/models/explore.py` L336 ↔ `static/js/views/explore_workshops.js` L159,181,288,364 |
| **Tip** | API Kontrat Uyumsuzluğu |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | `ExploreWorkshop.to_dict()` → `"date": self.date.isoformat()` |
| **Beklenen Değer** | Frontend `w.scheduled_date` okur; blueprint'te mapping yok |
| **Etki** | Workshop tarih sütunu her zaman "—" gösterir; frontend tarih filtreleri çalışmaz |

**Önerilen Aksiyon:**
- `to_dict()` çıktısına `"scheduled_date": self.date.isoformat() if self.date else None` ekleyin (geriye uyumluluk için `date` de kalabilir). VEYA
- Frontend referanslarını `w.date` olarak güncelleyin.
- FS/TS API spesifikasyonunda alan adını netleştirin.

---

### A-003 · Backend→Frontend Alan İsmi Uyumsuzluğu: `type` vs `requirement_type`

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/models/explore.py` L936 ↔ `static/js/views/explore_requirements.js` L131,359,429 ↔ `explore_workshop_detail.js` L288,504 |
| **Tip** | API Kontrat Uyumsuzluğu |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | `ExploreRequirement.to_dict()` → `"type": self.type` |
| **Beklenen Değer** | Frontend `r.requirement_type` okur; blueprint'te mapping yok |
| **Etki** | Requirement tip pill'leri her zaman "—" gösterir; tip bazlı filtreleme çalışmaz |

**Önerilen Aksiyon:**
- `to_dict()` çıktısına `"requirement_type": self.type` ekleyin (uyumluluk aliası). VEYA
- Frontend referanslarını `r.type` olarak güncelleyin.
- Aynı sorun `decision_text` (model: `text`) ve `l4_code` için Frontend'de de olabilir — frontend dosyaları taranmalı.

---

### A-004 · cloud_alm.py — HTTP Push Placeholder (Gerçek Entegrasyon Yok)

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/services/cloud_alm.py` L~120-150 |
| **Tip** | Eksik İmplementasyon |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | `push_requirement_to_alm()` — HTTP çağrısı yapılmaz, simüle edilmiş başarı döner |
| **Beklenen Değer** | FS/TS GAP entegrasyon bölümü: gerçek Cloud ALM REST API çağrısı, retry mekanizması |
| **Etki** | `alm_synced=True` set edilir ama ALM tarafında backlog item oluşmaz; senkronizasyon simülasyondur |

**Önerilen Aksiyon:**
1. Gerçek API client'ını `_do_push()` fonksiyonuna implemente edin (SAP Cloud ALM REST endpoint).
2. Retry dekoratörü ekleyin (FS/TS'te belirtilen retry requirement).
3. `dry_run` parametresi zaten mevcut — korunmalı.
4. Bu endpoint'e integration test yazın (mock HTTP ile).

---

### A-005 · Attachment Category Enum Uyumsuzluğu (3 Yönlü)

| Alan | Değer |
|------|-------|
| **Kaynak** | D1 (FS/TS GAP-07) ↔ M9 L1572 ↔ UG §6.4 Tab I |
| **Tip** | Enum Uyumsuzluğu |
| **Severity** | **SEV-2** |

| Kaynak | Tanımlanan Kategoriler |
|--------|----------------------|
| **FS/TS / User Guide** | Screenshot, BPMN Export, AS-IS Document, TO-BE Document, Spec, Test Evidence, Other |
| **Model (comment)** | screenshot, bpmn_diagram, test_evidence, meeting_notes, config_doc, design_doc, general |

**Fark Detayı:**

| FS/TS / User Guide | Model Karşılığı | Durum |
|--------------------|-----------------|-------|
| Screenshot | screenshot | ✅ Eşleşiyor |
| BPMN Export | bpmn_diagram | ⚠️ İsim farklı |
| AS-IS Document | — | ❌ Model'de yok |
| TO-BE Document | — | ❌ Model'de yok |
| Spec | — | ❌ Model'de yok |
| Test Evidence | test_evidence | ✅ Eşleşiyor |
| Other | general | ⚠️ İsim farklı |
| — | meeting_notes | ➕ Model'de ekstra |
| — | config_doc | ➕ Model'de ekstra |
| — | design_doc | ➕ Model'de ekstra |

**Önerilen Aksiyon:**
- FS/TS'i ve modeli ortak kategori seti üzerinde hizalayın.
- `as_is_document`, `to_be_document`, `spec` kategorilerini model'e ekleyin ya da FS/TS'ten çıkarın.
- Frontend file-upload formundaki dropdown seçeneklerini kontrol edin.

---

### A-006 · FS/TS İç Tutarsızlık: Tablo Sayısı (24 vs 25)

| Alan | Değer |
|------|-------|
| **Kaynak** | `explore-phase-fs-ts.md` Section 16 ↔ Section 18 |
| **Tip** | Doküman İç Tutarsızlığı |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | Section 16 "Data Model Summary": "24 tablo (13 orijinal + 11 gap)" |
| **Beklenen Değer** | Section 18 "Phase Summary": "25 tablo" — doğru sayı |
| **Kök Neden** | `phase_gate` tablosu GAP-12 ile eklenmiş ancak Section 16 özeti güncellenmemiş |

**Gerçek Sayım:** 13 orijinal + 11 gap + 1 phase_gate = **25 tablo** (Section 18 doğru).

**Önerilen Aksiyon:** Section 16'yı "25 tablo (13 orijinal + 12 gap)" olarak güncelleyin.

---

### A-007 · Veritabanı Seviyesinde Enum Kısıtlaması Yok

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/models/explore.py` — tüm enum-like kolonlar |
| **Tip** | Veri Bütünlüğü |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | Tüm enum alanları `db.String(N)` + `comment="val1 \| val2 \| val3"` olarak tanımlı |
| **Beklenen Değer** | `db.Enum()` veya `CheckConstraint` ile izin verilen değerler kısıtlanmalı |
| **Etki** | Geçersiz değer yazılabilir (örn: `status="foo"`); SQLite geliştirme ortamı için kabul edilebilir, PostgreSQL prodüksiyon için riskli |

**Etkilenen Kolonlar (seçili):** `status`, `type`, `priority`, `category`, `fit_decision`, `attendance_status`, `organization`, `alm_sync_status`, `fit_status`, `complexity` (~20+ kolon)

**Önerilen Aksiyon:**
- En azından kritik kolonlara (`status`, `fit_decision`, `priority`) `CheckConstraint` ekleyin.
- Veya uygulama katmanında bir `validate_enum()` decorator/hook kullanın.

---

## Bölüm B — Kod → Test Kapsamı

### B-001 · Phase 1 Gap Endpoint'leri İçin Yetersiz Test Kapsamı

| Alan | Değer |
|------|-------|
| **Kaynak** | `tests/test_explore.py` ↔ `app/blueprints/explore_bp.py` (Phase 1 routes) |
| **Tip** | Eksik Test |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | TEST-002 API testleri ağırlıklı olarak Phase 0 endpoint'lerini kapsar |
| **Beklenen Değer** | GAP-03, GAP-04, GAP-07, GAP-09, GAP-18 endpoint'leri test edilmeli |

**Test Edilmeyen/Yetersiz Phase 1 Endpoint'leri:**

| GAP | Endpoint Grubu | Route Sayısı | Test Durumu |
|-----|---------------|:------------:|-------------|
| GAP-04 | Workshop Reopen / Create Delta | 2 | ❌ Test yok |
| GAP-03 | Workshop Dependencies CRUD | 3 | ❌ Test yok |
| GAP-18 | Cross-Module Flags CRUD | 2 | ❌ Test yok |
| GAP-09 | Scope Change Requests (create/list/get/transition/implement) | 5 | ❌ Test yok |
| GAP-07 | Attachments CRUD | 4 | ❌ Test yok |
| — | Change History | 1 | ❌ Test yok |
| **Toplam** | | **~17 route** | **0 test** |

**Önerilen Aksiyon:** TEST-002'ye en az 20 test ekleyin (endpoint başına CRUD + validation + edge case).

---

### B-002 · Phase 2 Endpoint'leri Test Edilmemiş

| Alan | Değer |
|------|-------|
| **Kaynak** | `tests/test_explore.py` ↔ `app/blueprints/explore_bp.py` (Phase 2 routes) |
| **Tip** | Eksik Test |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | Phase 2 endpoint'leri (BPMN, Workshop Documents, Snapshots, Steering Committee) için test yok |
| **Beklenen Değer** | En azından happy-path testleri olmalı |

**Test Edilmeyen Phase 2 Endpoint'leri:**

| Endpoint | Route |
|----------|-------|
| BPMN Get | `GET /process-steps/<id>/bpmn` |
| BPMN Create | `POST /process-steps/<id>/bpmn` |
| Generate Minutes | `POST /workshops/<id>/generate-minutes` |
| AI Summary | `POST /workshops/<id>/ai-summary` |
| Documents List | `GET /workshops/<id>/documents` |
| Capture Snapshot | `POST /snapshots` |
| Snapshots List | `GET /snapshots` |
| Steering Committee | `POST /steering-committee` |
| **Toplam** | **~8 route** |

**Önerilen Aksiyon:** En az 10 test ekleyin (Phase 2 stabilize olduğunda).

---

### B-003 · Tek Rol Testi (Yalnızca PM)

| Alan | Değer |
|------|-------|
| **Kaynak** | `tests/test_explore.py` — `_grant_pm_role()` helper |
| **Tip** | Yetersiz Kapsam |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | Tüm API testleri `_grant_pm_role()` ile PM rolü verir; diğer roller test edilmez |
| **Beklenen Değer** | PERMISSION_MATRIX'teki 7 rolün tamamı test edilmeli |

**Test Edilmeyen Roller ve Kritik Yetki Senaryoları:**

| Rol | Kritik Senaryo | Test? |
|-----|---------------|-------|
| Module Lead | Kendi alanı dışında approve → 403 | ❌ |
| Consultant | REQ transition yetkisi yok → 403 | ❌ |
| BPO | Sadece approve/reject yetkisi | ❌ |
| Tech Lead | ALM push yetkisi | ❌ |
| Viewer | Yazma işlemi → 403 | ❌ |
| Stakeholder | Sadece dashboard erişimi | ❌ |

**Önerilen Aksiyon:**
1. `_grant_role(role_name)` generic helper oluşturun.
2. Her kritik yetki senaryosu için 1 pozitif + 1 negatif test yazın (~14 test).

---

### B-004 · Servis Katmanı Unit Test Eksikliği

| Alan | Değer |
|------|-------|
| **Kaynak** | `app/services/` (8 dosya) ↔ `tests/test_explore.py` |
| **Tip** | Eksik Test |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | Servis fonksiyonları yalnızca dolaylı olarak API testleri üzerinden test edilir |
| **Beklenen Değer** | Her servis modülü için izole unit test `test_explore_services.py` |

| Servis Dosyası | LOC | Dolaylı Test | Doğrudan Unit Test |
|----------------|:---:|:----------:|:-----------------:|
| fit_propagation.py | 278 | ✅ (TEST-003) | ❌ |
| requirement_lifecycle.py | 244 | ✅ (TEST-003) | ❌ |
| open_item_lifecycle.py | 280 | ✅ (TEST-003) | ❌ |
| signoff.py | 279 | ⚠️ Kısmi | ❌ |
| workshop_session.py | 302 | ❌ | ❌ |
| cloud_alm.py | 259 | ❌ | ❌ |
| code_generator.py | 92 | ✅ (TEST-003) | ❌ |
| minutes_generator.py | 240 | ❌ | ❌ |

**Önerilen Aksiyon:**
- `tests/test_explore_services.py` dosyası oluşturun.
- minutes_generator ve cloud_alm için zorunlu (A-001 bug'larının regression testi).
- workshop_session.carry_forward_steps için izole test (multi-session doğrulama).
- Hedef: ~30 unit test.

---

### B-005 · Sınırlı Response Body Doğrulaması

| Alan | Değer |
|------|-------|
| **Kaynak** | `tests/test_explore.py` — TEST-002 API testleri |
| **Tip** | Test Kalitesi |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | Testler ağırlıklı olarak HTTP status code kontrol eder (`assertEqual(resp.status_code, 200)`) |
| **Beklenen Değer** | Kritik endpoint'ler için response body yapısı ve değer doğrulaması |
| **Etki** | A-002 ve A-003 gibi serialization bug'ları testlerden kaçar |

**Örnek Eksik Assertion'lar:**
```python
# Mevcut:
self.assertEqual(resp.status_code, 200)

# Beklenen:
data = resp.get_json()
self.assertIn("date", data)  # veya "scheduled_date"
self.assertEqual(data["status"], "draft")
self.assertIsInstance(data["scope_items"], list)
```

**Önerilen Aksiyon:** En az list, get-detail ve transition endpoint'leri için response body assertion'ları ekleyin.

---

### B-006 · Multi-Session Workshop Test Eksikliği

| Alan | Değer |
|------|-------|
| **Kaynak** | `tests/test_explore.py` ↔ `app/services/workshop_session.py` |
| **Tip** | Eksik Test |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | Multi-session senaryoları (GAP-10) için entegrasyon testi yok |
| **Beklenen Değer** | carry_forward_steps, validate_session_start, ara session kapanış kuralları test edilmeli |

**Test Edilmesi Gereken Senaryolar:**
1. Session A kapanış → fit kararları yansımaz (ara session)
2. Session B başlatma → önceki step'ler taşınır
3. Session B kapanış → tüm step'lerde fit zorunlu
4. Duplicate carry-forward koruması
5. Önceki session tamamlanmadan sonraki başlatılamaz

**Önerilen Aksiyon:** TEST-004 Integration bölümüne `TestMultiSessionWorkflow` sınıfı ekleyin (~5 test).

---

## Bölüm C — Kullanıcı Kılavuzu → FS/TS Uyumu

### C-001 · Fit Propagation Derinliği: L4→L3→L2→L1 vs L4→L3→L2

| Alan | Değer |
|------|-------|
| **Kaynak** | UG-TR §6.3, §6.6 ↔ D1 Section 14 ↔ `fit_propagation.py` |
| **Tip** | Doküman Tutarsızlığı |
| **Severity** | **SEV-2** |
| **User Guide** | "Kararlar L4→L3→L2→**L1** yansıtılır" (§6.3, §6.6 — her iki dilde) |
| **FS/TS** | Section 14 Updated References: "fit propagation L4→L3→L2" (L1 bahsedilmez) |
| **Kod** | `propagate_fit_from_step()` → L4→L3→L2 cascade; `recalculate_project_hierarchy()` can traverse to L1 but only recalculates L2 readiness |

**Önerilen Aksiyon:**
- Eğer L1'e (Value Chain) yansıtma yapılmıyorsa: User Guide'dan "→L1" ifadesini çıkarın.
- Eğer L1'e readiness bilgisi yansıtılıyorsa: FS/TS'e ekleyin.

---

### C-002 · Scope Change Lifecycle — User Guide'da "Implemented" Statüsü Eksik

| Alan | Değer |
|------|-------|
| **Kaynak** | UG-TR §9.4 ↔ D1 GAP-09 ↔ M9 ScopeChangeRequest model |
| **Tip** | Doküman Eksikliği |
| **Severity** | **SEV-2** |
| **User Guide** | §9.4 dört statü gösterir: Requested → Under Review → Approved/Rejected, ardından "implement edilir" (eylem olarak) |
| **FS/TS + Kod** | SCOPE_CHANGE_TRANSITIONS dict'inde 5 geçiş: `requested→under_review`, `under_review→approved`, `under_review→rejected`, `approved→implemented`, `implemented→closed` |
| **Fark** | User Guide "Implemented" ve "Closed" statülerini ayrı durum olarak göstermiyor |

**Önerilen Aksiyon:**
- User Guide §9.4'e tam lifecycle diyagramı ekleyin:
  ```
  Requested → Under Review → Approved → Implemented → Closed
                           → Rejected
  ```

---

### C-003 · Attachment Kategorileri Uyumsuzluğu

| Alan | Değer |
|------|-------|
| **Kaynak** | UG-TR §6.4 Tab I ↔ M9 L1572 |
| **Tip** | Doküman-Kod Uyumsuzluğu |
| **Severity** | **SEV-3** |
| **User Guide** | Screenshot / BPMN Export / AS-IS Document / TO-BE Document / Spec / Other |
| **Model** | screenshot / bpmn_diagram / test_evidence / meeting_notes / config_doc / design_doc / general |
| **Detay** | A-005 ile aynı kök neden — 3 yönlü uyumsuzluk |

**Önerilen Aksiyon:** A-005 çözüldüğünde User Guide'ı da güncelleyin.

---

### C-004 · TR / EN İçerik Tutarlılığı ✅ SORUN YOK

| Alan | Değer |
|------|-------|
| **Kaynak** | `explore-phase-user-guide.md` ↔ `explore-phase-user-guide-en.md` |
| **Tip** | Pozitif Bulgu |
| **Severity** | — |
| **Sonuç** | Her iki versiyon 1 048 satır, aynı yapı (13 bölüm + sözlük), profesyonel çeviri |
| **Kontrol Edilen** | Bölüm numaralandırma, tablo yapısı, terminoloji tutarlılığı, rol isimleri, enum değerleri |
| **Not** | Herhangi bir eksik/fazla bölüm, çeviri hatası veya yapısal farklılık tespit edilmemiştir |

---

## Bölüm D — Görev Listesi (D9) Doğruluğu

### D-001 · Başlık Metriklerinde Stale Değerler

| Alan | Değer |
|------|-------|
| **Kaynak** | `EXPLORE_PHASE_TASK_LIST.md` başlık bölümü |
| **Tip** | Doküman Güncelliği |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | D9: "65 tablo, 296 route" |
| **Beklenen Değer** | `project-inventory.md` v1.1: 71 tablo, 321 route |
| **Kök Neden** | D9 başlığı oluşturulduğu tarihteki değerleri yansıtıyor; sonraki sprint'lerde güncellenmemiş |

**Önerilen Aksiyon:** D9 başlığını güncel metriklerle güncelleyin. Bir "snapshot tarihi" notu ekleyin.

---

### D-002 · 4 Tamamlanmamış Görev (175/179 = %98)

| Alan | Değer |
|------|-------|
| **Kaynak** | `EXPLORE_PHASE_TASK_LIST.md` |
| **Tip** | İlerleme Takibi |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | 4 görev ⬜ NOT STARTED |

| Görev ID | Açıklama | Kategori | Tahmini Efor |
|----------|----------|----------|:--------:|
| T-029 | SQLite→PostgreSQL veri göç scripti | DevOps | 4h |
| TEST-005 | Frontend bileşen testleri (Vitest) | Test | 16h |
| TEST-006 | E2E testler (Playwright) | Test | 12h |
| DEV-003 | API dokümantasyonu (Swagger/OpenAPI) | DevOps | 8h |

**Toplam Kalan Efor:** ~40h

**Önerilen Aksiyon:**
- TEST-005 ve TEST-006 için öncelik belirleyin (frontend stability dependency).
- DEV-003 (Swagger) → `flask-smorest` veya `flasgger` entegrasyonu ile otomatik oluşturma düşünün.
- T-029 → PostgreSQL'e geçiş planlandığında önceliklendirin.

---

### D-003 · Phase 2 Görevleri "Complete" İşaretli Ama Stub Olabilir

| Alan | Değer |
|------|-------|
| **Kaynak** | D9 Phase 2 görevleri ↔ B9 endpoint implementasyonları |
| **Tip** | Durum Doğruluğu |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | A-016 (BPMN), A-017, A-029 (Minutes), A-030, A-057 (Snapshot), A-058 (Steering) → ✅ Complete |
| **Beklenen Değer** | Bu endpoint'ler çalışır durumda ancak bazıları placeholder mantık içerir |

**Detay:**
- `generate-minutes` endpoint'i → minutes_generator.py'deki A-001 bug'ları nedeniyle çalışmaz
- `ai-summary` endpoint'i → Gerçek AI değil, placeholder JSON döner
- `steering-committee` → Template bazlı, gerçek veri agregasyonu sınırlı
- BPMN endpoint'leri → Dosya upload/retrieve çalışır, BPMN parse etme yok

**Önerilen Aksiyon:** D9'da Phase 2 görevlerinin durumunu "✅ Complete (Stub)" olarak netleştirin.

---

## Bölüm E — Seed Data Kapsamı

### E-001 · 25 Tablodan Yalnızca 12'si Seed Ediliyor (%48)

| Alan | Değer |
|------|-------|
| **Kaynak** | `scripts/seed_data/explore.py` ↔ `app/models/explore.py` (25 model) |
| **Tip** | Demo Veri Eksikliği |
| **Severity** | **SEV-2** |

**Seed Edilen 12 Tablo:**

| # | Tablo | Kayıt Sayısı | Durum |
|---|-------|:------------:|-------|
| 1 | process_levels | 265 (5 L1 + 10 L2 + 50 L3 + 200 L4) | ✅ |
| 2 | explore_workshops | 20 | ✅ |
| 3 | workshop_scope_items | ~40 | ✅ |
| 4 | workshop_attendees | 60 | ✅ |
| 5 | workshop_agenda_items | 80 | ✅ |
| 6 | process_steps | 100 | ✅ |
| 7 | explore_decisions | 50 | ✅ |
| 8 | explore_open_items | 30 | ✅ |
| 9 | explore_requirements | 40 | ✅ |
| 10 | requirement_oi_links | 15 | ✅ |
| 11 | requirement_dependencies | 10 | ✅ |
| 12 | oi_comments | 20 | ✅ |

**Seed Edilmeyen 13 Tablo:**

| # | Tablo | GAP | Phase | Etki |
|---|-------|-----|:-----:|------|
| 1 | cloud_alm_sync_log | — | 0 | ALM senkronizasyon geçmişi boş |
| 2 | l4_seed_catalog | GAP-01 | 0 | L4 seeding wizard demo edilemez |
| 3 | **project_roles** | **GAP-05** | **0 CRITICAL** | **Yetki sistemi demo edilemez** |
| 4 | **phase_gates** | **GAP-12** | **0 CRITICAL** | **L2 milestone takibi boş** |
| 5 | workshop_dependencies | GAP-03 | 1 | Bağımlılık ilişkileri görünmez |
| 6 | cross_module_flags | GAP-18 | 1 | Modüller arası bayraklar boş |
| 7 | workshop_revision_logs | GAP-04 | 1 | Reopen geçmişi yok |
| 8 | attachments | GAP-07 | 1 | Dosya ekleri boş |
| 9 | scope_change_requests | GAP-09 | 1 | Scope değişiklik süreci demo edilemez |
| 10 | scope_change_logs | GAP-09 | 1 | Scope değişiklik logu boş |
| 11 | bpmn_diagrams | GAP-02 | 2 | BPMN viewer boş |
| 12 | workshop_documents | GAP-06 | 2 | Toplantı tutanakları boş |
| 13 | daily_snapshots | GAP-08 | 2 | Dashboard'da trend grafiği boş |

**Önerilen Aksiyon:** Öncelik sırasına göre seed fonksiyonları ekleyin:
1. **P0:** `project_roles` (7 rol + yetki), `phase_gates`, `l4_seed_catalog` → Demo kritik
2. **P1:** `workshop_dependencies`, `scope_change_requests`, `attachments` → Phase 1 demo
3. **P2:** `daily_snapshots`, `workshop_documents`, `bpmn_diagrams` → Dashboard/Report demo

---

### E-002 · Phase 0 Critical Tabloların Seed Eksikliği

| Alan | Değer |
|------|-------|
| **Kaynak** | `scripts/seed_data/explore.py` ↔ D1 GAP-05, GAP-12, GAP-01 |
| **Tip** | Demo Hazırlık Eksikliği |
| **Severity** | **SEV-2** |
| **Mevcut Değer** | `project_roles`, `phase_gates`, `l4_seed_catalog` tabloları boş |
| **Beklenen Değer** | Phase 0 CRITICAL özellikler demo edilebilir olmalı |
| **Etki** | |

| Tablo | Demo Etkisi |
|-------|-------------|
| `project_roles` | Yetki sistemi çalışmaz — tüm endpoint'lerde `has_permission()` hata verebilir veya varsayılan izin verir |
| `phase_gates` | L2 Area Milestone Tracker widget'ı boş — onay/readiness akışı test edilemez |
| `l4_seed_catalog` | SAP Best Practice'ten L4 yükleme wizard'ı çalışmaz — L4 oluşturma sadece manual |

**Önerilen Aksiyon:**
```python
# Eklenecek seed verisi:
# 1. project_roles: 7 rol (PM, Module Lead×5, Consultant, BPO, Tech Lead, Viewer, Stakeholder)
# 2. phase_gates: Her L2 area için 1 kayıt (10 area × 1 gate = 10 kayıt)
# 3. l4_seed_catalog: SAP Best Practice kataloğundan 50+ L4 template
```

---

### E-003 · Phase 2 Demo Özellikleri Boş

| Alan | Değer |
|------|-------|
| **Kaynak** | `scripts/seed_data/explore.py` |
| **Tip** | Demo Veri Eksikliği |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | `daily_snapshots`, `workshop_documents`, `bpmn_diagrams` tabloları boş |
| **Beklenen Değer** | En az 7 günlük snapshot, 2-3 meeting minutes dokümanı, 5+ BPMN diyagramı |
| **Etki** | Dashboard boş, meeting minutes listesi boş, BPMN viewer boş |

**Önerilen Aksiyon:**
- `daily_snapshots`: 14 gün için günlük metrik kaydı oluşturun (trend grafikleri için).
- `workshop_documents`: Completed workshop'lar için örnek meeting minutes oluşturun.
- `bpmn_diagrams`: Birkaç basit BPMN XML dosyası embedded olarak ekleyin.

---

### E-004 · Cloud ALM Entegrasyonu Demo Edilemez

| Alan | Değer |
|------|-------|
| **Kaynak** | E-001 (seed eksik) + A-004 (HTTP placeholder) |
| **Tip** | Bileşik Sorun |
| **Severity** | **SEV-3** |
| **Mevcut Değer** | `cloud_alm_sync_log` tablosu boş + HTTP çağrısı simülasyon |
| **Beklenen Değer** | Demo için: birkaç requirement'ın "synced" statüde olması ve sync log kayıtları |
| **Etki** | "Push to Cloud ALM" ve "Sync All" akışları görsel olarak doğru çalışır gibi görünür ama hiçbir gerçek senkronizasyon olmaz; sync log'lar boş kalır |

**Önerilen Aksiyon:**
1. Seed'e 5 adet requirement için mock `cloud_alm_sync_log` kayıtları ekleyin (status: synced, sync_error, out_of_sync).
2. Bu requirement'ların `alm_synced=True` ve `alm_id` alanlarını set edin.
3. A-004 çözülene kadar "simülasyon modu" UI'da clear bir banner ile belirtin.

---

## Ek: Kapsam Matrisi

### Model Sınıfları vs Test Kapsamı

| # | Model | Table | Tests (Model) | Tests (API) | Tests (BR) |
|---|-------|-------|:-------------:|:-----------:|:----------:|
| 1 | ProcessLevel | process_levels | ✅ | ✅ | — |
| 2 | ExploreWorkshop | explore_workshops | ✅ | ✅ | ✅ |
| 3 | WorkshopScopeItem | workshop_scope_items | ✅ | ✅ | — |
| 4 | WorkshopAttendee | workshop_attendees | ✅ | ⚠️ | — |
| 5 | WorkshopAgendaItem | workshop_agenda_items | ✅ | ⚠️ | — |
| 6 | ProcessStep | process_steps | ✅ | ✅ | ✅ |
| 7 | ExploreDecision | explore_decisions | ✅ | ✅ | — |
| 8 | ExploreOpenItem | explore_open_items | ✅ | ✅ | ✅ |
| 9 | ExploreRequirement | explore_requirements | ✅ | ✅ | ✅ |
| 10 | RequirementOpenItemLink | requirement_oi_links | ✅ | ✅ | ✅ |
| 11 | RequirementDependency | requirement_dependencies | ✅ | ✅ | — |
| 12 | OpenItemComment | oi_comments | ✅ | ✅ | — |
| 13 | CloudALMSyncLog | cloud_alm_sync_log | ✅ | ✅ | — |
| 14 | L4SeedCatalog | l4_seed_catalog | ✅ | ⚠️ | — |
| 15 | ProjectRole | project_roles | ✅ | ❌ | ❌ |
| 16 | PhaseGate | phase_gates | ✅ | ❌ | ❌ |
| 17 | WorkshopDependency | workshop_dependencies | ✅ | ❌ | — |
| 18 | CrossModuleFlag | cross_module_flags | ✅ | ❌ | — |
| 19 | WorkshopRevisionLog | workshop_revision_logs | ✅ | ❌ | — |
| 20 | Attachment | attachments | ✅ | ❌ | — |
| 21 | ScopeChangeRequest | scope_change_requests | ✅ | ❌ | — |
| 22 | ScopeChangeLog | scope_change_logs | ✅ | ❌ | — |
| 23 | BPMNDiagram | bpmn_diagrams | ✅ | ❌ | — |
| 24 | ExploreWorkshopDocument | workshop_documents | ✅ | ❌ | — |
| 25 | DailySnapshot | daily_snapshots | ✅ | ❌ | — |

**Kapsam Özeti:**
- Model CRUD testleri: 25/25 (**%100**)
- API endpoint testleri: 13/25 (**%52**)
- Business rule testleri: 6/25 (**%24**) — yalnızca ilgili modellerde

### Servis Fonksiyonları vs Test Kapsamı

| Servis | Fonksiyon | Dolaylı Test | Doğrudan Test |
|--------|----------|:------------:|:------------:|
| fit_propagation | propagate_fit_from_step | ✅ API | ❌ |
| fit_propagation | calculate_system_suggested_fit | ✅ BR | ❌ |
| fit_propagation | recalculate_l3_consolidated | ⚠️ | ❌ |
| fit_propagation | recalculate_l2_readiness | ⚠️ | ❌ |
| requirement_lifecycle | transition_requirement | ✅ BR | ❌ |
| requirement_lifecycle | batch_transition | ✅ API | ❌ |
| open_item_lifecycle | transition_open_item | ✅ BR | ❌ |
| open_item_lifecycle | reassign_open_item | ✅ API | ❌ |
| signoff | check_signoff_readiness | ⚠️ | ❌ |
| signoff | signoff_l3 | ⚠️ | ❌ |
| signoff | override_l3_fit | ❌ | ❌ |
| signoff | get_consolidated_view | ❌ | ❌ |
| workshop_session | carry_forward_steps | ❌ | ❌ |
| workshop_session | validate_session_start | ❌ | ❌ |
| workshop_session | get_session_summary | ❌ | ❌ |
| cloud_alm | push_requirement_to_alm | ❌ | ❌ |
| cloud_alm | bulk_sync_to_alm | ❌ | ❌ |
| code_generator | generate_workshop_code | ✅ BR | ❌ |
| code_generator | generate_requirement_code | ✅ BR | ❌ |
| minutes_generator | generate | ❌ | ❌ |
| minutes_generator | generate_ai_summary | ❌ | ❌ |

---

## Sonuç ve Öncelikli Aksiyon Planı

### Acil (Sprint İçinde)

| # | Bulgu | Aksiyon | Tahmini Efor |
|---|-------|---------|:--------:|
| 1 | A-001 | minutes_generator.py 8 attribute düzeltmesi | 2h |
| 2 | A-002 | `date` → `scheduled_date` mapping (to_dict veya frontend) | 1h |
| 3 | A-003 | `type` → `requirement_type` mapping (to_dict veya frontend) | 1h |
| 4 | B-004 | minutes_generator + cloud_alm unit testleri | 4h |

### Yakın Dönem (Sonraki Sprint)

| # | Bulgu | Aksiyon | Tahmini Efor |
|---|-------|---------|:--------:|
| 5 | A-005 | Attachment category enum hizalaması | 2h |
| 6 | B-001 | Phase 1 endpoint testleri (~20 test) | 8h |
| 7 | B-003 | Multi-role permission testleri (~14 test) | 6h |
| 8 | E-001/E-002 | project_roles, phase_gates, l4_seed_catalog seed | 4h |
| 9 | D-001 | D9 stale metrikleri güncelleme | 0.5h |
| 10 | C-001/C-002 | User Guide düzeltmeleri | 2h |

### Backlog

| # | Bulgu | Aksiyon | Tahmini Efor |
|---|-------|---------|:--------:|
| 11 | A-004 | Cloud ALM gerçek HTTP entegrasyonu | 12h |
| 12 | A-007 | DB-level enum constraints | 4h |
| 13 | B-002 | Phase 2 endpoint testleri | 6h |
| 14 | B-006 | Multi-session integration testleri | 4h |
| 15 | E-003/E-004 | Phase 2 + ALM seed data | 4h |
| 16 | D-002 | 4 kalan görev tamamlama | 40h |

**Toplam Tahmini Düzeltme Eforu:** ~100h (acil: 8h, yakın dönem: 22.5h, backlog: 70h)

---

*Bu rapor `explore-phase-fs-ts.md`, `app/models/explore.py`, `app/blueprints/explore_bp.py`, 8 servis dosyası, `tests/test_explore.py`, `EXPLORE_PHASE_TASK_LIST.md`, `scripts/seed_data/explore.py` ve User Guide (TR+EN) dosyalarının satır satır incelenmesiyle oluşturulmuştur.*

*Toplam incelenen: ~13 835 LOC, 16 dosya.*
