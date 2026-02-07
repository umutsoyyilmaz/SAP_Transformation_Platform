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

| Layer       | Technology       |
|-------------|------------------|
| Language    | Python 3.11      |
| Web Framework | Flask          |
| ORM         | SQLAlchemy       |

> Additional components (PostgreSQL, Redis, pgvector, AI SDKs) will be
> introduced in later sprints per `MASTER_PLAN.md`.

---

## Quick Start (Sprint 1)

> **Note:** Docker-based setup is out of scope for Sprint 1.
> Use a local Python virtual environment.

```bash
# 1. Clone the repository
git clone https://github.com/<org>/SAP_TRANSFORMATION_PLATFORM.git
cd SAP_TRANSFORMATION_PLATFORM

# 2. Create and activate a virtual environment (Python 3.11)
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run placeholder (no application code in Sprint 1)
# Flask application entry point will be added in Sprint 2.
# For now, verify the environment:
python -c "import flask; import sqlalchemy; print('Environment ready.')"
```

---

## Current Status

| Release   | Sprint   | Status      |
|-----------|----------|-------------|
| Release 1 | Sprint 1 | **Active** |

See [`MASTER_PLAN.md`](MASTER_PLAN.md) for the full release and sprint
breakdown.

---

## License

*To be defined.*
