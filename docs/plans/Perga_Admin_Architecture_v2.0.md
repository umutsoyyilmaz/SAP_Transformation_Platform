# PERGA — Multi-Tenant Admin Panel Architecture Design Document

**NAVIGATE COMPLEXITY**

*Industry Research & Recommendations — Jira Cloud | Monday.com | Linear | Best Practices*

**Version 2.0 — February 2026 — All 4 Phases IMPLEMENTED — 10 ADR Confirmed**

Univer Yazılım ve Danışmanlık A.Ş.

---

## Table of Contents

1. Executive Summary
2. Industry Analysis: How the Leaders Do It
   - 2.1 Jira Cloud (Atlassian)
   - 2.2 Monday.com
   - 2.3 Linear
3. Comparative Matrix
4. Perga Architecture Recommendation
   - 4.1 Two-Layer Admin Model
   - 4.2 Role Hierarchy & TeamMember Entegrasyonu
   - 4.3 Permission System (RBAC)
   - 4.4 Multi-Tenant Data Isolation
   - 4.5 Authentication Strategy
   - 4.6 Permission vs Membership Kuralı (ADR-9)
   - 4.7 Tenant Context Middleware (ADR-10)
5. Data Model Design
6. Admin Panel UI Wireframes
7. Migration Plan (Mevcut Sistem → Yeni Mimari)
8. Implementation Status (All Phases Complete)
9. Technology Stack & Codebase Summary
10. Decision Log

---

## 1. Executive Summary

Perga, SAP S/4HANA dönüşüm projelerini yönetmek için geliştirilen bir SaaS platformudur. Platform, birden fazla müşteri şirketine hizmet verebilmek için sağlam bir multi-tenant yapısı, rol tabanlı erişim kontrolü (RBAC) ve iki katmanlı admin paneline sahiptir.

Bu doküman, endüstri liderlerinin (Jira Cloud, Monday.com, Linear) admin panel mimarilerini analiz ederek Perga için en uygun yaklaşımı belirlemiştir. 10 mimari karar (ADR) alınmış, tamamı onaylanmış ve **tüm 4 faz başarıyla uygulanmıştır.**

> **✅ Uygulama Durumu — Şubat 2026**
>
> | Faz | Sprint | Durum | Test |
> |-----|--------|-------|------|
> | Phase 1: Foundation + Tenant Admin | Sprint 1-4 | ✅ Tamamlandı | All pass |
> | Phase 2: Platform Admin + RBAC | Sprint 5-6 | ✅ Tamamlandı | 65/65 pass |
> | Phase 3: SSO & Enterprise | Sprint 7-8 | ✅ Tamamlandı | 164/164 pass |
> | Phase 4: Scale & Polish | Sprint 9-10 | ✅ Tamamlandı | 99/99 pass |
>
> **Toplam: ~2280+ test, 31 blueprint, 20 model modülü, 38 servis**

> **Kesinleşen Mimari Kararlar (10 ADR)**
>
> - **ADR-1:** Tenant İzolasyonu — Shared DB + tenant_id (Hybrid opsiyonu ile) ✅ Uygulandı
> - **ADR-2:** Kimlik Doğrulama — Custom JWT auth + SSO (Azure AD / SAP IAS) ✅ Uygulandı
> - **ADR-3:** Yetkilendirme — Permission-based RBAC (roller = izin koleksiyonları) ✅ Uygulandı
> - **ADR-4:** Admin Panel — İki katman (Platform Admin + Tenant Admin) ✅ Uygulandı
> - **ADR-5:** Başlangıç Roller — 8 sistem rolü (SAP Activate uyumlu) + Custom Roles ✅ Uygulandı
> - **ADR-6:** TeamMember — Proje içi bilgi katmanı, opsiyonel user_id FK ile bağlantı ✅ Uygulandı
> - **ADR-7:** Öncelik — Tenant Admin paneli Phase 1, Platform Admin Phase 2 ✅ Uygulandı
> - **ADR-8:** JWT Payload — Sadece sub/tenant_id/roles; project listesi DB'den kontrol edilir ✅ Uygulandı
> - **ADR-9:** Erişim Kuralı — "Permission kapıyı açar, Membership odayı belirler" ✅ Uygulandı
> - **ADR-10:** Tenant Filter — Scoped Base Model (TenantModel abstract class) ✅ Uygulandı

---

## 2. Industry Analysis: How the Leaders Do It

Aşağıda üç farklı proje yönetim platformunun admin panel yapıları detaylı olarak incelenmiştir.

### 2.1 Jira Cloud (Atlassian)

Atlassian'ın Jira Cloud platformu, endüstrinin en karmaşık ve olgun multi-tenant mimarilerinden birine sahiptir. Micros PaaS üzerine kurulu shared-infrastructure modeli ile milyonlarca tenantı destekler.

**Admin Hiyerarşisi (4 Seviye)**

| Seviye | Rol | Kapsam | Tipik Görevler |
|--------|-----|--------|----------------|
| 1 | Organization Admin | Tüm site ve ürünler | Faturalama, güvenlik politikaları, diğer admin atamaları |
| 2 | Site Admin | Tek bir Jira sitesi | Kullanıcı yönetimi, uygulama kurulumu |
| 3 | Product Admin | Tek ürün (Jira/Confluence) | Günlük operasyonlar, şema yönetimi |
| 4 | Project Admin | Tek proje/space | Rol atama, workflow düzenleme |

**İzin Sistemi**

- **Global Permissions:** Sistem genelinde geçerli izinler (admin, browse users vb.)
- **Permission Schemes:** Projeler arası paylaşılabilen izin şablonları
- **Project Roles:** Proje bazlı esnek roller (Lead Developer, QA Lead vb.)
- **Issue Security:** Bireysel iş öğesi seviyesinde görünürlük kontrolü
- **Workflow Restrictions:** Durum geçişlerinde izin kontrolü

> **Jira'dan Alınacak Ders**
>
> - Permission Schemes sayesinde yüzlerce projede tutarlı izin yönetimi mümkün
> - Project Roles ile proje adminleri global admin'e ihtiyaç duymadan yetki yönetebiliyor
> - SSO/SAML desteği domain doğrulama ile entegre çalışıyor

### 2.2 Monday.com

Monday.com daha basit bir admin yapısı kullanır. Tek bir Account Admin rolü vardır; Enterprise planda custom sub-admin roller tanımlanabilir.

**Kullanıcı Tipleri (4 Seviye)**

| Tip | Erişim | Maliyet | Öne Çıkan Özellik |
|-----|--------|---------|-------------------|
| Admin | Tam kontrol | Ücretli lisans | Kullanıcı, faturalama, güvenlik, API yönetimi |
| Member | Main board düzenleme | Ücretli lisans | Private/Shareable board'lara davet ile erişim |
| Viewer | Sadece görüntüleme | Ücretsiz, sınırsız | Rapor görüntüleme, yorum yapamaz |
| Guest | Sınırlı (dış kullanıcı) | Ücretsiz (Pro/Ent.) | Sadece davet edilen Shareable board'lar |

**İzin Katmanları**

- **Account Permissions:** Hangi kullanıcı tipinin hangi özellikleri kullanabileceği
- **Workspace Permissions:** Açık vs Kapalı çalışma alanları (Enterprise)
- **Board Permissions:** Owner, Editor, Contributor, Viewer rolleri
- **Column Permissions:** Hassas sütunlarda düzenleme/görüntüleme kısıtlaması

> **Monday.com'dan Alınacak Ders**
>
> - Viewer ve Guest kullanıcıların ücretsiz/sınırsız olması hızlı adapte olma sağlıyor
> - Bulk import (CSV) ile toplu kullanıcı onboarding destekleniyor
> - Custom Roles (Enterprise) sub-admin yetkileri tanımlama imkanı veriyor
> - Tidy Up özelliği inaktif board'ları temizleyerek platform hijyeni sağlıyor

### 2.3 Linear

Linear minimalist yaklaşımıyla öne çıkar. Workspace → Teams → Projects hiyerarşisinde 3 seviyeli bir rol yapısı kullanır.

**Rol Hiyerarşisi**

| Rol | Kapsam | Temel Yetkiler |
|-----|--------|----------------|
| Workspace Owner | Tüm workspace | Faturalama, güvenlik, audit log, OAuth onayları |
| Workspace Admin | Tüm workspace | Rutin operasyonlar, sınırlı yetkiler (Ent. için özelleştirilebilir) |
| Team Owner | Tek takım | Takım ayarları, üye yönetimi, izinler |
| Member | Workspace geneli | Tam erişim (özel takımlar hariç) |
| Guest | Davet edilen takımlar | Sadece davet edilen takımlara erişim |

> **Linear'dan Alınacak Ders**
>
> - Basit rol modeli hızlı onboarding ve düşük öğrenme eğrisi sağlıyor
> - Team bazlı izolasyon (Private Teams) ek güvenlik katmanı oluşturuyor
> - Allowed email domains ile otomatik workspace katılımı destekleniyor
> - SCIM entegrasyonu ile IdP tabanlı kullanıcı yönetimi (Enterprise)

---

## 3. Comparative Matrix

| Özellik | Jira Cloud | Monday.com | Linear | Perga (Uygulanan) |
|---------|-----------|------------|--------|-------------------|
| Admin Seviyeleri | 4 (Org/Site/Product/Project) | 2 (Admin/Custom) | 3 (Owner/Admin/Team) | 3 (Platform/Tenant/Project) ✅ |
| Kullanıcı Tipleri | Groups + Roles | 4 tip (Admin/Member/Viewer/Guest) | 5 (Owner–Guest) | 8 sistem rol + custom roles ✅ |
| İzin Modeli | Permission Schemes + Project Roles | Account + Board + Column | Workspace + Team | Permission-based RBAC ✅ |
| Multi-Tenancy | Shared infra, tenant izolasyon | Tek account per org | Workspace per org | Shared DB + tenant_id + Schema-per-tenant ✅ |
| SSO Desteği | SAML/OIDC (tüm planlarda) | Enterprise plan | Google SSO + SAML (Ent.) | OIDC + SAML + Domain-based ✅ |
| SCIM Provisioning | Evet | Enterprise | Evet (Enterprise) | SCIM 2.0 (RFC 7643/7644) ✅ |
| Custom Roles | Project Roles ile | Enterprise Custom Roles | Hayır (sabit roller) | Evet (tenant özel) ✅ |
| Proje Bazlı Erişim | Permission Scheme per proje | Board Permissions | Team membership | project_members tablo ✅ |
| Audit Log | Evet (Organization) | Evet (Enterprise) | Evet (Enterprise) | Evet (immutable, tüm CRUD) ✅ |
| Feature Flags | Evet (internal) | Evet (internal) | Evet (internal) | Evet (tenant bazlı) ✅ |
| Rate Limiting | Evet (plan-based) | Evet | Evet | Evet (plan-based, 5 tier) ✅ |
| Data Export | Evet | Evet | Evet | KVKK/GDPR JSON/CSV ✅ |

---

## 4. Perga Architecture Recommendation

### 4.1 Two-Layer Admin Model

Jira ve diğer platformlardan öğrenilen en önemli ders: Platform Admin ile Tenant Admin ayrımı zorunludur. Bu ayrım, müşteri özerkliğini sağlarken destek yükünü azaltır.

| | Layer 1: Platform Admin (Perga Ekibi) | Layer 2: Tenant Admin (Müşteri) |
|---|---------------------------------------|--------------------------------|
| Erişim | Perga iç ekibi | Müşteri IT / PM |
| Kullanıcı Yön. | Tenant oluştur/dondur/sil | Kendi şirket kullanıcıları CRUD |
| Lisans | Plan ve kotaları yönet | Kendi kullanımını görüntüle |
| Güvenlik | Global politikalar | Şifre politikası, SSO config |
| Proje | Tüm tenant projelerini gör | Kendi projelerini oluştur/yönet |
| Raporlama | Platform metrikleri | Şirket içi raporlar |
| Master Data | Global şablonlar | Process hierarchy, scope items |
| URL | `/platform-admin/*` | `/admin/*` (tenant-scoped) |

### 4.2 Role Hierarchy & TeamMember Entegrasyonu

Perga için önerilen rol yapısı, SAP Activate metodolojisinin gerektirdiği rol çeşitliliğini destekleyecek şekilde tasarlanmıştır:

| Rol | Tip | Kapsam | Tipik Kullanıcı |
|-----|-----|--------|-----------------|
| Platform Super Admin | System | Tüm tenantlar | Perga DevOps |
| Tenant Admin | Tenant | Tek tenant | Müşteri IT Yöneticisi |
| Program Manager | Tenant | Tüm projeler | SAP Program Yöneticisi |
| Project Manager | Project | Atanan projeler | SAP Proje Yöneticisi |
| Functional Consultant | Project | Atanan projeler | SAP Fonksiyonel Danışman |
| Technical Consultant | Project | Atanan projeler | SAP ABAP/Basis |
| Tester | Project | Atanan projeler | Test Mühendisi |
| Business User / Key User | Project | Atanan projeler | Son Kullanıcı Temsilcisi |
| Viewer | Project | Atanan projeler | Yönetici / Denetçi |

> **TeamMember ↔ User Entegrasyonu (ADR-6)**
>
> - **Proje içi TeamMember:** Bilgi katmanı — kim hangi görevde, iletişim bilgileri, SAP modül sorumluluğu
> - **Tenant Admin User:** Yönetim katmanı — login, rol atama, proje assign, deaktif etme
> - **Bağlantı:** TeamMember tablosuna opsiyonel `user_id` FK eklenir
> - **Kayıtlı kullanıcı →** user_id dolu (link kurulur), **harici kişi →** user_id NULL (sadece bilgi)
> - **Mevcut TeamMember verisi bozulmaz, kademeli geçiş sağlanır**

### 4.3 Permission System (RBAC)

Jira'nın Permission Scheme yaklaşımından esinlenerek, roller granular izinlerin koleksiyonu olarak tanımlanır. Bu sayede yeni özellik eklenince sadece izin tanımı ve rol ataması yapılır:

| Kategori | İzin | Tenant Admin | PM | Consultant | Tester | Viewer |
|----------|------|-------------|-----|------------|--------|--------|
| Requirements | create/edit | ✓ | ✓ | ✓ | — | — |
| Requirements | delete | ✓ | ✓ | — | — | — |
| Requirements | approve | ✓ | ✓ | — | — | — |
| Workshops | create/facilitate | ✓ | ✓ | ✓ | — | — |
| Workshops | approve | ✓ | ✓ | — | — | — |
| Tests | create | ✓ | ✓ | ✓ | ✓ | — |
| Tests | execute | ✓ | ✓ | — | ✓ | — |
| Tests | approve | ✓ | ✓ | — | — | — |
| Projects | create | ✓ | ✓ | — | — | — |
| Projects | archive | ✓ | — | — | — | — |
| Users | invite/deactivate | ✓ | — | — | — | — |
| Reports | view | ✓ | ✓ | ✓ | ✓ | ✓ |
| Reports | export | ✓ | ✓ | ✓ | — | — |
| Admin | settings | ✓ | — | — | — | — |

### 4.4 Multi-Tenant Data Isolation

Endüstri analizi üç temel yaklaşım göstermektedir. Perga varsayılan olarak Shared DB + tenant_id modelini kullanır, büyük kurumsal müşteriler için schema-per-tenant desteği Sprint 10'da uygulanmıştır:

| Model | Avantaj | Dezavantaj | Kim İçin | Perga Durumu |
|-------|---------|------------|----------|-------------|
| Shared DB + tenant_id | Düşük maliyet, kolay yönetim | Titiz middleware gerekli | Küçük-orta tenantlar | ✅ Varsayılan (aktif) |
| Schema-per-tenant | İyi izolasyon, orta maliyet | Migration karmaşıklığı | Orta-büyük tenantlar | ✅ Uygulandı (Sprint 10) |
| Database-per-tenant | Maksimum izolasyon | Yüksek maliyet, yönetim | Enterprise müşteriler | Gelecek sürüm |

**Schema-per-Tenant Servisi** (`app/services/schema_service.py`):

- `create_tenant_schema(tenant_id)` — Dedicated PostgreSQL schema oluşturur
- `clone_tables_to_schema(schema_name)` — Public schema tablolarını klonlar
- `set_search_path(schema_name)` — Session-level `search_path` değiştirir
- `list_tenant_schemas()` — Tüm tenant schema'larını listeler
- SQLite ortamlarında graceful fallback ("requires PostgreSQL" mesajı)

> **Kritik Uygulama Kuralları (Tümü Uygulandı)**
>
> - ✅ Her API isteği tenant context taşır (JWT claims + `tenant_context` middleware)
> - ✅ Her DB sorgusu tenant_id filtresi içerir (`TenantModel.query_for_tenant()`)
> - ✅ Composite index: `(tenant_id, entity_id)` tüm tablolarda
> - ✅ Audit log: Tüm CRUD işlemleri immutable log'a yazılır (`audit_bp`)
> - ✅ Feature flags: Tenant bazlı özellik açma/kapama (`feature_flag_service`)
> - ✅ Soft delete: `SoftDeleteMixin` ile veri kalıcı olarak silinmez
> - ✅ KVKK/GDPR export: Tenant verisi JSON/CSV olarak export edilebilir

### 4.5 Authentication Strategy

Platform üç katmanlı kimlik doğrulama stratejisi uygulamıştır. Tüm fazlar tamamlanmıştır:

| Phase | Yöntem | Durum | Detay |
|-------|--------|-------|-------|
| Phase 1 (MVP) | Email + Password + JWT | ✅ Aktif | bcrypt hash, access token (15dk) + refresh token (7gün), Basic Auth (production) |
| Phase 2 | SSO (SAML/OIDC) | ✅ Aktif | Azure AD (OIDC), SAP IAS (SAML), Google Workspace |
| Phase 3 | Domain-based SSO + SCIM | ✅ Aktif | Tenant email domainına göre otomatik yönlendirme + SCIM 2.0 provisioning |

**SSO Servisi** (`app/services/sso_service.py` — 704 satır):

- OIDC Authorization Code Flow with PKCE (Azure AD)
- SAML SP-initiated SSO (SAP IAS) — SAMLResponse parsing
- Domain-based tenant auto-matching (`TenantDomain` modeli)
- İlk SSO login'de otomatik user provisioning
- Tenant-specific SSO konfigürasyonu (`SSOConfig` modeli)

**SCIM 2.0 Servisi** (`app/services/scim_service.py` — 414 satır):

- RFC 7643/7644 uyumlu user provisioning
- User CRUD via SCIM JSON schema
- Bearer token authentication per tenant
- Azure AD, Okta vb. IdP push desteği

> **JWT Token Yapısı (ADR-8) — Uygulandı**
>
> JWT payload'da **sadece** şu alanlar tutulur:
>
> - `sub`: user_id
> - `tenant_id`: müşteri şirket ID
> - `roles`: ["project_manager", "consultant"]
> - `exp`: 15 dakika (access token), 7 gün (refresh token)
>
> ⚠️ **Project listesi JWT'de TUTULMAZ.** Project membership her istekte DB'den kontrol edilir.

### 4.6 Permission vs Membership Kuralı (ADR-9)

Sistemde üç erişim katmanı vardır. Bunların birbirine karışmaması için tek bir net kural tanımlanmıştır:

> **"Permission kapıyı açar, Membership odayı belirler."**

| Katman | Ne Kontrol Eder | Nereden Gelir | Örnek |
|--------|----------------|---------------|-------|
| Tenant Context | Hangi şirketin verisi | JWT `tenant_id` claim | Kullanıcı sadece kendi tenant verisini görür |
| Permission | Ne yapabilir (yetenek) | Role → Permission tablosu | `requirements.create`, `tests.execute` |
| Project Membership | Nereye erişir (kapsam) | `project_members` tablosu | Project-5'e atanmış, Project-7'ye değil |

**Erişim kontrol sırası (middleware zinciri):**

```
1. JWT valid mi?                    → 401 Unauthorized
2. Tenant context doğru mu?         → 403 Forbidden
3. İlgili permission var mı?        → 403 Forbidden ("Yetkiniz yok")
4. Project membership var mı?       → 403 Forbidden ("Bu projeye erişiminiz yok")
5. → İşlemi gerçekleştir
```

**Somut senaryolar:**

| Senaryo | Permission | Membership | Sonuç |
|---------|-----------|------------|-------|
| Consultant, Project-5'te requirement oluşturmak istiyor | ✓ requirements.create | ✓ Project-5 üyesi | ✅ İzin verilir |
| Consultant, Project-7'de requirement oluşturmak istiyor | ✓ requirements.create | ✗ Project-7 üyesi değil | ❌ Reddedilir |
| Viewer, Project-5'te requirement oluşturmak istiyor | ✗ requirements.create yok | ✓ Project-5 üyesi | ❌ Reddedilir |
| Tenant Admin, herhangi bir projede | ✓ (tüm izinler) | — (tenant-wide erişim) | ✅ Tüm projelere erişir |
| Program Manager, herhangi bir projede | ✓ (PM izinleri) | — (tenant-wide erişim) | ✅ Tüm projelere erişir |

**İstisna:** Tenant-scoped roller (Tenant Admin, Program Manager) project membership kontrolünden muaftır — tüm tenant projelerine erişir.

### 4.7 Tenant Context Middleware (ADR-10)

Shared DB + tenant_id modelinde en kritik teknik risk, bir sorguda tenant filtresi unutulması ve veri sızıntısı olmasıdır. Bu riski ortadan kaldırmak için Scoped Base Model yaklaşımı seçilmiştir.

**Neden Scoped Base Model (Yöntem B)?**

| Yöntem | Açıklama | Avantaj | Dezavantaj |
|--------|----------|---------|------------|
| A: SQLAlchemy Event Listener | `before_compile` event'inde otomatik filter | Sıfır kod tekrarı | Debug çok zor, implicit behavior, beklenmeyen davranış riski |
| **B: Scoped Base Model** | Abstract `TenantModel` class, explicit inherit | Açık ve okunabilir, unutma riski düşük, test edilebilir | Her modelde inherit gerekli |

**Seçilen: Yöntem B — TenantModel Abstract Class**

```python
class TenantModel(db.Model):
    """Tüm tenant-scoped entity'ler bu class'tan inherit eder."""
    __abstract__ = True

    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id'),
        nullable=False,
        index=True
    )

    @classmethod
    def query_for_tenant(cls, tenant_id):
        """Tenant-scoped query helper."""
        return cls.query.filter_by(tenant_id=tenant_id)
```

```python
# Kullanım — Her tenant-scoped model:
class Project(TenantModel):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    # tenant_id otomatik gelir

class Requirement(TenantModel):
    __tablename__ = 'requirements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300))
    # tenant_id otomatik gelir
```

```python
# Request middleware — her istekte tenant context set eder:
@app.before_request
def set_tenant_context():
    if request.endpoint and 'api' in request.endpoint:
        tenant_id = get_tenant_from_jwt()  # JWT'den parse et
        g.tenant_id = tenant_id

# Route'larda kullanım:
@app.route('/api/v1/requirements')
@require_permission('requirements.view')
def list_requirements():
    items = Requirement.query_for_tenant(g.tenant_id).all()
    return jsonify([r.to_dict() for r in items])
```

**Güvenlik katmanları:**

- `TenantModel` inherit etmeyen model → tenant_id alanı yok → derleme zamanında fark edilir
- `query_for_tenant()` kullanılmazsa → code review'da yakalanır
- Ek güvenlik: `@app.after_request` hook ile response'ta tenant_id kontrolü (paranoid mode)

---

## 5. Data Model Design

Aşağıdaki tablo yapısı, mevcut Perga veritabanına eklenecek multi-tenant ve RBAC tablolarını tanımlar:

### tenants

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz tenant kimliği |
| name | VARCHAR(200) NOT NULL | Şirket adı (Görünen) |
| slug | VARCHAR(100) UNIQUE | URL-safe benzersiz isim |
| domain | VARCHAR(200) | Email domainı (SSO için) |
| plan | VARCHAR(50) DEFAULT 'trial' | Abonelik planı: trial/standard/premium/enterprise |
| max_users | INT DEFAULT 10 | Maksimum kullanıcı sayısı |
| max_projects | INT DEFAULT 3 | Maksimum proje sayısı |
| is_active | BOOLEAN DEFAULT TRUE | Tenant aktif mi? |
| settings | JSONB | Tenant özel ayarlar (SSO config, tema vb.) |
| created_at / updated_at | TIMESTAMPTZ | Oluşturma / güncelleme tarihi |

### users

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kullanıcı kimliği |
| tenant_id | INT FK → tenants.id | Ait olduğu tenant |
| email | VARCHAR(200) NOT NULL | Unique per tenant |
| password_hash | VARCHAR(256) | bcrypt hash (SSO'da NULL) |
| full_name | VARCHAR(200) | Kullanıcı adı |
| avatar_url | VARCHAR(500) | Profil resmi URL |
| status | VARCHAR(20) DEFAULT 'active' | active / suspended / invited / deactivated |
| auth_provider | VARCHAR(50) DEFAULT 'local' | local / azure_ad / sap_ias / google |
| last_login_at | TIMESTAMPTZ | Son giriş zamanı |
| created_at / updated_at | TIMESTAMPTZ | Oluşturma / güncelleme tarihi |

### roles

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Rol kimliği |
| tenant_id | INT FK (NULL = system role) | NULL: tüm tenantlarda geçerli, değilse tenant özel |
| name | VARCHAR(100) NOT NULL | Rol adı (tenant_admin, consultant vb.) |
| display_name | VARCHAR(200) | Görünen isim |
| description | TEXT | Rol açıklaması |
| is_system | BOOLEAN DEFAULT FALSE | Silinemez sistem rolü mü? |
| created_at | TIMESTAMPTZ | Oluşturma tarihi |

### permissions + role_permissions + user_roles

| Tablo | Sütunlar | Açıklama |
|-------|----------|----------|
| permissions | id, codename, category, display_name | Granular izin tanımları (requirements.create, tests.execute vb.) |
| role_permissions | role_id FK, permission_id FK | Rol-izin eşleştirmesi (M:N) |
| user_roles | user_id FK, role_id FK, assigned_by, assigned_at | Kullanıcı-rol ataması (M:N, tenant-scoped) |

### project_members

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kimlik |
| project_id | INT FK → projects.id | Proje |
| user_id | INT FK → users.id | Kullanıcı |
| role_in_project | VARCHAR(50) | Projede özel rol (opsiyonel override) |
| joined_at | TIMESTAMPTZ | Projeye katılım tarihi |

### sessions (Auth)

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | UUID PK | Session kimliği |
| user_id | INT FK → users.id | Kullanıcı |
| token_hash | VARCHAR(256) | Refresh token hash |
| ip_address | VARCHAR(45) | İstemci IP |
| user_agent | TEXT | Browser/cihaz bilgisi |
| expires_at | TIMESTAMPTZ | Token geçerlilik süresi |
| created_at | TIMESTAMPTZ | Oluşturma tarihi |

### sso_configs (Sprint 7)

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kimlik |
| tenant_id | INT FK → tenants.id | Ait olduğu tenant |
| provider | VARCHAR(50) | SSO sağlayıcı: azure_ad / sap_ias / google |
| config | JSON | Provider-specific konfigürasyon (client_id, metadata_url vb.) |
| is_active | BOOLEAN DEFAULT FALSE | SSO aktif mi? |
| created_at / updated_at | TIMESTAMPTZ | Oluşturma / güncelleme tarihi |

### tenant_domains (Sprint 7)

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kimlik |
| tenant_id | INT FK → tenants.id | Ait olduğu tenant |
| domain | VARCHAR(200) UNIQUE | Email domainı (örn: acme.com) |
| verified | BOOLEAN DEFAULT FALSE | Domain doğrulanmış mı? |
| created_at | TIMESTAMPTZ | Oluşturma tarihi |

### feature_flags (Sprint 9)

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kimlik |
| key | VARCHAR(100) UNIQUE | Benzersiz flag anahtarı (örn: ai_assistant) |
| display_name | VARCHAR(200) | Görünen isim |
| description | TEXT | Flag açıklaması |
| default_enabled | BOOLEAN DEFAULT FALSE | Varsayılan durum |
| category | VARCHAR(50) DEFAULT 'general' | general / ai / beta / experimental |
| created_at / updated_at | TIMESTAMPTZ | Oluşturma / güncelleme tarihi |

### tenant_feature_flags (Sprint 9)

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| id | SERIAL PK | Benzersiz kimlik |
| tenant_id | INT FK → tenants.id | Ait olduğu tenant |
| feature_flag_id | INT FK → feature_flags.id | Hangi flag |
| is_enabled | BOOLEAN NOT NULL | Tenant-specific override |
| UNIQUE | (tenant_id, feature_flag_id) | Her tenant-flag çifti benzersiz |

---

## 6. Admin Panel UI Wireframes

Admin paneli iki ayrı arayüz olarak tasarlanacaktır:

### Platform Admin Panel

| Sayfa | URL Pattern | İçerik |
|-------|-------------|--------|
| Dashboard | /platform-admin/ | Toplam tenant, aktif kullanıcı, API kullanım, hata oranları |
| Tenants | /platform-admin/tenants | Tenant listesi, oluştur/düzenle/dondur/sil |
| Tenant Detail | /platform-admin/tenants/:id | Kullanıcılar, projeler, kullanım istatistikleri, plan |
| Plans & Billing | /platform-admin/billing | Abonelik planları, kota yönetimi |
| System Health | /platform-admin/health | Server metrikleri, DB performansı, hata logları |
| Audit Log | /platform-admin/audit | Tüm tenantların işlem geçmişi |

### Tenant Admin Panel

| Sayfa | URL Pattern | İçerik |
|-------|-------------|--------|
| Dashboard | /admin/ | Kullanıcı sayısı, proje sayısı, son aktiviteler |
| Users | /admin/users | Kullanıcı listesi, davet et, rol ata, deaktif et |
| User Detail | /admin/users/:id | Profil, rol atamaları, proje üyelikleri |
| Roles | /admin/roles | Sistem rolleri + özel roller, izin matriksi |
| Projects | /admin/projects | Proje listesi, üye atama, arşivle |
| Teams | /admin/teams | Takım oluştur, kullanıcıları grupla |
| Company Settings | /admin/settings | Şirket profili, logo, SAP modülleri, SSO config |
| Audit Log | /admin/audit | Şirket içi işlem geçmişi |

---

## 7. Migration Plan (Mevcut Sistem → Yeni Mimari)

Mevcut sistemde Program, Project, TeamMember ve string-based assigned_to alanları bulunmaktadır. Yeni multi-tenant mimariye geçişte çakışma riski vardır. Bu plan kademeli ve geriye dönük uyumlu bir geçiş sağlar.

### Mevcut → Yeni Eşleştirme

| Mevcut Yapı | Yeni Yapı | Çakışma Riski | Çözüm |
|-------------|-----------|---------------|-------|
| Program (müşteri grubu) | Tenant | program_id vs tenant_id karışabilir | 1:1 migration script |
| Project (program altında) | Project (tenant altında) | project.program_id → project.tenant_id | FK ekleme + backfill |
| TeamMember.assigned_to (string) | users.id (int FK) | Tip uyumsuzluğu | Kademeli, nullable FK |
| assigned_to alanları (çeşitli tablolar) | user_id FK | String → int geçişi | Yeni alan ekle, eskiyi koru |

### Migration Adımları

**Phase 1a: Tenant Tablosu Oluştur**

- `tenants` tablosu oluştur (Alembic migration)
- Mevcut her Program kaydı için bir Tenant kaydı yarat (migration script)
- Program.id → Tenant.id 1:1 mapping tablosu tut (geçiş dönemi için)

**Phase 1b: Project'e tenant_id Ekle**

- `projects` tablosuna `tenant_id` FK ekle (nullable başlangıçta)
- Mevcut `program_id` üzerinden `tenant_id` alanını doldur (backfill script)
- Doğrulama: tüm projeler bir tenant'a bağlı mı?
- `tenant_id` NOT NULL yap

**Phase 1c: TeamMember'a user_id Ekle**

- `team_members` tablosuna `user_id` FK ekle (nullable — harici kişiler için NULL kalacak)
- Mevcut veri dokunulmaz — hiçbir kayıt silinmez veya değiştirilmez
- Yeni kullanıcılar kaydolunca, eşleşen TeamMember kayıtlarına user_id set edilir

**Phase 2: Program Entity Deprecation**

- Tüm API'lerde `program_id` yerine `tenant_id` kullanılmaya başlanır
- Program entity read-only moda alınır
- Frontend'de Program referansları Tenant'a güncellenir
- Program tablosu archive'a alınır (silinmez, soft-deprecate)

> **Migration Güvenlik Kuralları**
>
> - Her adım Alembic migration ile yapılır (geri alınabilir)
> - Her adım sonrası data integrity check script çalıştırılır
> - Eski alanlar silinmez, yeni alanlar eklenir (additive migration)
> - Canlı sistemde downtime olmamalı — tüm migration'lar online uygulanabilir

---

## 8. Implementation Status (All Phases Complete)

Tüm 4 faz başarıyla uygulanmıştır. Aşağıda her fazın detaylı durumu:

### Phase 1: Foundation + Tenant Admin MVP (Sprint 1-4) ✅

| Sprint | İçerik | Durum |
|--------|--------|-------|
| Sprint 1 | DB Models — tenants, users, roles, permissions, user_roles, sessions, project_members (7 tablo) | ✅ |
| Sprint 2 | JWT Auth — login, register, refresh, logout, bcrypt hash | ✅ |
| Sprint 3 | Middleware — tenant_context, permission_required, project_access, blueprint_permissions, rate_limiter, security_headers | ✅ |
| Sprint 4 | Admin UI — Tenant Admin panel, kullanıcı CRUD, davet, rol atama, proje assign | ✅ |

**Dosyalar:** `app/models/auth.py`, `app/middleware/`, `app/blueprints/auth_bp.py`, `app/blueprints/admin_bp.py`

### Phase 2: Platform Admin + RBAC Engine (Sprint 5-6) ✅

| Sprint | İçerik | Test | Durum |
|--------|--------|------|-------|
| Sprint 5 | tenant_id migration — tüm mevcut tablolara tenant_id FK, TenantModel abstract class | 65/65 | ✅ |
| Sprint 6 | Platform Admin — tenant CRUD, lisans yönetimi, kullanım metrikleri, blueprint permissions | 65/65 | ✅ |

**Dosyalar:** `app/blueprints/platform_admin_bp.py`, `app/middleware/blueprint_permissions.py`, `app/models/base.py`

### Phase 3: SSO & Enterprise (Sprint 7-8) ✅

| Sprint | İçerik | Test | Durum |
|--------|--------|------|-------|
| Sprint 7 | SSO Infrastructure — OIDC (Azure AD), SAML (SAP IAS), domain-based tenant matching, SSOConfig + TenantDomain models | 84/84 | ✅ |
| Sprint 8 | SCIM 2.0 + Bulk Import + Custom Roles + SSO E2E flow | 80/80 | ✅ |

**Dosyalar:** `app/services/sso_service.py` (704 LOC), `app/services/scim_service.py` (414 LOC), `app/services/bulk_import_service.py`, `app/services/custom_role_service.py`, `app/blueprints/sso_bp.py`, `app/blueprints/scim_bp.py`, `app/blueprints/bulk_import_bp.py`, `app/blueprints/custom_roles_bp.py`

### Phase 4: Scale & Polish (Sprint 9-10) ✅

| # | Item | Sprint | Durum |
|---|------|--------|-------|
| 4.1 | Feature Flags — global + tenant override, CRUD API, admin UI | Sprint 9 | ✅ |
| 4.2 | Redis Cache — permission/role cache (5dk TTL), tenant-aware invalidation | Sprint 9 | ✅ |
| 4.3 | Tenant Rate Limiting — plan-based: trial=100/min → enterprise=5000/min | Sprint 9 | ✅ |
| 4.4 | Dashboard Metrics — platform summary, user trends, plan distribution, login activity | Sprint 9 | ✅ |
| 4.5 | Onboarding Wizard — 4-step: company → admin → project → ready | Sprint 9 | ✅ |
| 4.6 | Data Export — KVKK/GDPR JSON/CSV export (users, roles, sessions, programs) | Sprint 10 | ✅ |
| 4.7 | Soft Delete — `SoftDeleteMixin` with deleted_at, restore(), query_active() | Sprint 10 | ✅ |
| 4.8 | Schema-per-Tenant — PG schema isolation for enterprise tenants | Sprint 10 | ✅ |
| 4.9 | Performance Tests — latency, throughput, concurrent access benchmarks | Sprint 10 | ✅ |
| 4.10 | Security Audit — OWASP Top 10 pattern tests (injection, XSS, SSRF, traversal) | Sprint 10 | ✅ |

**Dosyalar:** `app/services/feature_flag_service.py`, `app/services/cache_service.py`, `app/services/dashboard_service.py`, `app/services/onboarding_service.py`, `app/services/tenant_export_service.py`, `app/services/schema_service.py`, `app/models/feature_flag.py`, `app/models/soft_delete.py`, `app/blueprints/feature_flag_bp.py`, `app/blueprints/dashboard_bp.py`, `app/blueprints/onboarding_bp.py`, `app/blueprints/tenant_export_bp.py`

---

## 9. Technology Stack & Codebase Summary

### Core Stack

| Bileşen | Teknoloji | Detay |
|---------|-----------|-------|
| Framework | Flask 3.1.0 | App Factory pattern, 31 blueprint |
| ORM | SQLAlchemy 2.0.36 | Flask-SQLAlchemy, `db.session.get()` API |
| Dev DB | SQLite | File-based (`instance/sap_platform_dev.db`) |
| Test DB | SQLite | In-memory (`:memory:`) |
| Production DB | PostgreSQL | Railway, pool_size=5, max_overflow=10, pool_pre_ping=True |
| Cache | Redis | `REDIS_URL` env var, memory fallback for dev |
| Rate Limiter | Flask-Limiter | Per-blueprint + tenant plan-based limits |
| Auth | JWT + Basic Auth + SSO | Access token 15dk, Refresh 7gün, OIDC/SAML |
| SCIM | SCIM 2.0 | RFC 7643/7644, Bearer token auth |
| Email | SMTP | Configurable, TLS support |
| WSGI | Gunicorn | Timeout 120s, production deployment |
| Deployment | Railway | Auto-deploy on git push |
| Testing | pytest 8.3.4 | Session-scoped app, autouse rollback |

### Codebase Metrics

| Metrik | Değer |
|--------|-------|
| Blueprint sayısı | 31 |
| Model modülü | 20 |
| Servis modülü | 38 |
| Middleware modülü | 13 |
| Test dosyası | 38 Python + 1 Shell |
| Toplam test | ~2280+ |
| API route sayısı | ~150+ |
| Production URL | https://app.univer.com.tr |

### Registered Blueprints (31)

| # | Blueprint | URL Prefix | Sprint |
|---|-----------|-----------|--------|
| 1 | program_bp | /api/v1/programs | Sprint 1 |
| 2 | backlog_bp | /api/v1/backlog | Sprint 1 |
| 3 | testing_bp | /api/v1/testing | Sprint 1 |
| 4 | raid_bp | /api/v1/raid | Sprint 1 |
| 5 | ai_bp | /api/v1/ai | Sprint 1 |
| 6 | integration_bp | /api/v1/integrations | Sprint 1 |
| 7 | health_bp | /api/v1/health | Sprint 1 |
| 8 | metrics_bp | /api/v1/metrics | Sprint 1 |
| 9 | explore_bp | /api/v1/explore | Sprint 1 |
| 10 | data_factory_bp | /api/v1/data-factory | Sprint 1 |
| 11 | reporting_bp | /api/v1/reporting | Sprint 1 |
| 12 | audit_bp | /api/v1/audit | Sprint 3 |
| 13 | cutover_bp | /api/v1/cutover | Sprint 1 |
| 14 | notification_bp | /api/v1/notifications | Sprint 1 |
| 15 | run_sustain_bp | /api/v1/run-sustain | Sprint 1 |
| 16 | pwa_bp | / (manifest, sw.js) | Sprint 1 |
| 17 | traceability_bp | /api/v1/traceability | Sprint 1 |
| 18 | auth_bp | /api/v1/auth | Sprint 2 |
| 19 | admin_bp | /admin | Sprint 4 |
| 20 | platform_admin_bp | /platform-admin | Sprint 6 |
| 21 | sso_bp | /api/v1/sso | Sprint 7 |
| 22 | sso_ui_bp | /sso | Sprint 7 |
| 23 | scim_bp | /api/v1/scim | Sprint 8 |
| 24 | bulk_import_bp | /api/v1/admin/bulk-import | Sprint 8 |
| 25 | custom_roles_bp | /api/v1/admin/roles | Sprint 8 |
| 26 | roles_ui_bp | /roles | Sprint 8 |
| 27 | feature_flag_bp | /api/v1/admin/feature-flags | Sprint 9 |
| 28 | feature_flag_ui_bp | /feature-flags | Sprint 9 |
| 29 | dashboard_bp | /api/v1/admin/dashboard | Sprint 9 |
| 30 | onboarding_bp | /api/v1/onboarding | Sprint 9 |
| 31 | tenant_export_bp | /api/v1/admin/export | Sprint 10 |

### Middleware Stack (İstek İşleme Sırası)

```
Request → Basic Auth (production) → JWT Validation → Tenant Context → 
  Security Headers → Rate Limiter → Blueprint Permissions → 
  Permission Required → Project Access → Route Handler → 
  Timing → Response
```

| Middleware | Dosya | Görev |
|-----------|-------|-------|
| basic_auth | `app/middleware/basic_auth.py` | Production API koruması |
| jwt_auth | `app/middleware/jwt_auth.py` | JWT token doğrulama |
| tenant_context | `app/middleware/tenant_context.py` | `g.tenant_id` set eder |
| security_headers | `app/middleware/security_headers.py` | CSP, HSTS, X-Frame-Options |
| rate_limiter | `app/middleware/rate_limiter.py` | Plan-based rate limiting |
| blueprint_permissions | `app/middleware/blueprint_permissions.py` | Blueprint → permission mapping |
| permission_required | `app/middleware/permission_required.py` | `@require_permission` decorator |
| project_access | `app/middleware/project_access.py` | project_members kontrolü |
| timing | `app/middleware/timing.py` | Request/response süresi |
| diagnostics | `app/middleware/diagnostics.py` | DB/health diagnostics |
| logging_config | `app/middleware/logging_config.py` | Structured logging |

### Rate Limiting (Tenant Plan-Based)

| Plan | Limit | Kullanım |
|------|-------|----------|
| trial | 100/minute | Deneme tenantları |
| starter | 300/minute | Başlangıç planı |
| professional | 600/minute | Profesyonel plan |
| premium | 1000/minute | Premium plan |
| enterprise | 5000/minute | Kurumsal plan |

---

## 10. Decision Log

| # | Karar | Seçenek | Gerekçe | Durum |
|---|-------|---------|---------|-------|
| ADR-1 | Tenant izolasyon modeli | Shared DB + tenant_id + Schema-per-tenant | Düşük maliyet varsayılan, enterprise için PG schema izolasyonu | ✅ Uygulandı |
| ADR-2 | Authentication yöntemi | JWT + Basic Auth + SSO (OIDC/SAML) | MVP'den üretime: JWT → SSO → SCIM 2.0 | ✅ Uygulandı |
| ADR-3 | Yetkilendirme modeli | Permission-based RBAC + Custom Roles | Esnek, yeni özellik eklemede kolay, tenant-özel roller | ✅ Uygulandı |
| ADR-4 | Admin panel ayrımı | İki katman (Platform + Tenant) | Müşteri özerkliği, destek yükü azaltma | ✅ Uygulandı |
| ADR-5 | Başlangıç rol sayısı | 8 sistem rolü + custom roles | SAP Activate + tenant-özel roller | ✅ Uygulandı |
| ADR-6 | TeamMember entegrasyonu | Info-only + opsiyonel user_id FK | Bilgi katmanı vs yönetim katmanı ayrımı | ✅ Uygulandı |
| ADR-7 | Hangi admin panel önce | Tenant Admin (Phase 1) → Platform Admin (Phase 2) | Sıralı implementasyon tamamlandı | ✅ Uygulandı |
| ADR-8 | JWT payload içeriği | Sadece sub/tenant_id/roles | Project listesi dinamik, JWT ile sync sorunu yaratmaz | ✅ Uygulandı |
| ADR-9 | Erişim kontrol kuralı | Permission + Membership ayrımı | "Permission kapıyı açar, Membership odayı belirler" | ✅ Uygulandı |
| ADR-10 | Tenant filter mekanizması | Scoped Base Model (TenantModel) | Açık, okunabilir, test edilebilir | ✅ Uygulandı |

> **Platform Durumu — Şubat 2026**
>
> - ✅ Tüm 10 ADR onaylandı ve uygulandı
> - ✅ 4 faz, 10 sprint tamamlandı
> - ✅ 31 blueprint, 20 model modülü, 38 servis, 13 middleware
> - ✅ ~2280+ test (pytest), production smoke test
> - ✅ Production: https://app.univer.com.tr (Railway + PostgreSQL + Gunicorn)
> - ✅ SSO + SCIM 2.0 + Custom Roles + Feature Flags + Redis Cache
> - ✅ KVKK/GDPR data export + Soft Delete + Schema-per-Tenant
> - ✅ OWASP Top 10 güvenlik testleri

---

*— End of Document — v2.0 — All 4 Phases Implemented — 10 ADR Confirmed —*
