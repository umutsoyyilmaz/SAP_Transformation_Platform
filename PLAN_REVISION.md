# Plan Revizyonu & Buffer Analizi

**Document ID:** P6-PLAN-REVISION  
**Sprint:** 9.5 (Post-Sprint 9 Analiz)  
**Date:** 2025-02-09

---

## 1. Mevcut Plan Sorunları

### Kritik Bulgular

| # | Sorun | Önem | Kanıt |
|---|-------|------|-------|
| 1 | **Sıfır tampon süresi** — Sprint/Release arası buffer yok | 🔴 | 48 hafta, hiç boşluk yok |
| 2 | **%30-40 planlanmamış iş** — Revizyon R1, R2, Analysis Hub, Hierarchy Refactoring, Workshop, Code Review | 🔴 | 6 büyük deliverable plan dışı |
| 3 | **S12 aşırı yüklü** — 4 AI asistan tek sprint'te (30 saat) | 🟠 | Her asistan ~7.5 saat → yetmez |
| 4 | **S15 aşırı yüklü** — 4 AI asistan tek sprint'te (27 saat) | 🟠 | Aynı pattern |
| 5 | **Güvenlik S14'te** — Platform 6 ay auth'suz çalışıyor | 🟠 | Kısmen Code Review'da çözüldü |
| 6 | **39 çözülmemiş code review bulgusu** — Sprint ayrılmamış | 🟡 | 67 bulgu, 28 çözüldü |
| 7 | **Velocity verisi güvenilmez** — 18 haftalık iş 3 günde bitti | 🟡 | Sürdürülebilir hız ölçülmedi |
| 8 | **UAT/dış doğrulama yok** — Tüm gate'ler self-assessed | 🟡 | Rollback kriteri yok |

### Gerçekleşen Plansız İşler (S1-S9)

| İş | Sprint | Plansa | Etki |
|----|--------|--------|------|
| Revision R1: Program Selector → Context-Based | Post-S2 | ❌ | +438/-213 lines |
| Revision R2: Scenario → İş Senaryosu + Workshop | Post-S3 | ❌ | +1320/-703 lines |
| Analysis Hub: 4-tab view | Post-S3 | ❌ | +1908 lines, 5 endpoint |
| Hierarchy Refactoring: L1/L2/L3 + N:M | Post-S3 | ❌ | ScopeItem removed, model redesign |
| Workshop Enhancements: Documents, L3 creation | Post-S3 | ❌ | 4 new endpoint |
| Code Review & Hardening: 28/67 fix | Post-S9 | ❌ | Güvenlik + performans |
| Monitoring & Observability | Post-S9 | ❌ | Health + Metrics + Logging |
| Test Strategy Expansion | Post-S9 | ❌ | Integration + Performance tests |
| Git Workflow + Hooks | Post-S9 | ❌ | Commit validation |

**Sonuç:** Tamamlanan 9 sprint'in ~%35'i planlanmamış rework.

---

## 2. Revize Edilmiş Zaman Çizelgesi

### Eklenen Buffer ve Düzeltmeler

| Değişiklik | Etki |
|-----------|------|
| Her Release sonrası **1 hafta buffer** | +6 hafta |
| S12 → S12a + S12b (2 + 2 AI asistan) | +2 hafta |
| S15 → S15a + S15b (2 + 2 AI asistan) | +2 hafta |
| **S9.5: Tech Debt Sprint** (kalan code review + iyileştirmeler) | +2 hafta |
| Her sprint'e **%20 rework bütçesi** | Kapsam azaltma (sprint başına ~3 saat) |
| **Toplam ek süre** | **+12 hafta → 48 → 60 hafta (~15 ay)** |

### Yeni Sprint Haritası

```
RELEASE 2 (TAMAMLANDI) ✅
─────────────────────────
S1-S8  ✅  (Hafta 1-16)
R2 Gate ✅

RELEASE 3 (DEVAM EDİYOR) 🔄
────────────────────────────
S9    ✅  Integration Factory (Hafta 17-18)
S9.5  🔄  Tech Debt & Hardening (Hafta 19-20)          ← YENİ
S10   ⬜  Data Factory (Hafta 21-22)
S11   ⬜  Reporting Engine (Hafta 23-24)
S12a  ⬜  AI Phase 2a: Steering Pack + Risk Sentinel (Hafta 25-26)  ← BÖLÜNDÜ
S12b  ⬜  AI Phase 2b: WBS + WRICEF Drafter (Hafta 27-28)           ← BÖLÜNDÜ
      🔲  R3 BUFFER (Hafta 29)                         ← YENİ

R3 Gate (Hafta 29)

RELEASE 4
─────────
S13   ⬜  Cutover Hub (Hafta 30-31)
S14   ⬜  Security & Platform Hardening (Hafta 32-33)
S15a  ⬜  AI Phase 3a: Test Gen + Data Guardian (Hafta 34-35)       ← BÖLÜNDÜ
S15b  ⬜  AI Phase 3b: Impact Analyzer + Defect Triage+ (Hafta 36-37) ← BÖLÜNDÜ
S16   ⬜  AI Risk Sentinel ML + Polish (Hafta 38-39)
      🔲  R4 BUFFER (Hafta 40)                         ← YENİ

R4 Gate (Hafta 40)

RELEASE 5
─────────
S17   ⬜  Run/Sustain Module (Hafta 41-42)
S18   ⬜  Notification + External Comms (Hafta 43-44)
S19   ⬜  AI Phase 4: Cutover Optimizer + Hypercare (Hafta 45-46)
S20   ⬜  AI Performance + Polish (Hafta 47-48)
      🔲  R5 BUFFER (Hafta 49)                         ← YENİ

R5 Gate (Hafta 49)

RELEASE 6
─────────
S21   ⬜  AI Phase 5: Meeting Intelligence + NL Workflow (Hafta 50-51)
S22   ⬜  External Integrations (Hafta 52-53)
S23   ⬜  Mobile PWA + Multi-Program (Hafta 54-55)
S24   ⬜  Final Polish + Launch Prep (Hafta 56-57)
      🔲  R6 BUFFER + UAT (Hafta 58-59)                ← YENİ

R6 Gate / Platform v1.0 (Hafta 60)
```

### Önceki vs Yeni Karşılaştırma

| Metrik | Önceki Plan | Revize Plan |
|--------|------------|-------------|
| Toplam Süre | 48 hafta (12 ay) | 60 hafta (15 ay) |
| Sprint Sayısı | 24 | 28 (S9.5, S12a/b, S15a/b) |
| Buffer Haftaları | 0 | 6 (Release arası 4 + R6 UAT 2) |
| Rework Bütçesi | 0% | 20% per sprint (~3 saat) |
| AI Sprint Max | 4 asistan/sprint | 2 asistan/sprint |
| Go-Live Tarihi | Hafta 48 (~Ocak 2027) | Hafta 60 (~Nisan 2027) |

---

## 3. Sprint 9.5 — Tech Debt Sprint (Mevcut)

### Scope (2 Hafta, ~30 saat)

| Görev | Durum | Sprint |
|-------|-------|--------|
| P5: Progress Report tutarsızlıkları | ✅ | 9.5a |
| P10: Monitoring & Observability | ✅ | 9.5a |
| P2: Git Workflow & Hooks | ✅ | 9.5a |
| P8: Test Strategy genişlet | ✅ | 9.5b |
| P1: Frontend karar analizi | ✅ | 9.5b |
| P3: Dev/Prod DB tutarsızlığı | ✅ | 9.5b |
| P6: Plan revizyonu & buffer | 🔄 | 9.5b |
| P7: AI asistan önceliklendirme | ⬜ | 9.5c |
| P4: Dış entegrasyon tahmin revize | ⬜ | 9.5c |
| P9: Knowledge Base versiyonlama | ⬜ | 9.5c |

---

## 4. Velocity Tracking Tavsiyesi

### Sürdürülebilir Hız Ölçümü

S10'dan itibaren her sprint için gerçek saatleri takip edin:

```
Sprint: S10
Planlanan: 16 saat
Gerçekleşen: __ saat
Rework: __ saat (%__)
Tamamlanan Görev: __/__ (%__)
Yeni Testler: __
Toplam Test: __
Notlar: ___
```

3 sprint sonra (S10-S12a) ortalama velocity hesaplanır, R4-R6 tarihleri buna göre revize edilir.

---

## 5. Revize Gate Kriterleri

Her Release Gate'e eklenmesi gerekenler:

| Kriter | Açıklama |
|--------|----------|
| ✅ Tüm mevcut testler geçiyor | Sadece coverage değil, **%100 pass rate** |
| ✅ Yeni modülün integration testi var | En az 3 cross-module senaryo |
| ✅ Performance threshold | API yanıt süresi < 500ms (%95 percentile) |
| ✅ Güvenlik taraması | Bilinen vulnerability yok |
| ✅ Regression pass | Önceki release'in tüm testleri geçiyor |
| ✅ Monitoring live | Health check + metrics endpoint çalışıyor |

### Rollback Kriterleri (Yeni)

| Kriter | Aksiyon |
|--------|---------|
| >5 test fail | Sprint uzat, commit revert |
| Güvenlik açığı (Critical) | Immediate hotfix, sprint pause |
| Data loss riski | Full stop, backup verify |
| API p95 > 2000ms | Performance sprint ekle |

---

## 6. Bağımlılık Zinciri Analizi

```
S7 (AI Infra) ──→ S8 (AI P1) ──→ S12a/b (AI P2) ──→ S15a/b (AI P3) ──→ S19 (AI P4) ──→ S21 (AI P5)
     ↓
S4 (Traceability v1) ──→ S5 (Test) ──→ S9 (Integration) ──→ S13 (Cutover)
                                           ↓
                          S10 (Data Factory) ──→ S15a (Data Guardian)
                                                      ↓
S6 (Notification) ────────────────────→ S18 (External Comms)

S11 (Reporting) ──→ S12a (Steering Pack)

S13 (Cutover) ──→ S19 (Cutover Optimizer)

S14 (Security) ⚠ BLOCKER: R4'e kadar auth yok
```

**Kritik yol:** S7 → S8 → S12a/b → S15a/b → S19 → S21 (AI pipeline)  
**En riskli geçiş:** S11 → S12a (Reporting → Steering Pack, back-to-back)

---

## 7. Karar Logu

| Tarih | Karar | Etkisi |
|-------|-------|--------|
| 2025-02-09 | Plan 48 → 60 haftaya uzatıldı | Go-live Nisan 2027 |
| 2025-02-09 | S12, S15 bölündü (2+2 AI asistan) | Sprint başına risk azaldı |
| 2025-02-09 | Her release sonrası 1 hafta buffer eklendi | Rework kapasitesi arttı |
| 2025-02-09 | S9.5 Tech Debt sprint'i tanımlandı | 10 iyileştirme prompt'u çözülüyor |
| 2025-02-09 | Gate kriterlerine regression + performance eklendi | Release kalitesi arttı |

---

*Bu doküman S10 başlangıcında velocity verisiyle güncellenecektir.*
