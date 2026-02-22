# ADR-002: SAP Auth Concept / RBAC Ayrımı

**Durum:** ✅ Onaylandı
**Tarih:** 2026-02-22
**Yazar:** Umut Soyyılmaz
**İlgili FDD:** `FDD-I02-authorization-concept-design.md`
**Bloke Ettiği Sprint İtemleri:** S5-01, S7-02
**Kapsam:** Platform RBAC modeli ile SAP yetkilendirme konsepti arasındaki sorumluluk sınırı

---

## 1. Karar Özeti

| # | Karar | Gerekçe |
|---|-------|---------|
| **D1** | Platform RBAC (`Role`, `Permission`, `permission_service.py`) ile SAP auth konsepti tümüyle **ayrı katmanlarda** yönetilecek | İki sistemin lifecycle'ı farklı; platform rolleri deploy-time değişir, SAP auth konsepti proje bazlı ve müşteri-taraflı |
| **D2** | SAP auth kavramlarını temsil eden model **`SapAuthRole`** olarak adlandırılacak — `Role` adı platform RBAC'a aittir | Ad çakışması → RBAC middleware'ı yanlış modeli kullanır; `SapAuthRole` prefix'i kesinlikle hataları önler |
| **D3** | SOD (Segregation of Duties) Matrix: production'da PostgreSQL partial index, test ortamında mock/SQLite-safe alternatif | SQLite `CREATE INDEX … WHERE` sözdizimini desteklemez; test suite'ini kırmamak için isolation gerekli |
| **D4** | S7-02'ye kadar SapAuthRole modeli üzerinde herhangi bir breaking API değişikliği yapılmayacak | Sprint 9'da frontend entegrasyonu planlanıyor; erken kırma migration maliyetini artırır |

**Seçilen Yol:** Option A — Tam katman ayrımı, platform RBAC dokunulmadan kalır.

---

## 2. Bağlam

SAP projelerinde iki tür "rol" kavramı mevcuttur:

| Kavram | Açıklama | Platform Temsili |
|--------|----------|-----------------|
| **Platform Rolü** | Sistemin erişim kontrolü; `require_permission` dekoratörüyle uygulanır | `app/models/user.py::Role`, `permission_service.py` |
| **SAP Auth Konsepts Rolü** | SAP sistemindeki t-code / authorization object kümeleri; proje bazlı tasarlanır | `SapAuthRole` (FDD-I02 §3) |

Önceki bir tasarım taslağında her ikisi için `Role` adı önerilmişti. Aynı ismin kullanılması:
- `permission_service.has_permission()` yanlış tabloyu sorgulayabilirdi
- Migration sırasında `roles` tablosuna yanlış data gidebilirdi
- Model import'larında ambiguity yaratırdı

---

## 3. Seçenekler

### Option A — Tam Ayrım ✅ SEÇİLDİ

```
platform/
  app/models/user.py::Role              → platform RBAC
  app/services/permission_service.py    → has_permission(), require_permission()

sap_auth/
  app/models/sap_auth.py::SapAuthRole   → SAP yetkilendirme konsepti
  app/models/sap_auth.py::SapAuthObject → authorization object (e.g. F_KNA1_BUK)
  app/models/sap_auth.py::SodMatrix     → çakışan rol çiftleri
  app/services/sap_auth_service.py      → CRUD + risk analizi
```

**Avantajlar:**
- Platform RBAC'a sıfır dokunuş — mevcut 45 blueprint'te hiçbir değişiklik gerekmez
- SAP auth modeli bağımsız olarak gelişebilir (PFCG benzeri interface, S7-02)
- Test edilebilirlik: sap_auth_service saf Python, Flask `g` gerektirmez

**Dezavantajlar:**
- İki ayrı permission sistemi — dokümantasyon ve onboard maliyeti

### Option B — Birleşik Role Tablosu

`type` kolonu ile ayırt: `role_type = "platform" | "sap_auth"`

**Neden Reddedildi:** `permission_service.py` tüm Role satırlarını okur; `type` filtresi yoksa SAP auth rolleri middleware'a sızar. Güvenlik açığı oluşturur.

---

## 4. Teknik Kararlar

### 4.1 Model İsimlendirmesi

```python
# app/models/sap_auth.py

class SapAuthRole(db.Model):
    """
    SAP authorization concept role — NOT a platform RBAC role.

    Represents a composite role (Sammelrolle) or single role (Einzelrolle)
    in the SAP authorization concept. Used for SoD analysis and
    authorization documentation during SAP go-live projects.

    Platform RBAC is managed separately in app/models/user.py::Role.
    """
    __tablename__ = "sap_auth_roles"
    ...

class SapAuthObject(db.Model):
    """Authorization object within a SapAuthRole (PFCG level)."""
    __tablename__ = "sap_auth_objects"
    ...

class SodMatrix(db.Model):
    """
    Segregation of Duties — conflicting role-pair registry.

    Risk levels: critical | high | medium | low
    Each row = (role_a, role_b, risk_level, control_measure)
    """
    __tablename__ = "sod_matrix"
    ...
```

### 4.2 SOD Matrix — PostgreSQL vs SQLite

SOD matrix'te "aynı kullanıcıda çakışan iki rol" sorgusunu hızlandırmak için PostgreSQL partial index mantıklıdır:

```sql
-- PostgreSQL: sadece yüksek riskli çiftleri indexle
CREATE INDEX ix_sod_high_risk ON sod_matrix (role_a_id, role_b_id)
WHERE risk_level IN ('critical', 'high');
```

**Sorun:** SQLite `WHERE` clause'lu partial index'i desteklemez.

**Çözüm:** Model seviyesinde koşullu index:

```python
# app/models/sap_auth.py
import os

# Sadece PostgreSQL ortamında partial index oluştur
_table_args = [
    db.Index("ix_sod_matrix_role_pair", "role_a_id", "role_b_id"),
]
if "postgres" in os.getenv("DATABASE_URL", ""):
    _table_args.append(
        db.Index(
            "ix_sod_high_risk",
            "role_a_id", "role_b_id",
            postgresql_where=db.text("risk_level IN ('critical', 'high')"),
        )
    )

class SodMatrix(db.Model):
    __tablename__ = "sod_matrix"
    __table_args__ = tuple(_table_args)
```

Test ortamında (`DATABASE_URL=''` veya `sqlite://`) partial index oluşturulmaz; temel `ix_sod_matrix_role_pair` index her iki ortamda çalışır.

### 4.3 Extension Points (S7-02 için rezerve)

Aşağıdaki alanlar S5-01'de **schema'ya eklenmeyecek**, S7-02'de eklenecek:

```python
# S7-02'de eklenecek (breaking migration riski — Sprint 9'dan önce eklenmemeli)
pfcg_export_xml = db.Column(db.Text, nullable=True)   # PFCG download entegrasyonu
btp_iam_mapping = db.Column(db.JSON, nullable=True)   # SAP BTP IAM senkronizasyonu
```

**Neden Şimdi Eklenmedi:** Sprint 9'daki frontend entegrasyonu bu alanların formatını belirleyecek. Erken ekleme, migration cleanup maliyeti yaratır ve alan semantiğini kilitlemiş olur.

---

## 5. Tenant Isolation

`SapAuthRole`, `SapAuthObject`, `SodMatrix` modelleri `tenant_id = nullable=False` ile tanımlanacak. Her sorgu `tenant_id` filtresi içerecek.

```python
# DOĞRU
roles = SapAuthRole.query.filter_by(
    tenant_id=tenant_id,
    project_id=project_id
).all()

# YANLIŞ — tenant sızıntısı
roles = SapAuthRole.query.filter_by(project_id=project_id).all()
```

---

## 6. Test Stratejisi

SOD matrix sorguları SQLite'ta:
- `ix_sod_high_risk` partial index oluşturulmaz → query hâlâ doğru sonucu verir (sadece full scan)
- Performans testleri PostgreSQL ortamında çalıştırılır
- `@pytest.mark.integration` ile işaretlenir

```python
@pytest.mark.unit
def test_sod_matrix_detects_conflicting_roles(session):
    """SQLite-safe: no partial index needed to test correctness."""
    ...
```

---

## 7. Etkilenen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `app/models/sap_auth.py` | **YENİ** — SapAuthRole, SapAuthObject, SodMatrix |
| `app/services/sap_auth_service.py` | **YENİ** — CRUD + risk analizi |
| `app/blueprints/sap_auth_bp.py` | **YENİ** — REST API |
| `app/__init__.py` | blueprint register — S7-02'de |
| `migrations/versions/...` | Alembic migration — S7-02'de |

> **Not:** S5-01 yalnızca bu ADR'ı üretir. Model ve servis dosyaları S7-02'de yazılacak.

---

## 8. Kararın Onay Tarihi ve İzlenecek Kontroller

- [x] ADR oluşturuldu ve SPRINT-PLAN'a referans eklendi
- [ ] `SapAuthRole` model implementasyonu — S7-02
- [ ] SOD matrix PostgreSQL migration — S7-02
- [ ] BTP IAM mapping extension point — Sprint 9 sonrası
