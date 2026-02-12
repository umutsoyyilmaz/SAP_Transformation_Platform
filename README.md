# SAP Transformation Management Platform

**Repository:** `SAP_TRANSFORMATION_PLATFORM`  
**Commit:** `TS-Sprint 3` | **Tarih:** 10 Şubat 2026

---

## Purpose

Transform the **ProjektCoPilot** prototype into a modular, enterprise-grade
SAP Transformation Management Platform.

This platform provides structured project management capabilities for
SAP S/4HANA transformation programs — including module tracking, milestone
governance, risk management, AI-assisted decision support, and end-to-end
traceability from requirements to test execution.

### Platform at a Glance

| Metric | Value |
|--------|-------|
| DB Tables | 77 |
| API Routes | 336 |
| Pytest Tests | 916 (904 passed + 11 deselected + 1 xfail) |
| Model Classes | 77 |
| Blueprints | 12 |
| Services | 12 |
| AI Assistants | 3 active / 14 planned |
| Alembic Migrations | 11 |
| Commits | 73 |

---

## Modules (12)

| # | Module | Models | Routes | Tests | Status |
|---|--------|:------:|:------:|:-----:|--------|
| 1 | Program Setup | 6 | 25 | 36 | ✅ |
| 2 | Scope & Requirements | 3 | 20 | 45 | ✅ |
| 3 | Backlog Workbench (WRICEF) | 5 | 28 | 59 | ✅ |
| 4 | Test Hub | 17 | 71 | 203 | ✅ |
| 5 | RAID Module | 4 | 30 | 46 | ✅ |
| 6 | Integration Factory | 5 | 26 | 76 | ✅ |
| 7 | Explore Phase Manager | 25 | 66 | 192 | ✅ |
| 8 | AI Infrastructure | 5 | 29 | 141 | ✅ |
| 9 | AI Phase 1 (3 Assistants) | — | — | 72 | ✅ |
| 10 | Traceability Engine v1+v2 | — | 8 | — | ✅ |
| 11 | Notification Service | — | 6 | — | ✅ |
| 12 | Monitoring & Observability | — | 12 | 15 | ✅ |

### AI Assistants (3 Active)

| Assistant | Capability | UI Integration |
|-----------|-----------|----------------|
| NL Query | Text-to-SQL + SAP glossary | Chat UI |
| Requirement Analyst | Fit/Gap classification + similarity search | 🤖 AI Analyze button |
| Defect Triage | Severity + module routing + duplicate detection | 🤖 AI Triage button |

---

## Governance

This project follows a **governance-first** execution model:

- All work is driven by **sprint-tracked tasks**.
- The authoritative execution roadmap is defined in
  [`SAP_Platform_Project_Plan_v2.md`](docs/plans/SAP_Platform_Project_Plan_v2.md).
- Every change maps to a specific **Release → Sprint → Task** in the plan.
- No files, dependencies, or patterns are introduced outside of task scope.

---

## Architecture

The platform architecture is defined in
[`sap_transformation_platform_architecture_v2.md`](docs/specs/sap_transformation_platform_architecture_v2.md)
and serves as the single source of truth for module boundaries, tech stack
decisions, and directory structure.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.13 |
| Web Framework | Flask | 3.1.0 |
| ORM | SQLAlchemy | 2.0.36 |
| Migration | Flask-Migrate (Alembic) | 4.0.7 |
| DB (dev) | SQLite | — |
| DB (prod) | PostgreSQL 16 | pgvector |
| AI LLM | Anthropic / OpenAI / Gemini / LocalStub | Multi-provider |
| AI Search | RAG (cosine + BM25 + RRF hybrid) | pgvector |
| Frontend | Vanilla JS SPA (→ Vue 3 planned) | — |
| CSS | SAP Fiori Horizon | Custom tokens |
| Charts | Chart.js | 4.4.7 |
| Test | pytest | 8.3.4 |

---

## Offline Yerel Test Ortamı (Hızlı Başlangıç)

Projede `Makefile` ile tek komutla kurulum, seed data yükleme ve çalıştırma yapılabilir.
İnternet bağlantısı gerekmez (bağımlılıklar kurulduktan sonra).

### İlk Kurulum (tek sefer)

```bash
# 1. Repoyu klonlayın
git clone https://github.com/umutsoyyilmaz/SAP_Transformation_Platform.git
cd SAP_Transformation_Platform

# 2. Tam kurulum: venv + bağımlılıklar + DB migration + demo veri
make setup

# 3. Uygulamayı başlatın
make run
# → http://localhost:5001 adresinde açılır
```

### Günlük Kullanım

```bash
make run              # Uygulamayı başlat (http://localhost:5001)
make test             # 916 testi çalıştır
make status           # Proje durumu + DB kayıt sayıları
make seed             # Demo veriyi yeniden yükle (mevcut veriyi temizler)
make seed-verbose     # Demo veri yükle (detaylı çıktı)
```

### Sprint Sonrası Deploy

Her sprint sonunda yeni kodu alıp deploy etmek için:

```bash
git pull                # Yeni kodu çek
make deploy             # migrate → seed → test → hazır!
make run                # Uygulamayı başlat
```

### Sıfırlama

```bash
make reset              # DB sil → yeniden oluştur → seed data yükle
make clean              # DB + cache dosyalarını temizle
```

### Demo Veri İçeriği (140 kayıt)

Seed script gerçekçi bir Türk otomotiv şirketi SAP dönüşüm projesi oluşturur:

| Veri | Adet | Açıklama |
|------|------|----------|
| Program | 1 | Türk Otomotiv A.Ş. — S/4HANA Greenfield Dönüşüm |
| Phases | 6 | SAP Activate: Discover → Prepare → Explore → Realize → Deploy → Run |
| Gates | 7 | Quality gates + Go/No-Go decision gate |
| Workstreams | 12 | FI/CO, MM, SD, PP, QM, PM, HCM, Basis, BTP, Migration, Test, Change Mgmt |
| Team Members | 10 | Program Manager, Solution Architect, Consultants, Developers |
| Committees | 4 | SteerCo, PMO, CAB, ARB |
| Scenarios | 5 | Greenfield vs Brownfield, Big-Bang vs Phased, Selective Data |
| Requirements | 20 | Business, Functional, Technical, Non-functional, Integration |
| Traces | 12 | Requirements → Phases, Workstreams, Scenarios |
| Sprints | 3 | Sprint 1-3 (completed, completed, active) |
| Backlog Items | 25 | WRICEF: 4W, 5R, 5I, 4C, 4E, 3F — çeşitli statuslerde |
| Config Items | 10 | IMG konfigürasyon (FI, MM, SD, PP, Basis) |
| Functional Specs | 8 | Onaylı ve taslak FS dokümanları |
| Technical Specs | 5 | TS dokümanları (ABAP, BTP, Migration) |
| **Toplam** | **140** | Tam izlenebilirlik zinciri: Scenario → Req → WRICEF/Config → FS → TS |

---

## Current Status

| Release | Sprint | Status | Tests | Endpoints | Tables |
|---------|--------|--------|------:|----------:|-------:|
| Release 1 | Sprint 1-4 | ✅ Tamamlandı | 252 | 118 | 30 |
| Release 2 | Sprint 5-8 | ✅ Tamamlandı | 393 | 175 | 39 |
| Release 3 | Sprint 9 | ✅ Tamamlandı | 603 | 242 | 45 |
| — | Explore Phase | ✅ Tamamlandı | 766 | 295 | 65 |
| — | TS-Sprint 1-3 | ✅ Tamamlandı | 916 | 336 | 77 |
| — | Code Review & Hardening | ✅ 28/67 bulgu düzeltildi | — | — | — |
| — | Monitoring | ✅ Health + Metrics | — | — | — |

Detaylı ilerleme raporu: [`PROGRESS_REPORT.md`](docs/plans/PROGRESS_REPORT.md)  
Teknik borç: [`TECHNICAL_DEBT.md`](docs/plans/TECHNICAL_DEBT.md)  
Değişiklik geçmişi: [`CHANGELOG.md`](docs/plans/CHANGELOG.md)

---

## Documentation

| Directory | Contents |
|-----------|----------|
| `docs/specs/` | Functional & technical specifications |
| `docs/reviews/` | Review findings and audit reports |
| `docs/plans/` | Project plans, changelog, task lists |
| `docs/archive/` | Superseded documents |
| `User Guide/` | End-user documentation (EN + TR) |

---

## License

*To be defined.*
