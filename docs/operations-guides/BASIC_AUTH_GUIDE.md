# 🔐 SAP Transformation Platform — Basic Auth Dokümantasyonu

**Tarih:** 2026-02-13  
**Durum:** Aktif (Production)

---

## Ne Yapıldı?

Production ortamına HTTP Basic Authentication eklendi. Site açıldığında tarayıcı kullanıcı adı/şifre soruyor. Doğru girilmezse erişim engelleniyor.

### Neden?

- Platform henüz herkese açık değil (demo/geliştirme aşaması)
- Yetkisiz erişimi engellemek için basit bir koruma katmanı
- İleride gerçek authentication sistemi (login sayfası, JWT, roller) gelince kaldırılacak

---

## Teknik Detaylar

### Eklenen Dosya

**`app/middleware/basic_auth.py`**
```python
"""Simple HTTP Basic Auth for production."""
import os
from flask import request, Response

def init_basic_auth(app):
    """Add basic auth if SITE_USERNAME and SITE_PASSWORD are set."""
    username = os.environ.get('SITE_USERNAME')
    password = os.environ.get('SITE_PASSWORD')
    
    if not username or not password:
        app.logger.info("Basic auth: disabled (no SITE_USERNAME/SITE_PASSWORD)")
        return
    
    app.logger.info("Basic auth: enabled")
    
    @app.before_request
    def require_basic_auth():
        if request.path == '/health':
            return None
        auth = request.authorization
        if not auth or auth.username != username or auth.password != password:
            return Response(
                'Login required.', 401,
                {'WWW-Authenticate': 'Basic realm="SAP Transformation Platform"'}
            )
```

### Değiştirilen Dosya

**`app/__init__.py`** — 2 satır eklendi:
- Satır ~27: `from app.middleware.basic_auth import init_basic_auth`
- Satır ~91: `init_basic_auth(app)` (init_security_headers'dan sonra)

### Railway Environment Variables

| Key | Value | Açıklama |
|-----|-------|----------|
| `SITE_USERNAME` | `admin` | Basic auth kullanıcı adı |
| `SITE_PASSWORD` | `Perga2026!` | Basic auth şifresi |

### Nasıl Çalışıyor?

1. `create_app()` sırasında `init_basic_auth(app)` çağrılır
2. `SITE_USERNAME` ve `SITE_PASSWORD` environment variable'ları kontrol edilir
3. İkisi de varsa → `before_request` middleware eklenir → her istek auth gerektirir
4. İkisinden biri yoksa → auth devre dışı (local development'ta şifresiz çalışır)
5. `/health` endpoint'i auth'tan muaf (Railway health check için)

### Ortam Davranışı

| Ortam | SITE_USERNAME | SITE_PASSWORD | Sonuç |
|-------|---------------|---------------|-------|
| Production (Railway) | ✅ Set | ✅ Set | 🔒 Auth aktif |
| Local Development | ❌ Yok | ❌ Yok | 🔓 Auth yok |

---

## Şifre Değiştirme

Railway Dashboard → Variables → `SITE_PASSWORD` değerini değiştir → Otomatik redeploy olur.

---

## Kaldırma Talimatları

### Yöntem 1: Sadece Devre Dışı Bırak (Hızlı)

Railway Dashboard → Variables → `SITE_USERNAME` ve `SITE_PASSWORD` değişkenlerini sil. Auth otomatik devre dışı kalır. Kod değişikliği gerekmez.

### Yöntem 2: Kodu Tamamen Kaldır (Temiz)

Aşağıdaki Copilot prompt'unu kullan.

---

## 🤖 COPILOT PROMPT — Basic Auth Kaldırma

```
## GÖREV: Basic Auth Kaldır

SAP Transformation Platform'dan HTTP Basic Authentication'ı tamamen kaldır.

### Adım 1: Middleware dosyasını sil
rm app/middleware/basic_auth.py

### Adım 2: app/__init__.py'den import ve çağrıyı kaldır
Şu 2 satırı bul ve sil:

1. Import satırı:
   from app.middleware.basic_auth import init_basic_auth

2. Çağrı satırı:
   init_basic_auth(app)

Doğrulama:
grep -n "basic_auth" app/__init__.py
# Sonuç boş olmalı

### Adım 3: Railway env vars kaldır
Railway Dashboard → Variables → şu değişkenleri sil:
- SITE_USERNAME
- SITE_PASSWORD

### Adım 4: Commit & Push
git add -A
git commit --no-verify -m "Remove basic auth - switching to proper auth system"
git push

### Adım 5: Test
Site artık şifre sormadan açılmalı:
https://app.univer.com.tr
```

---

## 🤖 COPILOT PROMPT — Şifre Değiştirme

```
## GÖREV: Basic Auth Şifresini Değiştir

Railway Dashboard → Variables sekmesi → şu değişkenleri güncelle:

| Key | Yeni Value |
|-----|-----------|
| SITE_USERNAME | (yeni kullanıcı adı) |
| SITE_PASSWORD | (yeni şifre) |

Otomatik redeploy bekle. Sonra test et:
https://app.univer.com.tr
```

---

*Son güncelleme: 2026-02-13*
