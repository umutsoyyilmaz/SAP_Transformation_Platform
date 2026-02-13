# Requirement Lifecycle

> Canonical reference for the ExploreRequirement state machine, convert rules,
> and button visibility matrix.  
> Source of truth: `app/models/explore.py` → `REQUIREMENT_TRANSITIONS`

---

## Status Flow

```
                          ┌──────────┐
                          │  draft   │◄────────────────────────┐
                          └────┬─────┘                         │
                               │ submit_for_review             │ reactivate
                               ▼                               │
                       ┌──────────────┐                  ┌─────┴────┐
              ┌────────│ under_review  │───────────────►  │ deferred │
              │        └──────┬───────┘   defer          └──────────┘
              │               │                                ▲
         reject               │ approve                        │ defer
              │               ▼                                │
              ▼        ┌──────────────┐                        │
        ┌──────────┐   │   approved   │────────────────────────┘
        │ rejected │   └──────┬───────┘
        └──────────┘          │
                              │ push_to_alm  ← requires convert first!
                              ▼
                       ┌──────────────┐
                       │  in_backlog  │
                       └──────┬───────┘
                              │ mark_realized
                              ▼
                       ┌──────────────┐
                       │   realized   │
                       └──────┬───────┘
                              │ verify
                              ▼
                       ┌──────────────┐
                       │   verified   │  ← terminal state
                       └──────────────┘
```

### Transition Table

| Action              | From             | To            | Pre-condition                         |
|---------------------|------------------|---------------|---------------------------------------|
| `submit_for_review` | draft            | under_review  | —                                     |
| `approve`           | under_review     | approved      | No blocking open items (link_type=blocks) |
| `reject`            | under_review     | rejected      | `rejection_reason` required           |
| `return_to_draft`   | under_review     | draft         | —                                     |
| `defer`             | draft, approved  | deferred      | `deferred_to_phase` required          |
| `push_to_alm`       | approved         | in_backlog    | **Must be converted first** (ADR-1)   |
| `mark_realized`     | in_backlog       | realized      | —                                     |
| `verify`            | realized         | verified      | —                                     |
| `reactivate`        | deferred         | draft         | Clears deferred_to_phase              |

---

## Convert vs. Transition

These are **two separate operations** (ADR-1):

| Operation      | What it does                                        | When allowed               |
|---------------|-----------------------------------------------------|----------------------------|
| **Convert**    | Creates a BacklogItem (WRICEF) or ConfigItem        | status = `approved` or `realized` |
| **Transition** | Changes `status` field (e.g. approved → in_backlog) | Per transition table above  |

### ADR-1: Convert Must Be Explicit

> `push_to_alm` does **NOT** auto-convert. The user must explicitly convert
> first, choosing target type (WRICEF vs Config) and WRICEF sub-type.
> This was previously DEF-004: push_to_alm silently created backlog items.

**Convert flow:**

1. User clicks **⚙ Convert** on an approved requirement
2. Modal opens with:
   - **Target Type**: Auto-detect / WRICEF (Backlog Item) / Configuration Item
   - **WRICEF Type**: Auto-detect / Enhancement / Report / Interface / Conversion / Workflow / Form
   - **Module Override**: SAP module dropdown
3. Backend creates `BacklogItem` or `ConfigItem` and links via `backlog_item_id` / `config_item_id`
4. After conversion, **Move to Backlog** button becomes available

### Auto-detect Logic

When WRICEF type is "Auto-detect", keyword matching runs against title + description:

| WRICEF Type   | Keywords                                              |
|---------------|-------------------------------------------------------|
| report        | report, alv, fiori app, analytics, dashboard          |
| interface     | interface, idoc, bapi, api, rfc, integration          |
| conversion    | conversion, migration, data load, legacy, cutover     |
| enhancement   | enhancement, user exit, badi, bte, custom             |
| form          | form, smartform, sapscript, adobe, print, output      |
| workflow      | workflow, approval, notification, escalation          |

Fallback: `req.type` mapping → `enhancement` as final default.

### Config vs. WRICEF Auto-detect

When target type is "Auto-detect":
- `req.type` in (`configuration`, `workaround`) → **ConfigItem**
- All others → **BacklogItem** (WRICEF)

---

## Button Visibility Matrix

Buttons shown in the requirement detail panel depend on **both** status
and convert state:

| Status        | Converted? | Available Actions                                    |
|---------------|------------|------------------------------------------------------|
| `draft`       | n/a        | Submit for Review · Defer                            |
| `under_review`| n/a        | Approve · Reject                                     |
| `approved`    | **No**     | ⚙ Convert First · Defer                             |
| `approved`    | **Yes**    | Move to Backlog · 🔗 Push to ALM · Defer            |
| `in_backlog`  | Yes        | Realize · 🔗 Push to ALM                            |
| `in_backlog`  | No (edge)  | Realize · ⚙ Convert                                 |
| `realized`    | —          | Verify                                               |
| `verified`    | —          | _(terminal — no actions)_                            |
| `deferred`    | —          | _(reactivate via admin)_                             |
| `rejected`    | —          | _(terminal — no actions)_                            |

### Batch Convert

Shown in the KPI strip when there are approved, unconverted requirements:
- Button: **⚙ Batch Convert (N)**
- Uses auto-detect for all items (no manual WRICEF selection)
- Partial success: shows count of converted + errors

---

## Side Effects by Action

| Action            | Side Effects                                              |
|-------------------|-----------------------------------------------------------|
| `approve`         | Sets `approved_by_id`, `approved_by_name`, `approved_at`  |
| `reject`          | Sets `rejection_reason`                                   |
| `defer`           | Sets `deferred_to_phase`                                  |
| `reactivate`      | Clears `deferred_to_phase`, `rejection_reason`            |
| `push_to_alm`     | Sets `alm_sync_status = "pending"`. Requires convert.     |
| Convert (separate) | Creates BacklogItem/ConfigItem, sets FK on requirement    |

---

## API Endpoints

| Method | Path                                        | Purpose               |
|--------|---------------------------------------------|------------------------|
| POST   | `/api/v1/explore/requirements/{id}/transition` | Status transition    |
| POST   | `/api/v1/explore/requirements/{id}/convert`    | Convert to WRICEF/CFG |
| POST   | `/api/v1/explore/requirements/batch-transition` | Batch transitions   |
| POST   | `/api/v1/explore/requirements/batch-convert`   | Batch auto-convert   |

### Transition Payload
```json
{
  "action": "approve",
  "user_id": "user-1",
  "approved_by_name": "Jane Doe",
  "rejection_reason": "...",
  "deferred_to_phase": "Phase 2"
}
```

### Convert Payload
```json
{
  "project_id": 1,
  "target_type": "backlog",
  "wricef_type": "interface",
  "module": "SD"
}
```

---

## Permission Mapping

| Action              | Required Permission       |
|---------------------|---------------------------|
| submit_for_review   | `req_submit_for_review`   |
| approve             | `req_approve`             |
| reject              | `req_reject`              |
| return_to_draft     | `req_approve`             |
| defer               | `req_defer`               |
| push_to_alm         | `req_push_to_alm`        |
| mark_realized       | `req_mark_realized`       |
| verify              | `req_verify`              |
| reactivate          | `req_submit_for_review`   |

---

_Last updated: 2026-02-13 — Sprint 25_
