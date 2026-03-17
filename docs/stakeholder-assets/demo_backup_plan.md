# SAP Transformation Platform — Demo Yedek Plan

> Internet kesilirse, sistem cokerse veya beklenmedik bir sorun olursa ne yapilir?

---

## Yedek Strateji Ozeti

| Risk | Cozum | Hazirlik |
|---|---|---|
| Internet kesildi | Yerel calisir — internet gerekmez | `make vendor-assets` (bir kez) |
| DB bozuldu | Snapshot geri yukle | `make demo-restore` |
| Uygulama crash | Yeniden baslat | `make run` |
| Ekran paylasim sorunu | Onceden kaydedilmis video | Loom linki hazir |
| Bilgisayar ariza | Telefondaki video | Video'yu telefona indir |

---

## 1. Offline Demo (Internet Kesilirse)

Platform **tamamen yerel** calisir:

- **Flask sunucu:** `localhost:5001` — internet bagimsiz
- **SQLite veritabani:** Yerel dosya (`instance/sap_platform_dev.db`)
- **Vendor JS:** Chart.js ve Frappe Gantt artik yerel (`static/vendor/`)
- **Service Worker:** PWA cache ile onceden ziyaret edilen sayfalari saklar

**Yapilmasi gereken (bir kez):**
```bash
make vendor-assets    # CDN kutuphanelerini yerel indir
make demo-reset       # DB hazirla + snapshot al
```

Bundan sonra internet olmadan tam demo yapilabilir.

**Not:** AI Insights ekrani LLM API'ye baglidir — internet yoksa AI sorgulari calismaz.
Diger tum ekranlar (Dashboard, Explore, Test, Cutover, RAID) tamamen offline calisir.

---

## 2. Demo Reset (DB Bozulursa)

Her demo sonrasi veya sorun durumunda:

```bash
# Hizli geri yukleme (<1 saniye)
make demo-restore

# Eger snapshot da bozuksa (tam sifirdan)
make demo-reset       # ~15 saniye
```

**Onerilen akis:**
1. Demo gunu sabahi: `make demo-reset` (temiz snapshot olustur)
2. Her demo arasi: `make demo-restore` (snapshot'tan geri yukle)
3. Acil durum: `make reset` (fallback — ayni seyi yapar)

---

## 3. Onceden Kaydedilmis Video

Video kaydi her zaman yedek olarak hazir olmali:

- **Nerede:** Loom hesabinda + yerel bilgisayarda
- **Uzunluk:** 3-4 dakika (VIDEO_STORYBOARD.md'ye gore)
- **Paylasim:** Toplanti davetine Loom linki ekle
- **Telefon:** Video'yu telefona da indir (bilgisayar arizasi icin)

**Video ile demo yapma senaryosu:**
> "Platformu canli gostermek isterdim ama teknik bir sorun var.
> Size 3 dakikalik kaydi gostereyim, sonra sorularinizi yanitleyelim."

---

## 4. Demo Sirasinda Sorun Cikarsa

### Ekran dondu / uygulama yanitlamiyor
1. Tarayici sekmesini kapat
2. Terminal'de `Ctrl+C` > `make run`
3. Tekrar login ol
4. "Kucuk bir teknik sorun, hemen duzeltiyorum" de

### Yanlis veri gorunuyor / ekran bos
1. `Ctrl+C` > `make demo-restore` > `make run`
2. 15 saniye icerisinde temiz veriyle geri don

### Login calismadi
- Kullanici: `admin@anadolu.com`
- Sifre: `Anadolu2026!`
- Alternatif: `pm@anadolu.com` / `Test1234!`
- Son care: Dev mode'da auth devre disi (`API_AUTH_ENABLED=false`)

### Belirli bir ekran yuklenmiyor
- Diger ekranlardan devam et (5 perde var, 1 tanesi atlansa demo calismaya devam eder)
- "Bu ozellik uzerinde calisiyoruz" ile gecistir

---

## 5. Demo Oncesi Checklist

```
[ ] make demo-restore && make run (veya ilk kez: make demo-reset)
[ ] http://localhost:5001 aciliyor mu?
[ ] Login basarili mi?
[ ] Dashboard veri gorunuyor mu?
[ ] Explore > L1-L4 aciliyor mu?
[ ] Cutover > Go/No-Go renkleri gorunuyor mu?
[ ] Loom video linki hazir mi? (yedek)
[ ] Telefonda video var mi? (son yedek)
[ ] Ekran paylasim araci test edildi mi?
[ ] Bildirimler / mesajlar sessize alindi mi?
```

---

## 6. Iletisim Sablonu (Sorun Durumunda)

**Eger demo yapilamayacaksa:**

> Merhaba [isim],
>
> Demo sirasinda teknik bir sorun yasadik. Size platformun
> 3 dakikalik tanitim videosunu gonderiyorum: [Loom linki]
>
> Canli demo icin uygun bir zamani belirlersek memnun olurum.
>
> Saygilarimla,
> [isim]
