# AI Asistan Önceliklendirme Analizi

**Document ID:** P7-AI-PRIORITY  
**Sprint:** 9.5  
**Date:** 2025-02-09

---

## 1. Mevcut Durum

### Uygulanan Asistanlar (3/14)

| # | Asistan | Dosya | Durum | Kullanıcı Değeri |
|---|---------|-------|-------|-----------------|
| 1 | **NL Query** | `nl_query.py` (587 LOC) | ✅ Tam çalışır | 🟢 Yüksek |
| 2 | **Requirement Analyst** | `requirement_analyst.py` | ✅ Tam çalışır | 🟢 Yüksek |
| 3 | **Defect Triage** | `defect_triage.py` | ✅ Tam çalışır | 🟢 Yüksek |

### AI Altyapı Durumu

| Bileşen | Durum | Hazırlık |
|---------|-------|----------|
| LLM Gateway (3 sağlayıcı + stub) | ✅ | Production-ready |
| RAG Pipeline (hybrid semantic+keyword) | ✅ | Production-ready |
| Suggestion Queue (HITL lifecycle) | ✅ | Production-ready |
| Prompt Registry (built-in + YAML override) | ✅ | Production-ready |
| Cost Tracking (per-call, dashboard) | ✅ | Production-ready |
| Audit Logging | ✅ | Production-ready |
| 22 API Endpoint | ✅ | Production-ready |

---

## 2. Kalan 11 Asistan — Öncelik Sıralaması

### Sıralama Kriterleri

| Kriter | Ağırlık | Açıklama |
|--------|---------|----------|
| **Kullanıcı Etkisi** | 35% | Günlük kullanımda ne kadar faydalı |
| **Bağımlılık Hazırlığı** | 25% | Bağlı modüller mevcut mu |
| **Uygulama Kolaylığı** | 20% | Mevcut altyapı ile ne kadar hızlı uygulanabilir |
| **Stratejik Değer** | 20% | Platform differentiation'a katkısı |

### Öncelik Matrisi

| Öncelik | Asistan | Etki | Hazırlık | Kolaylık | Strateji | Skor | Sprint |
|---------|---------|:----:|:--------:|:--------:|:--------:|:----:|--------|
| **P1** | Risk Assessment | 9 | 10 | 9 | 8 | **9.0** | S12a |
| **P2** | Test Case Generator | 9 | 9 | 7 | 9 | **8.5** | S12a |
| **P3** | Change Impact Analyzer | 8 | 8 | 6 | 9 | **7.7** | S12b |
| **P4** | Status Report Generator | 7 | 9 | 8 | 7 | **7.6** | S12b |
| **P5** | Scope Recommender | 7 | 8 | 7 | 7 | **7.2** | S15a |
| **P6** | Go-Live Readiness Checker | 8 | 4 | 5 | 9 | **6.7** | S15a |
| **P7** | Data Migration Advisor | 7 | 3 | 5 | 8 | **5.9** | S15b |
| **P8** | Sprint Planner | 6 | 7 | 6 | 5 | **5.9** | S15b |
| **P9** | Meeting Summarizer | 6 | 7 | 7 | 5 | **6.1** | S19 |
| **P10** | Cutover Planner | 7 | 2 | 4 | 8 | **5.4** | S19 |
| **P11** | Training Recommender | 4 | 5 | 5 | 4 | **4.4** | S21 |

---

## 3. Sprint Ataması (Revize Plan ile Uyumlu)

### S12a — AI Phase 2a: High-Value Quick Wins (2 asistan)

**Risk Assessment** (P1)
- Prompt template zaten var (`risk_assessment.yaml` v2)
- RAID modülü ve modeller hazır
- İhtiyaç: Assistant sınıfı + 2 endpoint + suggestion entegrasyonu
- Tahmini süre: 8 saat
- ROI: Yüksek riskler otomatik tespit + uyarı

**Test Case Generator** (P2)
- Test Hub (S5) ve Requirement modülü (S3) hazır
- İhtiyaç: Assistant sınıfı + prompt + template-based test case generation
- Tahmini süre: 10 saat
- ROI: Her requirement için test case taslağı → QA süresini %40 azaltır

### S12b — AI Phase 2b: Strategic Value (2 asistan)

**Change Impact Analyzer** (P3)
- Traceability engine (S4) hazır
- Cross-entity bağlantılar (requirement_traces tablosu) mevcut
- İhtiyaç: Assistant + graph traversal + impact matrix generation
- Tahmini süre: 12 saat
- ROI: Değişiklik talepleri için otomatik etki analizi

**Status Report Generator** (P4)
- Program modülü + metrics altyapısı hazır
- İhtiyaç: Assistant + reporting template + Markdown çıktı
- Tahmini süre: 8 saat
- ROI: Haftalık/aylık raporlama otomatize

### S15a — AI Phase 3a: Module-Specific (2 asistan)

**Scope Recommender** (P5)
- Scope modülü hazır, Fit/Gap analiz verileri mevcut
- İhtiyaç: Assistant + historical pattern matching
- Tahmini süre: 10 saat

**Go-Live Readiness Checker** (P6)
- S13 (Cutover Hub) tamamlandıktan sonra
- İhtiyaç: Checklist engine + cross-module validation queries
- Tahmini süre: 12 saat

### S15b — AI Phase 3b: Advanced (2 asistan)

**Data Migration Advisor** (P7)
- S10 (Data Factory) tamamlandıktan sonra
- İhtiyaç: Data quality pattern detection + validation rules
- Tahmini süre: 12 saat

**Sprint Planner** (P8)
- Backlog modülü hazır
- İhtiyaç: Capacity model + prioritization algorithm + LLM suggestion
- Tahmini süre: 10 saat

### S19 — AI Phase 4: Mature Platform (2 asistan)

**Meeting Summarizer** (P9)
- Workshop modülü hazır
- İhtiyaç: Long-text summarization + action item extraction
- Tahmini süre: 8 saat

**Cutover Planner** (P10)
- S13 (Cutover Hub) tamamlandıktan sonra
- İhtiyaç: Timeline optimization + dependency-aware scheduling
- Tahmini süre: 12 saat

### S21 — AI Phase 5: Polish (1 asistan)

**Training Recommender** (P11)
- Düşük öncelik, son release'de
- Tahmini süre: 8 saat

---

## 4. Risk Assessment — Hemen Uygulanabilir

Risk Assessment asistanı **en hazır** ve **en acil** olan:

```
Mevcut Durum:
✅ risk_assessment.yaml v2 prompt template hazır
✅ RAID modülü + Risk modeli hazır (S6'da uygulandı)
✅ RAG pipeline hazır (benzer risk tespiti)
✅ Suggestion queue hazır
✅ API endpoint pattern'ı (Defect Triage'dan kopyalanabilir)

Eksikler:
❌ app/ai/assistants/risk_assessment.py (assistant sınıfı)
❌ AI_BP'de risk assessment endpoint'leri
❌ Risk puanlama ve sinyal toplama logic'i

Yaklaşık ihtiyaç: ~6-8 saat
```

**Tavsiye:** Risk Assessment asistanı S10 beklenmeden hemen uygulanabilir. Prompt, model ve altyapı hazır.

---

## 5. Toplam AI Asistan Bütçesi

| Sprint | Asistanlar | Tahmini Süre | Altyapı Hazırlığı |
|--------|-----------|-------------|-------------------|
| S12a | Risk Assessment + Test Case Gen | 18 saat | ✅ Tam hazır |
| S12b | Impact Analyzer + Status Report | 20 saat | ✅ Tam hazır |
| S15a | Scope Recommender + Go-Live Checker | 22 saat | ⚠️ S13 bağımlı |
| S15b | Data Migration + Sprint Planner | 22 saat | ⚠️ S10 bağımlı |
| S19 | Meeting Summarizer + Cutover Planner | 20 saat | ⚠️ S13 bağımlı |
| S21 | Training Recommender | 8 saat | ✅ Bağımsız |
| **Toplam** | **11 asistan** | **~110 saat** | |

---

## 6. Karar Noktaları

| Karar | Seçenekler | Tavsiye |
|-------|-----------|---------|
| Risk Assessment'ı erken mi uygulayalım? | S10 bekle / Hemen uygula | **Hemen** (prompt + model hazır) |
| NL Workflow Builder (orijinal plandaki) gerekli mi? | Evet / Hayır / R6'ya ertele | R6'ya ertele (Training Recommender daha pratik) |
| Embedding backfill ne zaman? | S10 / S12a / Şimdi | **S10 öncesi** (Data Factory için gerekli) |
| A/B testing framework gerekli mi? | Evet / Hayır | **Hayır** — S19'a kadar tek prompt versiyonu yeterli |

---

*Revize Plan (PLAN_REVISION.md) ile uyumlu sprint atamaları kullanılmıştır.*
