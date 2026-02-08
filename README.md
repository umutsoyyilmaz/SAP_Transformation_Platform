# SAP Transformation Management Platform

**Repository:** `SAP_TRANSFORMATION_PLATFORM`

---

## Purpose

Transform the **ProjektCoPilot** prototype into a modular, enterprise-grade
SAP Transformation Management Platform.

This platform will provide structured project management capabilities for
SAP S/4HANA transformation programs — including module tracking, milestone
governance, risk management, and AI-assisted decision support.

---

## Governance

This project follows a **governance-first** execution model:

- All work is driven by **Notion-managed sprints and tasks**.
- The authoritative execution roadmap is defined in
  [`MASTER_PLAN.md`](MASTER_PLAN.md).
- Every change maps to a specific **Release → Sprint → Task** in the plan.
- No files, dependencies, or patterns are introduced outside of task scope.

---

## Architecture

The platform architecture is defined in
`sap_transformation_platform_architecture.md` and serves as the single
source of truth for module boundaries, tech stack decisions, and directory
structure.

---

## Tech Stack (Foundation)

| Layer       | Technology       | Version  |
|-------------|------------------|----------|
| Language    | Python           | 3.13     |
| Web Framework | Flask          | 3.1.0    |
| ORM         | SQLAlchemy       | 2.0.36   |
| Migration   | Flask-Migrate    | 4.0.7    |
| DB (dev)    | SQLite           | —        |
| DB (prod)   | PostgreSQL 16    | pgvector |
| Frontend    | Vanilla JS SPA   | —        |
| CSS         | SAP Fiori Horizon| Custom   |
| Charts      | Chart.js         | 4.4.7    |
| Test        | pytest           | 8.3.4    |

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
make test             # 136 testi çalıştır
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

| Release   | Sprint   | Status        | Tests | Endpoints | Tables |
|-----------|----------|---------------|-------|-----------|--------|
| Release 1 | Sprint 1 | ✅ Tamamlandı | 10    | 5         | 1      |
| Release 1 | Sprint 2 | ✅ Tamamlandı | 36    | 24        | 6      |
| Release 1 | Sprint 3 | ✅ Tamamlandı | 77    | 45        | 12     |
| Release 1 | Sprint 4 | ✅ Tamamlandı | 136   | 73        | 15     |

Detaylı ilerleme raporu: [`PROGRESS_REPORT.md`](PROGRESS_REPORT.md)

---

## License

*To be defined.*
