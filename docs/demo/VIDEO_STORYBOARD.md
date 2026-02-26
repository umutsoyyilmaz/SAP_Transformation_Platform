# SAP Transformation Platform — Video Storyboard (3-4 dk)

> **Format:** Loom / screen recording
> **Amac:** Toplanti oncesi async izleme, LinkedIn paylasim
> **Ton:** Profesyonel ama enerjik, SAP terminolojisi dogal kullanilmali
> **Cozunurluk:** 1440x900, tarayici tam ekran, sidebar acik

---

## Sahne 1 — Hook (0:00 - 0:15)

**Kayit:** Program karti yuklu Dashboard ekrani

**Anlatim:**
> "SAP donusum projenizin requirement'larindan go-live'a kadar
> her asamasini tek platformda yonetebilseniz nasil olurdu?
> Anadolu Gida'nin S/4HANA projesine bakalim."

**Not:** Hizli, dikkat cekici. Ilk 5 saniyede deger onerisi.

---

## Sahne 2 — Proje Saglik Skoru (0:15 - 0:45)

**Kayit:** Dashboard > Health score ring animasyonu > KPI kartlari

**Anlatim:**
> "Saglik skoru 6 canli sinyalden hesaplaniyor:
> test gecis orani, defect yaslandirma, RAID durumu,
> acik kalemler, takvim ve kapsam.
> Realize fazinda, Sprint 3 aktif. Her seyi tek bakista goruyorsunuz."

**Aksiyon:** Health score ring'in dolmasini goster, sonra KPI kartlarini tara.

---

## Sahne 3 — Surec Zekasi (0:45 - 1:15)

**Kayit:** Explore > L1 > L2 > L3 > L4 agac acilisi > Workshop detay

**Anlatim:**
> "Signavio'daki surec hiyerarsiniz burada.
> Materials Management > Purchasing > PO Management.
> Her L4 adim icin Fit-to-Standard karari var.
> Workshop'larda alinmis kararlar, acik kalemler ve requirement'lar."

**Aksiyon:** L1'den L4'e yavasce ac (agac animasyonu), sonra bir workshop'a gir.

---

## Sahne 4 — Izlenebilirlik (1:15 - 2:00)

**Kayit:** Backlog > INT-SD-001 sec > Traceability graf

**Anlatim:**
> "WRICEF backlog'unda e-Fatura arayuzu: INT-SD-001.
> Izlenebilirlik grafini acinz — tam zincir:
> Requirement, fonksiyonel spec, teknik spec, test case ve defect.
> Hicbir oge kopuk degil. Denetim icin tam iz suresi."

**Aksiyon:** Backlog listesinden item sec, traceability sekmesine tikla, grafin render olmasini bekle.

**Not:** Bu sahne en onemli "wow" ani — yavascca goster.

---

## Sahne 5 — Test Kalitesi (2:00 - 2:30)

**Kayit:** Test Plans > SIT dashboard > Defect listesi

**Anlatim:**
> "SIT Cycle 1: 18 test case, 14 pass, 2 fail.
> 8 defect — S1 seviyesinde e-Fatura timeout sorunu.
> Her defect SLA'ya bagli: S1 icin 1 saat yanit, 4 saat cozum.
> Test > Requirement geriye dogru izleme tek tikla."

**Aksiyon:** SIT dashboard grafiklerini goster, defect listesine gec, bir defect ac.

---

## Sahne 6 — Go-Live Karar Ani (2:30 - 3:15)

**Kayit:** Cutover > CUT-001 > Go/No-Go listesi > Hypercare

**Anlatim:**
> "Wave 1 cutover sureci aktif — 56 saatlik pencere.
> Go/No-Go kontrol listesi: 5 go, 1 pending, 1 no_go.
> Yetkilendirmede 12 SOD cakismasi blocker.
> Rollback deadline Pazar 02:00.
> Hypercare'de 6 incident — P1 odeme sorunu 210 dakikada cozulmus.
> Gercek bir go-live karar ani, tum veriler tek ekranda."

**Aksiyon:** Go/No-Go listesini yavasce tara (renkler gorunsun), sonra hypercare paneline gec.

---

## Sahne 7 — Kapaniş (3:15 - 3:30)

**Kayit:** AI Insights ekrani veya Dashboard'a donus

**Anlatim:**
> "AI gomulu: requirement analiz, test case onerisi, risk skorlama.
> Requirement'tan go-live'a, tek platform.
> Demo gormek icin iletisime gecin."

**Aksiyon:** Ekran logo/dashboard'da donar.

---

## Teknik Notlar

| Parametre | Deger |
|---|---|
| Cozunurluk | 1440x900 veya 1920x1080 |
| Tarayici | Chrome (koyu tema devre disi) |
| Font boyutu | Varsayilan (%100 zoom) |
| Kayit araci | Loom, OBS veya QuickTime |
| Ses | Dis mikrofon (laptop mic degil) |
| Muzik | Yok (profesyonel ton) |
| Altyazi | Loom otomatik veya SRT |

## Kayit Oncesi Kontrol

- [ ] `make demo-restore && make run`
- [ ] Login: `admin@anadolu.com` / `Anadolu2026!`
- [ ] Program secili
- [ ] Bildirimler / popup'lar kapali
- [ ] Desktop temiz (kisisel dosya gorunmesin)
- [ ] Tarayici sekmeleri sadece demo icin
- [ ] Kayit araci test edildi
