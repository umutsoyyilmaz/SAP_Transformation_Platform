# PERGA — Multi-Tenant Admin Panel Implementation Project Plan

**Mimari Doküman Referansı:** Perga_Admin_Architecture_v1.2.md (10 ADR Confirmed)

**Versiyon:** 1.0 — Şubat 2026

**Hazırlayan:** Univer Yazılım ve Danışmanlık A.Ş.

---

## İçindekiler

1. [Proje Özeti](#1-proje-özeti)
2. [Mevcut Durum Analizi (AS-IS)](#2-mevcut-durum-analizi-as-is)
3. [Hedef Durum (TO-BE)](#3-hedef-durum-to-be)
4. [Boşluk Analizi (GAP)](#4-boşluk-analizi-gap)
5. [İş Kırılım Yapısı (WBS)](#5-iş-kırılım-yapısı-wbs)
   - Phase 1: Foundation + Tenant Admin MVP
   - Phase 2: Platform Admin + RBAC Engine
   - Phase 3: SSO & Enterprise
   - Phase 4: Scale & Polish
6. [Sprint Planı ve Takvim](#6-sprint-planı-ve-takvim)
7. [Teknik Tasarım Detayları](#7-teknik-tasarım-detayları)
8. [Migration Stratejisi](#8-migration-stratejisi)
9. [Test Stratejisi](#9-test-stratejisi)
10. [Risk Matrisi](#10-risk-matrisi)
11. [Kabul Kriterleri](#11-kabul-kriterleri)
12. [Bağımlılıklar ve Önkoşullar](#12-bağımlılıklar-ve-önkoşullar)

---

## 1. Proje Özeti

### Amaç

Perga platformunu tek kullanıcılı/Basic Auth yapısından, endüstri standartlarında multi-tenant, JWT tabanlı, RBAC destekli bir SaaS platformuna dönüştürmek.

### Kapsam

| Alan | Dahil | Hariç |
|------|-------|-------|
| Kimlik doğrulama | JWT auth, email+password, refresh token | Sosyal login (Google, GitHub) |
| Yetkilendirme | Permission-based RBAC, 8 sistem rolü | Attribute-based access control (ABAC) |
| Multi-tenancy | Shared DB + tenant_id, tenant CRUD | Schema-per-tenant, DB-per-tenant (Phase 3+ opsiyonu) |
| Admin panel | Tenant Admin (Phase 1), Platform Admin (Phase 2) | Mobil admin uygulaması |
| SSO | SSO-ready altyapı (Phase 2), SAML/OIDC (Phase 3) | LDAP entegrasyonu |
| Migration | Program → Tenant, TeamMember → user_id FK | Mevcut müşteri verisinin toplu taşınması |

### Başarı Metrikleri

| Metrik | Hedef | Ölçüm Yöntemi |
|--------|-------|----------------|
| Auth geçiş süresi | Mevcut API'ler JWT ile çalışır | Smoke test suite %100 pass |
| Tenant izolasyon | Tenant-A verisi Tenant-B'den erişilemez | Cross-tenant penetration testi |
| Rol doğruluğu | 8 sistem rolü doğru izin kümesine sahip | Permission matrix unit testleri |
| API uyumluluğu | Mevcut 17 blueprint çalışmaya devam eder | Mevcut test suite regression testi |
| Admin panel | Kullanıcı CRUD + rol atama + proje assign çalışır | E2E test senaryoları |

---

## 2. Mevcut Durum Analizi (AS-IS)

### 2.1 Kimlik Doğrulama (Mevcut)

| Bileşen | Durum | Dosya |
|---------|-------|-------|
| API Key auth | ✅ Aktif | `app/auth.py` |
| HTTP Basic Auth | ✅ Aktif | `app/auth.py` + `app/middleware/basic_auth.py` |
| SPA bypass (same-origin) | ✅ Aktif | `app/auth.py` |
| Rol hiyerarşisi | ⚠️ Basit (admin/editor/viewer) | `app/auth.py` — string tabanlı, env var'dan |
| JWT auth | ❌ Yok | — |
| User tablosu | ❌ Yok | — |
| Şifre hashing (bcrypt) | ❌ Yok | — |
| Login/Register/Refresh | ❌ Yok | — |

### 2.2 Veri Modeli (Mevcut — 18 Model Dosyası)

| Model Dosyası | Tablo Sayısı | tenant_id | Öne Çıkan |
|---------------|-------------|-----------|-----------|
| `app/models/program.py` | 6 | ❌ | Program, Phase, Gate, Workstream, TeamMember, Committee |
| `app/models/explore.py` | 15+ | ❌ | ProcessLevel, ExploreWorkshop, ProjectRole, PERMISSION_MATRIX |
| `app/models/testing.py` | 11 | ❌ | TestPlan, TestCycle, TestCase, Defect, TestRun, TestSuite |
| `app/models/requirement.py` | ~3 | ❌ | Requirements domain |
| `app/models/scope.py` | 3 | ❌ | Process (L2/L3/L4), Analysis |
| `app/models/integration.py` | 5 | ❌ | Interface, Wave, ConnectivityTest, SwitchPlan |
| `app/models/audit.py` | 1 | ❌ | AuditLog (actor = string) |
| `app/models/backlog.py` | ~2 | ❌ | Backlog items |
| `app/models/raid.py` | ~4 | ❌ | Risk, Action, Issue, Decision |
| `app/models/cutover.py` | ~3 | ❌ | Cutover planning |
| `app/models/notification.py` | ~2 | ❌ | Notifications |
| `app/models/scheduling.py` | 3 | ❌ | ScheduledJob, EmailLog, NotificationPreference |
| `app/models/data_factory.py` | ~2 | ❌ | Data migration |
| `app/models/run_sustain.py` | ~2 | ❌ | Go-live, hypercare |
| `app/models/scenario.py` | ~1 | ❌ | Test scenarios |
| **Toplam** | **~60+ tablo** | **0 tenant_id** | — |

### 2.3 Multi-Tenant (Mevcut)

| Bileşen | Durum | Dosya |
|---------|-------|-------|
| Tenant registry | ⚠️ Dosya tabanlı (`tenants.json`) | `app/tenant.py` |
| Tenant resolution | ⚠️ Header/env var tabanlı | `app/tenant.py` |
| DB izolasyonu | ⚠️ DB-per-tenant (ayrı dosya/DB) | `app/tenant.py` |
| tenant_id sütunu | ❌ Hiçbir modelde yok | — |
| TenantModel abstract class | ❌ Yok | — |
| Tenant CRUD API | ❌ Yok | — |

### 2.4 Yetkilendirme (Mevcut)

| Bileşen | Durum | Dosya |
|---------|-------|-------|
| `PERMISSION_MATRIX` | ⚠️ Hardcoded dict, sadece explore modülü | `app/models/explore.py` |
| `ProjectRole` model | ⚠️ `user_id` string, FK yok | `app/models/explore.py` |
| Permission service | ⚠️ Sadece explore ile çalışıyor | `app/services/permission.py` |
| `@require_role` decorator | ⚠️ admin/editor/viewer, env var tabanlı | `app/auth.py` |
| `@require_permission` decorator | ❌ Yok | — |
| DB-driven permissions | ❌ Yok | — |
| roles/permissions tabloları | ❌ Yok | — |

### 2.5 API Yüzeyi (17 Blueprint)

```
program_bp      backlog_bp      testing_bp      raid_bp
ai_bp           integration_bp  health_bp       metrics_bp
explore_bp      data_factory_bp reporting_bp    audit_bp
cutover_bp      notification_bp run_sustain_bp  pwa_bp
traceability_bp
```

- Hiçbir endpoint'te `@require_permission` yok
- Tümü Basic Auth / API Key ile korunuyor
- project_id parametre olarak geliyor ama membership kontrolü yok

### 2.6 Altyapı

| Bileşen | Development | Production |
|---------|-------------|------------|
| Veritabanı | SQLite | PostgreSQL (Railway) |
| Migration | Alembic (17 versiyon, auth ile ilgili yok) | Alembic + auto-add-columns |
| Cache | Yok | Redis (hazır ama kullanılmıyor) |
| CI/CD | — | Railway auto-deploy (git push) |
| Test | pytest (35+ test dosyası) | Playwright E2E + smoke_test_production.sh |

---

## 3. Hedef Durum (TO-BE)

```
┌───────────────────────────────────────────────────────────────┐
│                    PERGA SaaS Platform                        │
├───────────────────────────────────────────────────────────────┤
│  Platform Admin (/platform-admin/*)                          │
│  ├── Tenant CRUD, Lisans, Sistem Sağlığı, Global Audit      │
│  └── Sadece Perga iç ekibi erişir                            │
├───────────────────────────────────────────────────────────────┤
│  Tenant Admin (/admin/*)                                     │
│  ├── Kullanıcı CRUD, Rol Atama, Proje Assign                │
│  ├── Şirket Ayarları, Takım Yönetimi                         │
│  └── Müşteri IT/PM erişir                                    │
├───────────────────────────────────────────────────────────────┤
│  Middleware Zinciri                                           │
│  JWT → Tenant Context → Permission → Project Membership      │
├───────────────────────────────────────────────────────────────┤
│  Veri Katmanı                                                │
│  ├── TenantModel abstract class (tüm modeller inherit)       │
│  ├── Shared DB + tenant_id filtresi                          │
│  └── users, roles, permissions, project_members tabloları    │
├───────────────────────────────────────────────────────────────┤
│  Auth Katmanı                                                │
│  ├── JWT (access 15dk + refresh 7gün)                        │
│  ├── bcrypt password hashing                                 │
│  ├── Email davet + kayıt akışı                               │
│  └── SSO-ready (Phase 3: SAML/OIDC)                         │
└───────────────────────────────────────────────────────────────┘
```

---

## 4. Boşluk Analizi (GAP)

### 4.1 Sıfırdan İnşa Edilecek Bileşenler

| # | Bileşen | Karmaşıklık | Tahmini Efor | ADR Ref |
|---|---------|-------------|-------------|---------|
| G1 | `tenants` model + API | Orta | 3 gün | ADR-1 |
| G2 | `users` model + bcrypt hash | Orta | 3 gün | ADR-2 |
| G3 | `roles` + `permissions` + junction tabloları | Yüksek | 4 gün | ADR-3, ADR-5 |
| G4 | `project_members` tablosu | Düşük | 1 gün | ADR-9 |
| G5 | `sessions` tablosu (refresh token) | Düşük | 1 gün | ADR-8 |
| G6 | JWT auth engine (login/register/refresh/logout) | Yüksek | 5 gün | ADR-2, ADR-8 |
| G7 | `TenantModel` abstract class | Orta | 2 gün | ADR-10 |
| G8 | Tenant context middleware (JWT→g.tenant_id) | Orta | 2 gün | ADR-10 |
| G9 | Permission middleware (`@require_permission`) | Yüksek | 4 gün | ADR-9 |
| G10 | 8 sistem rolü seed data | Düşük | 1 gün | ADR-5 |
| G11 | Tenant Admin UI — kullanıcı CRUD | Yüksek | 5 gün | ADR-4, ADR-7 |
| G12 | Tenant Admin UI — rol atama + proje assign | Orta | 3 gün | ADR-4 |
| G13 | Platform Admin UI — tenant CRUD | Yüksek | 5 gün | ADR-4 |
| G14 | Email davet akışı | Orta | 3 gün | ADR-7 |
| G15 | Alembic migration'lar (yeni tablolar) | Orta | 2 gün | — |

### 4.2 Mevcut Bileşenlerde Gerekli Değişiklikler

| # | Bileşen | Değişiklik | Karmaşıklık | Tahmini Efor |
|---|---------|-----------|-------------|-------------|
| M1 | 60+ model tablosu | `tenant_id` FK ekleme + index | Yüksek (hacim) | 5 gün |
| M2 | `TeamMember` model | `user_id` FK ekleme (nullable) | Düşük | 0.5 gün |
| M3 | `ProjectRole` model | `user_id` string → int FK | Orta | 1.5 gün |
| M4 | `PERMISSION_MATRIX` → DB | Dict → roles/permissions tablosu | Orta | 2 gün |
| M5 | `app/services/permission.py` | DB-driven rewrite | Orta | 2 gün |
| M6 | `AuditLog` model | `tenant_id` + `actor` → FK | Düşük | 0.5 gün |
| M7 | `app/auth.py` | JWT primary, API key/Basic fallback | Yüksek | 3 gün |
| M8 | `app/tenant.py` | JSON → DB-driven tenant registry | Orta | 2 gün |
| M9 | 17 blueprint | `@require_permission` decorator ekleme | Yüksek (hacim) | 5 gün |
| M10 | `app/__init__.py` | Yeni model/middleware import + init | Düşük | 1 gün |
| M11 | Program → Tenant migration script | 1:1 mapping + tenant_id backfill | Orta | 2 gün |
| M12 | Mevcut test suite güncelleme | Auth/tenant uyumu | Yüksek | 3 gün |

### 4.3 Efor Özeti

| Kategori | Toplam Efor |
|----------|------------|
| Sıfırdan inşa (G1–G15) | **44 gün** |
| Mevcut sistem değişiklikleri (M1–M12) | **27.5 gün** |
| Buffer (%20 risk marjı) | **14.3 gün** |
| **Toplam** | **~86 iş günü (~4.3 ay, 2 kişi ile ~2.2 ay)** |

---

## 5. İş Kırılım Yapısı (WBS)

### Phase 1: Foundation + Tenant Admin MVP (Sprint 1–4, 8 hafta)

#### Sprint 1 — Data Model Foundation (Hafta 1–2)

| # | İş Paketi | Detay | Çıktı | Efor |
|---|-----------|-------|-------|------|
| 1.1.1 | Alembic migration: `tenants` tablosu | id, name, slug, domain, plan, max_users, max_projects, is_active, settings, created_at, updated_at | migration dosyası + model | 1 gün |
| 1.1.2 | Alembic migration: `users` tablosu | id, tenant_id FK, email, password_hash, full_name, avatar_url, status, auth_provider, last_login_at | migration dosyası + model | 1 gün |
| 1.1.3 | Alembic migration: `roles` + `permissions` | roles, permissions, role_permissions, user_roles tabloları | migration dosyası + modeller | 2 gün |
| 1.1.4 | Alembic migration: `project_members` | project_id FK, user_id FK, role_in_project, joined_at | migration dosyası + model | 0.5 gün |
| 1.1.5 | Alembic migration: `sessions` | id UUID, user_id FK, token_hash, ip_address, user_agent, expires_at | migration dosyası + model | 0.5 gün |
| 1.1.6 | 8 sistem rolü seed script | Platform Super Admin, Tenant Admin, Program Manager, Project Manager, Functional Consultant, Technical Consultant, Tester, Viewer | seed_roles.py + 42 permission tanımı | 1.5 gün |
| 1.1.7 | `TenantModel` abstract class | tenant_id FK, query_for_tenant() classmethod, composite index macro | app/models/base.py | 1 gün |
| 1.1.8 | UNIQUE constraint: (tenant_id, email) | Users tablosu composite unique | migration + model | 0.5 gün |

**Sprint 1 Çıktıları:**
- ✅ 7 yeni tablo oluşturulmuş (Alembic)
- ✅ 8 sistem rolü + 42 permission seed edilmiş
- ✅ TenantModel abstract class kullanıma hazır
- ✅ Mevcut tablolara DOKUNULMADI (additive only)

```python
# Sprint 1 Target: app/models/auth.py (YENİ DOSYA)

class Tenant(db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    domain = db.Column(db.String(200))
    plan = db.Column(db.String(50), default='trial')
    max_users = db.Column(db.Integer, default=10)
    max_projects = db.Column(db.Integer, default=3)
    is_active = db.Column(db.Boolean, default=True)
    settings = db.Column(db.JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256))  # NULL for SSO users
    full_name = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')
    auth_provider = db.Column(db.String(50), default='local')
    # Composite unique: same email can exist in different tenants
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'email', name='uq_user_tenant_email'),
    )
```

---

#### Sprint 2 — JWT Auth Engine (Hafta 3–4)

| # | İş Paketi | Detay | Çıktı | Efor |
|---|-----------|-------|-------|------|
| 1.2.1 | JWT token servis | Access token (15dk) + refresh token (7gün), HS256/RS256 | app/services/jwt_service.py | 1.5 gün |
| 1.2.2 | Auth blueprint: `/api/v1/auth/login` | Email+password → JWT pair, bcrypt verify | app/blueprints/auth_bp.py | 1 gün |
| 1.2.3 | Auth blueprint: `/api/v1/auth/register` | Sadece davet ile (invite token required) | auth_bp.py | 1 gün |
| 1.2.4 | Auth blueprint: `/api/v1/auth/refresh` | Refresh token → yeni access token, token rotation | auth_bp.py | 0.5 gün |
| 1.2.5 | Auth blueprint: `/api/v1/auth/logout` | Session invalidate, refresh token revoke | auth_bp.py | 0.5 gün |
| 1.2.6 | Auth blueprint: `/api/v1/auth/me` | Current user profile (JWT'den) | auth_bp.py | 0.5 gün |
| 1.2.7 | JWT middleware integration | `@app.before_request`: JWT parse → g.user_id, g.tenant_id, g.roles | app/middleware/jwt_auth.py | 1.5 gün |
| 1.2.8 | Backward compat: API key + Basic Auth fallback | Mevcut auth yöntemleri yedek olarak korunur | app/auth.py güncelleme | 1 gün |
| 1.2.9 | Password hashing utility | bcrypt hash/verify helper | app/utils/crypto.py | 0.5 gün |
| 1.2.10 | Auth unit testleri | Login, register, refresh, logout, token expiry, invalid token | tests/test_auth.py | 1.5 gün |

**Sprint 2 Çıktıları:**
- ✅ `/api/v1/auth/*` endpoint'leri çalışıyor
- ✅ JWT token üretim ve doğrulama
- ✅ Mevcut API key / Basic Auth hâlâ çalışıyor (backward compat)
- ✅ Auth test suite pass

```
JWT Token Payload:
{
  "sub": 42,              // user_id
  "tenant_id": 7,         // tenant
  "roles": ["project_manager", "consultant"],
  "exp": 1740000000,      // 15 dakika
  "iat": 1739999100,
  "type": "access"
}
```

**Erişim kontrol akışı (Sprint 2 sonunda):**

```
İstek geldi
  │
  ├─ Authorization: Bearer <JWT>  → JWT parse → g.user_id, g.tenant_id, g.roles
  ├─ X-API-Key: <key>             → API key lookup → g.role (fallback)
  ├─ Authorization: Basic <b64>   → Basic auth verify → g.role (fallback)  
  └─ Same-origin SPA              → Auto-grant (dev only)
```

---

#### Sprint 3 — Tenant Context + Permission Middleware (Hafta 5–6)

| # | İş Paketi | Detay | Çıktı | Efor |
|---|-----------|-------|-------|------|
| 1.3.1 | Tenant context middleware | JWT tenant_id → g.tenant_id; her DB sorgusu filtreli | app/middleware/tenant_context.py | 2 gün |
| 1.3.2 | `@require_permission` decorator | Permission string kontrolü: `@require_permission('requirements.create')` | app/auth.py güncelleme | 2 gün |
| 1.3.3 | Project membership middleware | project_id parametresi varsa → project_members kontrolü | app/middleware/project_access.py | 1.5 gün |
| 1.3.4 | Permission servis (DB-driven) | User → roles → permissions lookup, cache (5dk TTL) | app/services/permission.py rewrite | 2 gün |
| 1.3.5 | Tenant-wide rol istisnaları | Tenant Admin ve Program Manager → project membership bypass | permission service | 0.5 gün |
| 1.3.6 | `TeamMember.user_id` FK ekleme | Nullable FK + migration, mevcut veri korunur | migration + model güncelleme | 0.5 gün |
| 1.3.7 | Cross-tenant güvenlik testi | Tenant-A user → Tenant-B verisi erişim denemesi | tests/test_tenant_isolation.py | 1.5 gün |

**Sprint 3 Çıktıları:**
- ✅ Middleware zinciri: JWT → Tenant → Permission → Membership
- ✅ `@require_permission('category.action')` decorator kullanıma hazır
- ✅ Tenant izolasyonu doğrulandı — cross-tenant erişim engelleniyor
- ✅ TeamMember → User bağlantısı hazır (nullable FK)

**Middleware zinciri somut akış:**

```
1. JWT valid mi?                     → 401 Unauthorized
2. g.tenant_id set                   → JWT claims'den alınır
3. Permission var mı?                → User roles → permissions lookup
   └─ requirements.create?          → 403 "Yetkiniz yok"
4. Project membership var mı?        → project_members tablosu
   └─ Tenant Admin/PM?             → Bypass (tenant-wide)
   └─ Diğer roller?                → 403 "Bu projeye erişiminiz yok"
5. → İşlem başarılı
```

---

#### Sprint 4 — Tenant Admin UI MVP (Hafta 7–8)

| # | İş Paketi | Detay | Çıktı | Efor |
|---|-----------|-------|-------|------|
| 1.4.1 | Admin blueprint: `/admin/*` route'ları | SPA host, API proxy, session yönetimi | app/blueprints/admin_bp.py | 1 gün |
| 1.4.2 | Admin API: kullanıcı CRUD | GET/POST/PUT/DELETE `/api/v1/admin/users` | admin API endpoint'leri | 2 gün |
| 1.4.3 | Admin API: rol atama | POST/DELETE `/api/v1/admin/users/:id/roles` | admin API endpoint'leri | 1 gün |
| 1.4.4 | Admin API: proje assign | POST/DELETE `/api/v1/admin/projects/:id/members` | admin API endpoint'leri | 1 gün |
| 1.4.5 | Admin UI: kullanıcı listesi sayfası | Tablo, arama, filtre, status badge | templates/admin/users.html + JS | 2 gün |
| 1.4.6 | Admin UI: kullanıcı detay sayfası | Profil, rol atamaları, proje üyelikleri | templates/admin/user_detail.html | 1.5 gün |
| 1.4.7 | Admin UI: davet et modal | Email gir → davet maili gönder → status: invited | templates/admin/invite.html | 1 gün |
| 1.4.8 | Admin UI: rol yönetimi sayfası | Sistem rolleri listesi, izin matrisi görüntüleme | templates/admin/roles.html | 1 gün |
| 1.4.9 | Email davet akışı | Davet token → kayıt sayfası → şifre belirleme → active | email_service + auth_bp güncellemesi | 1.5 gün |
| 1.4.10 | Admin dashboard | Kullanıcı sayısı, proje sayısı, son aktiviteler | templates/admin/dashboard.html | 1 gün |

**Sprint 4 Çıktıları:**
- ✅ Tenant Admin paneli çalışıyor (`/admin/*`)
- ✅ Kullanıcı CRUD: listele, oluştur, davet et, deaktif et
- ✅ Rol atama ve proje assign işlevsel
- ✅ Email davet akışı çalışıyor

---

### Phase 1 Toplam Çıktı Kontrolü

| Deliverable | Sprint | Durum |
|-------------|--------|-------|
| 7 yeni DB tablosu (Alembic) | S1 | ✅ Done |
| TenantModel abstract class | S1 | ✅ Done |
| 8 sistem rolü + 42 permission | S1 | ✅ Done |
| JWT auth (login/register/refresh/logout) | S2 | ✅ Done (52/52 tests) |
| Backward compat (API key + Basic Auth) | S2 | ✅ Done |
| Middleware zinciri (JWT → Tenant → Permission → Membership) | S3 | ✅ Done (42/42 tests) |
| `@require_permission` decorator | S3 | ✅ Done |
| Cross-tenant izolasyon | S3 | ✅ Done |
| Tenant Admin UI (kullanıcı CRUD + rol atama + proje assign) | S4 | ✅ Done (35/35 tests) |
| Email davet akışı | S4 | ✅ Done |

---

### Phase 2: Platform Admin + RBAC Tam Devreye (Sprint 5–6, 4 hafta) ✅ COMPLETE

#### Sprint 5 — Mevcut Modeller tenant_id Geçişi (Hafta 9–10)

| # | İş Paketi | Detay | Efor |
|---|-----------|-------|------|
| 2.1.1 | Program → Tenant migration script | Her Program → 1 Tenant kaydı, mapping tablosu | 1.5 gün |
| 2.1.2 | `projects` tablosuna tenant_id ekle | Nullable FK → backfill → NOT NULL | 1 gün |
| 2.1.3 | Explore modeli tabloları tenant_id | ProcessLevel, ExploreWorkshop, ProjectRole + 13 tablo | 2 gün |
| 2.1.4 | Testing modeli tabloları tenant_id | TestPlan, TestCycle, TestCase, Defect, TestRun + 6 tablo | 1.5 gün |
| 2.1.5 | Diğer modeller tenant_id | requirement, scope, integration, backlog, RAID, cutover, notification, scheduling, data_factory, run_sustain, scenario | 2 gün |
| 2.1.6 | AuditLog tenant_id + actor FK | Immutable log tenant-scoped | 0.5 gün |
| 2.1.7 | Composite index ekleme | (tenant_id, id) tüm tablolarda | 0.5 gün |
| 2.1.8 | Data integrity check script | Tüm kayıtlar bir tenant'a bağlı mı? Orphan kontrolü | 1 gün |

**Sprint 5 Çıktıları:** ✅ TAMAMLANDI (14 Şubat 2026)
- ✅ 96+ model / 16 dosya tenant_id sütununa sahip (scripts/add_tenant_id.py)
- ✅ Program → Tenant backfill migration script (scripts/migrate_tenant_backfill.py)
- ✅ 98 composite (tenant_id, id) index oluşturuldu (scripts/add_tenant_indexes.py)
- ✅ Data integrity check doğrulandı — 0 error (scripts/check_tenant_integrity.py)
- ✅ AuditLog actor_user_id FK eklendi
- ✅ 76/76 Sprint 5 tests PASSED (tests/test_tenant_migration.py)
- ✅ 205/205 combined auth tests PASSED (S2-S5)
- ✅ 1855/1857 full regression PASSED (2 pre-existing failures)

---

#### Sprint 6 — Platform Admin + Blueprint Güncelleme (Hafta 11–12) ✅ COMPLETE

| # | İş Paketi | Detay | Efor | Durum |
|---|-----------|-------|------|-------|
| 2.2.1 | Platform Admin blueprint | `/platform-admin/*` route'ları, super admin only | 1 gün | ✅ Done |
| 2.2.2 | Platform Admin API: tenant CRUD | GET/POST/PUT/DELETE `/api/v1/platform-admin/tenants` + freeze/unfreeze | 1.5 gün | ✅ Done — 9 API endpoints |
| 2.2.3 | Platform Admin UI: tenant listesi | Oluştur, düzenle, dondur, sil + plan/kota | 2 gün | ✅ Done — SPA index.html |
| 2.2.4 | Platform Admin UI: dashboard | Toplam tenant, aktif kullanıcı, API kullanım | 1 gün | ✅ Done |
| 2.2.5 | Platform Admin UI: sistem sağlığı | DB performansı, hata logları (mevcut /health entegrasyonu) | 1 gün | ✅ Done |
| 2.2.6 | Blueprint'lere permission ekleme — Batch 1 | program_bp, explore_bp, testing_bp (yoğun blueprint'ler) | 2 gün | ✅ Done — app.before_request hook |
| 2.2.7 | Blueprint'lere permission ekleme — Batch 2 | backlog_bp, raid_bp, integration_bp, cutover_bp, data_factory_bp, reporting_bp, run_sustain_bp, traceability_bp, audit_bp | 2 gün | ✅ Done — 12 blueprint korunuyor |
| 2.2.8 | Test suite oluşturma | Platform admin + blueprint permission + legacy fallthrough + superuser bypass testleri | 2 gün | ✅ Done — 65/65 PASSED |

**Sprint 6 Metrikleri:**
- ✅ Platform Admin paneli çalışıyor (`/platform-admin/*`) — 9 API endpoint + 1 UI route
- ✅ 12 blueprint tamamı `before_request` permission guard ile korunuyor
- ✅ Explore blueprint path-based routing (requirements/workshops/reports)
- ✅ Legacy auth fallthrough korunuyor (JWT yoksa izin kontrolü atlanır)
- ✅ 65/65 Sprint 6 testleri PASSED, 1920/1922 regression (2 pre-existing failure)
- **Dosyalar:** `blueprint_permissions.py`, `platform_admin_bp.py`, `platform_admin/index.html`, `test_platform_admin.py`

---

### Phase 3: SSO & Enterprise (Sprint 7–8, 4 hafta)

| # | İş Paketi | Detay | Efor | Durum |
|---|-----------|-------|------|-------|
| 3.1 | SSO altyapısı (SAML/OIDC) | Authlib kütüphanesi, SSOConfig + TenantDomain modelleri | 3 gün | ✅ Done |
| 3.2 | Azure AD entegrasyonu | OIDC discovery, token exchange, user provisioning | 3 gün | ✅ Done |
| 3.3 | SAP IAS entegrasyonu | SAML2 assertion, attribute mapping, SP metadata | 2 gün | ✅ Done |
| 3.4 | Domain-based tenant eşleştirme | Email domain → tenant auto-assign (login sırasında) | 1.5 gün | ✅ Done |
| 3.5 | SCIM user provisioning | Auto user create/update/deactivate from IdP | 3 gün | ✅ Done |
| 3.6 | Bulk user import (CSV) | Toplu kullanıcı yükleme, validation, progress bar | 2 gün | ✅ Done |
| 3.7 | Custom roles | Tenant Admin özel rol tanımlama UI | 2.5 gün | ✅ Done |
| 3.8 | SSO E2E testleri | Mock IdP ile SAML/OIDC flow test | 2 gün | ✅ Done |

**Sprint 7 Metrikleri:**
- ✅ SSOConfig + TenantDomain modelleri (2 yeni tablo)
- ✅ OIDC flow: Azure AD discovery, token exchange, user auto-provisioning
- ✅ SAML flow: AuthnRequest oluşturma, SAMLResponse parse, assertion extract
- ✅ Domain-based tenant matching: email domain → tenant otomatik eşleştirme
- ✅ SSO Admin UI: sağlayıcı CRUD + domain yönetimi SPA (`/sso-admin`)
- ✅ 17 API endpoint (6 flow + 9 admin + 2 UI/utility)
- ✅ 84/84 Sprint 7 testleri PASSED, ~2004/2006 regression (2 pre-existing failure)
- **Dosyalar:** `sso_service.py`, `sso_bp.py`, `auth.py` (models), `sso_admin/index.html`, `test_sso.py`

**Sprint 8 Metrikleri:**
- ✅ SCIM 2.0 user provisioning: RFC 7643/7644 uyumlu User CRUD + token auth
- ✅ SCIM token yönetimi: generate, validate, revoke (Tenant.settings'te hash)
- ✅ SCIM filter & pagination: `userName eq "..."` filter, startIndex/count
- ✅ Bulk CSV import: parse → validate → import pipeline, template download
- ✅ Custom roles: Tenant Admin özel rol CRUD, permission assignment, level cap
- ✅ System role koruması: is_system=True roller modify/delete edilemez
- ✅ SSO E2E testleri: Mock OIDC full flow (login → callback → provision → JWT)
- ✅ SSO E2E testleri: Mock SAML full flow (login → callback → provision → JWT)
- ✅ Custom Roles Admin UI: `/roles-admin` SPA (role CRUD + permission grid)
- ✅ 80/80 Sprint 8 testleri PASSED, 2084/2086 regression (2 pre-existing)
- **Dosyalar:** `scim_service.py`, `scim_bp.py`, `bulk_import_service.py`, `bulk_import_bp.py`, `custom_role_service.py`, `custom_roles_bp.py`, `roles_admin/index.html`, `test_sprint8.py`

---

### Phase 4: Scale & Polish (Sprint 9–10, 4 hafta)

| # | İş Paketi | Detay | Efor |
|---|-----------|-------|------|
| 4.1 | Feature flags sistemi | Tenant bazlı özellik açma/kapama, DB tablosu + admin UI | 2 gün |
| 4.2 | Tenant-aware Redis cache | Permission cache (5dk TTL), role lookup cache, invalidation | 2 gün |
| 4.3 | Rate limiting (tenant bazlı) | Plan'a göre API kota: trial=100/dk, premium=1000/dk | 1.5 gün |
| 4.4 | Admin dashboard metrikleri | Grafik: kullanıcı trend, proje aktivite, API kullanım | 2 gün |
| 4.5 | Onboarding wizard | Yeni tenant: şirket bilgisi → ilk admin → ilk proje → hazır | 2 gün |
| 4.6 | Tenant data export | KVKK/GDPR uyumlu veri export (JSON/CSV) | 1.5 gün |
| 4.7 | Soft delete standardizasyonu | `deleted_at` pattern tüm modellerde | 1 gün |
| 4.8 | Schema-per-tenant opsiyonu | Büyük kurumsal müşteriler için PG schema izolasyonu | 3 gün |
| 4.9 | Performance testi | 1000 concurrent user, 50 tenant simulasyonu | 2 gün |
| 4.10 | Güvenlik denetimi | Penetration test, OWASP top 10 kontrolü | 2 gün |

**Phase 4 Çıktıları:**
- ✅ Feature flags, caching, rate limiting aktif
- ✅ Onboarding wizard yeni tenant kurulumunu kolaylaştırıyor
- ✅ KVKK/GDPR data export hazır
- ✅ Performance ve güvenlik testleri geçti

---

## 6. Sprint Planı ve Takvim

```
2026
Mart         Nisan        Mayıs        Haziran      Temmuz       Ağustos
─────────────────────────────────────────────────────────────────────────
│ Sprint 1  │ Sprint 2  │ Sprint 3  │ Sprint 4  │            │
│ DB Models │ JWT Auth  │ Middleware│ Admin UI  │            │
│ + Seed    │ + API     │ + Perms   │ + Invite  │            │
├───────────┴───────────┴───────────┴───────────┤            │
│         PHASE 1: Foundation + Tenant Admin MVP │            │
│           MILESTONE 1: Auth MVP (S1-S2 sonu)   │            │
│           MILESTONE 2: Admin MVP (S3-S4 sonu)  │            │
├────────────────────────────────────────────────┤            │
                                                │ Sprint 5  │ Sprint 6  │
                                                │ tenant_id │ Platform  │
                                                │ Migration │ Admin+BP  │
                                                ├───────────┴───────────┤
                                                │  PHASE 2: Platform +  │
                                                │    Full RBAC          │
                                                │  MILESTONE 3 (S6 sonu)│
                                                ├───────────────────────┤
```

```
2026
Eylül        Ekim         Kasım        Aralık
─────────────────────────────────────────────────
│ Sprint 7  │ Sprint 8  │ Sprint 9  │ Sprint 10 │
│ SSO infra │ SSO test  │ Cache     │ Security  │
│ + Azure   │ + SCIM    │ + Flags   │ + Perf    │
├───────────┴───────────┼───────────┴───────────┤
│    PHASE 3: SSO &     │    PHASE 4: Scale &   │
│     Enterprise        │       Polish          │
│  MILESTONE 4 (S8 sonu)│  MILESTONE 5 (S10)    │
├───────────────────────┴───────────────────────┤
```

### Milestone Özeti

| Milestone | Tarih | Deliverable | Go/No-Go Kriteri |
|-----------|-------|-------------|-----------------|
| M1: Auth MVP | Nisan 2026 sonu | JWT auth çalışıyor, DB tabloları hazır | Login/refresh/logout testleri pass |
| M2: Admin MVP | Mayıs 2026 sonu | Tenant Admin paneli, kullanıcı CRUD, rol atama | Admin UI E2E test pass |
| M3: Full RBAC | Temmuz 2026 sonu | Tüm modeller tenant-scoped, Platform Admin, 17 BP korumalı | Cross-tenant test + smoke test pass |
| M4: SSO | Eylül 2026 sonu | Azure AD / SAP IAS SSO, SCIM, bulk import | SSO E2E test pass |
| M5: Production-Ready | Aralık 2026 sonu | Feature flags, cache, rate limit, security audit | Pentest pass, 1000 user perf test pass |

---

## 7. Teknik Tasarım Detayları

### 7.1 Yeni Dosya Yapısı

```
app/
├── models/
│   ├── base.py              ← YENİ: TenantModel abstract class
│   ├── auth.py              ← YENİ: Tenant, User, Role, Permission, Session, ProjectMember
│   ├── program.py           ← GÜNCELLEME: tenant_id, TeamMember.user_id FK
│   ├── explore.py           ← GÜNCELLEME: tenant_id, ProjectRole.user_id FK
│   └── ... (diğerleri)      ← GÜNCELLEME: tenant_id ekleme
├── blueprints/
│   ├── auth_bp.py           ← YENİ: login, register, refresh, logout, me
│   ├── admin_bp.py          ← YENİ: Tenant Admin API + UI
│   ├── platform_admin_bp.py ← YENİ: Platform Admin API + UI
│   └── ... (mevcutlar)      ← GÜNCELLEME: @require_permission
├── middleware/
│   ├── jwt_auth.py          ← YENİ: JWT parse + g.user_id/g.tenant_id
│   ├── tenant_context.py    ← YENİ: Tenant-scoped query enforcement
│   ├── project_access.py    ← YENİ: Project membership check
│   └── ... (mevcutlar)
├── services/
│   ├── jwt_service.py       ← YENİ: Token generate/verify/refresh
│   ├── permission.py        ← REWRITE: DB-driven, cached
│   ├── user_service.py      ← YENİ: User CRUD, invite, deactivate
│   └── ... (mevcutlar)
├── utils/
│   ├── crypto.py            ← YENİ: bcrypt hash/verify
│   └── ...
├── auth.py                  ← GÜNCELLEME: JWT primary + fallback
├── tenant.py                ← GÜNCELLEME: DB-driven tenant registry
└── __init__.py              ← GÜNCELLEME: yeni import'lar + middleware registration
```

### 7.2 Veritabanı ER Diyagramı (Yeni Tablolar)

```
┌──────────────┐       ┌──────────────────┐        ┌──────────────┐
│   tenants    │       │      users       │        │    roles     │
├──────────────┤       ├──────────────────┤        ├──────────────┤
│ id PK        │──┐    │ id PK            │        │ id PK        │
│ name         │  │    │ tenant_id FK ────┼───────→│ tenant_id FK │
│ slug UNIQUE  │  │    │ email            │   ┌───→│ name         │
│ domain       │  └───→│ password_hash    │   │    │ is_system    │
│ plan         │       │ full_name        │   │    └──────────────┘
│ max_users    │       │ status           │   │           │
│ is_active    │       │ auth_provider    │   │           │ role_permissions
│ settings     │       └──────────────────┘   │           ▼
└──────────────┘              │               │    ┌──────────────┐
                              │ user_roles    │    │ permissions  │
                              ▼               │    ├──────────────┤
                       ┌─────────────┐        │    │ id PK        │
                       │ user_roles  │        │    │ codename     │
                       ├─────────────┤        │    │ category     │
                       │ user_id FK  │        │    │ display_name │
                       │ role_id FK ─┼────────┘    └──────────────┘
                       │ assigned_by │
                       │ assigned_at │     ┌──────────────────┐
                       └─────────────┘     │ project_members  │
                                           ├──────────────────┤
                                           │ id PK            │
                                           │ project_id FK    │
                                           │ user_id FK       │
                                           │ role_in_project  │
                                           │ joined_at        │
                                           └──────────────────┘
```

### 7.3 Permission Tanımları (42 Permission, 7 Kategori)

| Kategori | Permission Codename | Açıklama |
|----------|-------------------|----------|
| **requirements** | requirements.view | Gereksinimi görüntüle |
| | requirements.create | Gereksinim oluştur |
| | requirements.edit | Gereksinimi düzenle |
| | requirements.delete | Gereksinimi sil |
| | requirements.approve | Gereksinimi onayla |
| **workshops** | workshops.view | Workshop görüntüle |
| | workshops.create | Workshop oluştur |
| | workshops.facilitate | Workshop yönet |
| | workshops.approve | Workshop onayla |
| **tests** | tests.view | Test görüntüle |
| | tests.create | Test oluştur |
| | tests.execute | Test çalıştır |
| | tests.approve | Test onayla |
| **projects** | projects.view | Proje görüntüle |
| | projects.create | Proje oluştur |
| | projects.edit | Proje düzenle |
| | projects.archive | Proje arşivle |
| **users** | users.view | Kullanıcı listele |
| | users.invite | Kullanıcı davet et |
| | users.edit | Kullanıcı düzenle |
| | users.deactivate | Kullanıcı deaktif et |
| **reports** | reports.view | Rapor görüntüle |
| | reports.export | Rapor dışa aktar |
| **admin** | admin.settings | Şirket ayarları |
| | admin.roles | Rol yönetimi |
| | admin.audit | Audit log görüntüle |
| **backlog** | backlog.view | Backlog görüntüle |
| | backlog.create | Backlog item oluştur |
| | backlog.edit | Backlog item düzenle |
| **raid** | raid.view | RAID görüntüle |
| | raid.create | RAID oluştur |
| | raid.edit | RAID düzenle |
| | raid.resolve | RAID çöz |
| **integration** | integration.view | Entegrasyon görüntüle |
| | integration.create | Entegrasyon oluştur |
| | integration.edit | Entegrasyon düzenle |
| **cutover** | cutover.view | Cutover görüntüle |
| | cutover.create | Cutover oluştur |
| | cutover.edit | Cutover düzenle |
| | cutover.execute | Cutover çalıştır |
| **data** | data.view | Veri görüntüle |
| | data.create | Veri oluştur |
| | data.migrate | Veri taşı |

### 7.4 Rol → Permission Matris (8 Rol)

| Permission | Platform Admin | Tenant Admin | Program Mgr | Project Mgr | Func. Consultant | Tech. Consultant | Tester | Viewer |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| requirements.view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| requirements.create | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| requirements.edit | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| requirements.delete | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| requirements.approve | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| workshops.* | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| tests.view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| tests.create | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — |
| tests.execute | ✓ | ✓ | ✓ | ✓ | — | — | ✓ | — |
| tests.approve | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| projects.create | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| projects.archive | ✓ | ✓ | — | — | — | — | — | — |
| users.* | ✓ | ✓ | — | — | — | — | — | — |
| reports.view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| reports.export | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| admin.* | ✓ | ✓ | — | — | — | — | — | — |
| backlog.* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| raid.* | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| integration.* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| cutover.* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| data.* | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |

---

## 8. Migration Stratejisi

### 8.1 İlkeler

1. **Additive only** — Mevcut sütunlar/tablolar silinmez, yenileri eklenir
2. **Nullable başlangıç** — Yeni FK'lar nullable olarak eklenir → backfill → NOT NULL
3. **Alembic reversible** — Her migration geri alınabilir (downgrade)
4. **Zero downtime** — Online migration, uygulama çalışırken uygulanır
5. **Data integrity check** — Her adım sonrası doğrulama scripti çalıştırılır

### 8.2 Migration Sırası

```
Step 1: Yeni tablolar oluştur (tenants, users, roles, permissions, ...)
        → Mevcut sisteme dokunmaz, uygulanabilir
        
Step 2: Program → Tenant 1:1 migration
        → Her Program kaydı için bir Tenant kaydı yarat
        → program_tenant_mapping tablosu tut (geçiş dönemi)
        
Step 3: Mevcut tablolara tenant_id ekleme (nullable)
        → ALTER TABLE ... ADD COLUMN tenant_id INT REFERENCES tenants(id)
        → Her tablo için ayrı migration
        
Step 4: tenant_id backfill
        → UPDATE projects SET tenant_id = (SELECT t.id FROM tenants t 
           JOIN program_tenant_mapping m ON m.tenant_id = t.id 
           WHERE m.program_id = projects.program_id)
        → Diğer tablolar: project.tenant_id üzerinden zincirleme
        
Step 5: tenant_id NOT NULL + index
        → ALTER TABLE ... ALTER COLUMN tenant_id SET NOT NULL
        → CREATE INDEX idx_<table>_tenant ON <table>(tenant_id)
        
Step 6: TeamMember.user_id FK ekleme
        → Nullable FK, mevcut veri korunur
        → Eşleşen email'ler üzerinden opsiyonel backfill
        
Step 7: ProjectRole.user_id tip değişikliği
        → String → Integer FK (nullable, kademeli)
```

### 8.3 Rollback Planı

| Adım | Rollback Yöntemi | Risk |
|------|-----------------|------|
| Step 1 | `alembic downgrade -1` (tablo drop) | Düşük — yeni tablolar, bağımlılık yok |
| Step 2 | Mapping tablosu silinir | Düşük — bilgi kaybı yok |
| Step 3-4 | tenant_id sütun drop | Orta — backfill tekrarı gerekir |
| Step 5 | NOT NULL kaldır | Düşük |
| Step 6-7 | FK drop, eski sütunlar korunuyor | Düşük |

---

## 9. Test Stratejisi

### 9.1 Test Piramidi

```
          ┌───────────────┐
          │   E2E Tests   │   ← Playwright: Admin panel UI akışları
          │   (10 senaryo) │
          ├───────────────┤
          │  Integration  │   ← pytest: API endpoint'leri, DB sorguları
          │  (50+ test)   │   ← Auth flow, tenant izolasyon, RBAC
          ├───────────────┤
          │  Unit Tests   │   ← pytest: Service fonksiyonları, helpers
          │  (100+ test)  │   ← JWT, permission, crypto, model validation
          └───────────────┘
```

### 9.2 Kritik Test Senaryoları

| # | Senaryo | Tip | Öncelik |
|---|---------|-----|---------|
| T1 | Login → JWT dönüşü → protected endpoint erişimi | Integration | P0 |
| T2 | Tenant-A user → Tenant-B verisi erişim denemesi → 403 | Integration | P0 |
| T3 | Consultant, atanmadığı projede işlem → 403 | Integration | P0 |
| T4 | Tenant Admin, tüm projelerde CRUD → 200 | Integration | P0 |
| T5 | Expired JWT → 401, refresh → yeni JWT | Integration | P0 |
| T6 | Viewer, requirement oluşturma denemesi → 403 | Integration | P1 |
| T7 | Email davet → kayıt → şifre belirle → login | E2E | P1 |
| T8 | Tenant Admin kullanıcı deaktif → login denemesi → 403 | Integration | P1 |
| T9 | Mevcut API key auth hâlâ çalışıyor (backward compat) | Integration | P1 |
| T10 | 1000 concurrent JWT doğrulama → <50ms p95 | Performance | P2 |

### 9.3 Regression Test

Her sprint sonunda:
- Mevcut 35+ test dosyası çalıştırılır (`pytest tests/`)
- Smoke test production script (`./smoke_test_production.sh`)
- E2E admin panel testleri (`npx playwright test`)

---

## 10. Risk Matrisi

| # | Risk | Olasılık | Etki | Mitigasyon |
|---|------|---------|------|-----------|
| R1 | 60+ tabloya tenant_id ekleme sırasında veri kaybı | Düşük | Yüksek | Additive migration + data integrity check + backup |
| R2 | JWT geçişinde mevcut API entegrasyonları kırılır | Orta | Yüksek | Backward compat: API key + Basic Auth fallback korunur |
| R3 | Permission matrisi karmaşıklığı → yanlış yetkilendirme | Orta | Yüksek | Kapsamlı RBAC unit test + cross-tenant penetration test |
| R4 | Production'da migration downtime | Düşük | Orta | Online migration (nullable → backfill → NOT NULL) |
| R5 | Performance degradation (tenant_id filtre her sorguda) | Düşük | Orta | Composite index + Redis cache + load test |
| R6 | TeamMember → User eşleştirme hataları | Orta | Düşük | Email-based auto-match + manual review UI |
| R7 | SSO entegrasyonunda IdP yapılandırma sorunları | Yüksek | Orta | Phase 3'e ertelenmiş, mock IdP ile test |
| R8 | Refresh token çalınması (XSS) | Düşük | Yüksek | HttpOnly cookie, token rotation, IP binding |
| R9 | Sprint takviminde gecikme | Orta | Orta | %20 buffer dahil edildi, fazlar bağımsız deploy edilebilir |
| R10 | Mevcut test suite auth değişikliğiyle kırılır | Yüksek | Orta | conftest.py'de test fixture: auto-JWT token, test tenant |

---

## 11. Kabul Kriterleri

### Phase 1 Kabul Kriterleri (Milestone 2)

| # | Kriter | Doğrulama Yöntemi |
|---|--------|------------------|
| AC-1 | Kullanıcı email+şifre ile login olabilir ve JWT alabilir | curl test |
| AC-2 | JWT ile protected endpoint'e erişilebilir | curl + pytest |
| AC-3 | Expired JWT reddedilir (401) | pytest |
| AC-4 | Refresh token ile yeni JWT alınabilir | pytest |
| AC-5 | Tenant Admin kullanıcı oluşturabilir/davet edebilir | Admin UI E2E |
| AC-6 | Tenant Admin rol atayabilir ve değiştirebilir | Admin UI E2E |
| AC-7 | Tenant Admin kullanıcıyı projelere atayabilir | Admin UI E2E |
| AC-8 | Mevcut API key auth hâlâ çalışıyor | smoke test |
| AC-9 | 8 sistem rolü seed edilmiş ve izinleri doğru | pytest |
| AC-10 | Mevcut test suite regression geçiyor | pytest full run |

### Phase 2 Kabul Kriterleri (Milestone 3)

| # | Kriter | Doğrulama Yöntemi |
|---|--------|------------------|
| AC-11 | Tenant-A kullanıcısı Tenant-B verisini göremez | penetration test |
| AC-12 | Tüm 60+ tablo tenant_id sütununa sahip | DB schema check |
| AC-13 | Platform Admin tenant oluşturabilir/dondurabilir | Admin UI E2E |
| AC-14 | 17 blueprint tamamı permission-controlled | route audit script |
| AC-15 | Viewer rolü sadece okuma yapabilir | RBAC test suite |

### Phase 3 Kabul Kriterleri (Milestone 4)

| # | Kriter | Doğrulama Yöntemi |
|---|--------|------------------|
| AC-16 | Azure AD SSO ile login olunabilir | E2E test |
| AC-17 | CSV ile 100+ kullanıcı toplu yüklenebilir | Integration test |
| AC-18 | Tenant Admin özel rol oluşturabilir | Admin UI E2E |

---

## 12. Bağımlılıklar ve Önkoşullar

### 12.1 Python Paket Bağımlılıkları (Yeni)

| Paket | Versiyon | Amaç | Phase |
|-------|---------|------|-------|
| `PyJWT` | >=2.8 | JWT token oluşturma/doğrulama | Phase 1 |
| `bcrypt` | >=4.0 | Şifre hashing | Phase 1 |
| `email-validator` | >=2.0 | Email format doğrulama | Phase 1 |
| `python3-saml` | >=1.16 | SAML SSO (Phase 3) | Phase 3 |
| `authlib` | >=1.3 | OIDC SSO (Phase 3) | Phase 3 |

### 12.2 Altyapı Önkoşulları

| Önkoşul | Durum | Sorumlu |
|---------|-------|---------|
| PostgreSQL production DB | ✅ Hazır (Railway) | DevOps |
| Redis instance | ✅ Hazır (kullanılmıyor) | DevOps |
| SMTP mail servisi | ⚠️ Gerekli (davet maili) | DevOps |
| Azure AD test tenant | ❌ Gerekli (Phase 3) | IT Admin |
| SAP IAS test instance | ❌ Gerekli (Phase 3) | SAP Basis |

### 12.3 Teknik Borç (Çözülmesi Gereken)

| # | Borç | Neden | Ne Zaman |
|---|------|-------|----------|
| TB-1 | `assigned_to` string alanları (çeşitli modellerde) | User FK yerine string kullanılmış | Phase 2 (tenant_id geçişi sırasında) |
| TB-2 | `ProjectRole.user_id` string tipi | Proper FK olmalı | Phase 2 |
| TB-3 | `PERMISSION_MATRIX` hardcoded dict | DB-driven olmalı | Phase 1 Sprint 3 |
| TB-4 | `tenants.json` dosya tabanlı registry | DB'ye taşınmalı | Phase 2 |
| TB-5 | Auth disabled by default in dev | Development'ta da JWT test edilmeli | Phase 1 Sprint 2 |

---

## Ek A: Referans ADR Özeti

| ADR | Karar | Bu Plana Etkisi |
|-----|-------|----------------|
| ADR-1 | Shared DB + tenant_id | Sprint 5: tüm tablolara tenant_id ekleme |
| ADR-2 | JWT + SSO-ready | Sprint 2: JWT engine, Sprint 7-8: SSO |
| ADR-3 | Permission-based RBAC | Sprint 1: tablo, Sprint 3: middleware |
| ADR-4 | İki katmanlı admin | Sprint 4: Tenant Admin, Sprint 6: Platform Admin |
| ADR-5 | 8 sistem rolü | Sprint 1: seed data |
| ADR-6 | TeamMember + nullable user_id FK | Sprint 3: FK ekleme |
| ADR-7 | Tenant Admin önce | Sprint 4 (Phase 1) vs Sprint 6 (Phase 2) |
| ADR-8 | JWT payload = sub/tenant_id/roles | Sprint 2: token yapısı |
| ADR-9 | Permission + Membership ayrımı | Sprint 3: middleware zinciri |
| ADR-10 | TenantModel abstract class | Sprint 1: base.py |

---

## Ek B: Sprint Retrospektif Şablonu

Her sprint sonunda doldurulacak:

| Konu | Detay |
|------|-------|
| Sprint # / Tarih | — |
| Planlanan iş paketleri | — |
| Tamamlanan | — |
| Tamamlanamayan (neden) | — |
| Carry-over items | — |
| Blockers | — |
| Teknik karar / ADR güncellemesi | — |
| Sonraki sprint focus | — |

---

*— End of Document — v1.0 — Perga Admin Implementation Plan —*
*Kaynak: Perga_Admin_Architecture_v1.2.md (10 ADR Confirmed)*
