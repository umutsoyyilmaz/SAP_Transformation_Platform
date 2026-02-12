# SAP Transformation Management Platform

**Repository:** `SAP_TRANSFORMATION_PLATFORM`  
**Version:** 1.0 | **Date:** February 2026

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
| DB Tables | 103 |
| API Routes | ~450 |
| Pytest Tests | 1 593+ |
| Model Classes | 103 |
| Blueprints | 17 |
| Services | 15+ |
| AI Assistants | 13 |
| Alembic Migrations | 11+ |

---

## Modules (17)

| # | Module | Status |
|---|--------|--------|
| 1 | Program Setup | ✅ |
| 2 | Scope & Requirements | ✅ |
| 3 | Backlog Workbench (WRICEF) | ✅ |
| 4 | Test Hub | ✅ |
| 5 | RAID Module | ✅ |
| 6 | Integration Factory | ✅ |
| 7 | Explore Phase Manager | ✅ |
| 8 | AI Infrastructure | ✅ |
| 9 | AI Assistants (13) | ✅ |
| 10 | Traceability Engine v1+v2 | ✅ |
| 11 | Notification Service | ✅ |
| 12 | Monitoring & Observability | ✅ |
| 13 | Data Factory — ETL / Migration | ✅ |
| 14 | Cutover & Go-Live | ✅ |
| 15 | Governance & Audit | ✅ |
| 16 | Executive Cockpit & Reporting | ✅ |
| 17 | Mobile PWA | ✅ |

### AI Assistants (13)

| Assistant | Capability |
|-----------|-----------|
| NL Query | Text-to-SQL + SAP glossary |
| Requirement Analyst | Fit/Gap classification + similarity search |
| Defect Triage | Severity + module routing + duplicate detection |
| Test Case Generator | Auto-generate test cases from requirements |
| Change Impact | Impact analysis for change requests |
| Risk Assessment | AI-powered risk scoring |
| Sprint Planner | Sprint capacity & story assignment |
| Data Validator | Migration data quality checks |
| Cutover Advisor | Go-live readiness assessment |
| Knowledge Base Q&A | RAG-powered KB queries |
| Code Reviewer | Code quality analysis |
| Integration Mapper | System integration suggestions |
| Performance Analyzer | Performance bottleneck detection |

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

## Quick Start (English)

```bash
# 1. Clone
git clone https://github.com/umutsoyyilmaz/SAP_Transformation_Platform.git
cd SAP_Transformation_Platform

# 2. Full setup: venv + deps + DB migration + demo data
make setup

# 3. Run
make run          # → http://localhost:5001
```

### Daily Usage

```bash
make run              # Start the application (http://localhost:5001)
make test             # Run the full test suite
make status           # Project overview + DB record counts
make seed             # Reload demo data (clears existing)
```

### Docker (Production)

```bash
# Development
docker compose -f docker/docker-compose.yml up -d

# Production (with resource limits, no source mount)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

---

## Hızlı Başlangıç (Türkçe)

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
make test             # 1593+ testi çalıştır
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

| Release | Sprint | Status |
|---------|--------|--------|
| Release 1 | Sprint 1-4 | ✅ Complete |
| Release 2 | Sprint 5-8 | ✅ Complete |
| Release 3 | Sprint 9 | ✅ Complete |
| — | Explore Phase (S10-S14) | ✅ Complete |
| — | TS-Sprint 1-3 (S15-S17) | ✅ Complete |
| — | Code Review & Hardening (S18) | ✅ Complete |
| — | Monitoring (S19) | ✅ Complete |
| — | Data Factory & Cutover (S20) | ✅ Complete |
| — | Governance & Audit (S21) | ✅ Complete |
| — | Executive Cockpit (S22) | ✅ Complete |
| — | Mobile PWA (S23) | ✅ Complete |
| — | Final Polish v1.0 (S24) | ✅ Complete |

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

MIT License — see [LICENSE](LICENSE) for details.
