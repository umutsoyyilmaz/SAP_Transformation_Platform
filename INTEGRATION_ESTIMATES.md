# Dış Sistem Entegrasyonu — Tahmin Revizyonu

**Document ID:** P4-INTEGRATION-EST  
**Sprint:** 9.5  
**Date:** 2025-02-09

---

## 1. Mevcut Durum Özeti

### İç Entegrasyon Fabrikası (S9 — ✅ Tamamlandı)

| Metrik | Değer |
|--------|-------|
| Model | 5 (Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist) |
| API endpoint | 26 |
| Test fonksiyonu | 76 (24 sınıfta) |
| Traceability zincirleri | 4 entity tipi destekleniyor |
| Protokol tipleri | 11 (RFC, IDoc, BAPI, OData, REST, SOAP…) |

### Dış Entegrasyon Konnektörleri: 0/4 İnşa Edildi

---

## 2. Orijinal Plan vs. Gerçekçi Tahmin

### S22 Orijinal Tahmin: 18 saat — **Çok İyimser**

Orijinal plan 4 dış sisteme (Jira, Cloud ALM, ServiceNow, Teams) + webhook framework + yönetim UI'si için toplam 18 saat tahmin ediyor.

### Gerçekçi Maliyet Analizi

| Görev | Orijinal | Revize | Gerekçe |
|-------|:--------:|:------:|---------|
| **Paylaşımlı Altyapı** | | | |
| REST API istemci soyutlaması (retry, rate-limit, circuit breaker) | 0 saat | **4 saat** | 4 sistemin tümünde gerekli, planlanmamış |
| Webhook framework (gelen + giden + imza doğrulama) | 2 saat | **5 saat** | Güvenlik duyarlı, kripto gerektiriyor |
| Entegrasyon yönetim UI'si (bağlantılar, senkronizasyon logları) | 3 saat | **5 saat** | 4 sistem × durum/yapılandırma/log |
| **Konnektörler** | | | |
| Jira (çift yönlü defect/requirement sync) | 4 saat | **12 saat** | OAuth2, alan eşleme, webhook dinleyici, çakışma çözümleme |
| SAP Cloud ALM (test case sync) | 4 saat | **10 saat** | SAP OData istemcisi, CALM API karmaşık |
| ServiceNow (incident sync) | 3 saat | **8 saat** | REST API, tek yön → Jira'dan basit |
| Teams (toplantı kaydı alma) | 2 saat | **6 saat** | MS Graph API, OAuth2, büyük dosya indirme |
| **Test** | | | |
| Entegrasyon testleri (mock dış API'ler) | (dahil) | **6 saat** | 4 sistem × mock server + senaryo |
| **Toplam** | **18 saat** | **56 saat** | **3.1× orijinal tahmin** |

---

## 3. Bağımlılık Zinciri

```
S9  ✅ Integration Factory (model, API, traceability)
│
├─→ S14 ⬜ Security & Platform Hardening (JWT, RBAC)
│     └─→ Dış API kimlik doğrulama için zorunlu (OAuth2 token exchange)
│
├─→ S18 ⬜ Bildirim + Dış İletişim
│     ├─→ Celery + Redis asenkron altyapı
│     ├─→ Webhook giden framework
│     └─→ Email / Slack / Teams temelleri
│
└─→ S22 ⬜ Dış Sistem Entegrasyonları
      ├─→ Jira: JWT auth (S14) + webhook (S18) + backlog model ✅
      ├─→ Cloud ALM: test modeli (S5 ✅) + auth (S14)
      ├─→ ServiceNow: Run/Sustain modeli (S17) + auth (S14)
      └─→ Teams: Meeting Intelligence (S21) + auth (S14)
```

### Sistem Bazında Hard Dependencies

| Dış Sistem | Model Bağımlılıkları | Altyapı Bağımlılıkları | Sprint Bağımlılıkları |
|-----------|---------------------|----------------------|---------------------|
| **Jira** | BacklogItem ✅, Requirement ✅, Defect ✅ | JWT auth, Celery, webhook | S14, S18 |
| **SAP Cloud ALM** | TestCase ✅, TestExecution ✅, Process ✅ | JWT auth, OData client | S14 |
| **ServiceNow** | Incident, Problem (**inşa edilmedi**) | JWT auth, Celery, REST | S14, S17, S18 |
| **Teams** | Meeting transcripts (**inşa edilmedi**) | OAuth2, Graph API | S14, S21 |

---

## 4. Boşluk Analizi

| Boşluk | Derece | Detay |
|--------|--------|-------|
| Asenkron görev altyapısı yok | 🔴 KRİTİK | Celery + Redis yapılandırılmadı; 4 konnektörün tümü asenkron sync gerektiriyor |
| OAuth2/JWT token değişimi yok | 🔴 KRİTİK | S14 başlamadı; dış API'ler servis-servis auth gerektiriyor |
| Webhook framework yok | 🟠 YÜKSEK | Gelen/giden webhook işleme yok; Jira ve ServiceNow gerçek zamanlı sync için gerekli |
| REST API istemci soyutlaması yok | 🟠 YÜKSEK | Yeniden kullanılabilir HTTP client (retry, rate-limit) yok |
| Run/Sustain modeli yok | 🟠 ORTA | ServiceNow → Incident/Problem modelleri (S17) |
| Meeting Intelligence yok | 🟡 DÜŞÜK | Teams meeting fetch → (S21) |
| Sync çakışma çözümleme stratejisi yok | 🟡 DÜŞÜK | Jira çift yönlü sync → strateji kararı gerekli |

---

## 5. Sprint Yeniden Yapılandırma Önerileri

### Opsiyon A: S22'yi İkiye Böl (⭐ Önerilen)

| Sprint | Hafta | Kapsam | Saat |
|--------|-------|--------|:----:|
| S22a | 52-53 | Paylaşımlı altyapı + Jira entegrasyonu + yönetim UI | ~26 |
| S22b | 54-55 | Cloud ALM + ServiceNow + Teams + entegrasyon testleri | ~30 |

**Etki:** S23 (Mobile PWA) ve S24 (Final Polish) +2 hafta kayar. Toplam: 60 → 62 hafta.

### Opsiyon B: 2 Entegrasyon Öncelikle, 2 Ertelensin

| Sprint | Kapsam | Saat | Gerekçe |
|--------|--------|:----:|---------|
| S22 (hafta 52-53) | Jira + ServiceNow + paylaşımlı altyapı | ~29 | En yüksek müşteri değeri |
| S24+ | Cloud ALM + Teams | ~16 | Düşük öncelik, v1.0 sonrasına |

**Etki:** Timeline değişmez; Cloud ALM ve Teams R6+ stretch goal olur.

### Opsiyon C: Kapsamı Tek Entegrasyona İndir

| Sprint | Kapsam | Saat |
|--------|--------|:----:|
| S22 | Yalnız Jira çift yönlü + paylaşımlı altyapı | ~21 |

**Etki:** Cloud ALM, ServiceNow, Teams v1.0 sonrasına. Önemli kapsam kesintisi.

---

## 6. Erken Yapılması Gereken Eylemler

| # | Eylem | Ne Zaman | Neden |
|---|-------|----------|-------|
| 1 | Webhook framework'ü S18'e taşı | S18 planlaması | S18 zaten Celery+Redis kurulumu yapıyor; webhook temeli burada oluşmalı |
| 2 | API istemci soyutlamasını S14'te prototiple | S14 planlaması | OAuth2 client credential akışları generic HTTP client ile eşlenebilir |
| 3 | Çakışma çözümleme stratejisi belirle | S18 öncesi | Jira çift yönlü sync tasarımı için gerekli (last-write-wins / manual merge / timestamp) |
| 4 | Signavio'yu ayrı tut | — | BPMN import/export (16 saat) mimari olarak farklı; S22 ile birleştirme |
| 5 | Entegrasyon seed verilerini S10'da ekle | S10 planlaması | Interface/Wave/ConnectivityTest kayıtları traceability doğrulaması için |

---

## 7. Signavio Entegrasyonu (Ayrı İz)

| Bileşen | Durum | Tahmini Süre | Bağımlılık |
|---------|-------|:------------:|------------|
| BPMN 2.0 XML parser | Tasarım taslağı hazır | ~8 saat | ScopeItem kararı |
| Signavio REST API connector | Planlı (Faz 2) | ~8 saat | Parser tamamlanması |
| 15 yeni API endpoint | Tasarlandı, inşa edilmedi | Dahil | 5 tasarım kararı bekliyor |

**Tavsiye:** Signavio REST API entegrasyonlarından ayrı tutulmalı. ScopeItem hiyerarşi kararları onaylandıktan sonra başlanabilir.

---

## 8. Özet Tablo

| Boyut | Mevcut | Revize |
|-------|--------|--------|
| S22 orijinal tahmin | 18 saat | **56 saat (3.1×)** |
| Sprint sayısı | 1 (S22) | **2 (S22a + S22b)** |
| Toplam timeline etkisi | +0 hafta | **+2 hafta (62 toplam)** |
| En yüksek risk | — | Celery altyapısı yok (S18 blocker) |
| Acil karar | — | Opsiyon A/B/C seçimi |

---

*PLAN_REVISION.md ile uyumlu olarak revize edilmiştir.*
