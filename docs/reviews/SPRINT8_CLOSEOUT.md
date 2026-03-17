# Sprint 8 Closeout

Sprint 8 covers the primary user-facing platform surfaces that still used native browser dialogs or inconsistent modal patterns.

## Closed Scope

- Workspace: `Dashboard`, `Executive Cockpit`
- Discover / Explore cockpit surfaces
- Governance: `RAID`, `Reports`, `Reports AI`
- Program / Project Setup launchpad flows
- Backlog / Test Planning / Test Plan Detail / Execution Center
- Cutover / Integration
- Evidence capture and approvals touchpoints

## Critical Regression Commands

Native dialog audit:

```bash
make ui-dialog-audit
```

Contract checks:

```bash
make ui-contract-critical
```

Browser smoke:

```bash
make ui-smoke-critical
```

Combined:

```bash
make ui-regression-critical
```

## What The Closeout Guarantees

- Core platform views use modal-driven confirmation and prompt flows instead of native `confirm()` / `prompt()`.
- A repo-wide native dialog audit blocks new browser-dialog regressions on core user surfaces.
- Critical user journeys have contract tests and Playwright smoke coverage.
- The smoke pack spans workspace, explore, governance, project setup, launchpad, cutover/integration, and test management.

## Manual test checklist

- Programs
  Create a program, open it, then open `Project Setup` from the project launchpad.
- Project Setup
  Create/edit phases, workstreams, committees, and team members; verify delete flows use modal confirmation.
- Scope & Hierarchy
  Seed or import hierarchy in `Project Setup`, then open `Explore > Scope & Process` and verify baseline is visible but structural mutation is not offered.
- Workshop Hub
  Create a workshop, start it, review KPI/readiness numbers, and open a workshop detail page.
- Workshop Detail
  Add a decision, open item, and requirement; verify outcome summary and KPI counts refresh correctly.
- Outcomes / Traceability
  Check requirement/open item handoff, then confirm traceability views still resolve under the active project.
- Governance
  Run `Reports`, `RAID`, and `AI Steering Pack`; verify modal flows and delete confirmations.
- Delivery / Testing
  Validate delete or destructive actions in `Backlog`, `Cutover`, `Integration`, and `Execution Center` use modal dialogs instead of browser-native prompts.

## Residual exclusions

These areas are intentionally outside Sprint 8 closeout and should be treated as separate cleanup work:

- Admin-only templates under `templates/platform_admin`, `templates/sso_admin`, `templates/roles_admin`
- Niche utility editors and specialty modules not in the core user regression pack
- Browser install prompt handling in `static/js/pwa.js`

Those residuals are not blockers for core platform testing.
