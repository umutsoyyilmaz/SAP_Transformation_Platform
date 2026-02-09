# Knowledge Base Versioning — Tasarım & Uygulama

**Document ID:** P9-KB-VERSIONING  
**Sprint:** 9.5  
**Date:** 2025-02-09

---

## 1. Problem Tanımı

Mevcut KB ve embedding sistemi aşağıdaki eksikliklere sahipti:

| Eksiklik | Risk |
|----------|------|
| Content hash yok | Embedding'in güncel olup olmadığı tespit edilemiyordu |
| Destructive re-indexing | `index_entity()` tüm eski chunk'ları silip yenilerini ekliyordu — rollback imkansız |
| KB versiyon tanımlayıcısı yok | Embedding setleri "KB v1" vs "KB v2" olarak etiketlenemiyordu |
| Source tracking yok | Hangi model/boyut ile embed edildiği bilinmiyordu |
| Batch/run takibi yok | "42 varlık embed edildi" kaydı tutulmuyordu |
| Staleness tespiti yok | Kaynak değişip embedding'in güncellenmediği tespit edilemiyordu |

---

## 2. Uygulanan Çözüm

### 2.1 Model Değişiklikleri

**AIEmbedding — Yeni kolonlar:**

| Kolon | Tip | Varsayılan | Açıklama |
|-------|-----|-----------|----------|
| `kb_version` | String(30) | "1.0.0" | Bu embedding'i üreten KB versiyonu |
| `content_hash` | String(64) | null | Kaynak metin SHA-256 hash'i |
| `embedding_model` | String(80) | null | Kullanılan model (ör. gemini-embedding-001) |
| `embedding_dim` | Integer | null | Vektör boyutu (ör. 1536, 64) |
| `is_active` | Boolean | true | Soft-delete: yalnız aktif olanlar aranır |
| `source_updated_at` | DateTime(tz) | null | Kaynak entity'nin embed anındaki updated_at'i |

**KBVersion — Yeni model (kb_versions tablosu):**

| Kolon | Tip | Açıklama |
|-------|-----|----------|
| `version` | String(30), UNIQUE | Semantic version (1.0.0, 2.0.0) |
| `description` | Text | Sürüm açıklaması |
| `embedding_model` | String(80) | Bu sürümde kullanılan model |
| `embedding_dim` | Integer | Bu sürümdeki vektör boyutu |
| `total_entities` | Integer | Toplam entity sayısı |
| `total_chunks` | Integer | Toplam chunk sayısı |
| `status` | building / active / archived | Yaşam döngüsü |
| `created_by`, `created_at`, `activated_at`, `archived_at` | — | Audit |

**AISuggestion — Yeni kolon:**
- `kb_version`: Öneri üretilirken kullanılan KB versiyonu

### 2.2 RAG Pipeline Değişiklikleri

**Non-destructive indexing:**
1. Entity chunk'larının tüm metni birleştirilip SHA-256 hash'i hesaplanır
2. Aktif embedding'de aynı hash varsa → **atlama** (skip)
3. Değişiklik varsa → eski embedding'ler `is_active=False` yapılır (silinmez)
4. Yeni chunk'lar `is_active=True`, `kb_version`, `content_hash` ile eklenir

**Arama yalnız aktif embeddings:**
- `search()` artık `AIEmbedding.is_active == True` filtresi uygular

**Staleness tespiti:**
- `find_stale_embeddings()`: `content_hash=NULL` ve `is_active=True` olanları döndürür

**İstatistikler:**
- `get_index_stats()` artık `by_kb_version` ve `archived_chunks` bilgisi de döndürür

### 2.3 Yeni API Endpoint'leri (7 adet)

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/v1/ai/kb/versions` | GET | Tüm KB versiyonlarını listele |
| `/api/v1/ai/kb/versions` | POST | Yeni versiyon oluştur |
| `/api/v1/ai/kb/versions/<id>` | GET | Versiyon detayı + live chunk/entity sayıları |
| `/api/v1/ai/kb/versions/<id>/activate` | PATCH | Versiyonu aktifleştir (öncekini arşivle) |
| `/api/v1/ai/kb/versions/<id>/archive` | PATCH | Versiyonu arşivle |
| `/api/v1/ai/kb/stale` | GET | content_hash'i olmayan (eski) embedding'leri bul |
| `/api/v1/ai/kb/diff/<v1>/<v2>` | GET | İki versiyon arasındaki farkları göster |

### 2.4 Migration

`e7b2c3d4f501_kb_versioning.py` — kb_versions tablosu + AIEmbedding/AISuggestion yeni kolonlar.

---

## 3. Test Kapsamı

27 test (test_kb_versioning.py):

| Kategori | Test Sayısı |
|----------|:-----------:|
| KBVersion model CRUD & lifecycle | 4 |
| AIEmbedding versioning columns | 2 |
| compute_content_hash utility | 3 |
| AISuggestion kb_version | 1 |
| RAG non-destructive indexing | 5 |
| Index stats versioning | 1 |
| KB Version API endpoints | 7 |
| Staleness API | 1 |
| Version diff API | 1 |
| **Toplam** | **27** |    *(2 de mevcut AI testlerinde)* |

---

## 4. Kullanım Senaryoları

### Senaryo 1: İlk KB Oluşturma
```bash
POST /api/v1/ai/kb/versions {"version": "1.0.0", "description": "Initial KB"}
POST /api/v1/ai/embeddings/index {"entity_type": "requirement", "kb_version": "1.0.0"}
PATCH /api/v1/ai/kb/versions/1/activate
```

### Senaryo 2: KB Güncelleme
```bash
POST /api/v1/ai/kb/versions {"version": "1.1.0", "description": "Updated requirements"}
# Re-index changed entities → unchanged ones are automatically skipped
PATCH /api/v1/ai/kb/versions/2/activate  # v1.0.0 otomatik arşivlenir
```

### Senaryo 3: Staleness Kontrolü
```bash
GET /api/v1/ai/kb/stale  → {"stale_entities": [...], "total": 5}
# 5 entity'nin embedding'i content_hash'siz → yeniden indexlenmeli
```

### Senaryo 4: Versiyon Karşılaştırma
```bash
GET /api/v1/ai/kb/diff/1.0.0/1.1.0
→ {"added": [...], "removed": [...], "changed": [...], "unchanged": 42}
```

---

*Migration: `e7b2c3d4f501_kb_versioning.py`*
