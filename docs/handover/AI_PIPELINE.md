# AI Pipeline & Gateway

## LLM Gateway

**Dosya:** `app/ai/gateway.py`

Tum AI cagrilari bu gateway uzerinden yapilir. Dogrudan `import anthropic` veya
`import openai` YASAKTIR.

### Desteklenen Provider'lar
| Provider | Modeller | Kullanim |
|----------|---------|----------|
| Anthropic | Claude 3.5 Haiku, Claude 3.5 Sonnet, Claude Opus | Varsayilan |
| OpenAI | GPT-4o, GPT-4o-mini | Fallback |
| Google | Gemini 1.5 Pro, Gemini 1.5 Flash | Alternatif |
| Local Stub | — | Dev/test (API key gerektirmez) |

### Temel Kullanim
```python
from app.ai.gateway import LLMGateway

gw = LLMGateway()
result = gw.chat(
    messages=[{"role": "user", "content": "Analiz yap"}],
    model="claude-3-5-haiku-20241022",
    purpose="classification",      # Cache + routing icin
    user="test_user",
    program_id=1,
)

# Donus:
# {
#     "content": "...",
#     "prompt_tokens": 150,
#     "completion_tokens": 80,
#     "model": "claude-3-5-haiku-20241022",
#     "cost_usd": 0.0003,
#     "latency_ms": 450,
#     "provider": "anthropic",
#     "cache_hit": False,
#     "fallback_provider": None,
# }
```

### Cache Sistemi (2 Katman)
1. **Memory cache:** Ayni prompt+model -> aninda donus (0 latency, 0 maliyet)
2. **DB cache:** `AIResponseCache` tablosu (purpose bazli)
3. `cache.should_cache(purpose)` -> cache'lenebilir mi kontrol

### Smart Model Selector
Purpose'a gore otomatik tier routing:
- **Triage/classification:** Haiku (hizli, ucuz)
- **Analysis/summarization:** Sonnet (dengeli)
- **Reasoning/planning:** Opus (en yetenekli)

### Retry ve Fallback
- Max 3 deneme, exponential backoff: 1s -> 2s -> 4s
- Birincil basarisiz -> fallback chain dene
- Tumu basarisiz -> `RuntimeError` firlatir

### Loglama
- `AIUsageLog`: token, maliyet, latency, basari/hata
- `AIAuditLog`: prompt hash, yanit ozeti, fallback kullanildi mi
- Her ikisi de `db.session.flush()` ile kaydedilir (caller transaction'i bozmaz)

### Local Stub (Test/Dev)
API key yoksa otomatik aktif. User mesajina gore deterministik yanit:
- "classify" -> fit/gap analiz stub
- "defect" -> severity classification stub

---

## AI Assistant'lar

**Dizin:** `app/ai/assistants/`

| Assistant | Dosya | Islem |
|-----------|-------|-------|
| NL Query | `nl_query.py` | Dogal dil -> SQL/filtre cevirisi |
| Smart Search | `smart_search.py` | Semantic arama + oneri |
| Suite Optimizer | `suite_optimizer.py` | Test suite optimizasyonu |
| TC Maintenance | `tc_maintenance.py` | Test case bakim onerileri |
| Coverage Analyzer | `coverage.py` | Test coverage analizi |
| Classification | `classification.py` | Requirement/defect siniflandirma |
| Impact Analyzer | `impact.py` | Degisiklik etki analizi |
| Fit/Gap Analyzer | `fit_gap.py` | SAP fit-to-standard analizi |
| Anomaly Detector | `anomaly.py` | Data anomali tespiti |
| Report Generator | `report_gen.py` | Otomatik rapor olusturma |
| Minutes Generator | `minutes.py` | Toplanti notlari olusturma |
| BDD Generator | `bdd_gen.py` | Gherkin senaryo uretimi |
| Migration Planner | `migration.py` | Veri migration planlamasi |

### Assistant Olusturma Pattern'i
```python
# app/ai/assistants/<domain>.py
from app.ai.gateway import LLMGateway

def analyze_coverage(tenant_id: int, program_id: int, data: dict) -> dict:
    """
    Analyze test coverage gaps.

    Args:
        tenant_id: Tenant scope.
        program_id: Program scope.
        data: Test case and execution data.

    Returns:
        Analysis result with recommendations.
    """
    gw = LLMGateway()

    system_prompt = """Sen bir SAP test uzmanissin.
    Verilen test coverage verisini analiz et ve boşlukları belirle."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Coverage data: {data}"},
    ]

    result = gw.chat(
        messages=messages,
        model="claude-3-5-haiku-20241022",
        purpose="coverage_analysis",
        program_id=program_id,
    )

    return {
        "analysis": result["content"],
        "tokens_used": result["prompt_tokens"] + result["completion_tokens"],
        "cost_usd": result["cost_usd"],
    }
```

---

## AI Agent Gelistirme Sureci

**Dizin:** `.instructions/.prompts/`

Proje 6 agent'li bir gelistirme pipeline'i kullanir:

### Pipeline Fazlari

```
Faz 1: TASARIM
  Architect Agent  ->  FDD (Feature Design Document) olusturur
  UX Agent         ->  UXD (wireframe) olusturur
  UI Agent         ->  UID (visual mockup) olusturur

Faz 2: TEST PLANLAMA
  QA Agent         ->  TPD (Test Plan Document) olusturur

Faz 3: IMPLEMENTASYON
  Coder Agent      ->  Kod yazar (CLAUDE.md kurallarini uygular)

Faz 4: REVIEW
  Reviewer Agent   ->  Kod denetimi yapar, bulgu raporlar
```

### Agent Rol Dosyalari

| Dosya | Rol | Satir |
|-------|-----|-------|
| `.instructions/.prompts/architect.md` | Feature tasarimi, FDD uretimi | 237 |
| `.instructions/.prompts/ux-agent.md` | UX wireframe, kullanici akisi | 317 |
| `.instructions/.prompts/ui-agent.md` | Visual tasarim, component spec | 406 |
| `.instructions/.prompts/qa-agent.md` | Test plani, TPD uretimi | 369 |
| `.instructions/.prompts/coder.md` | Kod implementasyonu | 654 |
| `.instructions/.prompts/reviewer.md` | Code review, audit | 317 |
| `.instructions/.prompts/orchestration-guide-v3.md` | Pipeline yonetim rehberi | 747 |

### Ek Pipeline'lar (Audit)

Orchestration guide 4 ek audit pipeline tanimlar:
1. **Code Review Pipeline** — mevcut kodu gozden gecir
2. **Quick Fix Pipeline** — hizli hata duzeltme
3. **Blueprint Completion Pipeline** — eksik endpoint'leri tamamla
4. **Module Creation Pipeline** — sifirdan modul olustur

### Kural
- Yeni feature'lar TUM fazlardan gecmeli (hotfix haric)
- Her agent ayri bir session'dir
- Pipeline sirasi kesindir (faz atlanamaz)

---

## Token Butcesi ve Maliyet

### Per-Program Limitler
- Gateway uzerinden per-program token butcesi zorunlu kilinabilir
- `AIUsageLog` ile kullanim takip edilir
- Asim durumunda gateway hata doner

### Maliyet Hesaplama
```python
# app/ai/gateway.py -> calculate_cost()
# Her provider/model icin fiyatlandirma app/models/ai.py'de tanimli
cost = calculate_cost(model="claude-3-5-haiku", input_tokens=1000, output_tokens=500)
```

---

## SAP Cloud ALM Entegrasyonu

**Dosya:** `app/integrations/alm_gateway.py`

### Tum dis HTTP cagrilari bu gateway uzerinden yapilir

```python
from app.integrations.alm_gateway import ALMGateway

gw = ALMGateway(tenant_id=1)
result = gw.get("/api/calm/v1/requirements")

# GatewayResult donusu:
# result.ok          -> bool
# result.status_code -> int
# result.data        -> dict
# result.error       -> str (basarisiz ise)
# result.duration_ms -> float
```

### Guvenlik Mekanizmalari
- OAuth2 client credentials (token cache + auto-refresh)
- Timeout: 30 saniye
- Retry: max 2 deneme, exponential backoff
- Circuit breaker: 60s'de 5+ hata -> 30s pause (per tenant)
- Sync logu: `CloudALMSyncLog` tablosu
