# SAP Transformation Platform — 10 Dakika Partner Demo Senaryosu

> **Versiyon:** 1.0 | **Süre:** 10 dakika | **Hedef Kitle:** SAP Partner, Müşteri C-Level, Yatırımcı
>
> **Ön Koşul:** `make seed-demo` çalıştırılmış olmalı (GlobalTech Industries demo verisi)

---

## Demo Hazırlığı (Demo Öncesi)

```bash
# 1. Demo verisini yükle (yoksa)
make seed-demo

# 2. Uygulamayı başlat
make run
# → http://localhost:5001

# 3. Tarayıcıda aç — Dashboard görünmeli
```

**Tarayıcı:** Chrome (tam ekran, developer tools kapalı)
**Not:** Demo boyunca her ekranda 2-3 saniye bekleyin, kitleye zaman tanıyın.

---

## Dakika 0–1: Açılış & Platform Tanıtımı

### Söylem
> "SAP S/4HANA dönüşüm projelerini uçtan uca yönetmek için geliştirdiğimiz
> platformu gösteriyorum. Bugün GlobalTech Industries'ın ECC'den S/4HANA Cloud'a
> geçişini örnek alacağız — 3.200 çalışan, 4 fabrika, €1.2B ciro."

### Ekran: Dashboard
1. **Sol menüden Dashboard'u** gösterin
2. Program özeti: faz durumları, ilerleme yüzdeleri
3. KPI kartları: gereksinim sayıları, test coverage, defect metrikleri
4. "Platform SAP Activate metodolojisini doğrudan destekliyor" deyin

---

## Dakika 1–3: Explore Phase — Fit-to-Standard

### Söylem
> "Explore fazında SAP standart süreçlerini iş süreçleriyle karşılaştırıyoruz.
> Buna Fit-to-Standard diyoruz."

### Ekran: Explore → Process Hierarchy
1. **Explore** menüsüne tıklayın
2. **Process Hierarchy** sekmesi → L1-L4 ağaç yapısını gösterin
   - L1: Enterprise (SAP S/4HANA)
   - L2: OTC, PTP, FIN, P2M alanları
   - L3: Her alan altında 4 süreç (örn. OTC-10 Sales Inquiry)
   - L4: Alt süreçler (örn. OTC-10-01 Create Sales Inquiry)
3. "Her süreç seviyesinde scope/fit kararları alınıyor" deyin

### Ekran: Explore → Workshops
4. **Workshops** sekmesine geçin
5. **WS-SD-01** (OTC Fit-to-Standard) workshop'unu açın
   - Katılımcılar: 4 kişi (BPO, Module Lead, Facilitator, PM)
   - Scope items: L3 süreçlere bağlı
   - Agenda: 5 madde, her biri 30dk
   - Process Steps: Her L4'e fit/gap kararı
6. "Workshop'lar yapılandırılmış — her adımda karar kaydediliyor" deyin

### Ekran: Explore → Requirements
7. **Requirements** sekmesine geçin
8. 10 gereksinimi gösterin:
   - Farklı statüler: draft → under_review → approved → in_backlog
   - Farklı tiplr: functional, enhancement
   - Öncelikler: P1, P2, P3
9. **REQ-001** (Configurable Pricing Conditions) detayına girin
10. "Gereksinimler workshop'lardan otomatik oluşuyor, yaşam döngüsü izlenebilir" deyin

### Ekran: Explore → Open Items & Decisions
11. **Open Items** sekmesine geçin → 4 açık madde
12. **Decisions** sekmesine geçin → 4 karar kaydı
13. "Her açık madde bir gereksinime bağlı, çözüm süreci takip ediliyor" deyin

---

## Dakika 3–5: Backlog & Sprint Management

### Söylem
> "Onaylanan gereksinimler otomatik olarak WRICEF backlog'una dönüşüyor."

### Ekran: Backlog → Board
1. **Backlog** menüsüne tıklayın
2. **Board** görünümünü gösterin
   - Sprint 1 aktif: 6 WRICEF item
   - Tipler: ENH (Enhancement), INT (Interface), RPT (Report), WFL (Workflow)
   - Statüler: open, in_progress
3. **ENH-001** (Pricing Condition Enhancement) kartına tıklayın
   - Gereksinime bağlantı (REQ-001)
   - Öncelik, Story Points, atanmış kişi
4. "WRICEF tiplemesi SAP standartlarına uygun — W/R/I/C/E/F" deyin

### Ekran: Backlog → Config Items
5. **Config Items** sekmesine geçin → 4 konfigürasyon maddesi
6. "SAP konfigürasyonu ayrıca takip ediliyor — IMG activity'leri, transport request'ler" deyin

---

## Dakika 5–7: Test Management

### Söylem
> "Realize fazında test yönetimi kritik. Platform SIT, UAT, regression katmanlarını
> destekliyor."

### Ekran: Testing → Test Plan
1. **Testing** menüsüne tıklayın
2. **Test Plans** → "SIT Cycle 1 — OTC + PTP" aktif planı gösterin
3. **Test Cycle** → SIT Cycle 1 detayına girin

### Ekran: Testing → Test Cases
4. **Test Cases** sekmesine geçin → 10 test case
   - SD modülü: 4 TC (Sales Order, Credit Check, E-Invoice, ATP)
   - MM modülü: 4 TC (PR Flow, 3-Way Match, Approval, Consignment)
   - Integration: 1 TC (Credit Integration E2E)
   - Regression: 1 TC (Pricing Regression Suite)
5. Her test case'in gereksinimlere bağlı olduğunu gösterin

### Ekran: Testing → Executions & Defects
6. **Executions** → 8 execution sonucu:
   - 5 pass ✅, 2 fail ❌, 1 blocked ⛔
7. **Defects** → 3 defect:
   - DEF-001: Pricing Rounding Error (S2)
   - DEF-002: 3-Way Match False Reject (S2)
   - DEF-003: Credit Check Timeout (S1 — critical!)
8. "S1 defect otomatik olarak dashboard'da kırmızı bayrak, SLA takibi var" deyin

---

## Dakika 7–8: RAID Management

### Söylem
> "Proje risklerini, aksiyonları, issues ve kararları tek ekrandan yönetiyoruz."

### Ekran: RAID
1. **RAID** menüsüne tıklayın
2. **Risks** sekmesi:
   - R-001: E-Invoice Compliance Delay (High Impact)
   - R-002: Data Migration Volume (Medium)
   - R-003: Key User Availability (High)
3. **Actions** sekmesi: 3 aksiyon (1 tamamlanmış, 1 devam eden, 1 açık)
4. **Issues**: SAP BTP Workflow license pending
5. **Decisions**: SAP Analytics Cloud for reporting — approved
6. "Risk skoru otomatik hesaplanıyor, RAG status renk kodlu" deyin

---

## Dakika 8–9: Metrikleri & Raporlama

### Söylem
> "Tüm bu veriler gerçek zamanlı metriklere dönüşüyor."

### Ekran: Dashboard / Metrics
1. **Dashboard**'a geri dönün
2. Gösterin:
   - Explore ilerlemesi: % workshop tamamlanma
   - Backlog velocity: Sprint 1 durumu
   - Test coverage: gereksinim → test case mapping
   - Defect trend: severity dağılımı
   - RAID özeti: açık risk sayısı
3. "C-Level raporlaması için tek bakışta proje sağlığı" deyin

---

## Dakika 9–10: Kapanış & Differentiators

### Söylem
> "Son olarak platformun öne çıkan özelliklerini özetliyorum."

### Tema Noktaları (slide veya sözlü)

| # | Özellik | Açıklama |
|---|---------|----------|
| 1 | **SAP-Native** | SAP Activate, WRICEF, Fit-to-Standard doğrudan destekleniyor |
| 2 | **Uçtan Uca** | Explore → Realize → Test → Go-Live tek platformda |
| 3 | **Traceability** | Gereksinim → Backlog → Test Case → Defect tam izlenebilirlik |
| 4 | **Multi-Tenant** | Her müşteri izole DB, tek platform instance |
| 5 | **AI-Ready** | Google Gemini entegrasyonu — requirement analizi, test üretimi |
| 6 | **Docker-Ready** | `docker compose up` ile 5 dakikada production |
| 7 | **Türkçe & İngilizce** | Dual-language UI ve dokümantasyon |

### Kapanış
> "Platform şu an pilot aşamasında. İlk müşteriyle 30 dakikada ortam
> kurulabilir. Demo verisini gördünüz — gerçek proje verisiyle aynı
> akış çalışıyor. Sorularınız?"

---

## Demo Sonrası Teklif Akışı

1. **Hemen sonra:** Demo ortamına erişim linki paylaş
2. **1 gün içinde:** Müşteriye özel PoC planı gönder
3. **1 hafta içinde:** Pilot kurulum teklifi

---

## Olası Sorular & Cevaplar

| Soru | Cevap |
|------|-------|
| "SAP Solution Manager'dan farkı ne?" | SolMan on-premise, yavaş. Bu platform cloud-native, modern UX, AI-destekli. |
| "Kaç kullanıcı destekliyor?" | Multi-tenant mimari, tenant başına sınırsız kullanıcı. |
| "Mevcut SAP sistemimizle entegre olur mu?" | API-first mimari. Integration module ile RFC/BAPI/OData/IDoc destekli. |
| "Veri güvenliği nasıl?" | Tenant izolasyonu (ayrı DB), RBAC, audit trail, Docker secrets. |
| "Fiyatlandırma?" | Tenant başına lisans + kullanıcı bazlı model (pilot ücretsiz). |
| "Hangi SAP ürünlerini destekliyor?" | S/4HANA Cloud/On-Premise, ECC → S/4HANA migration, SuccessFactors, BTP. |

---

*Bu demo senaryosu `make seed-demo` ile oluşturulan GlobalTech Industries demo verisiyle çalışır.*
