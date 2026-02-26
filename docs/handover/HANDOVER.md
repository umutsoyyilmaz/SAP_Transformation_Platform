# Handover Guide — SAP Transformation Platform

Bu rehber, projeye yeni katilan gelistiriciler, AI agent'lar ve IDE'ler icin
tek giris noktasidir. Amaci: 1-2 saat icinde proje hakkinda yeterli bilgiyi
aktarmak ve uretken calismayi mumkun kilmaktir.

---

## Proje Ozeti

SAP donusum projelerini yoneten, cok kiracili (multi-tenant) Flask tabanli SaaS platform.

| Ozellik | Deger |
|---------|-------|
| Dil / Framework | Python 3.11+ / Flask 3.1 |
| ORM | SQLAlchemy 2.0 (PostgreSQL prod, SQLite test) |
| Frontend | Vanilla JS SPA, IIFE modulleri, `pg_*` component system |
| Auth | JWT + API Key, DB-backed RBAC |
| AI | LLM Gateway (Claude, GPT, Gemini), 13 AI assistant |
| Test | pytest (3300+ test), Playwright E2E |
| CI/CD | GitHub Actions, Ruff lint, mypy type check |

---

## Okuma Sirasi (Oncelik Sirasina Gore)

### Seviye 1 — Kod Yazabilmek Icin (30 dk)

| # | Dosya | Ne Ogretir |
|---|-------|------------|
| 1 | [CLAUDE.md](../../CLAUDE.md) | Mutlak kurallar, katman mimarisi, guvenlik |
| 2 | [Bu dosya](HANDOVER.md) | Genel bakis, yonlendirme |
| 3 | [ARCHITECTURE.md](ARCHITECTURE.md) | Katman mimarisi, request akisi, tenant izolasyonu |
| 4 | [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md) | Gelistirme ortami, yeni feature ekleme kontrol listesi |

### Seviye 2 — Mimariyi Anlamak Icin (1 saat)

| # | Dosya | Ne Ogretir |
|---|-------|------------|
| 5 | [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) | SPA routing, component system, CSS token'lar |
| 6 | [AI_PIPELINE.md](AI_PIPELINE.md) | LLM gateway, AI assistant'lar, agent gelistirme sureci |
| 7 | [.github/copilot-instructions.md](../../.github/copilot-instructions.md) | Detayli coding standartlari (1035 satir) |
| 8 | [docs/plans/CODING_STANDARDS.md](../plans/CODING_STANDARDS.md) | Proje-ozel standartlar, tier-based enforcement |

### Seviye 3 — Domain Bilgisi (Gerektiginde)

| Konu | Dosya |
|------|-------|
| Sistem mimarisi (detayli) | [docs/specs/sap_transformation_platform_architecture_v2.md](../specs/sap_transformation_platform_architecture_v2.md) |
| Feature tasarimlari (FDD) | [docs/fdd/](../fdd/) — 20 FDD dosyasi |
| Mimari kararlar (ADR) | [docs/plans/ADR-001.md](../plans/ADR-001.md) ... ADR-008 |
| Sprint planlama | [docs/fdd/SPRINT-PLAN-dependency-ordered.md](../fdd/SPRINT-PLAN-dependency-ordered.md) |
| Proje yol haritasi | [docs/plans/SAP_Platform_Project_Plan_v2.5.md](../plans/SAP_Platform_Project_Plan_v2.5.md) |
| Bilinen sorunlar | [docs/reviews/project/consolidated-review-report.md](../reviews/project/consolidated-review-report.md) |
| Teknik borc | [docs/plans/TECHNICAL_DEBT.md](../plans/TECHNICAL_DEBT.md) |

---

## Dizin Yapisi

```
SAP_Transformation_Platform/
|-- app/                         # Uygulama kodu
|   |-- ai/                      #   LLM gateway + 13 assistant
|   |-- blueprints/              #   HTTP endpoint'ler (50+ blueprint)
|   |-- integrations/            #   SAP Cloud ALM, dis servisler
|   |-- middleware/               #   JWT, tenant context, timing
|   |-- models/                  #   SQLAlchemy ORM modelleri
|   |-- services/                #   Is mantigi (commit sahibi)
|   +-- utils/                   #   Yardimci fonksiyonlar
|-- static/                      # Frontend
|   |-- css/                     #   pg-*.css component stilleri
|   |-- js/                      #   SPA router, API client
|   |   |-- components/          #   pg_*.js reusable bilesenler
|   |   +-- views/               #   44+ view modulu
|   +-- vendor/                  #   Chart.js, Frappe-Gantt
|-- templates/                   # Flask Jinja2 sablonlari
|-- tests/                       # pytest (104 test dosyasi, 3300+ test)
|-- migrations/versions/         # Alembic DB migration'lar (50+)
|-- scripts/                     # Seed data, migration, CI yardimcilari
|-- docs/                        # Dokumantasyon (125+ .md dosyasi)
|   |-- fdd/                     #   Feature Design Documents
|   |-- plans/                   #   ADR'ler, standartlar, yol haritasi
|   |-- specs/                   #   Teknik spesifikasyonlar
|   |-- reviews/                 #   Code/project review raporlari
|   +-- handover/                #   BU KLASOR — handover rehberleri
|-- .instructions/.prompts/      # AI agent rol tanimlari (6 agent)
+-- e2e/                         # Playwright E2E testleri
```

---

## Kritik Kurallar (Kisa Ozet)

Tam kurallar CLAUDE.md'de. Burada sadece en onemli 5 kural:

1. **Blueprint'te ORM yok** — `.query.`, `.filter(`, `db.session.execute(` yasak
2. **Service commit'ler** — `db.session.commit()` sadece `app/services/` icinde
3. **Tenant filtresi zorunlu** — `TenantModel` kullanan her sorguda `query_for_tenant(tenant_id)`
4. **Permission decorator zorunlu** — her route'ta `@require_permission("domain.verb")`
5. **AI sadece gateway uzerinden** — `from app.ai.gateway import LLMGateway`

---

## Katkida Bulunma Sureci

```
1. Feature Design  -->  2. Implementation  -->  3. Test  -->  4. Review  -->  5. Merge
   (FDD + ADR)           (Blueprint/Service/     (pytest +     (Code review     (PR)
                          Model + Frontend)       E2E)          + audit)
```

Detayli surec: [.instructions/.prompts/orchestration-guide-v3.md](../../.instructions/.prompts/orchestration-guide-v3.md)

---

## Dokumantasyon Otorite Hiyerarsisi

```
CLAUDE.md (en yuksek otorite — AI agent'lar bunu zorunlu okur)
  |
  +-- .github/copilot-instructions.md (senior engineer standartlari)
        |
        +-- docs/plans/CODING_STANDARDS.md (proje standartlari)
              |
              +-- .instructions/.prompts/* (agent-ozel kurallar)
                    |
                    +-- docs/fdd/* (feature-ozel kurallar)
```

Catisma durumunda ust seviye kazanir.
