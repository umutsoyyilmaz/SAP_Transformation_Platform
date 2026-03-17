# Scripts Index

This directory is organized by operational intent so humans and AI agents can find the right entry point quickly.

## Top-Level Entrypoints

- `manage_tenants.py`: tenant lifecycle CLI kept at the root because it is the main operator entry point and is referenced by Make targets.

## Categories

- `data/seed/`: seed and bootstrap data loaders for demos, SAP knowledge, and quick walkthrough environments.
- `data/migrate/`: schema-adjacent data backfills and migration helpers.
- `db/`: local database inspection, reset, and Alembic drift utilities.
- `audit/`: focused audits for UI contracts, legacy requirement links, and semantic data consistency.
- `testing/`: standalone smoke, regression, performance, and local test runner scripts.
- `infrastructure/`: deployment and asset-maintenance utilities.
- `analysis/`: project metrics and knowledge-base analysis/indexing utilities.

## Selection Guide

- Need demo data or a seeded walkthrough: start in `data/seed/`.
- Need schema hardening, tenant migration, or backfills: start in `data/migrate/`.
- Need DB reset, drift checks, or table counts: start in `db/`.
- Need release-gate or regression helpers: start in `testing/`.
- Need audits for correctness or cleanup work: start in `audit/`.
- Need deploy or static asset maintenance: start in `infrastructure/`.
- Need metrics or embedding/indexing workflows: start in `analysis/`.
