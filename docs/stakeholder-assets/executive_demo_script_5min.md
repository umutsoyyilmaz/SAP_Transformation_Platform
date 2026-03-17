# SAP Transformation Platform — 5 Dakika Demo Script

> **Hedef kitle:** C-level, SAP program yoneticileri, Big4 danismanlar
> **Sure:** 5 dakika canli demo + 30 sn AI bonus
> **Mesaj:** "Tek platformda SAP donusum yonetimi — requirement'tan go-live'a"

---

## Pre-Demo Kontrol Listesi (5 dk once)

- [ ] `make demo-restore && make run` (veya ilk kez: `make demo-reset && make run`)
- [ ] Tarayici: `http://localhost:5001`
- [ ] Login: `admin@anadolu.com` / `Anadolu2026!`
- [ ] Program sec: **"Anadolu Gida — S/4HANA Cloud Donusum"**
- [ ] Ekran cozunurlugu: 1440x900, zoom %100
- [ ] Ikinci sekme: Traceability gorunumu on-yukle (Perde 3 icin)
- [ ] Wifi stabil mi? (Yerel calisiyor, internet gerekmez)

---

## Perde 1 — Dashboard: Buyuk Resim (0:00 - 1:00)

**Ekran:** Ana Dashboard

**Gosterilecekler:**
- Saglik skoru halka grafigi (health score ring)
- KPI kartlari: faz ilerlemesi, acik defect, RAID ozeti
- Son aktivite akisi

**Konusma metni:**
> "Anadolu Gida'nin S/4HANA donusum projesindeyiz. Realize fazinda, %45 ilerleme.
> Saglik skoru 6 sinyalden hesaplaniyor: test gecis orani, defect yaslandirma,
> RAID kirmizi ogeleri, acik kalemler, takvim sapmasi ve kapsam yuzdesi.
> Tek bakista projenin nabzini goruyorsunuz."

**Wow ani:** Saglik skoru halkasinin animasyonlu yuklenisi.

**Gecis:** KPI kartindan RAID'e tikla.

---

## Perde 2 — Explore: Surec Zekasi (1:00 - 2:00)

**Ekran:** Explore > Surec Hiyerarsisi (L1-L4)

**Gosterilecekler:**
- L1 (Materials Management) > L2 (Purchasing) > L3 (PO Management) > L4 adimlari
- Fit/Gap renk kodlari (yesil=fit, sari=partial, kirmizi=gap)
- Bir workshop detayina gir: katilimcilar, agenda, kararlar, acik kalemler

**Konusma metni:**
> "Signavio'daki surec hiyerarsinizi platformda yonetiyorsunuz.
> 5 L1 deger zinciri, 50+ L3 senaryo, 200+ L4 adim.
> Her adim icin Fit-to-Standard karari var. Workshop WS-MM-01'e bakalim:
> 12 Fit, 3 Gap karari. Gap kararlarindan otomatik requirement olusturuluyor."

**Wow ani:** L1'den L4'e acilis animasyonu — tam Signavio deneyimi.

**Gecis:** Gap olan bir requirement'a tikla > Backlog'a gecis.

---

## Perde 3 — Izlenebilirlik: Requirement'tan Defect'e (2:00 - 3:00)

**Ekran:** Backlog (WRICEF) > Traceability gorunumu

**Gosterilecekler:**
- 28 WRICEF ogesi listesi (W/R/I/C/E/F tipleri, sprint atamasi)
- INT-SD-001 (e-Fatura GIB Arayuzu) secimi
- Traceability graf: REQ-SD-001 > INT-SD-001 > TC-SD-002 > DEF-SD-001

**Konusma metni:**
> "WRICEF backlog'unda 28 gelistirme ogesi var — 3 sprint'e dagilmis.
> e-Fatura arayuzune bakalim: INT-SD-001.
> Izlenebilirlik grafinde tam zinciri goruyorsunuz:
> Requirement > Fonksiyonel Spec > Teknik Spec > Test Case > Defect.
> Bu S1 defect — GIB timeout sorunu — hala cozum surecinde.
> Hicbir oge kopuk degil, her sey izlenebilir."

**Wow ani:** Traceability grafinin gorsel render'i — tek tikla tam zincir.

**Gecis:** Defect'e tiklayip Test Yonetimi'ne gec.

---

## Perde 4 — Test Kalitesi (3:00 - 4:00)

**Ekran:** Test Management > SIT Plan Dashboard > Defect Listesi

**Gosterilecekler:**
- SIT Master Plan durumu: 18 test case, 4 cycle
- SIT Cycle 1 sonuclari: 14 pass, 2 fail, 1 blocked, 1 deferred
- Defect listesi: severity dagilimi (1x S1, 2x S2, 3x S3, 1x S4)
- DEF-SD-001 detay: adimlar, SLA, atama

**Konusma metni:**
> "SIT Cycle 1 tamamlandi: 18 test case'den 14'u pass.
> 8 defect acildi — 1 S1 (e-Fatura timeout), 2 S2 (MES hurda, CPI retry).
> Her defect otomatik olarak tetikleyen test case'e ve SLA'ya bagli.
> S1 defect icin SLA: 1 saat icerisinde yanit, 4 saatte cozum."

**Wow ani:** Defect > Test Case > Requirement geri izleme tek tikla.

**Gecis:** "Simdi go-live hazirligina bakalim."

---

## Perde 5 — Go-Live Karar Ani (4:00 - 5:00)

**Ekran:** Cutover Hub > CUT-001 (Wave 1 executing)

**Gosterilecekler:**
- Cutover plani: "executing" durumu, 56 saatlik pencere, runbook timeline
- 18 runbook gorevi: 6 completed, 2 in_progress, 10 not_started
- Go/No-Go kontrol listesi: **5 go, 1 no_go (auth SOD), 1 pending (training)**
- Hypercare paneli: 6 incident, SLA durumu

**Konusma metni:**
> "Wave 1 cutover'i Cuma 22:00'de basladi — 56 saatlik pencere.
> Runbook'ta 18 gorev var: veri gocu, arayuz aktivasyonu, yetkilendirme.
> Go/No-Go kontrol listesine bakin:
> 5 go — test, veri, arayuz, prova, steering onay.
> 1 pending — egitim tamamlanma %87, hedef %90. Cumartesi crash session planlandi.
> 1 no_go — 12 SOD cakismasi cozulmedi. Rollback deadline: Pazar 02:00.
> Bu gercekci bir karar ani. Platform her veriyi tek ekranda sunuyor."

**Wow ani:** Go/No-Go'daki kirmizi blocker — gercek hayattaki gerilim.

**Gecis:** (Zaman varsa) "Son olarak AI yeteneklerine bakalim."

---

## Bonus — AI Insights (5:00 - 5:30)

**Ekran:** AI Insights

**Gosterilecekler:**
- AI kullanim gecmisi (audit log)
- Prompt katalogu: requirement analiz, test case uretimi, risk degerlendirme

**Konusma metni:**
> "AI butun platforma gomulu: requirement gap analizi, test case onerisi,
> RAID risk skorlamasi, cutover optimizasyonu.
> Tum AI cagrilari audit edilir — maliyet, token, model bilgisi kayit altinda."

---

## Demo Sonrasi

- Sorulari yanitsayin
- Demo verisini sifirlamak icin: `make demo-restore`
- Ayni gun ikinci demo icin: `make demo-restore && make run`

---

## Hizli URL Referansi

| Ekran | Nav Yolu |
|---|---|
| Dashboard | Sol menu > Dashboard |
| Explore Hiyerarsi | Sol menu > Explore > Surec Hiyerarsisi |
| Workshop Detay | Explore > Workshops > WS-MM-01 |
| WRICEF Backlog | Sol menu > Realize > Backlog |
| Traceability | Backlog item > Traceability sekme |
| Test Management | Sol menu > Test > Test Plans |
| Defect Listesi | Test > Defects |
| Cutover Hub | Sol menu > Deploy > Cutover |
| Go/No-Go | Cutover > CUT-001 > Go/No-Go sekme |
| Hypercare | Cutover > CUT-001 > Hypercare sekme |
| AI Insights | Sol menu > AI Insights |
