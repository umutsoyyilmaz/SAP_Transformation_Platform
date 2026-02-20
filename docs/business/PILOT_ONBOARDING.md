# SAP Transformation Platform — Pilot Onboarding Runbook

> **Version:** 1.0 | **Son Güncelleme:** 2026-02-13 | **Hedef:** Yeni müşteri/pilot ortamını 30 dakikada ayağa kaldırmak

---

## Ön Koşullar

| # | Gereksinim | Kontrol |
|---|-----------|---------|
| 1 | Python 3.11+ yüklü | `python --version` |
| 2 | Git yüklü | `git --version` |
| 3 | PostgreSQL 15+ (prod) veya SQLite (demo) | `psql --version` |
| 4 | Redis 7+ (opsiyonel — rate limiter/cache) | `redis-cli ping` |
| 5 | Proje klonlanmış | `git clone <repo-url>` |
| 6 | `.env` veya ortam değişkenleri hazır | Aşağıdaki tabloya bakınız |

### Ortam Değişkenleri

| Değişken | Zorunlu | Varsayılan | Açıklama |
|----------|---------|------------|----------|
| `APP_ENV` | Hayır | `development` | `development` / `testing` / `production` |
| `DATABASE_URL` | Evet (prod) | SQLite | PostgreSQL URI: `postgresql://user:pass@host:5432/dbname` |
| `REDIS_URL` | Hayır | `redis://localhost:6379/0` | Rate limiter / cache |
| `GEMINI_API_KEY` | Hayır | — | Google Gemini AI entegrasyonu |
| `SECRET_KEY` | Evet (prod) | auto | Flask session key |
| `TENANT_ID` | Hayır | `default` | Multi-tenant modda aktif tenant |

---

## Adım 1: Ortam Kurulumu (5 dk)

```bash
# 1. Sanal ortam oluştur
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Ortam doğrula
make check  # veya: python -c "from app import create_app; print('OK')"
```

---

## Adım 2: Veritabanı Oluşturma (3 dk)

### Seçenek A — SQLite (Demo / PoC)

```bash
# Otomatik — ilk çalıştırmada oluşur
make init-db
# veya
python -c "
from app import create_app
from app.models import db
app = create_app()
with app.app_context():
    db.create_all()
    print(f'✅ {len(db.metadata.tables)} tablo oluşturuldu')
"
```

### Seçenek B — PostgreSQL (Pilot / Prod)

```bash
# 1. Database oluştur
createdb sap_platform_pilot

# 2. ENV ayarla
export DATABASE_URL="postgresql://user:pass@localhost:5432/sap_platform_pilot"

# 3. Migration çalıştır
flask db upgrade

# 4. Doğrula
python scripts/migrate_tenants.py --verify
```

---

## Adım 3: Tenant Kaydı (2 dk) — Opsiyonel

> Tek müşteri kurulumunda bu adım atlanabilir (varsayılan `default` tenant kullanılır).

```bash
# Yeni tenant oluştur
make tenant-create ID=acme NAME="ACME Corp"

# Tenant DB'yi başlat
make tenant-init ID=acme

# Tenant listesini kontrol et
make tenant-list
```

Sonuç: `tenants.json` dosyasında yeni tenant kaydı + veritabanı hazır.

---

## Adım 4: Demo Verisi Yükleme (2 dk) — Opsiyonel

```bash
# Tam demo ortamı (OTC + PTP senaryoları)
make seed-demo

# Sadece OTC senaryosu
python scripts/seed_quick_demo.py --scenario otc

# Sadece PTP senaryosu
python scripts/seed_quick_demo.py --scenario ptp

# Mevcut veriyi silmeden ek veri ekle
python scripts/seed_quick_demo.py --no-reset
```

Demo verisi içeriği:
- 1 program (GlobalTech — S/4HANA Cloud) + 6 faz + gates
- 4 süreç alanı (OTC, PTP, FIN, P2M) → 24 L4 süreç
- 2 tamamlanmış Fit-to-Standard workshop
- 10 gereksinim + 4 açık madde + 4 karar
- 6 WRICEF backlog item + 4 config item + 1 sprint
- 10 test case + 8 execution + 3 defect (1x S1)
- 3 risk + 3 action + 1 issue + 1 decision (RAID)
- 7 audit trail kaydı

---

## Adım 5: Kullanıcı / Admin Ayarları (3 dk)

### Demo Kullanıcıları (seed ile otomatik gelir)

| Kullanıcı ID | Ad | Rol |
|-------------|-----|-----|
| `ahmet.yilmaz` | Ahmet Yılmaz | Program Manager |
| `elif.demir` | Elif Demir | Solution Architect |
| `burak.aydin` | Burak Aydın | Business Process Owner |
| `canan.ozturk` | Canan Öztürk | Explore Lead / Facilitator |
| `deniz.kaya` | Deniz Kaya | Technical Lead |
| `murat.celik` | Murat Çelik | Module Lead (MM) |
| `selin.arslan` | Selin Arslan | Test Manager |

### İlk Admin Oluşturma (custom kurulumda)

```bash
# Flask shell ile
flask shell
>>> from app.models.program import TeamMember
>>> from app.models import db
>>> admin = TeamMember(program_id=1, user_id="admin", name="Admin User", role="admin")
>>> db.session.add(admin)
>>> db.session.commit()
```

---

## Adım 6: Uygulamayı Başlat (1 dk)

```bash
# Development
make run
# → http://localhost:5001

# Production (Gunicorn)
gunicorn wsgi:app -b 0.0.0.0:8000 -w 4

# Docker
docker compose -f docker/docker-compose.yml up -d
# → http://localhost:8000
```

---

## Adım 7: Doğrulama Kontrol Listesi

| # | Kontrol | Komut / Yöntem | Beklenen |
|---|---------|---------------|----------|
| 1 | Uygulama başlıyor | `curl http://localhost:5001/api/health` | `{"status":"healthy"}` |
| 2 | DB bağlantısı | Health endpoint'te `db_status` | `ok` |
| 3 | Program görünüyor | Program sayfasını aç | GlobalTech listelenir |
| 4 | Explore çalışıyor | Workshop listesini aç | 2 workshop görünür |
| 5 | Backlog çalışıyor | Backlog Board'u aç | 6 WRICEF item |
| 6 | Test Management | Test Plan sayfası | 10 test case |
| 7 | RAID | RAID sayfası | 3 risk, 1 issue |
| 8 | Metrikler | Dashboard | Grafikler yükleniyor |

---

## Sorun Giderme

### Sık Karşılaşılan Hatalar

| Hata | Çözüm |
|------|-------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` yeniden çalıştır |
| `OperationalError: no such table` | `make init-db` veya `flask db upgrade` |
| `Connection refused (Redis)` | Redis başlat veya `REDIS_URL` kaldır — uygulama Redis olmadan çalışır |
| `GEMINI_API_KEY not set` | AI özellikleri için opsiyonel — platform AI olmadan tam çalışır |
| `Tenant not found` | `make tenant-list` ile kontrol et, `tenants.json` güncelle |

### Loglar

```bash
# Uygulama logları (development)
# Otomatik olarak stdout'a yazılır

# Startup diagnostics
# Uygulama başlarken tablo sayısı, DB durumu, Redis durumu gösterilir
```

---

## Docker ile Hızlı Kurulum (Alternatif)

```bash
# 1. Tek komutla tüm servisleri başlat
docker compose -f docker/docker-compose.yml up -d

# 2. DB migration
docker compose -f docker/docker-compose.yml exec app flask db upgrade

# 3. Demo verisi (opsiyonel)
docker compose -f docker/docker-compose.yml exec app python scripts/seed_quick_demo.py

# 4. Kontrol
curl http://localhost:8000/api/health
```

### Multi-Tenant Docker

```bash
# tenants.json düzenle → yeni tenant ekle
# docker-compose.tenant.yml kullan
docker compose -f docker/docker-compose.tenant.yml up -d
```

---

## Onboarding Tamamlama Tarihi

- [ ] Ortam kuruldu
- [ ] Veritabanı oluşturuldu
- [ ] Demo verisi yüklendi (opsiyonel)
- [ ] Uygulama başarıyla başlatıldı
- [ ] Health check geçti
- [ ] İlk admin kullanıcı oluşturuldu
- [ ] Müşteri/pilot ekibine demo yapıldı

**Onboarding Süresi:** ~30 dakika (Docker ile ~10 dakika)

---

*Bu doküman SAP Transformation Platform v1.0 için geçerlidir.*
