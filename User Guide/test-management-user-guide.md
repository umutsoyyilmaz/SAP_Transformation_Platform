# ProjektCoPilot — Test Management System
## Kullanıcı Rehberi v1.0

---

**Ürün:** ProjektCoPilot — Test Management System  
**Versiyon:** 1.0  
**Tarih:** 2026-02-10  
**Hedef Kitle:** Test Lead, Module Lead, Facilitator, BPO, Tester, PM  
**İlgili Dokümanlar:** Test Management FS/TS v1.0, Explore Phase FS/TS v1.1

---

## İçindekiler

1. [Giriş ve Genel Bakış](#1-giriş-ve-genel-bakış)
2. [Sisteme Erişim ve Roller](#2-sisteme-erişim-ve-roller)
3. [Module T1: Test Plan & Strategy](#3-module-t1-test-plan--strategy)
4. [Module T2: Test Suite Manager](#4-module-t2-test-suite-manager)
5. [Module T3: Test Execution](#5-module-t3-test-execution)
6. [Module T4: Defect Tracker](#6-module-t4-defect-tracker)
7. [Module T5: Test Dashboard](#7-module-t5-test-dashboard)
8. [Module T6: Traceability Matrix](#8-module-t6-traceability-matrix)
9. [Explore Phase'den Test'e Geçiş](#9-explore-phaseden-teste-geçiş)
10. [Cloud ALM Senkronizasyonu](#10-cloud-alm-senkronizasyonu)
11. [Sık Sorulan Sorular (SSS)](#11-sık-sorulan-sorular)
12. [Kısaltmalar ve Terimler](#12-kısaltmalar-ve-terimler)

---

## 1. Giriş ve Genel Bakış

### 1.1 Bu Rehber Kimin İçin?

Bu rehber, ProjektCoPilot platformundaki Test Management System'i kullanacak tüm proje ekibi üyeleri için hazırlanmıştır. Rolünüze göre hangi bölümlere öncelik vermeniz gerektiğini aşağıdaki tablodan görebilirsiniz:

| Rolünüz | Öncelikli Bölümler |
|---------|-------------------|
| **Test Lead** | Tüm bölümler — özellikle T1, T4, T5 |
| **Module Lead** | T2 (kendi alanınız), T3 (execution), T4 (defect) |
| **BPO (Business Process Owner)** | T3 (UAT execution), T4 (defect review), T6 (traceability) |
| **Tester** | T3 (execution), T4 (defect oluşturma) |
| **PM (Program Manager)** | T1 (strateji), T5 (dashboard), T6 (traceability) |
| **Facilitator / Consultant** | T2 (test case yazımı), T3 (execution) |

### 1.2 Test Management System Nedir?

Test Management System, SAP S/4HANA projelerinde Explore Phase'den çıkan tüm gereksinimlerin (requirement), WRICEF/Config item'larının ve iş süreçlerinin sistematik olarak test edilmesini sağlayan modüldür.

Sistem 6 test seviyesini kapsar:

```
┌─────────────────────────────────────────────────────────────────┐
│                    6 TEST SEVİYESİ                               │
│                                                                  │
│  1. UNIT TEST        Tekil nesne doğrulama (WRICEF/Config)      │
│  2. STRING TEST      Modül içi süreç zinciri                     │
│  3. SIT              Modüller arası uçtan uca entegrasyon        │
│  4. UAT              İş kullanıcısı kabul testi                  │
│  5. REGRESSION       Mevcut süreçlerin korunması                 │
│  6. PERFORMANCE      Yük altında sistem davranışı                │
│                                                                  │
│  + DEFECT MANAGEMENT (tüm seviyeleri kesen hata yönetimi)       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Test Management ve Explore Phase İlişkisi

Test Management, Explore Phase'in doğrudan devamıdır. Explore'da oluşturulan her çıktı, test sürecinin girdisidir:

```
EXPLORE PHASE'DE NE YAPTINIZ?              TEST'TE NE OLACAK?
──────────────────────────────              ──────────────────
Workshop'ta fit kararı verdiniz        →   SIT ve UAT senaryoları oluşur
Requirement oluşturdunuz               →   Test case'ler buna bağlanır
WRICEF Item tanımladınız               →   Unit test otomatik üretilir
Config Item tanımladınız               →   Unit test otomatik üretilir
E2E süreç akışı çizdiniz               →   SIT senaryosu bu akışı test eder
BPO olarak süreci onayladınız          →   UAT'ta siz tekrar test edeceksiniz
```

### 1.4 Navigasyon

Test Management System'e sol menüden **Test Mgmt** sekmesine tıklayarak erişirsiniz. Altında 6 alt ekran bulunur:

```
Test Mgmt
  ├── T1: Plan & Strategy       (test planı ve strateji)
  ├── T2: Suite Manager          (test case yönetimi)
  ├── T3: Execution              (test koşma)
  ├── T4: Defect Tracker         (hata takibi)
  ├── T5: Dashboard              (KPI ve Go/No-Go)
  └── T6: Traceability           (izlenebilirlik matrisi)
```

---

## 2. Sisteme Erişim ve Roller

### 2.1 Roller ve Yetkiler

Test Management System, Explore Phase'deki 7 role ek olarak **Test Lead** rolünü tanımlar. Her rolün neyi yapabilip yapamayacağı aşağıdadır:

| İşlem | PM | Module Lead | Test Lead | BPO | Tester | Facilitator | Tech Lead |
|-------|:--:|:----------:|:---------:|:---:|:------:|:----------:|:---------:|
| Test planı oluştur/düzenle | ✓ | — | ✓ | — | — | — | — |
| Test planı onayla | ✓ | — | — | — | — | — | — |
| Test suite oluştur | ✓ | ✓* | ✓ | — | — | — | — |
| Test case oluştur/düzenle | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Test case onayla | ✓ | ✓* | ✓ | — | — | — | — |
| Test koş (execute) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Defect oluştur | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Defect ata (assign) | ✓ | ✓* | ✓ | — | — | — | — |
| Defect çöz (resolve) | ✓ | ✓ | — | — | — | ✓ | ✓ |
| Defect retest yap | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Defect kapat (close) | ✓ | ✓ | ✓ | — | — | — | — |
| UAT sign-off ver | ✓ | — | — | ✓ | — | — | — |
| Dashboard export | ✓ | ✓ | ✓ | ✓ | — | — | — |

*\* Module Lead: yalnızca kendi process area'sında*

### 2.2 Kimin Ne Zaman Hangi Ekranı Kullanacağı

**Test Lead — Günlük rutin:**
1. T5 Dashboard → genel durum kontrolü, Go/No-Go kırmızıları
2. T4 Defect Tracker → yeni defect'leri triage et (severity, priority, atama)
3. T3 Execution → devam eden test run'ların ilerlemesi
4. T1 Plan → test takvimini güncelle

**Module Lead (örn. FI Lead) — Günlük rutin:**
1. T4 → kendi alanına atanmış defect'ler
2. T2 → test case'lerin onay durumu
3. T3 → kendi alanındaki test execution ilerlemesi

**BPO — UAT döneminde:**
1. T3 → UAT senaryolarını koş
2. T4 → bulduğu sorunları defect olarak aç
3. UAT sign-off → "Bu süreci kabul ediyorum" onayını ver

**Tester — Günlük rutin:**
1. T3 → atanmış test case'leri koş
2. T4 → başarısız adımlar için defect oluştur
3. T4 → çözülmüş defect'leri retest et

---

## 3. Module T1: Test Plan & Strategy

### 3.1 Ne Yapılır?

Test Plan, projenin test stratejisinin merkezi dokümanıdır. Proje başına tek bir test planı oluşturulur. Test planı şunları tanımlar:

- Hangi test seviyeleri uygulanacak?
- Her seviye için giriş ve çıkış kriterleri nelerdir?
- Hangi ortamlar (DEV, QAS, PRD) kullanılacak?
- Test takvimi nasıl?
- Roller ve sorumluluklar

### 3.2 Test Planı Oluşturma

**Yol:** Test Mgmt → T1: Plan & Strategy → "+ Test Plan Oluştur"

**Adımlar:**

1. **Plan bilgilerini girin:**
   - Plan adı (örn. "Arçelik S/4HANA Test Planı")
   - Versiyon (örn. "1.0")

2. **Strateji dokümanını yazın:** Strategy sekmesinde Markdown editörü açılır. Burada test yaklaşımınızı, riskleri, araçları ve kapsam dışı kalan alanları belgeleyebilirsiniz.

3. **Ortam matrisini doldurun:** Environments sekmesinde her test seviyesi için hangi ortamda test yapılacağını belirleyin:

   | Test Seviyesi | Ortam | Notlar |
   |--------------|-------|--------|
   | Unit Test | DEV | Developer kendi ortamında |
   | String Test | QAS | Transport sonrası |
   | SIT | QAS | Integration testi |
   | UAT | QAS | İş kullanıcısı ortamı |
   | Regression | QAS | Otomatik koşulabilir |
   | Performance | QAS (veya özel) | Yük testi ortamı |

4. **Giriş/çıkış kriterlerini tanımlayın:** Criteria sekmesinde her seviye için koşulları belirleyin. Sistem varsayılan kriterleri önceden doldurur, ihtiyaca göre düzenleyebilirsiniz.

5. **Onaya gönderin:** "Onaya Gönder" butonuna tıklayın. PM onayladığında plan `approved` durumuna geçer.

### 3.3 Test Takvimi

Calendar sekmesinde test döngülerinin (cycle) zaman çizelgesini görürsünüz. Bu, bir Gantt benzeri görünümdür:

```
              Hafta 1   Hafta 2   Hafta 3   Hafta 4   Hafta 5   Hafta 6
Unit Test     ████████████
String Test              ██████████
SIT                               ████████████
UAT                                          ████████████
Regression                                              ████████
Performance                       ████████████████████████████████
```

Her çubuk bir test döngüsüdür (test_cycle). Çubuğa tıkladığınızda döngünün detayına gidersiniz.

### 3.4 Test Döngüsü (Cycle) Oluşturma

**Yol:** T1: Plan → "+ Döngü Oluştur"

Test döngüsü, belirli bir test seviyesinin belirli bir zaman dilimindeki yürütme penceresidir. Örneğin "Wave 1 — SIT Cycle 1".

**Alanlar:**
- **Kod:** Otomatik atanır (TC-001, TC-002, ...)
- **İsim:** Açıklayıcı isim (örn. "Wave 1 — SIT Cycle 1")
- **Test seviyesi:** Unit, String, SIT, UAT, Regression, Performance
- **Wave:** Hangi wave'e ait (1, 2, 3, 4)
- **Planlanan başlangıç/bitiş:** Takvim seçimi
- **Atanmış suite'ler:** Bu döngüde koşulacak test suite'leri seçin

**Döngü başlatma:**
"Başlat" butonuna tıkladığınızda sistem giriş kriterlerini kontrol eder. Kriterler karşılanmıyorsa uyarı verir. `force=true` ile atlayabilirsiniz, ancak bu kayıt altına alınır.

---

## 4. Module T2: Test Suite Manager

### 4.1 Kavramlar

Test yönetiminin yapı taşları şu hiyerarşidedir:

```
Test Plan (proje genelinde 1 adet)
  └── Test Suite (seviye + alan bazlı gruplandırma)
        └── Test Case (bireysel test senaryosu)
              └── Test Step (sıralı test adımları)
```

**Test Suite** = test case'lerin mantıksal gruplandırmasıdır. Her suite tek bir test seviyesine aittir.

**Örnek suite'ler:**
- TS-UT-001: "FI — Unit Tests — Financial Closing"
- TS-SIT-003: "O2C End-to-End — Order to Cash"
- TS-UAT-008: "SD — Happy Path — Domestic Sales"
- TS-REG-002: "MM — Regression Suite — Procurement"

### 4.2 Suite Oluşturma

**Yol:** Test Mgmt → T2: Suite Manager

Ekranın üstünde 6 sekme bulunur — her biri bir test seviyesidir:

```
[Unit] [String] [SIT] [UAT] [Regression] [Performance]
```

İstediğiniz seviyeye tıklayın, ardından "+ Suite Oluştur" butonuna basın.

**Alanlar:**
- **İsim:** Açıklayıcı (örn. "FI — Unit Tests — GL Posting")
- **Test seviyesi:** Seçili sekmeden otomatik
- **Process area:** FI, SD, MM, PP, QM, ... (dropdown)
- **Wave:** 1, 2, 3, 4
- **Scope item:** Explore Phase'deki L3 scope item'a bağlantı (opsiyonel)
- **E2E senaryo:** O2C, P2P, R2R, H2R, ... (SIT ve UAT için)
- **Risk seviyesi:** Critical, High, Medium, Low (regression için)
- **Owner:** Suite sahibi (kişi)

### 4.3 Test Case Oluşturma — Manuel Yöntem

**Yol:** T2 → İlgili suite → "+ Test Case Oluştur"

**Alanlar:**

| Alan | Açıklama | Zorunlu |
|------|----------|---------|
| Başlık | Test case'in kısa açıklaması | Evet |
| Açıklama | Detaylı açıklama | Hayır |
| Öncelik | P1 (en yüksek) — P4 (en düşük) | Evet (varsayılan: P2) |
| Ön koşullar | Test öncesi ne olmalı? | Hayır |
| Test verisi | Hangi veriler kullanılacak? | Hayır |
| Tahmini süre | Koşma süresi (dakika) | Hayır |
| UAT kategorisi | Sadece UAT: Happy Path, Exception, Negative, Day-in-Life, Period-End | UAT için evet |
| Regression risk | Sadece Regression: Critical, High, Medium, Low | Regression için evet |
| Perf. test tipi | Sadece Performance: Load, Stress, Volume, Endurance, Spike | Performance için evet |

**Traceability bağlantıları (kritik!):**
- **Requirement:** Explore'daki hangi requirement'a bağlı?
- **WRICEF Item:** Hangi WRICEF item'ı test ediyor?
- **Config Item:** Hangi config item'ı test ediyor?
- **Process Level:** Hangi L3/L4 scope item/sub-process'e bağlı?

Bu bağlantıları kurmak zorunlu değildir ama **güçlü önerilir**. Bağlantı yoksa Traceability Matrix'te gap olarak görünür.

### 4.4 Test Adımları (Steps) Yazma

Test case oluşturduktan sonra, adımlarını tanımlamanız gerekir. Her adım için:

| # | Alan | Açıklama | Örnek |
|---|------|----------|-------|
| 1 | **Aksiyon** | Tester ne yapacak? | "VA01 ile satış siparişi oluştur" |
| 2 | **Beklenen sonuç** | Ne olmalı? | "Sipariş numarası oluşur, status Open" |
| 3 | **Test verisi** | Hangi veri? | "Müşteri: 1000001, Malzeme: FG-001, Miktar: 100" |
| 4 | **SAP transaction** | T-code | "VA01" |
| 5 | **Modül** | Cross-module ise | "SD" |
| 6 | **Checkpoint?** | Kritik doğrulama noktası mı? | ☑ Evet |

**Adım yazma ipuçları:**
- Her adımı atomik tutun — tek bir aksiyon, tek bir doğrulama.
- Beklenen sonucu kesin yazın — "Doğru çalışmalı" değil, "Sipariş numarası 10 haneli oluşmalı, status Open olmalı."
- Checkpoint işaretini integration noktalarında kullanın (modül geçişleri, interface çağrıları).

### 4.5 Test Case Otomatik Üretimi — Explore Phase'den

Bu, sistemin en güçlü özelliklerinden biridir. Explore Phase'de tanımladığınız WRICEF/Config item'ları ve süreç adımlarından otomatik test case üretebilirsiniz.

#### 4.5.1 WRICEF/Config'den Unit Test Üretimi

**Yol:** T2 → Unit sekmesi → İlgili suite → "WRICEF'ten Üret" butonu

**Ne olur:**
1. Bir dialog açılır, projenizdeki WRICEF ve Config item'ları listelenir.
2. Unit test üretmek istediğiniz item'ları seçin.
3. "Üret" butonuna tıklayın.
4. Sistem, her WRICEF/Config item'ın `unit_test_steps` alanını okur (bu alan Explore Phase'de FS/TS yazarken doldurulmuştur).
5. Her item için en az 1 test case oluşturulur, adımlar otomatik doldurulur.
6. Test case `draft` statüsünde oluşur — review edip onaylamanız gerekir.

**Örnek:**
```
WRICEF Item: WRICEF-042 (Report — GL Trial Balance)
  unit_test_steps:
    1. Report'u çalıştır (t-code: ZFI_TRIAL)
    2. Company Code filtresi uygula
    3. Tarih aralığı seç
    4. Sonuçları doğrula — bakiye tutarlılığı

    → Otomatik oluşturulan Test Case: UT-042
      Başlık: "Unit Test — GL Trial Balance Report"
      4 adım otomatik doldurulur
      requirement_id, wricef_item_id otomatik bağlanır
```

#### 4.5.2 Process Step'lerden SIT/UAT Üretimi

**Yol:** T2 → SIT veya UAT sekmesi → İlgili suite → "Süreçten Üret" butonu

**Ne olur:**
1. Bir dialog açılır, Explore Phase'deki scope item'lar (L3) listelenir.
2. Test case üretmek istediğiniz scope item'ları seçin.
3. UAT için ek olarak kategori seçin (Happy Path, Exception, Negative, ...).
4. "Üret" butonuna tıklayın.
5. Sistem, seçilen scope item'ların workshop'larındaki process_step'leri okur.
6. Fit kararı verilmiş adımlar sırayla test step'lere dönüşür.
7. Cross-module geçiş noktaları otomatik checkpoint olarak işaretlenir.

**Örnek:**
```
Scope Item: J58 — Domestic Sales (O2C)
  Workshop steps:
    1. Create Sales Order (SD) — fit
    2. Check ATP (MM) — fit
    3. Create Delivery (SD) — fit
    4. Post Goods Issue (WM) — partial_fit
    5. Create Invoice (SD) — fit
    6. Post Accounting (FI) — fit

    → Otomatik oluşturulan SIT Case: SIT-015
      Başlık: "SIT — O2C — Domestic Sales E2E"
      6 adım, modül geçişleri checkpoint
      Step 4'te "partial_fit" notu eklenir
```

### 4.6 Test Case Durumları

Bir test case şu durumlardan geçer:

```
draft ──► ready ──► approved ──► (deprecated)
  │                    │
  └── düzenleme        └── artık güncel değil
```

- **draft:** Yeni oluşturulmuş, henüz review edilmemiş
- **ready:** Review edildi, onaya hazır
- **approved:** Onaylandı, koşulabilir durumda
- **deprecated:** Artık kullanılmayan eski case

Sadece `approved` durumundaki test case'ler test run'a eklenebilir.

### 4.7 Test Case Klonlama

Regression suite oluştururken mevcut bir SIT veya Unit test case'i klonlayabilirsiniz:

**Yol:** T2 → İlgili test case → "Klonla" butonu

Klonlanan case yeni bir kodla oluşturulur (örn. SIT-015 → REG-008), tüm adımlar kopyalanır. Regression suite'e taşıyabilir ve risk seviyesini atayabilirsiniz.

---

## 5. Module T3: Test Execution

### 5.1 Test Koşma Akışı

Test execution, test case'lerin fiili olarak koşulduğu ekrandır. Akış şöyledir:

```
Test Cycle (zaman penceresi)
  └── Test Run (tek bir koşma oturumu)
        └── Test Execution (case bazlı sonuç)
              └── Test Step Result (adım bazlı sonuç)
```

### 5.2 Test Run Oluşturma

**Yol:** Test Mgmt → T3: Execution → Üstte cycle seçin → "+ Test Run Oluştur"

**Alanlar:**
- **İsim:** Açıklayıcı (örn. "SIT Run 1 — O2C Flow")
- **Ortam:** DEV, QAS, PRD, Sandbox
- **Test case'ler:** Bu run'da koşulacak case'leri seçin (suite'den veya tek tek)

"Oluştur" butonuna tıkladığınızda seçilen her test case için bir `test_execution` kaydı oluşur (status: `not_run`).

### 5.3 Test Koşma — Adım Adım

**Yol:** T3 → İlgili run → Koşmak istediğiniz case'e tıklayın → "Koş" butonu

Execution Workspace açılır. Bu alan tüm ekranınızı kaplar ve size adım adım rehberlik eder:

```
┌────────────────────────────────────────────────────────────┐
│  Test Case: SIT-015 — O2C Domestic Sales E2E               │
│  Suite: TS-SIT-003 | Priority: P1 | Status: In Progress    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1 of 6                                    ⏱ 00:12:34 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ AKSİYON:                                            │   │
│  │ VA01 ile satış siparişi oluştur                      │   │
│  │                                                      │   │
│  │ BEKLENEN SONUÇ:                                      │   │
│  │ Sipariş numarası 10 haneli oluşur, status: Open      │   │
│  │                                                      │   │
│  │ TEST VERİSİ:                                         │   │
│  │ Müşteri: 1000001, Malzeme: FG-001, Miktar: 100       │   │
│  │                                                      │   │
│  │ T-CODE: VA01  |  MODÜL: SD  |  ☑ CHECKPOINT          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  GERÇEKLEŞEN SONUÇ:                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [Buraya gerçekleşen sonucu yazın]                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  KANIT:                                                     │
│  [📎 Dosya Yükle]  [📷 Ekran Görüntüsü]                    │
│                                                             │
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐          │
│  │ PASS │  │ FAIL │  │ BLOCKED  │  │ SKIPPED  │          │
│  │  ✓   │  │  ✗   │  │    ⊘     │  │    ⊝     │          │
│  └──────┘  └──────┘  └──────────┘  └──────────┘          │
│                                                             │
│  [◄ Önceki]                              [Sonraki ►]       │
└────────────────────────────────────────────────────────────┘
```

**Her adım için:**

1. **Aksiyonu SAP'de gerçekleştirin.**
2. **Gerçekleşen sonucu yazın** — ne olduğunu not edin.
3. **Kanıt yükleyin** — ekran görüntüsü veya log dosyası (opsiyonel ama önerilir).
4. **Sonucu işaretleyin:**
   - **PASS** ✓ — Beklenen sonuç gerçekleşti
   - **FAIL** ✗ — Beklenen sonuç gerçekleşmedi → defect oluşturma ekranı açılır
   - **BLOCKED** ⊘ — Test koşulamadı (ortam sorunu, veri eksik, vb.)
   - **SKIPPED** ⊝ — Bu adım atlandı (gerekçe yazılmalı)

5. **Sonraki adıma geçin.**

### 5.4 Başarısız Adımda Defect Oluşturma

Bir adımı **FAIL** olarak işaretlediğinizde, ekranın alt kısmında hızlı defect oluşturma formu açılır:

```
┌────────────────────────────────────────────────────────┐
│  🐛 DEFECT OLUŞTUR                                      │
│                                                          │
│  Başlık: [Otomatik: "SIT-015 Step 3 Fail — ...]         │
│  Açıklama: [Otomatik: adımın aksiyonu + gerçekleşen]     │
│  Severity: [S1 ▾] [S2 ▾] [S3 ▾] [S4 ▾]                 │
│  Priority: [P1 ▾] [P2 ▾] [P3 ▾] [P4 ▾]                 │
│                                                          │
│  Otomatik doldurulan:                                    │
│  • Test Case: SIT-015                                    │
│  • Test Step: Step 3                                     │
│  • Requirement: REQ-042                                  │
│  • WRICEF Item: WRICEF-023                               │
│  • Process Area: SD                                      │
│  • Wave: 1                                               │
│                                                          │
│  [Defect Oluştur]                                        │
└────────────────────────────────────────────────────────┘
```

Sistem tüm traceability alanlarını test case'den otomatik doldurur. Siz sadece severity, priority seçer ve açıklamayı detaylandırırsınız.

### 5.5 Execution Sonuç Hesaplama

Test case koşması tamamlandığında, genel sonuç şöyle hesaplanır:

- Tüm adımlar PASS → Execution = **PASS**
- Herhangi bir adım FAIL → Execution = **FAIL**
- Herhangi bir adım BLOCKED ve hiçbir adım FAIL değilse → Execution = **BLOCKED**
- Hiçbir adım koşulmadıysa → Execution = **NOT_RUN**

### 5.6 Retest (Tekrar Test)

Bir defect çözüldüğünde (`resolved` → `retest` statüsüne geçtiğinde), ilgili test case yeniden koşulmalıdır.

**Yol:** T3 → İlgili run → Daha önce FAIL olan case → "Retest" butonu

Sistem yeni bir execution kaydı oluşturur (execution_number: 2, 3, ...). Önceki koşma sonuçları tarihçede kalır.

### 5.7 İlerleme Takibi

Execution ekranının sağ üstünde anlık ilerleme göstergesi bulunur:

```
Pass: ████████████████████░░░░ 78%  (156/200)
Fail: ████░░░░░░░░░░░░░░░░░░░  8%   (16/200)
Blocked: ██░░░░░░░░░░░░░░░░░░░  4%   (8/200)
Not Run: ████░░░░░░░░░░░░░░░░░ 10%  (20/200)
```

---

## 6. Module T4: Defect Tracker

### 6.1 Defect Nedir?

Defect (hata), test sırasında beklenen sonucun gerçekleşmediği her durumun kaydıdır. Defect'ler test seviyesinden bağımsızdır — Unit test'te de, UAT'ta da, Performance test'te de oluşabilir.

### 6.2 Defect Yaşam Döngüsü

Her defect şu 9 statüden geçebilir:

```
    ┌──────┐
    │ NEW  │ ← Test sırasında bulundu
    └──┬───┘
       │ assign (atama)
    ┌──▼──────┐
    │ASSIGNED │ ← Developer/consultant'a atandı
    └──┬──────┘
       │ start_work (çalışmaya başla)
    ┌──▼────────┐
    │IN PROGRESS│ ← Fix üzerinde çalışılıyor
    └──┬────────┘
       │ resolve (çöz)
    ┌──▼───────┐
    │ RESOLVED │ ← Fix yapıldı, retest bekliyor
    └──┬───────┘
       │ send_to_retest
    ┌──▼──────┐
    │ RETEST  │ ← Test ekibi fix'i doğruluyor
    └──┬──────┘
      / \
   pass   fail
    /       \
┌──▼────┐  ┌▼────────┐
│CLOSED │  │REOPENED │──► ASSIGNED'a geri döner
└───────┘  └─────────┘

Ek statüler:
• DEFERRED — Şimdi değil, backlog'a alındı
• REJECTED — Bu bir defect değil (by design, user error)
```

### 6.3 Defect Oluşturma — Manuel

**Yol:** Test Mgmt → T4: Defect Tracker → "+ Defect Oluştur"

**Zorunlu alanlar:**
- **Başlık:** Kısa ve açıklayıcı (kötü: "Hata var", iyi: "VA01 — Fiyat koşulu ZPR1 hesaplanmıyor")
- **Açıklama:** Adımlar, beklenen sonuç, gerçekleşen sonuç
- **Severity:** S1/S2/S3/S4
- **Priority:** P1/P2/P3/P4

**Severity ne anlama gelir?**

| Severity | Anlamı | Örnek |
|----------|--------|-------|
| **S1 — Showstopper** | Sistem çalışmıyor, iş duruyor | SAP tamamen erişilemez |
| **S2 — Critical** | Ana işlev bozuk, çözüm yok | Fatura oluşturulamıyor, workaround yok |
| **S3 — Major** | İşlev bozuk ama workaround var | Fiyat yanlış hesaplanıyor, manuel düzeltilebilir |
| **S4 — Minor** | Küçük sorun, iş etkilenmiyor | Ekranda yazım hatası, raporun formatı bozuk |

**Priority ne anlama gelir?**

| Priority | Anlamı | Ne zaman fix? |
|----------|--------|--------------|
| **P1 — Immediate** | Hemen çözülmeli | Saatler içinde |
| **P2 — High** | En kısa sürede | 1-2 iş günü |
| **P3 — Medium** | Sprint içinde | 3 iş günü |
| **P4 — Low** | Backlog'a alınabilir | Sprint sonu |

### 6.4 SLA (Hizmet Seviyesi Taahhüdü)

Bir defect atandığında (assigned) sistem otomatik olarak çözüm süresini hesaplar:

| Severity + Priority | İlk Yanıt | Çözüm Süresi | Son Tarih |
|---------------------|-----------|-------------|-----------|
| S1 + P1 | 1 saat | 4 saat | Otomatik hesaplanır |
| S2 + P2 | 4 saat | 1 iş günü | Otomatik hesaplanır |
| S3 + P3 | 1 iş günü | 3 iş günü | Otomatik hesaplanır |
| S4 + P4 | 2 iş günü | Sprint sonu | Otomatik hesaplanır |

SLA durumu renklerle gösterilir:
- 🟢 **On Track** — süre yeterli
- 🟡 **Warning** — süre azalıyor (%75 geçti)
- 🔴 **Breached** — süre aşıldı

### 6.5 Defect Görünümleri

Defect Tracker iki görünüm sunar:

**Tablo Görünümü** — filtreleme ve sıralama için ideal:

```
┌──────┬────┬────┬───────────────────────────────┬──────────┬────────────┬──────┐
│ Kod  │ S  │ P  │ Başlık                        │ Durum    │ Atanan     │ Yaş  │
├──────┼────┼────┼───────────────────────────────┼──────────┼────────────┼──────┤
│DEF-001│ S1 │ P1 │ Fatura oluşturulamıyor        │Assigned  │ Ali K.     │ 2g   │
│DEF-002│ S3 │ P3 │ Rapor formatı bozuk           │In Progr. │ Ayşe M.    │ 5g   │
│DEF-003│ S2 │ P2 │ Interface timeout hatası      │Resolved  │ Mehmet B.  │ 3g   │
└──────┴────┴────┴───────────────────────────────┴──────────┴────────────┴──────┘
```

**Kanban Görünümü** — akış takibi için ideal:

```
 New (3)     │ Assigned (5) │ In Progress (8) │ Resolved (4) │ Retest (2) │ Closed (45)
─────────────┼──────────────┼─────────────────┼──────────────┼────────────┼────────────
 DEF-047 S3  │ DEF-001 S1 🔴│ DEF-002 S3      │ DEF-003 S2   │ DEF-010 S3 │ DEF-009 S4
 DEF-048 S4  │ DEF-015 S2   │ DEF-005 S3      │ DEF-008 S3   │ DEF-022 S2 │ DEF-011 S3
 DEF-049 S3  │ DEF-017 S3   │ DEF-006 S4      │ DEF-012 S3   │            │ ...
             │ DEF-020 S3   │ DEF-007 S2 🟡   │ DEF-014 S4   │            │
             │ DEF-023 S4   │ DEF-016 S3      │              │            │
```

### 6.6 Defect Çözme (Resolve)

Defect'i düzelten kişi (developer/consultant) şu bilgileri doldurur:

- **Resolution (Çözüm):** Ne yapıldığını açıklayın
- **Resolution Type (Çözüm Tipi):** Aşağıdakilerden birini seçin:
  - `code_fix` — Kod düzeltmesi
  - `config_change` — Konfigürasyon değişikliği
  - `data_correction` — Veri düzeltmesi
  - `workaround` — Geçici çözüm
  - `by_design` — Tasarım gereği (defect değil)
  - `duplicate` — Başka bir defect'in kopyası
  - `cannot_reproduce` — Tekrar edilemiyor
- **Root Cause (Kök Neden):** Opsiyonel ama önerilir:
  - `code_error`, `config_error`, `data_issue`, `spec_gap`, `env_issue`, `user_error`, `design_flaw`

### 6.7 Retest ve Kapatma

1. Defect `resolved` olduktan sonra Test Lead "Retest'e Gönder" butonuna tıklar.
2. Defect `retest` statüsüne geçer.
3. Tester ilgili test case'i tekrar koşar.
4. Sonuç:
   - **Fix başarılı** → "Retest Başarılı" → defect `closed` olur
   - **Fix başarısız** → "Retest Başarısız" → defect `reopened` olur, tekrar assigned'a döner

### 6.8 Defect Bağlama (Linking)

Defect'ler arası ilişki kurabilirsiniz:

| Bağlantı Tipi | Anlamı | Ne zaman? |
|--------------|--------|-----------|
| **duplicate_of** | Bu defect başka birinin kopyası | Aynı hata iki kez açıldığında |
| **related_to** | İlişkili ama bağımsız | Benzer alandaki farklı hatalar |
| **caused_by** | Bu defect başka birinden kaynaklanıyor | Fix'in yan etkisi |
| **blocks** | Bu defect çözülmeden diğeri koşulamaz | Bağımlılık |

---

## 7. Module T5: Test Dashboard

### 7.1 Dashboard Widget'ları

Test Dashboard, test sürecinin anlık ve trend bazlı durumunu 10 widget ile gösterir:

| # | Widget | Ne Gösterir | Nasıl Okunur |
|---|--------|------------|-------------|
| 1 | **Test Execution Progress** | Seviye bazlı pass/fail/blocked/not_run | Her seviye için yatay bar — yeşil baskın olmalı |
| 2 | **Pass Rate Trend** | Günlük pass rate çizgi grafiği | Yukarı trend iyidir |
| 3 | **Defect Open/Close Rate** | Günlük açılan vs kapatılan defect | Kapatma çizgisi açma çizgisinin üstünde olmalı |
| 4 | **Defect Funnel** | New→Assigned→InProgress→Resolved→Closed | Daralan huni iyidir |
| 5 | **Severity Distribution** | S1/S2/S3/S4 dağılımı (donut) | S1/S2 oranı düşük olmalı |
| 6 | **Defect Aging** | Açık defect'lerin yaşı (0-3, 4-7, 8-14, 15+ gün) | Yaşlı defect az olmalı |
| 7 | **Test Coverage Map** | Process area × test level heatmap | Boş/kırmızı hücre olmamalı |
| 8 | **Go/No-Go Scorecard** | 10 kriter checklist | Tümü yeşil → Go-Live hazır |
| 9 | **Wave Readiness** | Wave bazlı özet | Her wave'in bağımsız durumu |
| 10 | **Top 10 Open Defects** | En kritik açık defect'ler | Acil aksiyon listesi |

### 7.2 Go/No-Go Scorecard

Bu, tüm test yönetiminin nihai çıktısıdır. Steering Committee'ye sunulur ve "Go-Live'a geçebilir miyiz?" sorusunu yanıtlar.

```
┌──────────────────────────────────────────────────────────────┐
│                    GO / NO-GO SCORECARD                        │
├────────────────────────────────────────┬──────────┬──────────┤
│ Kriter                                 │ Hedef    │ Durum    │
├────────────────────────────────────────┼──────────┼──────────┤
│ 1. Unit Test pass rate                 │ ≥ 95%    │ 🟢 97.5% │
│ 2. SIT pass rate                       │ ≥ 95%    │ 🟢 96.1% │
│ 3. UAT Happy Path — tümü pass         │ 100%     │ 🟢 100%  │
│ 4. UAT BPO Sign-off — tümü onaylı     │ 100%     │ 🟡 85%   │
│ 5. Open S1 (Showstopper) defect       │ = 0      │ 🟢 0     │
│ 6. Open S2 (Critical) defect          │ = 0      │ 🔴 2     │
│ 7. Open S3 (Major) defect             │ ≤ 5      │ 🟢 3     │
│ 8. Regression suite pass rate          │ 100%     │ 🟢 100%  │
│ 9. Performance target karşılama        │ ≥ 95%    │ 🟢 97%   │
│ 10. Tüm critical defect'ler kapalı    │ 100%     │ 🔴 94%   │
├────────────────────────────────────────┼──────────┼──────────┤
│ GENEL KARAR                            │          │ 🔴 NO-GO │
│ (Tüm kriterler yeşil olmalı)          │          │          │
└────────────────────────────────────────┴──────────┴──────────┘
```

Yukarıdaki örnekte 2 kriter kırmızı olduğu için karar NO-GO'dur. S2 defect'ler kapatılmalı ve BPO sign-off'ları tamamlanmalıdır.

### 7.3 Dashboard Export

Dashboard verileri 3 formatta dışa aktarılabilir:

- **PPTX** — Steering Committee sunumları için
- **PDF** — Arşivleme için
- **XLSX** — Detaylı analiz için

**Yol:** T5 → Sağ üst → "Export" → Format seçin → "İndir"

---

## 8. Module T6: Traceability Matrix

### 8.1 Ne Gösterir?

Traceability Matrix, Explore Phase'den test yönetimine kadar olan tüm zinciri tek bir tabloda gösterir:

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│Requirement│ WRICEF/Config│ Test Cases   │ Son Koşma    │ Açık Defect  │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-001   │ WRICEF-023   │ UT-001 ✅    │ PASS (02/08) │ 0            │
│          │              │ SIT-015 ✅   │ PASS (02/09) │ 0            │
│          │              │ UAT-008 ⚠️   │ FAIL (02/10) │ DEF-003 (S2) │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-002   │ CFG-018      │ UT-002 ✅    │ PASS (02/07) │ 0            │
│          │              │ —            │ —            │ —            │
│          │              │ ⚫ SIT eksik  │              │              │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-003   │ —            │ ⚫ Test yok   │ —            │ —            │
└──────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### 8.2 Renk Kodları

- 🟢 **Yeşil:** Test edildi ve geçti
- 🟡 **Sarı:** Test edildi ama sorun var (open defect)
- 🔴 **Kırmızı:** Test edildi ve başarısız
- ⚫ **Gri:** Test case yok veya hiç koşulmamış

### 8.3 Gap Tespiti

Traceability Matrix'in en önemli işlevi gap (boşluk) tespitidir:

- **REQ-003** gibi test case'i olmayan requirement'lar otomatik vurgulanır.
- **REQ-002 SIT** gibi belirli seviyede eksik test case'ler gösterilir.
- Bu gap'lerin kapatılması Test Lead'in sorumluluğundadır.

### 8.4 Filtreleme

Matrix şu boyutlarda filtrelenebilir:
- **Process area:** FI, SD, MM, PP, ...
- **Wave:** 1, 2, 3, 4
- **Scope item:** L3 scope item
- **Test level:** Belirli bir seviyeye odaklanma

### 8.5 Export

Matrix, Excel ve PDF formatında dışa aktarılabilir. Excel formatı pivot analiz için uygundur.

---

## 9. Explore Phase'den Test'e Geçiş

### 9.1 Geçiş Adımları

Explore Phase tamamlandığında test sürecine şu adımlarla geçilir:

**Adım 1 — Test Planı Oluşturma (Test Lead):**
T1'de test planı oluşturun, stratejiyi yazın, ortam matrisini doldurun, giriş/çıkış kriterlerini tanımlayın. PM'e onaya gönderin.

**Adım 2 — Test Döngülerini Planlama (Test Lead):**
T1'de wave bazlı test döngüleri oluşturun. Takvimi Realize fazı planıyla hizalayın.

**Adım 3 — Unit Test Suite'lerini Otomatik Üretme (Module Lead):**
T2 → Unit sekmesi → Her process area için suite oluşturun → "WRICEF'ten Üret" ile unit test case'leri otomatik oluşturun.

**Adım 4 — SIT Suite'lerini Otomatik Üretme (Test Lead + Module Lead):**
T2 → SIT sekmesi → E2E senaryo bazlı suite'ler oluşturun → "Süreçten Üret" ile SIT case'leri otomatik oluşturun.

**Adım 5 — UAT Suite'lerini Hazırlama (Module Lead + BPO):**
T2 → UAT sekmesi → Her L3 scope item için suite oluşturun → "Süreçten Üret" ile UAT case'leri üretin → BPO ile birlikte Happy Path, Exception, Negative senaryolarını gözden geçirin.

**Adım 6 — Regression Suite Oluşturma (Test Lead):**
T2 → Regression sekmesi → Kritik test case'leri SIT/Unit'ten klonlayın → Risk seviyesi atayın.

**Adım 7 — Performance Test Case'leri (Tech Lead):**
T2 → Performance sekmesi → Kritik transaction'lar için test case oluşturun → Hedef response time ve user sayısını tanımlayın.

**Adım 8 — Test Case'leri Onaylama (Module Lead / Test Lead):**
T2 → Tüm draft case'leri review edin → "Onayla" ile approved durumuna geçirin.

### 9.2 Geçiş Kontrol Listesi

| # | Görev | Sorumlu | Tamamlandı? |
|---|-------|---------|-------------|
| 1 | Test planı oluşturuldu ve onaylandı | Test Lead + PM | ☐ |
| 2 | Test döngüleri planlandı (cycle) | Test Lead | ☐ |
| 3 | Unit test case'leri üretildi (her WRICEF/Config için ≥1) | Module Lead'ler | ☐ |
| 4 | SIT case'leri üretildi (her E2E senaryo için) | Test Lead | ☐ |
| 5 | UAT case'leri üretildi (her L3 scope item için) | Module Lead + BPO | ☐ |
| 6 | Regression suite oluşturuldu | Test Lead | ☐ |
| 7 | Performance case'leri tanımlandı | Tech Lead | ☐ |
| 8 | Tüm case'ler approved durumunda | Test Lead | ☐ |
| 9 | QAS ortamı hazır | Basis/Tech ekibi | ☐ |
| 10 | Test verileri hazır | Module Lead'ler | ☐ |
| 11 | Cloud ALM sync test edildi | Test Lead | ☐ |

---

## 10. Cloud ALM Senkronizasyonu

### 10.1 Neler Senkronize Edilir?

ProjektCoPilot ve SAP Cloud ALM arasında çift yönlü senkronizasyon yapılabilir:

| ProjektCoPilot → Cloud ALM | Cloud ALM → ProjektCoPilot |
|---------------------------|---------------------------|
| Test case push | — |
| Test step push | — |
| Execution sonucu push | — |
| Defect push | Defect status güncelleme |

### 10.2 Nasıl Kullanılır?

**Tek test case senkronizasyonu:**
T2 → İlgili test case → "ALM'e Gönder" butonu

**Toplu senkronizasyon:**
T2 → Birden fazla case seçin → "Toplu ALM Sync" butonu

**Defect senkronizasyonu:**
T4 → İlgili defect → "ALM'e Gönder" butonu

**Execution sonucu:**
T3 → Execution tamamlandığında → "Sonucu ALM'e Gönder" butonu

### 10.3 Senkronizasyon Alanları

Test case gönderildiğinde şu alanlar Cloud ALM'e aktarılır:

| ProjektCoPilot Alanı | Cloud ALM Alanı |
|----------------------|----------------|
| code | External Reference |
| title | Summary |
| description | Description |
| priority | Priority |
| test_level | Test Type |
| process_area | Process Area Tag |
| adımlar (action/expected) | Test Steps |

---

## 11. Sık Sorulan Sorular

**S: Explore Phase'de requirement oluşturdum ama test case göremiyorum. Ne yapmalıyım?**
C: Test case'ler otomatik oluşmaz — "WRICEF'ten Üret" veya "Süreçten Üret" butonlarını kullanmanız gerekir. Önce ilgili test suite'i oluşturun, sonra üretim butonunu kullanın.

**S: Bir defect hangi seviyede bulundu nasıl anlarım?**
C: Her defect'in `test_level` alanı vardır ve defect oluşturulduğunda otomatik doldurulur. Defect detayında "Unit", "SIT", "UAT" vb. olarak görünür.

**S: SLA süresi iş günü mü yoksa takvim günü mü?**
C: S1+P1 ve S2+P2 için takvim saati (7/24), S3+P3 ve S4+P4 için iş günü hesaplanır.

**S: UAT sign-off'u kim verebilir?**
C: Sadece BPO (Business Process Owner) veya PM rolüne sahip kullanıcılar UAT sign-off verebilir.

**S: Test case'i değiştirmek istiyorum ama approved durumunda. Ne yapmalıyım?**
C: Approved case'i doğrudan düzenleyemezsiniz. Klonlayın, yeni versiyonu düzenleyin ve onaylayın. Eski case'i "deprecated" olarak işaretleyin.

**S: Regression suite'e hangi case'leri eklemeliyim?**
C: Risk bazlı yaklaşım kullanın. Core financial process'ler ve kritik interface'ler `critical` risk, aynı modüldeki değişiklikler `high` risk olarak işaretlenmelidir. Sistem, bir WRICEF/Config item değiştiğinde otomatik olarak etkilenen test case'leri belirler.

**S: Performance test için hedef response time'ı nereden belirleyeceğim?**
C: Performance test case oluştururken `perf_target_response_ms` alanına hedef süreyi milisaniye cinsinden girin. Tipik hedef: dialog transaction'lar için <2000ms, batch job'lar proje bazlı belirlenir.

**S: Go/No-Go scorecard otomatik mi hesaplanıyor?**
C: Evet. T5 Dashboard → Go/No-Go Scorecard tüm 10 kriteri gerçek zamanlı olarak hesaplar. Yeşil/kırmızı durumlar otomatik güncellenir.

**S: Cloud ALM'deki defect güncellendiğinde ProjektCoPilot'ta da güncellenir mi?**
C: Evet, defect senkronizasyonu çift yönlüdür. Cloud ALM'de defect status değiştiğinde ProjektCoPilot'taki karşılık gelen defect da güncellenir.

**S: Birden fazla wave varsa test döngüleri nasıl organize edilir?**
C: Her wave için bağımsız test döngüleri oluşturulur. Örneğin: "Wave 1 — Unit Cycle 1", "Wave 1 — SIT Cycle 1", "Wave 2 — Unit Cycle 1" şeklinde. Test takviminde tüm wave'ler paralel görünür.

---

## 12. Kısaltmalar ve Terimler

| Kısaltma | Açıklama |
|----------|----------|
| ALM | Application Lifecycle Management |
| BPO | Business Process Owner |
| Config | Configuration Item |
| DEF | Defect (hata kaydı) |
| DEV | Development ortamı |
| E2E | End-to-End (uçtan uca) |
| FS/TS | Functional Specification / Technical Specification |
| O2C | Order to Cash (siparişten tahsilata) |
| P2P | Procure to Pay (satın almadan ödemeye) |
| PM | Program/Project Manager |
| PRD | Production ortamı |
| QAS | Quality Assurance System (test ortamı) |
| R2R | Record to Report (kayıttan rapora) |
| REG | Regression Test |
| REQ | Requirement (gereksinim) |
| SIT | System Integration Test |
| SLA | Service Level Agreement (hizmet seviyesi taahhüdü) |
| UAT | User Acceptance Test (kullanıcı kabul testi) |
| UT | Unit Test |
| WRICEF | Workflow, Report, Interface, Conversion, Enhancement, Form |

---

*Doküman Sonu*

*Bu rehber, ProjektCoPilot Test Management System FS/TS v1.0 baz alınarak hazırlanmıştır. Teknik detaylar için test-management-fs-ts.md dokümanına başvurunuz.*
