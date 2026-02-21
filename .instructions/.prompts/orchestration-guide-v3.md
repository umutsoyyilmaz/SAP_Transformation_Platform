# 🎯 Agent Orkestrasyon Rehberi v3 — SAP Transformation Platform

> **6-Agent Pipeline:** Architect → UX → UI → QA → Coder → Reviewer
> **+ 4 Audit Pipeline:** Review, Quick Fix, Complete BP, Full Module
>
> Her agent ayrı bir VS Code Copilot Chat session'ında çalışır.
> Her adımda SEN checkpoint'sin — onay vermeden sonraki agent'a geçilmez.

---

## Repo Yapısı

```
project-root/
├── .github/
│   └── copilot-instructions.md        ← Senior Engineer coding standards
├── .instructions/.prompts/
│   ├── architect.md                    ← Agent 1: Fonksiyonel tasarım
│   ├── ux-agent.md                     ← Agent 2: Kullanıcı deneyimi
│   ├── ui-agent.md                     ← Agent 3: Görsel tasarım + V0.dev
│   ├── qa-agent.md                     ← Agent 4: Test planı (shift-left)
│   ├── coder.md                        ← Agent 5: Implementation
│   └── reviewer.md                     ← Agent 6: Code review
├── docs/
│   ├── fdd/                            ← Functional Design Documents
│   ├── uxd/                            ← UX Design Documents
│   ├── uid/                            ← UI Design Documents
│   ├── tpd/                            ← Test Plan Documents
│   ├── reviews/
│   │   ├── project/                    ← Stratejik audit raporları
│   │   └── code/                       ← Feature bazlı review raporları
│   ├── business/                       ← Investor pitch, demo script
│   ├── plans/                          ← Sprint/release planları
│   ├── specs/                          ← Teknik spesifikasyonlar
│   └── archive/                        ← Eski dokümanlar
└── CHANGELOG.md
```

---

# BÖLÜM A: YENİ FEATURE GELİŞTİRME PIPELINE'I

## Pipeline Genel Akış

```
Sen (feature talebi)
 │
 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: TASARIM                                                     │
│                                                                      │
│  ┌───────────┐     ┌───────────┐     ┌───────────┐                  │
│  │ ARCHITECT │────▶│  UX Agent │────▶│  UI Agent │                  │
│  │ FDD üretir│     │ UXD üretir│     │UID üretir │                  │
│  └─────┬─────┘     └─────┬─────┘     └─────┬─────┘                  │
│        │                 │                  │                         │
│    [Sen onaylar]    [Sen onaylar]     [Sen onaylar]                  │
│                                       V0.dev görseli                 │
└────────────────────────────────────────────────────────────────────────┘
 │
 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: TEST PLANLAMA (Shift-Left)                                  │
│                                                                      │
│  ┌───────────┐                                                       │
│  │ QA Agent  │ ← FDD + UXD + UID alır                               │
│  │ TPD üretir│ → Test senaryoları, traceability matrix               │
│  └─────┬─────┘                                                       │
│        │                                                             │
│    [Sen onaylar — neyin test edileceğini bilir]                      │
└────────────────────────────────────────────────────────────────────────┘
 │
 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: IMPLEMENTATION                                              │
│                                                                      │
│  ┌───────────┐                                                       │
│  │  CODER    │ ← FDD + UID + TPD alır                               │
│  │ Kod yazar │ → Model + Service + Blueprint + Tests                 │
│  └─────┬─────┘                                                       │
│        │                                                             │
│    [Sen test eder — QA Agent'ın listesini kullanarak]                │
└────────────────────────────────────────────────────────────────────────┘
 │
 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: REVIEW                                                      │
│                                                                      │
│  ┌───────────┐                                                       │
│  │ REVIEWER  │ ← Kod + FDD + TPD alır                               │
│  │ Review    │ → Yapısal rapor (🔴🟡🔵)                              │
│  └─────┬─────┘                                                       │
│        │                                                             │
│    [Sen merge eder veya düzeltme döngüsüne girer]                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ADIM 1: Architect Agent Session

### Başlat
Yeni Copilot Chat → aşağıdaki mesajı yapıştır:

```
@workspace Şu anda Architect Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/architect.md (rol tanımın)
- .github/copilot-instructions.md (mimari kurallar)
- app/models/ dizini (mevcut modeller)
- app/blueprints/ dizini (mevcut endpoint'ler)

## Feature Talebi
[TALEBİNİ YAZ]

FDD formatında tasarımı hazırla.
```

### Çıktı
`docs/fdd/FDD-XXX-feature-name.md`

### Onay Kriterlerin
```
☐ Business need net mi?
☐ Data model hierarchy'ye uyuyor mu?
☐ API contract'lar tutarlı mı?
☐ Business rules eksiksiz mi?
☐ State machine tanımlı mı?
☐ Edge case'ler düşünülmüş mü?
```

**Onay → FDD'yi kaydet → Adım 2'ye geç**
**Red → Architect'e geri bildirim ver, revize ettir**

---

## ADIM 2: UX Agent Session

### Başlat
Yeni Copilot Chat:

```
@workspace Şu anda UX Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/ux-agent.md (rol tanımın)
- docs/fdd/FDD-XXX-feature-name.md (onaylanmış fonksiyonel tasarım)
- .github/copilot-instructions.md §13 (SAP domain context)

FDD'nin §6 (UI Behavior) ve §7 (Acceptance Criteria) bölümlerini temel al.

Bu feature için UXD (UX Design Document) hazırla:
- User journey'ler (hangi persona, hangi akış)
- Screen inventory (hangi ekranlar gerekli)
- ASCII wireframe'ler (her ekran için)
- Form spesifikasyonları
- Empty/loading/error state tanımları
- Ekran geçiş diyagramı
```

### Çıktı
`docs/uxd/UXD-XXX-feature-name.md`

### Onay Kriterlerin
```
☐ User journey mantıklı mı? (Gereksiz adım var mı?)
☐ Wireframe'ler mevcut ekranlarla tutarlı mı?
☐ Form alanları FDD'deki data model ile uyuşuyor mu?
☐ Empty/error state'ler tanımlı mı?
☐ Ekran geçişleri net mi? (Kullanıcı kaybolmaz mı?)
☐ Deep link / URL yapısı doğru mu?
```

**Onay → UXD'yi kaydet → Adım 3'e geç**

---

## ADIM 3: UI Agent Session

### Başlat
Yeni Copilot Chat:

```
@workspace Şu anda UI Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/ui-agent.md (rol tanımın, design system, component catalog)
- docs/uxd/UXD-XXX-feature-name.md (onaylanmış UX tasarımı)
- docs/fdd/FDD-XXX-feature-name.md (referans: API contract'lar)

UXD'deki wireframe'leri görsel tasarıma dönüştür:
1. Her ekran için V0.dev prompt'u üret
2. Component specification'ları hazırla (props, states, variants)
3. Status badge renk mapping'ini belirle
4. Micro-interaction detaylarını tanımla
```

### Ara Adım: V0.dev Prototyping
1. UI Agent'ın ürettiği V0.dev prompt'unu kopyala
2. [v0.dev](https://v0.dev) adresine git, prompt'u yapıştır
3. Çıkan görseli incele
4. Beğenmediysen → UI Agent'a "şu kısmı değiştir" de, prompt'u revize ettir
5. **Beğendiysen → bu görsel artık "visual contract"** — Coder buna göre yazacak

### Çıktı
`docs/uid/UID-XXX-feature-name.md` (V0 prompt'ları + component spec'ler)

### Onay Kriterlerin
```
☐ V0.dev çıktısı UXD wireframe'leri ile uyuşuyor mu?
☐ Renkler/tipografi design system ile tutarlı mı?
☐ Component spec'ler Coder'ın ihtiyacını karşılıyor mu?
☐ Status badge renkleri doğru mu?
☐ Tüm state'ler (empty, loading, error) tanımlı mı?
```

**Onay → UID'yi kaydet → Adım 4'e geç**

---

## ADIM 4: QA Agent Session (Shift-Left)

### Başlat
Yeni Copilot Chat:

```
@workspace Şu anda QA Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/qa-agent.md (rol tanımın)
- docs/fdd/FDD-XXX-feature-name.md (business rules, API contract)
- docs/uxd/UXD-XXX-feature-name.md (user flows, edge cases)
- docs/uid/UID-XXX-feature-name.md (component specs, interactions)

Bu feature için kapsamlı bir TPD (Test Plan Document) hazırla:
- API test senaryoları (CRUD + validation + auth)
- Tenant isolation testleri (P0 — zorunlu)
- State machine test matrisi
- Boundary value testleri
- UI manual test senaryoları
- Traceability matrix (her business rule → en az 1 test)
```

### Çıktı
`docs/tpd/TPD-XXX-feature-name.md`

### Onay Kriterlerin
```
☐ Her business rule (FDD §4) en az bir test ile kapsanmış mı?
☐ Tenant isolation testleri (Section 3) eksiksiz mi?
☐ State machine geçişleri (valid + invalid) test edilmiş mi?
☐ Boundary value'lar (min/max/null/empty) tanımlı mı?
☐ UI manual test listesi elle yapılabilir detayda mı?
☐ Priority (P0/P1/P2) risk bazlı ve mantıklı mı?
☐ Coder Agent'a handoff bölümü net mi?
```

**Onay → TPD'yi kaydet → Adım 5'e geç**

---

## ADIM 5: Coder Agent Session

### Başlat
Yeni Copilot Chat:

```
@workspace Şu anda Coder Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/coder.md (rol tanımın ve code template'lerin)
- .github/copilot-instructions.md (coding standards — SENİN ANAYASAN)
- docs/fdd/FDD-XXX-feature-name.md (ne yapılacak)
- docs/uid/UID-XXX-feature-name.md (nasıl görünecek, component specs)
- docs/tpd/TPD-XXX-feature-name.md (hangi testlerin geçmesi gerekiyor)

FDD'deki Implementation Order'ı takip et.
Phase 1 (Model) ile başla.
Her phase tamamlandığında bana bildir, onay olmadan sonraki phase'e geçme.

EK KURAL: TPD'deki P0 ve P1 test senaryolarını pytest olarak implement et.
Test dosya yapısını TPD §10'daki Coder Agent Instructions'a göre oluştur.
```

### Phase İlerlemesi

**Phase 1: Model** → `flask db migrate` + `flask db upgrade` → kontrol et
**Phase 2: Service** → import kontrolü → devam et
**Phase 3: Blueprint** → `flask run` + `curl` test → devam et
**Phase 4: Tests** → `pytest tests/test_<domain>*.py -v` → tümü yeşil olmalı
**Phase 5: Frontend** (varsa) → UID component spec'lerine göre implement et

### Çıktı
Çalışan ve test edilmiş kod (feature branch'te commit'lenmiş)

---

## ADIM 6: Reviewer Agent Session

### Başlat
Yeni Copilot Chat:

```
@workspace Şu anda Reviewer Agent rolündesin.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/reviewer.md (rol tanımın ve review checklist'lerin)
- .github/copilot-instructions.md (coding standards)
- docs/fdd/FDD-XXX-feature-name.md (onaylanmış tasarım)
- docs/tpd/TPD-XXX-feature-name.md (test planı — coverage kontrolü için)

Aşağıdaki dosyaları REVIEW et:
1. app/models/<domain>.py
2. app/services/<domain>_service.py
3. app/blueprints/<domain>_bp.py
4. tests/test_<domain>*.py
5. [diğer değişen dosyalar]

Review'ında şunlara ÖZEL DİKKAT et:
- Tenant isolation — her query'de tenant_id var mı?
- FDD uyumu — eksik/fazla implement var mı?
- TPD coverage — P0 test senaryolarının hepsi implement edilmiş mi?
- Security — auth, validation, sensitive data
```

### Karar Matrisi
| Reviewer Verdict | Senin Aksiyonun |
|---|---|
| **APPROVE** | → Merge |
| **REQUEST CHANGES** (🟡) | → Coder Agent'a bulguları ver, düzelttir → tekrar review |
| **BLOCK** (🔴) | → Tasarım hatası → Architect'e geri. Kod hatası → Coder'a geri |

### Çıktı
`docs/reviews/code/REVIEW-XXX-feature-name.md`

---

## ADIM 7: Merge & Close

```bash
git checkout main
git merge feature/<branch-name>
echo "## [Feature] FDD-XXX: <feature title>" >> CHANGELOG.md
```

---

# BÖLÜM B: AUDİT & FİX PIPELINE'LARI

> Yeni feature geliştirmek ile mevcut kodu incelemek/düzeltmek farklı iş akışlarıdır.
> Audit'ten çıkan işler genellikle 4 tipten birine girer.

## Tip 1: Code Review (Mevcut Kodu İnceleme)

**Ne zaman:** Mevcut bir modülün kalitesini/güvenliğini değerlendirmek istediğinde.
**Agent:** Sadece **Reviewer Agent**
**Çıktı:** Audit raporu + aksiyon listesi

```
Sen (inceleme talebi) → Reviewer Agent → Audit Raporu → [Sen aksiyonları planlar]
```

### Başlat
```
@workspace Şu anda Reviewer Agent rolündesin. AUDIT MODU.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/reviewer.md (rol tanımın)
- .github/copilot-instructions.md (coding standards)

Aşağıdaki modülü AUDIT et:
1. app/models/<domain>.py
2. app/services/<domain>_service.py
3. app/blueprints/<domain>_bp.py
4. tests/test_<domain>*.py

AUDIT KONTROL LİSTESİ:
☐ Tenant isolation — tüm query'lerde tenant_id filter var mı?
☐ Auth/Permission — tüm endpoint'ler korumalı mı?
☐ Input validation — tüm input'lar validate ediliyor mu?
☐ Error handling — tutarlı error response formatı mı?
☐ Test coverage — P0 senaryolar (CRUD, tenant isolation, state machine) kapsanmış mı?
☐ Code quality — naming convention, docstring, type hint
☐ Performans — N+1 query, missing index, unbounded query var mı?

Bulgularını şu formatta ver:
🔴 BLOCK — Güvenlik/veri bütünlüğü riski, hemen düzeltilmeli
🟡 FIX — Kalite sorunu, bu sprint düzeltilmeli
🔵 IMPROVE — İyileştirme önerisi, backlog'a eklenebilir
```

### Çıktı
`docs/reviews/project/AUDIT-<domain>-<date>.md`

### Sonraki Adım
Rapordaki 🔴 bulgular → Tip 2 (Quick Fix) pipeline'ına girer.
Rapordaki 🟡 bulgular → Sprint task olarak Notion'a eklenir.

---

## Tip 2: Quick Fix (Küçük Düzeltme)

**Ne zaman:** Failing test, bug fix, code quality fix, tek dosya değişikliği.
**Agent'lar:** **Coder → Reviewer** (2 adım)
**Süre:** ~30 dakika - 1 saat

```
Sen (fix talebi) → Coder Agent → [Sen test eder] → Reviewer Agent → [Merge]
```

### Başlat
```
@workspace Şu anda Coder Agent rolündesin. QUICK FIX MODU.

Aşağıdaki dosyaları oku:
- .instructions/.prompts/coder.md (rol tanımın)
- .github/copilot-instructions.md (coding standards)

## Fix Talebi
[SORUNU AÇIKLA — hata mesajı, failing test, audit bulgusu]

## Etkilenen Dosyalar
[DOSYA LİSTESİ]

Düzeltmeyi yap ve mevcut testlerin hâlâ geçtiğini doğrula:
pytest tests/test_<affected>*.py -v
```

### Çıktı
Düzeltilmiş kod → Reviewer Agent'a gönder (review zorunlu, fix de olsa)

---

## Tip 3: Blueprint/Endpoint Tamamlama

**Ne zaman:** Servis mevcut ama blueprint eksik/stub, veya endpoint'ler yarım.
**Agent'lar:** **Architect (mini FDD) → QA → Coder → Reviewer** (4 adım, UX/UI skip)
**Süre:** ~2-4 saat

```
Sen (tamamlama talebi)
 → Architect Agent (mini FDD — sadece §2 Scope, §5 API Contract, §7 AC)
 → [Sen onaylar]
 → QA Agent (TPD — API testleri + tenant isolation)
 → [Sen onaylar]
 → Coder Agent
 → [Sen test eder]
 → Reviewer Agent
 → [Merge]
```

### Architect Mini FDD Başlat
```
@workspace Şu anda Architect Agent rolündesin. COMPLETION MODU.

Bu modülün servisi mevcut ama blueprint'i eksik/yarım:
- app/services/<domain>_service.py (mevcut, oku)
- app/blueprints/<domain>_bp.py (eksik veya stub)
- app/models/<domain>.py (mevcut, oku)

Servisin mevcut fonksiyonlarını analiz et ve eşleşen endpoint'leri tasarla.
Mini FDD formatında yaz — sadece:
- §2 Scope (in/out)
- §5 API Contract (her endpoint detaylı)
- §7 Acceptance Criteria
- §12 Implementation Order (sadece Phase 3: Blueprint + Phase 4: Tests)
```

### Çıktı
`docs/fdd/FDD-XXX-complete-<domain>-bp.md`

---

## Tip 4: Yeni Modül (Sıfırdan)

**Ne zaman:** ITSM gibi hiç mevcut olmayan modül eklerken.
**Agent'lar:** **Full 6-agent pipeline** (Bölüm A'daki tüm adımlar)
**Süre:** ~8-12 saat

```
Architect → [Onay] → UX → [Onay] → UI + V0 → [Onay] → QA → [Onay] → Coder → [Test] → Reviewer → [Merge]
```

Bu, Bölüm A'daki tam pipeline. Yeni modül = yeni feature, kısa yol yok.

---

## Tip 5: Dokümantasyon (Retroactive FDD)

**Ne zaman:** Mevcut modülün FDD'si yok, dokümante edilmesi gerekiyor.
**Agent:** Sadece **Architect Agent** (reverse engineering modu)
**Süre:** ~1 saat per modül

```
Sen (doküman talebi) → Architect Agent → FDD (retroactive) → [Sen onaylar]
```

### Başlat
```
@workspace Şu anda Architect Agent rolündesin. DOCUMENTATION MODU.

Bu modül çalışıyor ama FDD'si yok. Mevcut kodu analiz edip retroactive FDD üret:
- app/models/<domain>.py
- app/services/<domain>_service.py
- app/blueprints/<domain>_bp.py
- tests/test_<domain>*.py

FDD formatında yaz ama "§1 Business Context" bölümünü kısa tut —
odak §3 Data Model, §4 Business Rules, §5 API Contract olsun.
Kod ile uyumsuz bir şey bulursan 🟡 NOT olarak işaretle.
```

### Çıktı
`docs/fdd/FDD-RET-XXX-<domain>.md` (RET = retroactive)

---

# BÖLÜM C: UI MODERNİZASYON STRATEJİSİ

> Mevcut frontend: Flask templates + Vanilla JS + custom tm_ components.
> Hedef: Modern, profesyonel, enterprise-grade UI.

## Mevcut Durum

```
Frontend Stack:
├── Flask Jinja2 Templates (7 HTML, ~2350 satır)
├── Vanilla JavaScript (~20 custom components, tm_ prefix)
├── CSS (7 dosya, design-tokens.css mevcut)
└── Hiçbir build tool (no webpack, no vite, no bundler)
```

**Güçlü yanlar:** Çalışıyor, component library var (tm_data_grid, tm_modal, tm_toast...), design tokens tanımlı.
**Zayıf yanlar:** Monolith HTML, sınırlı reactivity, enterprise polish eksik.

## Modernizasyon Yolu

### Faz M1: Backend Stabilizasyon (ŞİMDİ)
Audit bulgularını düzelt, testleri yeşile çek, eksik BP'leri tamamla.
UI'a dokunma — backend sağlam olsun.

### Faz M2: Design System Tanımlama
UI Agent'ı kullanarak tam bir design system dokümanı oluştur:
- Renk paleti, tipografi, spacing, iconography
- Component kataloğu (mevcut tm_ component'lerin modernize hali)
- Dark mode / light mode token'ları
- V0.dev ile her component'in reference implementation'ı

**Çıktı:** `docs/uid/DESIGN-SYSTEM.md`

### Faz M3: Ekran Bazlı Modernizasyon
Her ekranı sırayla modernize et — pipeline'ın UI kolu ile:

```
UX Agent (ekran bazlı UXD)
→ UI Agent (V0.dev prompt + component spec)
→ [Sen V0'da onaylar]
→ Coder Agent (implement)
→ Reviewer Agent
→ [Merge]
```

**Sıralama (Impact × Effort matrisine göre):**

| Öncelik | Ekran | Neden |
|---|---|---|
| M3.1 | Login / Onboarding | İlk izlenim, pilot müşteriler ilk bunu görür |
| M3.2 | Program Dashboard | En çok kullanılan ekran, "wow factor" |
| M3.3 | Requirement Management | Core business, demo'larda her zaman gösterilir |
| M3.4 | Test Management | 26 model, 113 route — en karmaşık, en değerli |
| M3.5 | Workshop / Explore | WR-0 scope ile alignment |
| M3.6 | RAID | Stakeholder'ların direkt gördüğü modül |
| M3.7 | Cutover | Go-live kritik ekranlar |
| M3.8 | Reporting / Dashboard | Executive visibility |
| M3.9 | Admin panelleri | Internal use, düşük öncelik |

### Faz M4: Progressive Enhancement
- Responsive design (mobile support)
- Keyboard navigation (accessibility)
- Dark mode
- Offline capability (PWA geliştirme)
- Real-time updates (WebSocket/SSE)

---

# BÖLÜM D: DOKÜMANTASYON STRATEJİSİ

> Proje %90 backend complete, %10 documented. Bu farkı sistematik kapatıyoruz.

## Doküman Tipleri ve Üretim Sırası

### Tier 1: Zorunlu (Her yeni iş ile birlikte)
Bu günden itibaren her code change'e doküman eşlik eder:

| Doküman | Agent | Ne Zaman |
|---|---|---|
| FDD | Architect | Her yeni feature/fix öncesi |
| TPD | QA Agent | Her FDD onayı sonrası |
| Review Report | Reviewer | Her merge öncesi |

### Tier 2: Retroactive (Mevcut modüller için)
Aktif kullanılan modüllerden başlayarak retroactive FDD üret (Tip 5 pipeline):

| Öncelik | Modül | Model Sayısı | Route Sayısı | Neden |
|---|---|---|---|---|
| 1 | Testing | 26 | 113 | En büyük modül, en çok risk |
| 2 | Explore/Workshop | 17+ | 99 | WR-0 scope, aktif refactor |
| 3 | Auth/RBAC | 10 | 52 (auth+sso+scim+admin) | Güvenlik kritik |
| 4 | Program | 6 | 25 | Temel modül, diğer hepsi bağlı |
| 5 | RAID | 4 | 30 | Sık kullanılan |
| 6 | Cutover | 8 | 47 | Karmaşık, iyi dokümante edilmeli |
| 7 | Backlog | 6 | 32 | Core business |
| 8 | Data Factory | 7 | 40 | Karmaşık, az bilinen |
| 9+ | Diğerleri | ... | ... | Sırayla |

### Tier 3: UX/UI Dokümanlar (Faz M3 ile paralel)
Her ekran modernizasyonu sırasında UXD + UID doğal olarak üretilir.

### Tier 4: Proje Seviyesi
| Doküman | Durum | Aksiyon |
|---|---|---|
| README.md | Muhtemelen mevcut | Güncelle |
| ARCHITECTURE.md | Yok | Architect Agent ile oluştur |
| CONTRIBUTING.md | Yok | Pipeline kurallarını anlat |
| API_REFERENCE.md | Yok | Blueprint'lerden otomatik üret |

---

# BÖLÜM E: HIZLI REFERANS

## Pipeline Seçim Matrisi

| Durum | Pipeline Tipi | Agent Sırası | Tahmini Süre |
|---|---|---|---|
| Mevcut kodu incele | Tip 1: Review | Reviewer | 30dk - 1sa |
| Bug fix / failing test | Tip 2: Quick Fix | Coder → Reviewer | 30dk - 1sa |
| Stub BP tamamla | Tip 3: Complete | Architect(mini) → QA → Coder → Reviewer | 2-4sa |
| Sıfırdan yeni modül | Tip 4: Full | Full 6-agent | 8-12sa |
| Mevcut modül belgeleme | Tip 5: Document | Architect (reverse) | 1sa |
| Yeni feature (backend+UI) | Bölüm A: Full | Full 6-agent | 4-10sa |
| Sadece API (UI yok) | Kısa yol | Architect → QA → Coder → Reviewer | 2-4sa |
| Sadece UI değişikliği | Kısa yol | UX → UI + V0 → Coder → Reviewer | 2-3sa |
| Acil bug fix | Kısa yol | Coder → Reviewer | 30dk |
| UI ekran modernizasyonu | Bölüm C: M3 | UX → UI + V0 → Coder → Reviewer | 3-5sa/ekran |

## Çıktı Zinciri — Kim Neyi Kime Veriyor

```
                    ┌─────────┐
                    │   FDD   │ ← Architect üretir
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  UXD   │ │  UID   │ │  TPD   │
         │UX Agent│ │UI Agent│ │QA Agent│
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
             │     ┌────┘          │
             │     │               │
             ▼     ▼               ▼
         ┌──────────────────────────────┐
         │          CODER               │
         │ FDD: Ne yapılacak            │
         │ UID: Nasıl görünecek         │
         │ TPD: Ne test edilecek        │
         └──────────────┬───────────────┘
                        │
                        ▼
                   ┌──────────┐
                   │ REVIEWER │
                   │ FDD + TPD ile karşılaştırır
                   └──────────┘
```

**Önemli:** UXD doğrudan Coder'a gitmez — UXD'nin görsel karşılığı UID'dir. Coder, UID'deki component spec'leri kullanır.

## Sık Yapılan Hatalar

| Hata | Sonucu | Çözüm |
|---|---|---|
| Aynı session'da birden fazla agent | Context karışır, kalite düşer | Her agent = yeni session |
| FDD onaylamadan UX'e geçmek | UX yanlış requirement üzerine tasarlar | FDD "APPROVED" olmadan ilerlenme |
| V0.dev'den çıkanı onaylamadan Coder'a geçmek | Coder yanlış görsele göre yazar | V0 görseli = visual contract |
| QA'yı atlamak | "Test edeceğiz" → hiç test yazılmaz | QA her zaman Coder'dan önce |
| Coder'a tüm kodu tek seferde yazdırmak | Context window → kalite düşüşü | Phase bazlı: Model → Service → BP → Test |
| Review'ı atlamak | "Basit değişiklik" → production bug | Her merge review'den geçer |
| Audit bulgusunu doküman etmemek | Aynı sorun tekrar keşfedilir | Her audit raporu docs/reviews/'da saklanır |
| UI modernizasyonuna backend stabilizasyonsuz başlamak | Kırık API üzerine güzel UI = kırık ürün | Önce backend, sonra UI |

## Claude.ai ile Hibrit Kullanım

| Görev | VS Code Copilot | Claude.ai |
|---|---|---|
| İlk fikir aşaması, brainstorming | ❌ | ✅ |
| Best practice araştırması (web search) | ❌ | ✅ |
| Codebase audit (geniş context) | Sınırlı | ✅ |
| FDD ilk taslak | Sınırlı | ✅ |
| FDD refinement (dosya okuma) | ✅ (@workspace) | ❌ |
| UX/UI tasarım | ✅ | Sınırlı |
| QA test planı | ✅ | ✅ |
| Kod yazma/düzenleme | ✅ | ❌ |
| Code review | ✅ (diff görebilir) | Sınırlı |
| Mimari kararlar, trade-off analizi | ❌ | ✅ |
| Sprint planlama, önceliklendirme | ❌ | ✅ |
| Notion task yönetimi | ❌ | ✅ (MCP ile) |

---

# BÖLÜM F: MEVCUT AUDİT EYLEM PLANI

> Deep Audit (2026-02-21) bulgularından türetilen somut iş kalemleri.

## Sprint WR-A (Audit Remediation) — Önerilen Sıralama

### Hafta 1: Stabilizasyon
| # | İş | Pipeline Tipi | Effort | Agent Sırası |
|---|---|---|---|---|
| WR-A.1 | explore_service.py tenant isolation audit | Tip 1: Review | 2h | Reviewer |
| WR-A.2 | run_sustain_service.py tenant isolation audit | Tip 1: Review | 1h | Reviewer |
| WR-A.3 | 5 failing test düzeltme | Tip 2: Quick Fix | 2h | Coder → Reviewer |
| WR-A.4 | integration vs integrations naming doc | Tip 5: Document | 30min | Architect |

### Hafta 2: Tamamlama
| # | İş | Pipeline Tipi | Effort | Agent Sırası |
|---|---|---|---|---|
| WR-A.5 | Traceability BP tamamlama (1 route → full) | Tip 3: Complete | 4h | Architect → QA → Coder → Reviewer |
| WR-A.6 | Governance rules BP oluşturma | Tip 3: Complete | 4h | Architect → QA → Coder → Reviewer |
| WR-A.7 | Test naming convention standardize | Tip 5: Document | 1h | Architect |

### Hafta 3-4: Retroactive Documentation
| # | İş | Pipeline Tipi | Effort | Agent Sırası |
|---|---|---|---|---|
| WR-A.8 | Testing modülü retroactive FDD | Tip 5: Document | 1.5h | Architect |
| WR-A.9 | Explore/Workshop retroactive FDD | Tip 5: Document | 1.5h | Architect |
| WR-A.10 | Auth/RBAC retroactive FDD | Tip 5: Document | 1h | Architect |
| WR-A.11 | Program retroactive FDD | Tip 5: Document | 1h | Architect |

### Hafta 5+: UI Modernizasyon Başlangıcı (Bölüm C, Faz M2-M3)
| # | İş | Pipeline Tipi | Effort | Agent Sırası |
|---|---|---|---|---|
| WR-A.12 | Design System dokümanı | Özel | 4h | UI Agent |
| WR-A.13 | Login/Onboarding modernizasyonu | Bölüm C M3.1 | 5h | UX → UI → Coder → Reviewer |
| WR-A.14 | Program Dashboard modernizasyonu | Bölüm C M3.2 | 5h | UX → UI → Coder → Reviewer |
