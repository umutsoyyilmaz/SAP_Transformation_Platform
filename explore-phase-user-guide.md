# ProjektCoPilot — Explore Phase Manager
# Kullanıcı Kılavuzu v1.0

---

## Bu Kılavuz Hakkında

Bu kılavuz, ProjektCoPilot platformunun **Explore Phase Manager** modülünü kullanacak tüm proje ekibi üyelerine yöneliktir. SAP Activate metodolojisinin Explore fazını — süreç hiyerarşisi oluşturmadan workshop yürütmeye, requirement yönetiminden steering committee raporlamasına kadar — baştan sona yönetmenizi sağlar.

**Hedef kullanıcılar:**
- Program/Proje Yöneticileri
- SAP Danışmanları (Facilitator'lar)
- Modül Liderleri
- Müşteri Tarafı Süreç Sahipleri (Business Process Owner)
- Teknik Liderler ve Geliştiriciler
- İş Analistleri ve Test Uzmanları

**Ön koşullar:**
- ProjektCoPilot hesabı ve proje erişimi
- Tarayıcı: Chrome, Edge veya Firefox (güncel sürüm)
- Atanmış proje rolü (bkz. Bölüm 2)

---

## İçindekiler

1. Sisteme Genel Bakış
2. Roller ve Yetkiler
3. Proje Kurulumu
4. Ekran 1: Process Hierarchy Manager
5. Ekran 2: Workshop Hub
6. Ekran 3: Workshop Detail
7. Ekran 4: Requirement & Open Item Hub
8. Ekran 5: Explore Dashboard
9. Scope Değişiklik Yönetimi
10. Cloud ALM Entegrasyonu
11. Raporlama ve Export
12. Sık Sorulan Sorular
13. Kısayollar ve İpuçları

---

## 1. Sisteme Genel Bakış

### 1.1 Explore Fazı Nedir?

SAP Activate metodolojisinde Explore fazı, müşterinin mevcut iş süreçlerinin SAP S/4HANA standardıyla karşılaştırıldığı aşamadır. Her süreç için üç karardan biri verilir:

- **Fit** — SAP standardı yeterli, değişiklik gerekmez
- **Partial Fit** — küçük ayarlama veya konfigürasyonla çözülür
- **Gap** — SAP standardı karşılamıyor, geliştirme gerekir

Bu kararlar **Fit-to-Standard workshop'larında** alınır. Her workshop'ta alınan kararlar, oluşturulan gereksinimler ve açılan aksiyon maddeleri, projenin Realize fazındaki iş yükünü belirler.

### 1.2 Beş Ana Ekran

Explore Phase Manager beş ekrandan oluşur. Her biri farklı bir ihtiyaca hizmet eder:

| Ekran | Ne İşe Yarar | Kim Kullanır | Ne Sıklıkla |
|-------|-------------|-------------|-------------|
| **Process Hierarchy** | Süreç ağacını gösterir, büyük resmi verir | PM, BPO, Module Lead | Haftalık review |
| **Workshop Hub** | 300+ workshop'u planlar ve takip eder | PM, Facilitator | Her gün |
| **Workshop Detail** | Tek bir workshop'u yürütür | Facilitator | Workshop günü |
| **REQ & OI Hub** | Gereksinim ve aksiyon maddelerini yönetir | Tüm ekip | Her gün |
| **Explore Dashboard** | Trend analizi ve raporlama | PM, Steering Committee | Haftalık |

### 1.3 Ekranlar Arası Gezinme

Ekranlar birbirine bağlıdır. Herhangi bir ekrandan diğerine geçiş yapabilirsiniz:

- Process Hierarchy'de bir scope item'a tıklayın → o item'ın workshop'unu gösterir
- Workshop Hub'da bir satıra tıklayın → Workshop Detail açılır
- Workshop Detail'de bir requirement kodu tıklayın → REQ Hub'da o requirement'a gider
- REQ Hub'da workshop kodu tıklayın → Workshop Detail'e döner
- Dashboard'daki bir grafikte alana tıklayın → ilgili ekrana filtre uygulanmış şekilde gider

Sol menüdeki "Explore" altında beş ekranın tümüne erişebilirsiniz.

---

## 2. Roller ve Yetkiler

### 2.1 Rol Ataması

Her proje ekibi üyesine bir veya birden fazla rol atanır. Rolünüz hangi işlemleri yapabileceğinizi belirler. Rol ataması Proje Yöneticisi tarafından yapılır.

Rolünüzü görmek için: sağ üst köşedeki profil simgesine tıklayın → "Proje Rollerim" seçin.

### 2.2 Rol Tanımları

**Project Manager (PM)**
Tüm işlemleri yapabilir. Workshop planlama, requirement onaylama, scope değiştirme, ALM senkronizasyonu — hepsine yetkilidir. Genelde projede 1-2 kişi bu role sahiptir.

**Module Lead (Modül Lideri)**
Kendi süreç alanındaki (FI, SD, MM, vb.) workshop ve requirement'ları yönetir. SD Module Lead yalnızca SD alanındaki requirement'ları onaylayabilir veya reddedebilir. Başka alanların requirement'larını görebilir ama değiştiremez.

**Facilitator (Kolaylaştırıcı)**
Atandığı workshop'ları başlatır, yürütür ve tamamlar. Workshop sırasında fit kararı verir, decision/open item/requirement oluşturur. Atanmadığı workshop'ları değiştiremez.

**Business Process Owner (BPO — İş Süreci Sahibi)**
Müşteri tarafındaki süreç sahibi. Requirement onaylama (module lead ile birlikte), scope kararları verme, fit kararlarına katılma yetkisine sahiptir. Genelde müşteri organizasyonundaki departman yöneticileridir.

**Tech Lead (Teknik Lider)**
Requirement'ları Cloud ALM'ye aktarma, realize edildiğini işaretleme ve effort tahmini yapma yetkisine sahiptir. Genelde development ekibinin lideridir.

**Business Tester (İş Testi Uzmanı)**
Realize edilmiş requirement'ları doğrulama (verify) yetkisine sahiptir. UAT sürecinde requirement'ın kabul edildiğini onaylar.

**Viewer (İzleyici)**
Tüm ekranları görebilir ama hiçbir değişiklik yapamaz. Genelde üst yönetim veya harici paydaşlara verilir.

### 2.3 Yetki Matrisi — Hızlı Referans

| İşlem | PM | Module Lead | Facilitator | BPO | Tech Lead | Tester | Viewer |
|-------|:--:|:----------:|:----------:|:---:|:---------:|:------:|:------:|
| Workshop planlama | ✓ | Kendi alanı | — | — | — | — | — |
| Workshop başlatma | ✓ | ✓ | Kendi WS'si | — | — | — | — |
| Fit kararı verme | ✓ | ✓ | Kendi WS'si | ✓ | — | — | — |
| REQ oluşturma | ✓ | ✓ | ✓ | ✓ | — | — | — |
| REQ onaylama | ✓ | Kendi alanı | — | ✓ | — | — | — |
| REQ reddetme | ✓ | Kendi alanı | — | — | — | — | — |
| ALM'ye aktarma | ✓ | — | — | — | ✓ | — | — |
| Realize işaretleme | ✓ | — | — | — | ✓ | — | — |
| Verify (doğrulama) | ✓ | ✓ | — | ✓ | — | ✓ | — |
| Scope değiştirme | ✓ | — | — | ✓ | — | — | — |
| OI oluşturma | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| OI kapatma | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Dosya ekleme | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Dashboard görme | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**"Kendi alanı"** = Atandığı süreç alanı (FI, SD, MM, vb.)
**"Kendi WS'si"** = Facilitator olarak atandığı workshop

---

## 3. Proje Kurulumu

### 3.1 Süreç Ağacını Yükleme

Proje oluşturulduktan sonraki ilk adım süreç ağacını yüklemektir.

**Adım 1:** Sol menüden "Explore" → "Process Hierarchy" ekranına gidin.

**Adım 2:** Sağ üstteki "Import Scope Items" butonuna tıklayın.

**Adım 3:** SAP Best Practice scope item kataloğunu seçin:
- **JSON/Excel import:** SAP'den aldığınız scope item listesini yükleyin.
- Her satır bir L3 scope item'dır (J58, BD9, J45 gibi kodlarla).

**Adım 4:** Sistem otomatik olarak şunları oluşturur:
- 3 adet L1 (Value Chain): Core Business Processes, Management Processes, Support Processes
- 8-12 adet L2 (Process Area): Her scope item'ın ait olduğu süreç alanı
- 50-100 adet L3 (Scope Item): İmport edilen her satır

**Adım 5:** Import sonucunu kontrol edin. Process Hierarchy ekranında ağaç yapısında L1→L2→L3 görünmelidir.

### 3.2 L4 Sub-Process Oluşturma

L3 scope item'ların altına L4 alt süreçler eklenmelidir. Workshop başlatılmadan önce L4'lerin mevcut olması gerekir.

**Yol 1 — Katalogdan import (önerilen):**
1. Process Hierarchy'de bir L3 node'a tıklayın (örneğin J58).
2. Sağ panelde "Sub-Processes" tab'ına geçin.
3. "Import from Catalog" butonuna tıklayın.
4. SAP Best Practice kataloğundaki standart alt süreçler listelenir.
5. Uygun olanları seçin → "Import Selected" → L4'ler oluşturulur.

**Yol 2 — BPMN'den import:**
1. L3 node'da "Import from BPMN" butonuna tıklayın.
2. Signavio URL'i yapıştırın veya BPMN XML dosyasını yükleyin.
3. Sistem BPMN'deki activity'leri parse eder ve L4 olarak önerir.
4. Onaylayın → L4'ler oluşturulur.

**Yol 3 — Manuel giriş:**
1. L3 node'da "Add Sub-Process" butonuna tıklayın.
2. Kod (örn: J58.01), isim ve açıklama girin.
3. Kaydet → L4 oluşturulur.

### 3.3 Scope Belirleme

**Adım 1:** Process Hierarchy'de "Matrix" görünümüne geçin. Tüm L3 scope item'lar tablo halinde listelenir.

**Adım 2:** Her satırda "Scope" sütunundaki dropdown'dan seçim yapın:
- **In Scope** — projede var, workshop yapılacak
- **Out of Scope** — projede yok
- **Under Review** — henüz karar verilmedi

**Adım 3:** Her değişiklik otomatik loglanır. Kim, ne zaman, neyi hangi değere çevirdi kaydedilir.

### 3.4 Wave Atama

**Adım 1:** Matrix görünümünde "Wave" sütunundaki dropdown'dan seçim yapın:
- Wave 1, Wave 2, Wave 3, Wave 4 (veya daha fazla)

**Adım 2:** Önerilen sıralama:
- Wave 1: FI + CO (finansal temel)
- Wave 2: SD + MM (operasyonel süreçler)
- Wave 3: PP + QM (üretim)
- Wave 4: Geri kalan alanlar

### 3.5 Proje Rolleri Atama

**Adım 1:** Proje ayarlarından "Team & Roles" bölümüne gidin.

**Adım 2:** Her ekip üyesi için:
- Kullanıcıyı seçin
- Rol atayın (PM, Module Lead, Facilitator, vb.)
- Module Lead ve Facilitator için süreç alanı belirtin (FI, SD, vb.)

---

## 4. Ekran 1: Process Hierarchy Manager

### 4.1 Ekrana Erişim

Sol menü → Explore → Process Hierarchy

### 4.2 Üç Görünüm Modu

Ekranın üstündeki sekmelerden görünüm modunu seçin:

**Hierarchy (Ağaç) Görünümü:**
- L1→L2→L3→L4 ağaç yapısı
- Her node'un solundaki ok ile açıp kapatabilirsiniz
- Her node'da görünen bilgiler:
  - Seviye badge'i (L1 mor, L2 mavi, L3 yeşil, L4 sarı)
  - Süreç kodu ve adı
  - Fit durumu badge'i (Fit=yeşil, Partial=sarı, Gap=kırmızı, Pending=mor)
  - Fit dağılım çubuğu (L1/L2/L3'te — alt süreçlerin oransal dağılımı)
  - Workshop sayısı (varsa)

**Workshops Görünümü:**
- Aynı ağaç yapısı ama workshop odaklı
- Her L3 node'un yanında atanmış workshop kartları görünür
- Workshop'un tarihi, facilitator'ı ve durumu kartın üzerindedir

**Matrix Görünümü:**
- Tüm L3 scope item'lar düz tablo
- Sütunlar: Kod, İsim, Alan, Wave, Scope Durumu, Fit Durumu, Workshop Sayısı, REQ Sayısı, OI Sayısı
- Sıralama ve filtreleme yapılabilir
- Steering committee sunumları için ideal

### 4.3 Filtreler

Ekranın üstündeki filtre çubuğu:

- **Arama:** Kod veya isim ile arayın (örn: "J58" veya "Sales Order")
- **Fit Durumu:** Tümü / Fit / Partial Fit / Gap / Pending
- **Scope:** Tümü / In Scope / Out of Scope / Under Review
- **Alan:** FI, SD, MM, vb.
- **Wave:** 1, 2, 3, 4

Birden fazla filtre aynı anda uygulanabilir. Aktif filtre sayısı filtre butonunun yanında görünür.

### 4.4 Detay Paneli

Ağaçta bir node'a tıkladığınızda sağ tarafta detay paneli açılır. Dört tab içerir:

**Overview tab'ı:**
- Süreç kodu, adı, açıklaması
- Scope durumu
- Wave
- Alt süreç sayısı
- BPMN diyagramı (varsa — iframe veya görüntüleyici olarak gösterilir)

**Fit Analysis tab'ı:**
- Fit/Partial/Gap/Pending dağılım çubuğu ve yüzdeleri
- Alt süreçlerin fit durumu listesi
- Toplam requirement ve open item sayısı

**Requirements tab'ı:**
- Bu node'a (ve alt node'larına) bağlı requirement'ların listesi
- Priority, type, status bilgileri
- REQ koduna tıklayınca REQ Hub'a gider

**Workshop tab'ı:**
- Bağlı workshop(lar)ın listesi
- Workshop koduna tıklayınca Workshop Detail açılır

### 4.5 BPMN Diyagramı Görüntüleme

L3 veya L4 node'da BPMN diyagramı varsa:

1. Node'a tıklayın → Detay panelinde Overview tab'ını açın.
2. BPMN bölümünde diyagram gösterilir:
   - Signavio URL bağlanmışsa → iframe içinde Signavio görünümü
   - BPMN XML yüklenmişse → interaktif BPMN görüntüleyici
   - Görsel yüklenmişse → PNG/SVG olarak gösterilir
3. Zoom in/out ve pan yapabilirsiniz.

**BPMN yüklemek için:**
1. Node'un sağ tıklama menüsünden "Manage BPMN" seçin.
2. Yükleme yöntemi seçin: Signavio URL / BPMN XML dosyası / Görsel (PNG/SVG)
3. Yükleyin → Diyagram node'a bağlanır.

---

## 5. Ekran 2: Workshop Hub

### 5.1 Ekrana Erişim

Sol menü → Explore → Workshop Hub

### 5.2 Üç Görünüm Modu

**Table (Tablo) Görünümü — varsayılan:**
- Tüm workshop'lar tablo halinde
- Sütunlar: Kod, Scope Item, İsim, Alan, Wave, Tarih, Durum, Facilitator, Fit Çubuğu, Karar Sayısı, OI Sayısı, REQ Sayısı
- Herhangi bir sütun başlığına tıklayarak sıralayabilirsiniz
- Satıra tıklayınca Workshop Detail açılır

**Kanban Görünümü:**
- 4 sütun: Draft → Scheduled → In Progress → Completed
- Her workshop bir kart olarak görünür
- Kartları sürükleyerek durum değiştiremezsiniz (durum değişikliği Workshop Detail'den yapılır)
- Hızlı genel bakış için idealdir

**Capacity (Kapasite) Görünümü:**
- Facilitator bazlı kart grid'i
- Her kartta:
  - Facilitator adı ve alanı
  - Tamamlanan / aktif / planlanan workshop sayıları
  - Haftalık yük çubuğu grafiği
  - Kırmızı uyarı: haftada 3'ten fazla workshop varsa
  - Açık open item sayısı

### 5.3 Filtreleme

Filtre çubuğu:
- **Arama:** Kod, isim veya scope item ile arayın
- **Durum:** Draft / Scheduled / In Progress / Completed / Cancelled
- **Wave:** 1 / 2 / 3 / 4
- **Alan:** FI / SD / MM / vb.
- **Facilitator:** Dropdown'dan seçin
- **Tarih Aralığı:** Başlangıç ve bitiş tarihi

### 5.4 Gruplama

"Group By" seçicisinden workshop'ları şu ölçütlere göre gruplayabilirsiniz:
- **Wave** — wave bazlı (en yaygın)
- **Alan** — süreç alanı bazlı
- **Facilitator** — kişi bazlı
- **Durum** — status bazlı
- **Tarih** — hafta bazlı
- **Yok** — düz liste

Grup başlıkları yapışkan (sticky) kalır — kaydırırken hangi grupta olduğunuzu görürsünüz. Grupları daraltıp genişletebilirsiniz.

### 5.5 KPI Şeridi

Ekranın üstünde, uygulanan filtrelere göre güncellenen metrikler:
- Toplam workshop sayısı
- Tamamlanma yüzdesi
- Aktif workshop sayısı
- Planlanmış workshop sayısı
- Açık open item sayısı
- Gap sayısı
- Requirement sayısı

### 5.6 Workshop Oluşturma

1. Sağ üstteki "New Workshop" butonuna tıklayın.
2. Formu doldurun:
   - İsim (örn: "Sales Order Management")
   - Tip: Fit-to-Standard / Deep Dive / Follow-up / Delta Design
   - Süreç Alanı: SD, FI, MM, vb.
   - Wave
   - Tarih ve saat
   - Facilitator (dropdown'dan seçin)
   - Lokasyon veya toplantı linki
3. Scope item bağlayın: Hangi L3 scope item(lar) bu workshop'ta ele alınacak.
4. "Create" → Workshop "Draft" olarak oluşturulur.

### 5.7 Workshop Bağımlılıkları

Bazı workshop'lar birbirine bağımlıdır. Bağımlılık eklemek için:

1. Workshop satırındaki üç nokta menüsünden "Manage Dependencies" seçin.
2. Bağımlılık tipi seçin:
   - **Must Complete First** — bu workshop başlamadan önce diğeri tamamlanmalı
   - **Information Needed** — diğer workshop'tan bilgi bekleniyor
   - **Cross-Module Review** — ortak konular var, birlikte değerlendirme gerekli
   - **Shared Decision** — aynı karar her iki workshop'u etkiliyor
3. Hedef workshop'u seçin → "Add Dependency"

Bağımlılığı olan workshop'larda sarı badge görünür. Tamamlanmamış bağımlılıkları olan workshop başlatılabilir ama uyarı verilir.

---

## 6. Ekran 3: Workshop Detail

### 6.1 Ekrana Erişim

Workshop Hub'da bir satıra tıklayarak veya doğrudan URL ile erişirsiniz.

### 6.2 Workshop Başlığı

Ekranın üstünde:
- Workshop kodu ve adı (örn: WS-SD-01 — Sales Order Management)
- Durum badge'i (Draft / Scheduled / In Progress / Completed)
- Tip badge'i (Fit-to-Standard / Deep Dive / vb.)
- Tarih, saat ve lokasyon
- Facilitator adı
- Bağlı scope item'lar
- Aksiyon butonları (duruma göre değişir)

### 6.3 Workshop Yaşam Döngüsü

**Draft → Scheduled:**
- Tarih, facilitator ve katılımcılar atandığında workshop "Scheduled" olarak işaretlenir.
- Henüz başlamamıştır.

**Scheduled → In Progress (Workshop Başlatma):**
- "Start Workshop" butonuna tıklayın.
- Sistem kontrol eder:
  - Scope item'ların L4 alt süreçleri var mı? Yoksa hata mesajı: "Önce alt süreçleri oluşturun."
  - L4'ler varsa → her biri için bir process step kaydı oluşturulur.
  - Workshop "In Progress" olur.
- Eğer bu multi-session workshop'un 2+ session'ıysa, önceki session'ın verileri otomatik yüklenir.

**In Progress → Completed (Workshop Tamamlama):**
- "Complete Workshop" butonuna tıklayın.
- Sistem kontrol eder:
  - Tek session veya son session ise: tüm step'lerde fit kararı verilmiş olmalı. Yoksa kapatılamaz.
  - Ara session ise: fit kararı verilmemiş step'ler kalabilir — "sonraki session'da ele alınacak" uyarısı verilir.
  - Açık open item'lar varsa: uyarı verilir ama engel olmaz.
  - Çözülmemiş cross-module flag'ler varsa: uyarı verilir.
- Onaylarsanız:
  - Workshop "Completed" olur.
  - Son session ise: fit kararları L4→L3→L2→L1 otomatik yansır.

**Completed → Reopen (yeniden açma, gerekirse):**
- "Reopen Workshop" butonuna tıklayın (yalnızca PM ve Module Lead).
- Sebep yazılması zorunludur.
- Workshop "In Progress"a döner.
- Değişiklikler revision log'a kaydedilir.

### 6.4 Altı Tab

Workshop Detail'de altı tab bulunur:

#### Tab 1: Process Steps (Süreç Adımları)

Bu, workshop'un ana çalışma alanıdır.

Her L4 sub-process bir kart olarak listelenir. Kart üzerinde:
- Adım numarası ve kodu (örn: 1. BD9.01)
- Alt süreç adı
- Fit kararı badge'i (henüz verilmediyse boş)
- Karar sayısı, OI sayısı, REQ sayısı

**Karta tıklayınca açılan detay alanı:**

**A) Önceki Session Bilgisi (multi-session ise):**
- Önceki session'daki fit kararı, notlar ve kararlar salt okunur olarak gösterilir.
- Mavi bilgi kutusu: "Önceki Session (WS-FI-03A): Gap — IC netting logic tartışıldı"

**B) BPMN Görüntüleme:**
- Bu adımın BPMN diyagramı varsa burada gösterilir.

**C) Tartışma Notları:**
- Serbest metin alanı. Workshop sırasında tartışma notlarını buraya yazın.

**D) Fit Kararı Seçici:**
- Üç seçenek: Fit / Partial Fit / Gap
- Her seçeneğin altında kısa açıklama:
  - Fit: "SAP standardı bu süreci tam karşılıyor"
  - Partial Fit: "Konfigürasyon veya workaround ile çözülebilir"
  - Gap: "SAP standardı karşılamıyor, geliştirme gerekir"
- Birini seçin → karar kaydedilir, badge güncellenir.

**E) Decision (Karar) Ekleme:**
- "Add Decision" butonuna tıklayın.
- Karar metni yazın (örn: "Sipariş tipi ZOR standart OR ile karşılanacak")
- Kararı veren kişiyi seçin
- Kategori seçin: Process / Technical / Scope / Organizational / Data
- Kaydet → Mor kartla step'in altına eklenir.

**F) Open Item (Aksiyon Maddesi) Ekleme:**
- "Add Open Item" butonuna tıklayın.
- Başlık yazın (örn: "aATP senaryosunu SAP ile değerlendirme toplantısı planla")
- Priority seçin: P1 (Kritik) / P2 (Yüksek) / P3 (Orta) / P4 (Düşük)
- Kategori seçin: Clarification / Technical / Scope / Data / Process / Organizational
- Atanan kişiyi seçin
- Son tarihi belirleyin
- Kaydet → Turuncu kartla step'in altına eklenir.
- OI otomatik olarak OI Hub'da da görünür.

**G) Requirement (Gereksinim) Ekleme:**
- "Add Requirement" butonuna tıklayın (sadece Partial Fit veya Gap kararı verildiyse aktif).
- Başlık yazın (örn: "Multi-plant ATP with priority-based allocation")
- Priority: P1 / P2 / P3 / P4
- Tip: Development / Configuration / Integration / Migration / Enhancement / Workaround
- Tahmini efor (saat)
- Açıklama
- Kaydet → Mavi kartla step'in altına eklenir.
- REQ "Draft" olarak oluşturulur, REQ Hub'da da görünür.

**H) Cross-Module Flag:**
- "Flag for Another Module" butonuna tıklayın.
- Hedef süreç alanını seçin (örn: MM)
- Açıklama yazın (örn: "ATP konfigürasyonu procurement sürecini etkiliyor")
- Kaydet → Sarı bayrak step'e eklenir.

**I) Dosya Ekleme:**
- "Attach File" butonuna tıklayın.
- Dosya seçin (max 50MB) — screenshot, doküman, BPMN export, vb.
- Kategori seçin: Screenshot / BPMN Export / AS-IS Document / TO-BE Document / Spec / Other
- Yükle → dosya step'e bağlanır.

#### Tab 2: Decisions (Kararlar)

Tüm step'lerdeki kararların birleştirilmiş listesi.
- Kaynak step bazlı gruplanmış
- Her kart: karar kodu, metin, karar veren, kategori
- Bu tab sadece bakış amaçlıdır — kararlar step'lerden eklenir.

#### Tab 3: Open Items

Workshop'tan doğan tüm OI'ların listesi.
- Priority, durum, atanan kişi, son tarih bilgileri
- OI koduna tıklayınca OI Hub'a gider
- Overdue olanlar kırmızı görünür

#### Tab 4: Requirements

Workshop'tan doğan tüm requirement'ların listesi.
- Priority, tip, durum, efor bilgileri
- REQ koduna tıklayınca REQ Hub'a gider

#### Tab 5: Agenda

Workshop gündemi:
- Saat, gündem maddesi, süre, tip (Session / Break / Demo / Discussion / Wrap-up)
- Gündem maddeleri düzenlenebilir

#### Tab 6: Attendees (Katılımcılar)

Katılımcı listesi:
- İsim, rol, organizasyon (Customer / Consultant / Partner / Vendor)
- Katılım durumu: Confirmed / Tentative / Declined / Present / Absent
- Workshop günü katılım takibi için "Present" / "Absent" olarak işaretleyin

### 6.5 Workshop Sonrası İşlemler

**Meeting Minutes Oluşturma:**
1. Tamamlanmış workshop'ta "Generate Minutes" butonuna tıklayın.
2. Format seçin: Markdown / Word (DOCX) / PDF
3. Dahil edilecek bölümleri seçin: Katılımcılar / Gündem / Step Sonuçları / Özet
4. "Generate" → Doküman oluşturulur ve indirilebilir.

**AI Özeti:**
1. "AI Summary" butonuna tıklayın.
2. Sistem workshop'taki tüm notları, kararları, OI'ları analiz eder.
3. Yönetici özeti, ana çıkarımlar ve risk vurguları üretilir.
4. Özet workshop'a kaydedilir, sonradan erişilebilir.

### 6.6 Multi-Session Workshop'lar

Büyük scope item'lar birden fazla session gerektirir.

**Örnek:** WS-FI-03A (Session 1/2) ve WS-FI-03B (Session 2/2)

**Session A kapandığında:**
- Değerlendirilen step'lerin kararları kaydedilir
- Değerlendirilemeyen step'ler boş kalır
- Fit kararları henüz L4'e yansıtılmaz (son session'da yansıtılacak)

**Session B başladığında:**
- Aynı L4 step'ler yeniden oluşturulur
- Her step'in yanında Session A'daki bilgiler görünür:
  - "Önceki Session: Fit" veya "Önceki Session: Değerlendirilmedi"
  - Önceki notlar ve kararlar salt okunur
- Session A'da boş kalan step'ler öncelikli olarak listelenir
- Session A'daki kararlar yeniden değerlendirilebilir (değişebilir)

**Session B kapandığında (son session):**
- Tüm step'lerde fit kararı zorunludur
- Kararlar L4→L3→L2→L1 yansıtılır

---

## 7. Ekran 4: Requirement & Open Item Hub

### 7.1 Ekrana Erişim

Sol menü → Explore → Requirements & Open Items

### 7.2 İki Tab

Ekranın üstünde iki ana tab:
- **Requirements Registry** — tüm requirement'lar
- **Open Item Tracker** — tüm open item'lar

Her tab'ın kendi filtreleri, gruplaması, KPI'ları ve aksiyon butonları vardır.

### 7.3 Requirements Registry

#### KPI Şeridi
- Toplam requirement sayısı
- P1 (Kritik) sayısı
- Draft / Under Review / Approved / In Backlog / Realized sayıları
- Cloud ALM'ye senkronize edilmiş sayısı
- Toplam tahmini efor (saat)

Sayılar uygulanan filtrelere göre güncellenir.

#### Filtreler
- **Arama:** REQ kodu, başlık veya scope item ile arayın
- **Durum:** Draft / Under Review / Approved / In Backlog / Realized / Verified / Deferred / Rejected
- **Priority:** P1 / P2 / P3 / P4
- **Tip:** Development / Configuration / Integration / Migration / Enhancement / Workaround
- **Alan:** FI / SD / MM / vb.
- **Wave:** 1 / 2 / 3 / 4
- **ALM Senkronize:** Evet / Hayır

#### Gruplama
- Durum / Priority / Alan / Tip / Scope Item / Wave / Workshop / Yok

#### Requirement Satırı
Her satırda:
- REQ kodu (tıklanabilir)
- Priority pill'i (P1=kırmızı, P2=turuncu, P3=mavi, P4=gri)
- Tip pill'i
- Fit durumu pill'i (Gap=kırmızı, Partial=sarı)
- Başlık
- Scope item kodu
- Alan
- Efor (saat)
- Durum akış göstergesi (lifecycle'daki konum)
- Cloud ALM simgesi (senkronize ise)

#### Requirement Detayı (satıra tıklayınca)
Satır genişler, altında detay paneli açılır:

**İzlenebilirlik Bloğu:**
- Kaynak workshop kodu (tıklayınca Workshop Detail açılır)
- Scope item kodu (tıklayınca Process Hierarchy'e gider)
- Process step kodu
- Oluşturan kişi ve tarih
- Onaylayan kişi ve tarih (varsa)
- Cloud ALM ID (senkronize ise)

**Bağlı Open Item'lar:**
- Bu requirement'ı bloklayan OI'ların listesi
- OI durumu gösterilir — tümü kapandıysa yeşil tik, açık varsa uyarı

**Bağımlılıklar:**
- Bu requirement'ın bağımlı olduğu diğer requirement'lar
- Bağımlılığın durumu (tamamlandı mı?)

**Ekler:**
- Bu requirement'a bağlı dosyalar

**Aksiyon Butonları:**
Duruma göre değişir:
| Mevcut Durum | Görünen Butonlar |
|-------------|-----------------|
| Draft | Submit for Review, Edit, Defer |
| Under Review | Approve, Reject, Return to Draft, Edit |
| Approved | Push to Cloud ALM, Defer, Edit |
| In Backlog | Mark Realized, Edit |
| Realized | Verify, Edit |
| Deferred | Reactivate |

Her butona tıklandığında yorum yazma alanı açılır. Yetkiniz yoksa buton gri ve tıklanamaz olur.

#### Batch İşlemler
Birden fazla requirement seçmek için her satırın solundaki onay kutusunu işaretleyin. Ardından üstteki "Batch Actions" menüsünden seçim yapın:
- Batch Approve — seçili tüm requirement'ları onayla
- Batch Defer — seçili tüm requirement'ları ertele
- Export — seçilileri Excel'e aktar

Batch onaylamada her requirement'ın alan yetkisi ayrı kontrol edilir. Yetkinizin olmadığı alanlar başarısız olur, diğerleri işlenir.

### 7.4 Open Item Tracker

#### KPI Şeridi
- Toplam open item sayısı
- Open / In Progress / Blocked / Closed sayıları
- Overdue (gecikmiş) sayısı — 10'dan fazla ise kırmızı uyarı
- P1 açık sayısı

#### Filtreler
- **Arama:** OI kodu, başlık veya atanan kişi ile arayın
- **Durum:** Open / In Progress / Blocked / Closed / Cancelled
- **Priority:** P1 / P2 / P3 / P4
- **Kategori:** Clarification / Technical / Scope / Data / Process / Organizational
- **Atanan Kişi:** Dropdown (tüm atanan kişilerden oluşur)
- **Alan ve Wave**
- **Overdue Toggle:** Kırmızı buton — sadece gecikmiş OI'ları gösterir

#### Open Item Satırı
- OI kodu
- Priority pill'i
- Durum pill'i
- Kategori pill'i
- Başlık
- Atanan kişi
- Son tarih (overdue ise kırmızı)
- Scope item
- Alan

Gecikmiş OI'ların satırı kırmızı tonda vurgulanır.

#### Open Item Detayı (satıra tıklayınca)

**İzlenebilirlik:** Workshop, scope item, process step referansları.

**Bağlı Requirement:**
- Bu OI bir requirement'ı blokluyorsa mavi bilgi kutusu:
  "Bağlı Requirement: REQ-042 — Bu OI kapatıldığında requirement onay süreci açılabilir"

**Blocked Sebebi:**
- Durum "Blocked" ise neden blocked olduğu gösterilir.

**Çözüm:**
- Durum "Closed" ise çözüm metni gösterilir.

**Aktivite Logu:**
- Tüm durum değişiklikleri, yeniden atamalar ve yorumlar kronolojik sırayla

**Aksiyon Butonları:**
| Mevcut Durum | Görünen Butonlar |
|-------------|-----------------|
| Open | Start Progress, Mark Blocked, Close, Cancel, Edit |
| In Progress | Close, Mark Blocked, Cancel, Edit |
| Blocked | Unblock, Cancel |
| Closed | Reopen |
| Cancelled | Reopen |

"Close" butonuna tıklandığında çözüm metni yazmak zorunludur.
"Mark Blocked" butonunda engellenme sebebi zorunludur.

**Yeniden Atama:**
- "Reassign" butonuna tıklayın → yeni kişi seçin → yorum yazın → kaydet.

### 7.5 OI Kapatma ve Requirement Etkisi

Bir open item kapatıldığında, eğer bir requirement'ı blokluyorsa, sistem otomatik kontrol eder:

1. Bloklanan requirement'ın tüm bağlı OI'ları kapandı mı?
2. Evet → requirement sahibine bildirim: "Tüm blocker'lar kalktı, REQ-042 artık onaylanabilir"
3. Hayır → henüz açık OI var, requirement hâlâ bloklu

Bu kontrol otomatiktir, kullanıcının ek işlem yapmasına gerek yoktur.

---

## 8. Ekran 5: Explore Dashboard

### 8.1 Ekrana Erişim

Sol menü → Explore → Dashboard

### 8.2 Widget'lar

Dashboard 10 widget içerir. Her widget belirli bir soruyu yanıtlar:

**1. Workshop Completion Burndown**
- Soru: "Plana göre neredeyiz?"
- Gösterim: Alan grafiği — tamamlanan workshop sayısının zamana göre değişimi
- İdeal çizgi vs. gerçek çizgi

**2. Wave Progress Bars**
- Soru: "Her wave kaçta kaç?"
- Gösterim: Yatay çubuklar — Wave 1: %92, Wave 2: %50, Wave 3: %14, Wave 4: %0

**3. Fit/Gap Trend**
- Soru: "Gap sayısı artıyor mu azalıyor mu?"
- Gösterim: Yığılmış alan grafiği — fit/partial/gap/pending zaman içindeki dağılımı

**4. Requirement Pipeline**
- Soru: "Requirement'lar hangi aşamada?"
- Gösterim: Huni (funnel) — Draft → Review → Approved → Backlog → Realized → Verified

**5. Open Item Aging**
- Soru: "OI'lar ne kadar süredir açık?"
- Gösterim: Çubuk grafik — 0-3 gün, 4-7 gün, 8-14 gün, 15+ gün

**6. Overdue Trend**
- Soru: "Gecikme artıyor mu?"
- Gösterim: Çizgi grafik — overdue OI sayısının zamana göre değişimi

**7. Gap Density Heatmap**
- Soru: "Hangi alan-wave kesişiminde en çok gap var?"
- Gösterim: Isı haritası — satırlar = süreç alanları, sütunlar = wave'ler, renk = gap yoğunluğu

**8. Facilitator Load Comparison**
- Soru: "İş yükü dengeli mi?"
- Gösterim: Gruplu çubuklar — facilitator başına tamamlanan/aktif/planlanan workshop sayısı

**9. Scope Coverage**
- Soru: "L4'lerin yüzde kaçı değerlendirildi?"
- Gösterim: Halka (donut) — assessed vs. pending

**10. Top 10 Open Items by Age**
- Soru: "En eski açık OI'lar hangileri?"
- Gösterim: Tablo — OI kodu, başlık, yaş (gün), atanan, priority

### 8.3 Tarih Aralığı

Dashboard'un üstündeki tarih seçici ile görüntülenen dönem değiştirilebilir:
- Son 1 hafta / Son 2 hafta / Son 1 ay / Tüm proje
- Özel tarih aralığı

### 8.4 Veri Kaynağı

Dashboard verileri günlük snapshot'lardan gelir. Her gün otomatik olarak projenin tüm metrikleri kaydedilir. Bu sayede "geçen haftaya göre ne değişti" görülebilir.

---

## 9. Scope Değişiklik Yönetimi

### 9.1 Ne Zaman Gerekir?

Explore sırasında scope değişmesi gerekebilir:
- Yeni bir scope item eklenmesi isteniyor
- Mevcut bir scope item çıkarılmak isteniyor
- Bir gap çok büyük çıktı, scope tartışılıyor
- Wave değişikliği gerekiyor

### 9.2 Scope Change Request (SCR) Oluşturma

1. Process Hierarchy → Matrix görünümüne gidin.
2. İlgili scope item satırında "Request Scope Change" butonuna tıklayın.
3. Formu doldurun:
   - Değişiklik tipi: Add to Scope / Remove from Scope / Change Wave / Split / Merge
   - Önerilen değer (yeni scope status veya wave)
   - Gerekçe (neden bu değişiklik gerekli)
4. "Submit" → SCR oluşturulur.

### 9.3 Etki Analizi

Sistem otomatik olarak hesaplar:
- Kaç workshop etkilenir (iptal/yeniden planlama)
- Kaç requirement etkilenir
- Kaç open item etkilenir
- Efor değişimi tahmini

Bu bilgi SCR'ın detayında gösterilir.

### 9.4 Onay Süreci

1. SCR oluşturulur → durum: "Requested"
2. PM veya BPO review eder → durum: "Under Review"
3. Onaylanır → durum: "Approved" / Reddedilir → durum: "Rejected"
4. Onaylanan SCR implement edilir:
   - Scope status güncellenir
   - Etkilenen draft workshop'lar iptal edilir
   - Tüm değişiklikler audit log'a yazılır

### 9.5 Geçmişi Görüntüleme

Process Hierarchy'de herhangi bir scope item'ın geçmişini görmek için:
1. Node'a tıklayın → Detay paneli
2. "Change History" tab'ı → tüm değişiklikler kronolojik sırada
   - Kim değiştirdi, ne zaman, eski değer → yeni değer, SCR referansı (varsa)

---

## 10. Cloud ALM Entegrasyonu

### 10.1 Genel Akış

```
Requirement "Approved" → "Push to Cloud ALM" → ALM Backlog Item oluşur → Realize fazında çalışılır
```

### 10.2 Tek Requirement Aktarma

1. REQ Hub'da approved durumdaki bir requirement'ı açın.
2. "Push to Cloud ALM" butonuna tıklayın (yalnızca PM veya Tech Lead).
3. Sistem ALM API'sine bağlanır ve backlog item oluşturur.
4. Başarılı ise:
   - Requirement durumu "In Backlog" olur
   - ALM ID geri yazılır (örn: ALM-0234)
   - Senkronize simgesi görünür
5. Hata olursa:
   - Hata mesajı gösterilir
   - Tekrar dene butonu aktif olur

### 10.3 Toplu Aktarma

1. REQ Hub'da filtre uygulayın: Durum = Approved
2. Üstteki "Sync All to Cloud ALM" butonuna tıklayın.
3. Onay penceresi: "N adet requirement ALM'ye aktarılacak. Devam?"
4. "Confirm" → toplu aktarım başlar.
5. Sonuç raporu: N başarılı, M başarısız (hata detaylarıyla).

### 10.4 Senkronizasyon Durumları

| Durum | Anlamı | Simge |
|-------|--------|-------|
| — | Henüz aktarılmadı | Boş |
| Synced | Başarıyla aktarıldı | Yeşil bulut |
| Sync Error | Aktarım başarısız | Kırmızı bulut |
| Out of Sync | ProjektCoPilot'ta değişiklik yapıldı, ALM güncellenmedi | Sarı bulut |

---

## 11. Raporlama ve Export

### 11.1 Meeting Minutes

Workshop tamamlandıktan sonra → Workshop Detail → "Generate Minutes"
- Format: Markdown / Word / PDF
- İçerik: Katılımcılar + Gündem + Step Sonuçları + Özet

### 11.2 AI Summary

Workshop Detail → "AI Summary"
- Otomatik üretilen yönetici özeti
- Ana çıkarımlar, risk vurguları, sonraki adımlar

### 11.3 Steering Committee Sunumu

Dashboard → "Export Report" → format seçin (PPTX / PDF)
- 6 slide'lık otomatik sunum
- Executive summary, wave progress, fit/gap dağılımı, requirement pipeline, riskler, sonraki adımlar

### 11.4 Excel Export

REQ Hub veya OI Hub → "Export" butonu
- Mevcut filtrelere göre filtrelenmiş veri
- Excel (XLSX) formatında indirilir
- Tüm alanlar dahil

---

## 12. Sık Sorulan Sorular

**S: Workshop'ta yanlışlıkla yanlış fit kararı verdim. Nasıl düzeltirim?**

C: Workshop hâlâ "In Progress" ise → ilgili step'e tıklayın → fit kararını değiştirin. Workshop "Completed" ise → PM veya Module Lead "Reopen Workshop" butonuyla workshop'u yeniden açar, sebep yazar. Değişikliği yapın, tekrar kapatın. Tüm değişiklikler revision log'da kalır.

**S: Bir requirement birden fazla workshop'tan mı doğar?**

C: Hayır. Her requirement tek bir workshop'taki tek bir process step'ten doğar. Ama bir requirement başka requirement'lara bağımlı olabilir (dependency). Farklı workshop'lardan doğan requirement'lar dependency ile bağlanır.

**S: Open item'ı başka birine nasıl atarım?**

C: OI Hub'da ilgili OI'ya tıklayın → "Reassign" butonuna tıklayın → yeni kişiyi seçin → yorum yazın → kaydet. Atama değişikliği aktivite loguna kaydedilir.

**S: Scope item'ı yanlışlıkla "Out of Scope" yaptım. Geri alabilirim mi?**

C: Evet. Process Hierarchy → Matrix → ilgili satırda scope'u "In Scope"a çevirin. Veya formal yol: "Request Scope Change" ile SCR açın, onay sürecinden geçirin. Her iki durumda da değişiklik loglanır.

**S: Neden "Approve" butonu tıklanamıyor?**

C: Üç olası sebep:
1. Yetkiniz yok — sadece PM, Module Lead (kendi alanı) ve BPO onaylayabilir.
2. Requirement alan dışı — Module Lead olarak SD rolünüz var ama FI requirement'ı onaylamaya çalışıyorsunuz.
3. Blocking OI — bu requirement'ı bloklayan açık open item var. Önce OI'ları kapatın.

**S: Cloud ALM senkronizasyonu başarısız oldu. Ne yapmalıyım?**

C: REQ detayında hata mesajını kontrol edin. Genelde bağlantı hatası veya ALM tarafında yetki sorunudur. "Retry" butonu ile tekrar deneyin. Sorun devam ederse sistem yöneticinize bildirin.

**S: Dashboard verileri güncel mi?**

C: Dashboard günlük snapshot'lardan beslenir. En son snapshot genellikle bugünün sabahından alınmıştır. Anlık veriler için REQ Hub ve OI Hub'daki KPI şeritlerini kullanın — onlar gerçek zamanlıdır.

**S: Dosya yükleme limiti ne kadar?**

C: Tek dosya maksimum 50MB. Proje başına toplam 500MB. Desteklenen formatlar: PDF, DOCX, XLSX, PNG, JPG, SVG, BPMN, XML, TXT.

**S: Cross-module flag ne anlama geliyor?**

C: Bir workshop step'inde "bu konu başka bir modülü de ilgilendiriyor" demektir. Örneğin SD workshop'unda ATP konfigürasyonunun MM'deki procurement sürecini etkilediğini işaretlersiniz. Bu flag, MM workshop'u planlanırken görünür ve o workshop'ta ele alınır.

**S: Tamamlanmış bir workshop'un meeting minutes'ını sonradan üretebilir miyim?**

C: Evet. Workshop Detail → "Generate Minutes" butonu her zaman aktiftir. İstediğiniz zaman yeniden oluşturabilirsiniz.

---

## 13. Kısayollar ve İpuçları

### 13.1 Hızlı Gezinme

- `Ctrl + K` veya `/` → Global arama (herhangi bir REQ, OI, Workshop veya scope item'ı kod ile bulun)
- Sol menüde son ziyaret edilen 5 sayfa "Recent" altında listelenir

### 13.2 Verimli Workshop Yürütme

- Workshop öncesi L4 seeding'i tamamlayın — workshop başlatılamaz yoksa.
- Agenda'yı önceden hazırlayın — her step için tahmini süre verin.
- BPMN diyagramını yükleyin — tartışmayı hızlandırır.
- Notları gerçek zamanlı yazın — sonradan hatırlamak zordur.
- Her step için en az bir decision kaydı oluşturun — kararlar kaybolmasın.
- OI'ları specific tutun — "araştır" yerine "H. Demir şu konuyu şu tarihe kadar araştırsın."

### 13.3 Requirement Yönetimi İpuçları

- P1 requirement'ları hemen review'a gönderin — bekletmeyin.
- Effort tahminlerini büyük girin — sonradan azaltmak artırmaktan kolaydır.
- Her requirement'a en az bir cümlelik açıklama yazın.
- Blocking OI'ları takip edin — OI kapanmadan REQ onaylanamaz.
- Haftalık batch approval toplantısı yapın — tek tek onaylamak verimsizdir.

### 13.4 Open Item Takip İpuçları

- Son tarih koymadan OI oluşturmayın — tarihsiz OI'lar unutulur.
- Overdue toggle'ı günlük kontrol edin.
- Blocked OI'ları özel takip edin — neden blocked olduğunu düzenli sorun.
- OI kapatırken çözüm metnini detaylı yazın — gelecekte referans olur.

### 13.5 Raporlama İpuçları

- Steering committee'den önce Dashboard'daki trend grafiklerine bakın.
- "Export Report" ile otomatik sunum üretin, sonra özelleştirin.
- Gap density heatmap en çok dikkat çeken widget'tır — kırmızı bölgeleri açıklamaya hazır olun.

---

## Sözlük

| Terim | Açıklama |
|-------|----------|
| **L1** | Value Chain — en üst süreç seviyesi (Core, Management, Support) |
| **L2** | Process Area — fonksiyonel alan (FI, SD, MM, vb.) |
| **L3** | Scope Item — SAP Best Practice süreç tanımı (J58, BD9, vb.) |
| **L4** | Sub-Process — L3 altındaki detay adım (J58.01, BD9.03, vb.) |
| **Fit** | SAP standardı bu süreci karşılıyor |
| **Partial Fit** | Konfigürasyon veya workaround ile çözülebilir |
| **Gap** | SAP standardı karşılamıyor, geliştirme gerekir |
| **Fit-to-Standard** | SAP standardıyla karşılaştırma workshop'u |
| **Scope Item** | SAP Best Practice kataloğundaki süreç tanımı |
| **Wave** | Uygulama dalgası — hangi sırayla workshop yapılacak |
| **Requirement** | Gap veya Partial Fit sonucu doğan gereksinim |
| **Open Item** | Araştırılması veya takip edilmesi gereken aksiyon maddesi |
| **Decision** | Workshop'ta alınan formal karar |
| **Process Step** | Workshop bağlamında ele alınan L4 alt süreç |
| **SCR** | Scope Change Request — scope değişiklik talebi |
| **Cloud ALM** | SAP Application Lifecycle Management — backlog yönetim sistemi |
| **BPMN** | Business Process Model and Notation — süreç diyagramı standardı |
| **Facilitator** | Workshop'u yöneten SAP danışmanı |
| **BPO** | Business Process Owner — müşteri tarafında süreç sahibi |
| **UAT** | User Acceptance Testing — kullanıcı kabul testi |
| **Realize** | SAP Activate'in geliştirme/konfigürasyon fazı (Explore'dan sonra) |
| **Signavio** | SAP'ın süreç modelleme aracı |

---

*ProjektCoPilot — Explore Phase Manager User Guide v1.0*
*Son güncelleme: 10 Şubat 2026*
