# Other Documents, AI Module & Technical Debt — Review Findings

**Reviewer:** GitHub Copilot (Claude Opus 4.6)
**Date:** 2026-02-10
**Commit:** `3c331dd` (TS-Sprint 2)
**Scope:** D11-D16, M10, B10, T10/T11, AI katmanı (7 dosya), README (D21)
**Total Findings:** 38

---

## A. AI MODÜLÜ REVIEW (14 Finding)

### A-001 | D11 P1 Asistan "Risk Assessment" — Implement Edilmemiş
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D11 §4, ai_knowledge/prompts/risk_assessment.yaml |
| **Bulgu** | D11, Risk Assessment'ı P1 (skor 9.0, S12a sprint ataması) olarak önceliklendiriyor. YAML prompt template hazır (`risk_assessment.yaml`, 47 LOC). Ancak `app/ai/assistants/` dizininde yalnız 3 dosya var: `nl_query.py`, `requirement_analyst.py`, `defect_triage.py`. Risk Assessment assistant sınıfı oluşturulmamış. |
| **Etki** | D11'in en acil P1 önerisi hayata geçirilmemiş. 6-8 saat effort ile hemen uygulanabilir durumda (prompt + model + altyapı hazır). |
| **Öneri** | S12a (veya TS-Sprint 3) içinde `risk_assessment.py` assistant sınıfını oluştur + 2 endpoint ekle. |

### A-002 | D11 P2 Asistan "Test Case Generator" — Implement Edilmemiş
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D11 §3 S12a |
| **Bulgu** | P2 sıralı Test Case Generator (skor 8.5, S12a ataması) implement edilmemiş. Test modeli (TestCase, TestSuite) hazır, prompt template eksik. |
| **Etki** | QA süresini %40 azaltacak olarak tahmin ediliyor. |
| **Öneri** | S12a kapsamında prompt template + assistant sınıfı oluştur. Tahmini 10 saat. |

### A-003 | D11 14→11+3 Sayı Tutarsızlığı
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | D11 başlık + §2 |
| **Bulgu** | Doküman başlığı "14 AI Asistan" diyor. §1'de 3 aktif, §2'de 11 kalan = toplam 14 ✅. Ancak envanter (project-inventory.md §3.4) "3 aktif" diyor - bu tutarlı. İlk P1-P11 sıralama (11 satır) ile "14 AI asistan" başlığı arasındaki fark: 14 = 3 aktif + 11 planlı. Açıklama yeterli ama başlıkta "Kalan 11 Asistan" alt başlığı ile birlikte okunduğunda karışıklık yaratmıyor. |
| **Etki** | Yok — bilgi doğru ama başlık "Kalan ve Mevcut" olarak netleştirilebilir. |
| **Öneri** | Başlığa "(3 aktif + 11 planlı)" ek notu. |

### A-004 | M10 AIConversation Modeli — Envanterde Var, Kodda Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟠 HIGH |
| **Kaynak** | project-inventory.md M10 satırı vs. app/models/ai.py |
| **Bulgu** | Envanter (§3.1 M10) "5 class: AISuggestion, AIAuditLog, AIEmbedding, KBVersion, **AIConversation**" listeliyor. Ancak `app/models/ai.py`'da AIConversation sınıfı **mevcut değil**. `grep -in "AIConversation" app/models/ai.py` → 0 sonuç. Mevcut 5 sınıf: AIUsageLog, AIEmbedding, KBVersion, AISuggestion, AIAuditLog. |
| **Etki** | Envanter yanıltıcı. AIConversation planlanmışsa implement edilmemiş; planlanmamışsa envanter yanlış. |
| **Öneri** | (1) Envanterdeki M10'u düzelt: AIConversation → AIUsageLog. (2) AIConversation gerekiyorsa D5'e eklenip planlanmalı. |

### A-005 | M10 5 Class, Envanter "5 class" Diyor — Sınıf Adı Yanlış
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | project-inventory.md M10 |
| **Bulgu** | M10 gerçek 5 sınıf: `AIUsageLog`, `AIEmbedding`, `KBVersion`, `AISuggestion`, `AIAuditLog`. Envanter listelemesi `AIConversation` yazıp `AIUsageLog`'u atlamış. |
| **Etki** | AIUsageLog (token/cost tracking) envanterde görünmüyor → yeni geliştirici yanılabilir. |
| **Öneri** | Envanter M10 satırını düzelt. |

### A-006 | B10 29 Route — D3 Mimari Doküman "22 endpoint" Diyor
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | sap_transformation_platform_architecture_v2.md vs B10 |
| **Bulgu** | D11 §1 "22 API Endpoint" listeliyor. B10'da `grep -c "@ai_bp.route"` → **29 route**. Sprint 9.5 KB Versioning (+7 endpoint) sonrası D11'deki "22" güncellenmiş olmalıydı. D3'teki rakamlar da eski. |
| **Etki** | Mimari dokümanlar ile kod arasında 7 endpoint farkı. |
| **Öneri** | D11 §1 ve D3 AI modülü bölümünü 29 olarak güncelle. |

### A-007 | KB Versioning (D16) — Tam Implement Edilmiş ✅
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | D16, M10, B10, T11 |
| **Bulgu** | D16'da tanımlanan tüm bileşenler implement edilmiş: (1) KBVersion model + `kb_versions` tablosu (building/active/archived lifecycle) ✅, (2) AIEmbedding'e 6 yeni kolon (kb_version, content_hash, embedding_model, embedding_dim, is_active, source_updated_at) ✅, (3) AISuggestion'a kb_version kolonu ✅, (4) 7 API endpoint (list, create, get, activate, archive, stale, diff) ✅, (5) Non-destructive indexing (RAG pipeline) ✅, (6) Migration `e7b2c3d4f501` ✅, (7) 27 test (test_kb_versioning.py) ✅. |
| **Etki** | Pozitif — D16 %100 implement edilmiş. |
| **Öneri** | Yok. |

### A-008 | AI Gateway — Gemini Provider Eklendi Ama D3'te Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | app/ai/gateway.py, D3 mimari |
| **Bulgu** | Gateway'de 4 provider var: Anthropic, OpenAI, **Gemini**, LocalStub. D3 ve D11 yalnızca "3 sağlayıcı + stub" diyor. Gemini (free tier, google-genai SDK) eklenmiş ama dokümanlara yansımamış. `TOKEN_COSTS` dict'inde `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-embedding-001` modelleri var. |
| **Etki** | Düşük — işlevsellik doğru çalışıyor, doküman eski. |
| **Öneri** | D3 ve D11'e Gemini provider bilgisini ekle. |

### A-009 | AI Suggestion Types — SUGGESTION_TYPES vs D11 Asistan Listesi Uyumu
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | app/models/ai.py SUGGESTION_TYPES, D11 |
| **Bulgu** | `SUGGESTION_TYPES` set'i: `fit_gap_classification`, `requirement_analysis`, `defect_triage`, `risk_assessment`, `test_case_generation`, `scope_recommendation`, `general`. D11'deki 14 asistanın çoğu (change_impact, status_report, sprint_planner, meeting_summarizer vb.) burada tanımlı değil. Bu bir enforced validator ise, gelecek asistanlar bu set'e eklenmeli. |
| **Etki** | Set bir validator olarak kullanılmıyorsa sorun yok. Kullanılıyorsa yeni asistanlar reject edilir. |
| **Öneri** | (1) SUGGESTION_TYPES'ı genişlet veya (2) Bir validator olarak kullanılmıyorsa docstring'e "informational only" notu ekle. |

### A-010 | test_ai.py T10 — 69 Test, Envanter "69" Diyor ✅
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | tests/test_ai.py → `grep -c "def test_"` = 69 |
| **Bulgu** | Envanter T4 satırında 69 test, gerçek sayım 69 ✅. |
| **Etki** | Yok — tutarlı. |

### A-011 | test_ai_assistants.py T11 — 72 Test, Envanter "72" Diyor ✅
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | tests/test_ai_assistants.py → `grep -c "def test_"` = 72 |
| **Bulgu** | Envanter T5 satırında 72, gerçek sayım 72 ✅. T10+T11 = 141, envanter doğru. |
| **Etki** | Yok — tutarlı. |

### A-012 | AI Servisleri — app/services/ Altında AI Servisi Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 INFO |
| **Kaynak** | app/services/ dizini |
| **Bulgu** | Envanterde S8-S12 "AI servisleri" olarak tanımlanmamış; `app/services/` altında AI-spesifik servis dosyası yok. AI business logic'i şu dosyalarda: (1) `app/ai/gateway.py` — LLM router, (2) `app/ai/rag.py` — RAG pipeline, (3) `app/ai/suggestion_queue.py` — HITL lifecycle, (4) `app/ai/prompt_registry.py` — prompt yönetimi. Bunlar `app/ai/` altında, `app/services/` altında değil. |
| **Etki** | Mimari tutarlılık açısından sorun değil — AI katmanı bağımsız bir dizinde. |
| **Öneri** | Yok, mevcut organizasyon uygun. |

### A-013 | cost_summary Endpoint — Granularity Parametresi Kullanılmıyor
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | app/blueprints/ai_bp.py `/ai/usage/cost` endpoint |
| **Bulgu** | `cost_summary()` fonksiyonu `granularity` parametresini alıyor (daily/weekly/monthly) ama sadece `daily` gruplama yapıp geri dönüyor. Weekly/monthly gruplama implement edilmemiş. |
| **Etki** | API yanıltıcı — istemci weekly/monthly isteyince de daily alır. |
| **Öneri** | Weekly/monthly gruplama logic'ini ekle veya parametreyi kaldır. |

### A-014 | RAG Pipeline — 8 Entity Extractor Mevcut, Kapsam Yeterli
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | app/ai/rag.py |
| **Bulgu** | 8 entity-specific extractor: requirement, backlog_item, risk, test_case, defect, config_item, scenario, process. Generic fallback da mevcut. Explore Phase entity'leri (FitGapItem, RequirementItem vb.) generic extractor ile indexlenir. |
| **Etki** | Yok — yeterli kapsam. |

---

## B. FRONTEND KARARI — D12 (5 Finding)

### B-001 | Vue 3 Migration — Faz 0 Başlamamış
| Alan | Detay |
|------|-------|
| **Severity** | 🟠 HIGH |
| **Kaynak** | D12 §3 Phase 0, D5 Sprint 10, mevcut dosya sistemi |
| **Bulgu** | D12 "✅ Approved — Vue 3 Incremental Migration (Sprint 10 Start)" onay tarihi 2026-02-10. Ancak: (1) `find . -name "*.vue"` → **0 dosya**, (2) `package.json` veya `vite.config.ts` yok, (3) `node_modules/` yok, (4) Tüm 22 JS dosyası orijinal Vanilla JS yapısında. Faz 0 henüz başlamamış. |
| **Etki** | D12 kararı onaylanmış ama S10 henüz başlamadığı için implementasyon yok. Bu beklenen bir durum — TS-Sprint 2 tamamlandı, S10 sırada. |
| **Öneri** | S10 planlama sırasında D12 Faz 0 görevlerini (Vite + utils.js extract + scaffold) ilk iş olarak başlat. |

### B-002 | Frontend Metrikleri — D12 vs Gerçek Durum
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D12 §1, file system |
| **Bulgu** | D12, "15 JS dosya, 8,174 LOC" diyor. Gerçek durum: **22 JS dosya, ~11,964 LOC**. D12, Sprint 9+ tarihli (2025-02-09); o zamandan beri Explore Phase (6 yeni JS dosya: explore_hierarchy.js, explore_workshops.js, explore_workshop_detail.js, explore_requirements.js, explore_dashboard.js, explore-api.js, explore-shared.js) eklendi. |
| **Etki** | D12'nin analizi eski metriklere dayalı. Gerçek göç çalışması ~%46 daha büyük. |
| **Öneri** | D12'ye "Current State (Updated)" bölümü ekle: 22 dosya, ~12K LOC. Faz 2 tahminlerini revize et. |

### B-003 | D12 → D5 Proje Planı Yansıması — Tam Uyumlu ✅
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | D5 Sprint 10-14 |
| **Bulgu** | D12'nin 4 fazı D5'te detaylı görev olarak tanımlı: Sprint 10 (10.7-10.10 Vue Phase 0, 2.5 saat), Sprint 11 (11.9-11.13 Phase 1+2a, 10 saat), Sprint 12-13 (Phase 2b view migration), Sprint 14 (Phase 3 polish + test). Tutarlı. |
| **Etki** | Pozitif. |

### B-004 | Frontend Test — Sıfır
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D12 §1, filesystem |
| **Bulgu** | 0 frontend test. D12 bunu açıkça kabul ediyor ve Phase 3'te (Sprint 14) Vitest + Playwright planı var. D5'te 14.1-14.5 görevleri bunu kapsamlı planlıyor. Ancak mevcut 11,964 LOC Vanilla JS'de hiçbir test yok — herhangi bir regression görünmez. |
| **Etki** | Vue migration sırasında regression riski var. |
| **Öneri** | Phase 0'da (S10) kritik 5 akış için E2E baseline test eklemek (D12'nin Phase 0 + Phase 3 planına ek). |

### B-005 | D12 Eski Mimari (architecture v1.3) Referans Sorunu
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | D12 footer "scripts/analysis/collect_metrics.py analysis" |
| **Bulgu** | D12 metrikleri Sprint 9 tarihli. D12 başlığında approval tarihi 2026-02-10 olarak güncellenmiş ama §1 metrikleri eski. |
| **Etki** | Küçük. |
| **Öneri** | Approval notu ile birlikte updated metrics section ekle. |

---

## C. ENTEGRASYON DOKÜMANLAR (6 Finding)

### C-001 | D13 (Signavio PARKED) ↔ D1 (Explore FS/TS) Çelişki
| Alan | Detay |
|------|-------|
| **Severity** | 🟠 HIGH |
| **Kaynak** | D13, D1, app/models/explore.py |
| **Bulgu** | D13 "PARKED — Awaiting design approval" durumunda. 5 tasarım kararı onay bekliyor (ScopeItem independent entity, BPMN metadata, N:M relationships). **Ancak** Explore Phase (D1) FS/TS'teki `process_level` modeli `bpmn_available` ve `bpmn_reference` alanlarını zaten implement etmiş (M9 explore.py satır 120-121). D13'ün "BPMN metadata yok" Gap Analysis'i kısmen yanlış — basic BPMN referansı var, full XML blob yok. |
| **Etki** | D13 güncel değil — Explore Phase implementasyonunu (25 tablo, bpmn_available/bpmn_reference) hesaba katmıyor. |
| **Öneri** | D13'ü Explore Phase implementasyonuyla reconcile et. Gap analysis'i güncelle: "bpmn_reference mevcut, bpmn_xml blob eksik". |

### C-002 | D13 ScopeItem Kararı — Explore Phase'de Farklı Çözüm
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D13 §3.1, D1, M9 |
| **Bulgu** | D13 "ScopeItem'ı bağımsız entity olarak yeniden oluştur" diyor. Ancak Explore Phase (D1) bu sorunu farklı çözmüş: `workshop_scope_item` N:M junction table ile Workshop ↔ L3 Process bağlantısı, ve L3'te scope alanları (scope_decision, fit_gap, sap_reference) korunmuş. D13'ün önerdiği N:M ScopeItem ↔ L3 yapısı, mevcut workshop_scope_item ile çakışacak. |
| **Etki** | D13 onaylanırsa mevcut Explore Phase yapısıyla uyumsuzluk riski. |
| **Öneri** | D13'ü Explore Phase hierarchy'si ile align et. ScopeItem kararını Explore Phase'in mevcut çözümü ışığında yeniden değerlendir. |

### C-003 | D14 (56 saat) → D5 Proje Planı (18 saat) — Güncellenmemiş
| Alan | Detay |
|------|-------|
| **Severity** | 🔴 CRITICAL |
| **Kaynak** | D14 §2 vs D5 Sprint 22 |
| **Bulgu** | D14, S22 dış entegrasyon tahminini 18 saat → **56 saat (3.1×)** olarak revize etmiş. Ancak D5'teki Sprint 22 bölümü hâlâ **18 saat** gösteriyor (6 task: Jira 4h, Cloud ALM 4h, ServiceNow 3h, Teams 2h, UI 3h, Webhook 2h). D14'ün "S22a/S22b'ye böl" önerisi D5'e **yansımamış**. |
| **Etki** | Proje planı 38 saat eksik tahmin taşıyor. Timeline riski: +2 hafta kayma potansiyeli. |
| **Öneri** | D5 Sprint 22'yi D14'ün Opsiyon A/B/C'sinden birini seçerek güncelle. Minimum: 18→56 saat olarak düzelt. |

### C-004 | D14 Bağımlılık Zinciri — S14 (JWT/RBAC) Blocker
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D14 §3 |
| **Bulgu** | 4 dış entegrasyonun tümü S14 (Security & Platform Hardening) JWT/RBAC'a bağımlı. S14 henüz başlamamış. D14'ün bağımlılık zinciri: S14 → S18 → S22. Eğer S14 beklenenden uzun sürerse, S22 kayar. |
| **Etki** | Critical path risk. |
| **Öneri** | S14'ü erken başlatma stratejisi değerlendir. |

### C-005 | D15 (DB Consistency) — 5/8 Çözüldü, Kalan 3 Durumu
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | D15 §1, §3 |
| **Bulgu** | 8 bulgudan: **5 çözüldü** (✅ Fixed: #1 embedding_vector alignment, #2 NL Query DB-aware, #4 pgvector migration, #5 FK enforcement, #7 docker-compose). **3 kalan**: (1) #3 PostgreSQL-specific test environment → belgelenmiş, CI'da PG testi yok, (2) #6 JSON column migration (text→JSON) → gelecek sprint, (3) #8 pool_pre_ping → zararsız. |
| **Etki** | #3 en önemlisi — CI hiç PostgreSQL testi çalıştırmıyor. Prod'da sürpriz regression riski. |
| **Öneri** | GitHub Actions'a `pytest -m postgres` adımı ekle (Docker PG ile). |

### C-006 | D14 Signavio Ayrı Tut Önerisi — D13 ile Uyumlu ✅
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | D14 §7, D13 |
| **Bulgu** | D14 "Signavio'yu ayrı tut" diyor (16 saat, mimari farklı). D13 PARKED durumda. Her iki doküman tutarlı: Signavio ayrı iz olarak planlanmış. |

---

## D. TEKNİK BORÇ (9 Finding)

### D-001 | 7 .bak Dosya — Disk'te Yok (Zaten Temizlenmiş)
| Alan | Detay |
|------|-------|
| **Severity** | ✅ OK |
| **Kaynak** | project-inventory.md §5.2, dosya sistemi |
| **Bulgu** | Envanterde listelenen 7 .bak dosya (`requirement_bp.py.bak`, `scope_bp.py.bak`, `requirement.py.bak`, `scope.py.bak`, `seed_demo_data.py.bak`, `test_api_requirement.py.bak`, `test_api_scope.py.bak`) disk'te **mevcut değil**. `find . -name "*.bak" -type f` → 0 sonuç. Muhtemelen son commit'lerden birinde temizlenmiş ama workspace info şablondan geliyor. |
| **Etki** | Temizlik yapılmış ✅. Envanter güncellenebilir. |
| **Öneri** | project-inventory.md §5.2'yi güncelle: "7 .bak dosya — TEMİZLENDİ ✅". |

### D-002 | D4 (Architecture v1.3) — Hâlâ Disk'te
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | sap_transformation_platform_architecture_v1_backup.md |
| **Bulgu** | D4 (v1.3, 2,254 LOC) hâlâ `sap_transformation_platform_architecture_v1_backup.md` olarak disk'te. D3 (v2.1) ile süpersede edilmiş. Envanter "ESKİ — v2.1 ile süpersede edildi" notu düşmüş. |
| **Etki** | Yeni geliştirici yanlış dokümanı okuyabilir. Dosya adında "(2)" konfüzyona neden olur. |
| **Öneri** | (1) Dosyayı sil ve `.gitignore`'a ekle, veya (2) `_ARCHIVED/` dizinine taşı, veya (3) Dosya başına `> ⛔ ARCHIVED — See sap_transformation_platform_architecture_v2.md` banner'ı ekle. |

### D-003 | Alembic Migration — 10 Migration, Son: TS-Sprint 2
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | migrations/versions/ |
| **Bulgu** | 10 migration mevcut. Son: `g6b7c8d9e005_ts_sprint2_run_defect_enrich.py`. TS-Sprint 3 için yeni migration **gerekecek**: (1) `uat_sign_off` tablosu, (2) `perf_test_result` tablosu, (3) `test_daily_snapshot` tablosu — bunlar test-management-fs-ts.md'de tanımlı ama M6'da eksik. Ayrıca defect 9-status transition ve SLA tabloları da migration gerektirecek. |
| **Etki** | Planlanan iş — TS-Sprint 3'te gerekli. |
| **Öneri** | TS-Sprint 3 başlangıcında MIG11 hazırla. |

### D-004 | Test Coverage — 860 test / 321 route = 2.7 ort.
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | Tüm test dosyaları, tüm blueprint'ler |
| **Bulgu** | Ortalama 2.7 test/route. Dağılım: Program 1.4, Scenario 1.4, Scope 2.3, Requirement 2.0, Backlog 2.1, Testing 2.7, RAID 1.5, Integration 2.9, Explore 2.9, AI 4.9. En düşük: Program (1.4), Scenario (1.4), RAID (1.5). |
| **Etki** | Eski modüller (S1-S4 dönemi) düşük coverage'a sahip. |
| **Öneri** | Minimum hedef: **3.0 test/route**. Program, Scenario ve RAID modüllerini önceliklendirip her birine ~10-15 test ekle. Toplam ~45 ek test ile 905/321 = 2.82 olur. |

### D-005 | JSON Kolonları db.Text Olarak Tutuluyor
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | D15 §3, M10 metadata_json kolonları |
| **Bulgu** | `metadata_json`, `suggestion_data`, `current_data` kolonları `db.Text` olarak saklanıyor (D15 #6). PostgreSQL'de `db.JSON` kullanılabilir, SQLite'da ise text yeterli. Bu dual-DB uyumluluk nedeniyle bilinçli bir tercih ama PG'de JSON indexleme avantajı kaybediliyor. |
| **Etki** | Düşük — mevcut yaklaşım çalışıyor. |
| **Öneri** | S14 (DB hardening) veya S16'da db.JSON migration yap. |

### D-006 | CI'da PostgreSQL Testi Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟠 HIGH |
| **Kaynak** | D15 #3 |
| **Bulgu** | Tüm 860 test SQLite in-memory'de çalışıyor. PostgreSQL-specific davranışlar (JSONB operatörleri, pgvector `<=>` operator, array kolonlar, LISTEN/NOTIFY) hiç test edilmiyor. |
| **Etki** | Prodüksiyon deployment sırasında sürpriz hatalar. |
| **Öneri** | GitHub Actions'a `postgres` servis ekle, `pytest -m postgres` marker'ı oluştur. |

### D-007 | app/services/ Testing Servisi Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | app/services/ dizini, B6 |
| **Bulgu** | Testing modülü (55 route) Explore Phase'den farklı olarak servis katmanı kullanmıyor. Tüm business logic B6'da inline. Explore Phase 8 servis kullanıyor (traceability, workshop_session, fit_propagation vb.). |
| **Etki** | B6 (1,668 LOC) en büyük blueprint — SRP ihlali riski. Defect transition logic, SLA hesaplama, go-no-go scorecard gibi karmaşık kurallar servis katmanına çıkarılmalı. |
| **Öneri** | TS-Sprint 3-4'te `DefectLifecycleService` ve `TestExecutionService` servislerini oluştur. |

### D-008 | Makefile — 20+ Hedef, Ancak `make lint` ve `make format` Yok
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | Makefile |
| **Bulgu** | Makefile'da `make test`, `make run`, `make deploy` hedefleri var ama lint (flake8/ruff) ve format (black/isort) hedefleri yok. |
| **Etki** | Kod stili tutarlılığı CI'da enforce edilemiyor. |
| **Öneri** | `make lint` (ruff check .) ve `make format` (ruff format .) hedeflerini ekle. |

### D-009 | Prompt YAML Templates — 4 Dosya, 1'i Aktif Değil
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 INFO |
| **Kaynak** | ai_knowledge/prompts/ |
| **Bulgu** | 4 YAML prompt: nl_query.yaml (109 LOC), defect_triage.yaml (51), requirement_analyst.yaml (48), risk_assessment.yaml (47). İlk 3'ü aktif asistanlarca kullanılıyor. `risk_assessment.yaml` hazır ama asistan sınıfı yok (A-001 ile bağlantılı). |

---

## E. README — D21 (4 Finding)

### E-001 | README Proje Metrikleri Güncel Değil
| Alan | Detay |
|------|-------|
| **Severity** | 🟠 HIGH |
| **Kaynak** | README.md §Tech Stack, §Current Status, §Demo Veri |
| **Bulgu** | README kritik ölçüde güncel değil: (1) "Current Status" tablosu Sprint 4 / 136 test / 73 endpoint / 15 tablo'da kalmış. Gerçek: **321 route, 71 tablo, 860 test**. Sprint 5-9 + TS-Sprint 1-2 hiç eklenmemiş. (2) "Demo Veri" bölümü "140 kayıt" diyor; mevcut seed ~400+ kayıt. (3) `make test → 136 testi çalıştır` yazıyor; gerçekte 860. (4) Tech Stack'te Python 3.13 yazıyor — doğru mu kontrol et. |
| **Etki** | Yeni kullanıcı veya contributor yanıltılıyor. README projenin vitrini. |
| **Öneri** | README'yi kapsamlı güncelle: 12 blueprint, 74 model, 860 test, 3 AI asistan, 12 servis. |

### E-002 | README Modül Listesi Eksik
| Alan | Detay |
|------|-------|
| **Severity** | 🟡 MEDIUM |
| **Kaynak** | README.md |
| **Bulgu** | README'de modül listesi yok. Mevcut 12 blueprint: Program, Scenario, Scope, Requirement, Backlog, Testing, RAID, Integration, Explore, AI, Health, Metrics. Bunların hiçbiri README'de listelenmemiş. Also: Explore Phase (en büyük modül, 66 route), Test Management (55 route), AI (29 route) giydirmeler yok. |
| **Etki** | Proje kapsamı anlaşılmıyor. |
| **Öneri** | "## Modules" bölümü ekle (12 modül + route sayıları). |

### E-003 | README Kurulum Rehberi — Yeterli Ama Minimalist
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | README.md §Offline Yerel Test Ortamı |
| **Bulgu** | `make setup` + `make run` + `make test` akışı açık ve çalışır durumda ✅. Ancak: (1) Docker kurulumu anlatılmıyor (docker/README veya docker-compose up talimatı), (2) `.env` dosyası kurulumu eksik (özellikle GEMINI_API_KEY AI için gerekli), (3) PostgreSQL konfigürasyonu yok. |
| **Etki** | Düşük — dev ortamı SQLite ile çalışıyor. Docker/PG üretim kurulumu eksik. |
| **Öneri** | "### Production Setup (Docker)" ve "### Environment Variables" bölümleri ekle. |

### E-004 | README License — "To be defined"
| Alan | Detay |
|------|-------|
| **Severity** | 🟢 LOW |
| **Kaynak** | README.md §License |
| **Bulgu** | Lisans belirtilmemiş: "To be defined." Bu 20+ commit ve 76K LOC'luk bir proje için risk. |
| **Etki** | Contributor veya enterprise adopter'lar lisans belirsizliği nedeniyle katılamaz. |
| **Öneri** | MIT, Apache 2.0 veya proprietary lisansı seç. |

---

## Özet Tablo

| Bölüm | Finding | Critical | High | Medium | Low | OK/Info |
|--------|--------:|:--------:|:----:|:------:|:---:|:-------:|
| A. AI Modülü | 14 | 0 | 1 | 5 | 3 | 5 |
| B. Frontend | 5 | 0 | 1 | 2 | 1 | 1 |
| C. Entegrasyon | 6 | 1 | 1 | 2 | 0 | 2 |
| D. Teknik Borç | 9 | 0 | 2 | 3 | 3 | 1 |
| E. README | 4 | 0 | 1 | 1 | 2 | 0 |
| **Toplam** | **38** | **1** | **6** | **13** | **9** | **9** |

---

## Öncelik Matrisi — Hemen Yapılması Gerekenler

| # | Finding | Effort | Sprint |
|---|---------|--------|--------|
| 1 | C-003: D5 S22'yi 18→56 saat olarak güncelle | 0.5h | Hemen |
| 2 | E-001: README kapsamlı güncelle | 2h | Hemen |
| 3 | A-004/A-005: project-inventory.md M10 düzelt | 0.5h | Hemen |
| 4 | D-001: Envanter §5.2 .bak notunu güncelle | 0.5h | Hemen |
| 5 | A-001: Risk Assessment asistan sınıfını implement et | 8h | S12a / TS-Sprint 3 |
| 6 | D-006: CI'ya PostgreSQL test adımı ekle | 4h | S14 |
| 7 | C-001: D13'ü Explore implementasyonuyla reconcile et | 2h | D13 review sırasında |
| 8 | D-007: Testing servis katmanı oluştur | 8h | TS-Sprint 3-4 |
| 9 | B-001: Vue 3 Phase 0 başlat | 2.5h | S10 |
| 10 | D-004: Minimum 3.0 test/route hedefi için ek testler | 6h | S12-S14 |

---

**Dosya:** `other-docs-review-findings.md`
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)
**Tarih:** 2026-02-10
