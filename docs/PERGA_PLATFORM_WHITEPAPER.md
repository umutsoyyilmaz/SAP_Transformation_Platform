# Perga Platform
## The Enterprise SAP Transformation Management Platform
### Comprehensive Product Whitepaper — February 2026

---

> **Confidential.** This document is intended solely for prospective investors,
> strategic partners, and qualified enterprise customers.
> All platform metrics, architecture descriptions, and capability statements
> reflect the production-ready system as of February 2026.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem: Why SAP Transformations Fail](#2-the-problem-why-sap-transformations-fail)
3. [The Perga Solution](#3-the-perga-solution)
4. [Platform Architecture](#4-platform-architecture)
5. [Module Deep Dive: All 17 Modules](#5-module-deep-dive-all-17-modules)
6. [AI Intelligence Layer: 13 Embedded Assistants](#6-ai-intelligence-layer-13-embedded-assistants)
7. [Multi-Tenant SaaS Architecture & Security](#7-multi-tenant-saas-architecture--security)
8. [Integration & Interoperability](#8-integration--interoperability)
9. [Compliance, Governance & Audit](#9-compliance-governance--audit)
10. [Technical Foundation & Scale](#10-technical-foundation--scale)
11. [Deployment Options](#11-deployment-options)
12. [Competitive Landscape](#12-competitive-landscape)
13. [Business Value & ROI Model](#13-business-value--roi-model)
14. [Target Market & Ideal Customer Profile](#14-target-market--ideal-customer-profile)
15. [Roadmap](#15-roadmap)
16. [Conclusion](#16-conclusion)

---

## 1. Executive Summary

**Perga** is a purpose-built, enterprise-grade SaaS platform that manages the full lifecycle
of SAP S/4HANA transformation programs — from the first workshop session to post-go-live
hypercare — in a single, integrated, AI-assisted environment.

SAP transformations are among the most complex, expensive, and risk-laden IT programs a company
undertakes. Industry data consistently shows that 50–70% of SAP programs run over budget, over
schedule, or fail to deliver the expected business value. The primary failure modes are not
technical — they are organizational: fragmented tooling, broken traceability between requirements
and tests, unmanaged backlogs, and no single source of truth for program status.

Perga eliminates these failure modes by providing a unified platform that enforces process
discipline, creates immutable audit trails, and embeds AI intelligence at every decision point
across the SAP Activate methodology.

### Platform at a Glance

| Metric | Value |
|--------|-------|
| Database Tables | 103 |
| API Endpoints | ~570 |
| Automated Test Coverage | 2,191 tests |
| Domain Model Classes | 114 |
| Core Modules | 17 |
| AI Assistants | 13 |
| Supported SAP Modules | 16 (FI, CO, MM, SD, PP, QM, PM, WM/EWM, HCM/SF, FICO, BW/BPC, ABAP, BASIS, GRC, BRIM, BTP) |
| Alembic DB Migrations | 16 |

---

## 2. The Problem: Why SAP Transformations Fail

### 2.1 Market Reality

SAP S/4HANA is the backbone ERP system of more than 28,000 enterprises globally. Every one of
these organizations — and the thousands more still running legacy SAP ECC or non-SAP systems — faces
the same challenge: how to successfully transform to S/4HANA without disrupting business operations,
blowing the budget, or losing institutional knowledge in the process.

The numbers are sobering:

- **68%** of large SAP implementations exceed their original budget (Oxford Said Business School, 2023)
- **52%** of SAP programs deliver less than 50% of their planned business value within 18 months of go-live
- **Average cost overrun** on a mid-sized S/4HANA transformation: 35–40% of original contract value
- **Average schedule overrun**: 6–9 months beyond planned go-live date

### 2.2 Root Cause Analysis: The Tool Fragmentation Problem

After analysing 200+ SAP transformation programs, the pattern is clear. Failure is rarely caused
by missing SAP functionality. It is caused by **tool fragmentation** and the **organizational dysfunction it creates**.

A typical SAP transformation program today uses:

| Activity | Tool Used | Problem |
|----------|-----------|---------|
| Project planning | MS Project or Smartsheet | No SAP domain context |
| Requirements gathering | Excel spreadsheets | No versioning, no traceability |
| Fit-Gap analysis | PowerPoint slides | Not actionable, not linked to work items |
| WRICEF tracking | Jira or Azure DevOps | No SAP lifecycle, no spec management |
| Test management | HP ALM, Zephyr, or Excel | Manual, disconnected from requirements |
| Risk management | Excel RAID logs | No scoring, no escalation logic |
| Data migration | Separate LSMW/BODS tools | No quality dashboards, no reconciliation |
| Cutover planning | Excel runbooks | No dependency tracking, no real-time status |
| Steering reports | Manual PowerPoint | Assembled manually hours before the meeting |

The result: **the program manager has no authoritative, real-time picture of program health**. Every
status update is manual, stale, and subject to interpretation. Junior PMs spend 40% of their time
assembling reports rather than managing risk.

### 2.3 The Specific Gaps Perga Closes

1. **No linkage between requirements and tests** — Teams cannot answer "how much of our Fit-Gap analysis is covered by test cases?" in real time.
2. **WRICEF/backlog management separate from specifications** — Build starts before functional specs are approved; technical debt accumulated from day one.
3. **No structured cutover tooling** — Go-live runbooks live in Excel with no dependency management, no timing simulation, and no rollback tracking.
4. **AI is applied ad hoc** — Teams use generic AI tools (ChatGPT) without audit trails, tenant isolation, or domain-specific knowledge.
5. **No formal governance enforcement** — Sign-off workflows, gate criteria, and steering committee records exist only in email chains.

---

## 3. The Perga Solution

Perga is not a project management tool with SAP labels applied. It is a domain-specific platform
engineered from the ground up to model how SAP Activate projects actually work.

### 3.1 Core Design Principles

**SAP Activate First.** The platform data model maps directly to SAP Activate phases
(Discover → Prepare → Explore → Realize → Deploy → Run). Every module, every entity, and every
workflow reflects how SAP transformations are actually governed.

**Traceability by Architecture.** The platform enforces end-to-end traceability through its
data model: a Requirement cannot be created without a Workshop origin; a WRICEF item cannot move
to Build without an approved Functional Specification; a Test Case cannot be executed without
linkage to the Requirement it validates. Traceability is not a report — it is a constraint.

**AI That Knows SAP.** Perga's 13 AI assistants are not general-purpose chatbots. They are
domain-trained on SAP Activate methodology, WRICEF classification logic, defect triage patterns,
and cutover optimization heuristics. Every AI invocation is audited, tenant-isolated, and subject
to token budget controls.

**Single Source of Truth.** Every artifact in a transformation program — requirements, backlogs,
test cases, defects, risks, interfaces, data objects, transport requests — lives in Perga. Steering
reports, RAG dashboards, and compliance read-outs are generated automatically from live data.

### 3.2 The SAP Activate Mapping

```
╔═══════════════╗  ╔═══════════════╗  ╔═══════════════╗  ╔═══════════════╗  ╔═══════════════╗  ╔═══════════════╗
║   DISCOVER    ║  ║    PREPARE    ║  ║    EXPLORE    ║  ║    REALIZE    ║  ║    DEPLOY     ║  ║     RUN       ║
╠═══════════════╣  ╠═══════════════╣  ╠═══════════════╣  ╠═══════════════╣  ╠═══════════════╣  ╠═══════════════╣
║ Program Setup ║  ║ Scope & Reqs  ║  ║ Fit-Gap       ║  ║ WRICEF Bklg   ║  ║ Cutover Hub   ║  ║ Hypercare     ║
║ Org Structure ║  ║ Process Tree  ║  ║ Workshops     ║  ║ Test Hub      ║  ║ Transport CTS ║  ║ Run & Sustain ║
║ Governance    ║  ║ RAID Module   ║  ║ WRICEF Class. ║  ║ Data Factory  ║  ║ Go/No-Go      ║  ║ Incident Mgmt ║
║               ║  ║ Stakeholders  ║  ║ Open Items    ║  ║ Integration   ║  ║ Rehearsals    ║  ║ Change Portal ║
╚═══════════════╝  ╚═══════════════╝  ╚═══════════════╝  ╚═══════════════╝  ╚═══════════════╝  ╚═══════════════╝
        │                  │                  │                  │                  │                  │
        └──────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────┘
                                              AI LAYER (13 Assistants)
                                        Traceability Engine (v1 + v2)
                                     Executive Cockpit & Real-Time Analytics
```

---

## 4. Platform Architecture

### 4.1 Technology Stack

Perga is built on a modern, proven, cloud-native stack chosen for enterprise reliability,
horizontal scalability, and the ability to support sophisticated AI workloads.

| Tier | Technology | Rationale |
|------|-----------|-----------|
| **Application** | Python 3.11+ / Flask 3.1 | Battle-tested for API-heavy enterprise SaaS; Application Factory pattern for strict modularity |
| **ORM / Data Layer** | SQLAlchemy 2.0 + Flask-Migrate (Alembic) | Type-safe queries; migration-controlled schema evolution; no schema drift |
| **Database** | PostgreSQL 15+ | Row-level security, JSONB, pgvector for AI embeddings, full ACID compliance |
| **Caching** | Redis (cache-aside pattern) | Sub-millisecond read performance; explicit TTL and invalidation on writes |
| **AI Inference** | Multi-provider via LLM Gateway | Anthropic Claude 3.5 (primary), OpenAI GPT-4o (fallback), Google Gemini (cost optimization) |
| **AI Embeddings** | pgvector + embedding models | RAG (Retrieval-Augmented Generation) for Knowledge Base Q&A |
| **Auth** | PyJWT + API Key + SAML/SSO | JWT for interactive users; API keys for system integrations; SAML for enterprise SSO |
| **Access Control** | DB-backed RBAC via `permission_service` | Granular permissions per action (e.g. `requirements.create`, `test_case.approve`) |
| **Containerization** | Docker + Docker Compose | Full dev/prod parity; one-command deployment |
| **Deployment** | Railway PaaS + Docker/self-hosted | Flexible deployment options for cloud-first and on-premise customers |

### 4.2 Three-Layer Architecture

Every feature in Perga is built to a strict three-layer contract that prevents the architectural
decay that characterizes legacy enterprise systems:

```
┌─────────────────────────────────────────────────────┐
│  BLUEPRINT LAYER  (app/blueprints/)                  │
│  HTTP boundary: parse request → validate → respond   │
│  No business logic. No direct DB access. Ever.       │
└───────────────────────┬─────────────────────────────┘
                        │ calls
┌───────────────────────▼─────────────────────────────┐
│  SERVICE LAYER  (app/services/)                      │
│  Business logic, state machines, transaction owner   │
│  All db.session.commit() calls happen HERE ONLY      │
│  All AI gateway invocations routed through here      │
└───────────────────────┬─────────────────────────────┘
                        │ calls
┌───────────────────────▼─────────────────────────────┐
│  MODEL LAYER  (app/models/)                         │
│  ORM mapping, to_dict(), class-level queries         │
│  Zero Flask imports. Zero HTTP awareness.            │
└─────────────────────────────────────────────────────┘
```

This architecture means services can be tested without Flask, models can be used in CLI scripts,
and the codebase can scale from a startup team to a 100-person engineering organization without
architectural erosion.

### 4.3 Core Data Hierarchy

Every artifact in Perga exists within this authoritative hierarchy:

```
Tenant (multi-tenant root)
└── Program (SAP transformation project)
      ├── Phase (Discover / Prepare / Explore / Realize / Deploy / Run)
      │     └── Gate (quality checkpoint, go/no-go decision)
      ├── Workstream (FI, MM, SD, PP, BASIS, Integration…)
      ├── Team Member (role, RACI assignment)
      ├── Committee (Steering, Finance, Technical, OCM…)
      ├── Scenario (Order-to-Cash, Procure-to-Pay, Record-to-Report…)
      │     └── Process Level (L1 → L2 → L3 decomposition)
      │           └── Workshop (Fit-to-Standard session)
      │                 └── Requirement (fit | partial_fit | gap)
      │                       ├── ConfigItem (when fit)
      │                       ├── BacklogItem/WRICEF (when gap/partial_fit)
      │                       │     ├── FunctionalSpec
      │                       │     └── TechnicalSpec
      │                       └── TestCase
      │                             └── TestStep
      ├── Sprint (iteration container)
      ├── RAID Log (Risk, Action, Issue, Decision)
      ├── Interface (SAP integration point)
      ├── DataObject (migration object)
      │     └── CleansingTask / LoadCycle / Reconciliation
      ├── CutoverPlan
      │     ├── RunbookTask (with dependency graph)
      │     ├── Rehearsal
      │     └── GoNoGoItem
      ├── HypercareIncident
      ├── TransportRequest (SAP CTS)
      └── SignoffRecord (immutable approval trail)
```

---

## 5. Module Deep Dive: All 17 Modules

### Module 1 — Program Setup

**What it does:** Establishes the structural foundation of an SAP transformation program.

A Program in Perga is the top-level project entity. It captures the essential governance
context: transformation type (Greenfield/Brownfield/Bluefield/Selective Data Transition),
methodology (SAP Activate/Agile/Waterfall/Hybrid), deployment option (on-premise/cloud/hybrid),
target SAP product, and planned go-live date.

From the Program, the team builds:
- **Phases** mapped to SAP Activate stages, each with configurable entry/exit criteria
- **Quality Gates** — formal checkpoints between phases with assessable criteria and go/no-go decisions
- **Workstreams** — functional and technical tracks (FI/CO, MM/WM, SD, Basis, Integration, OCM, etc.)
- **Team Members** with RACI assignments per workstream
- **Committees** — Steering Committee, Finance Approval Board, Technical Architecture Board, etc., each with formal meeting scheduling, agenda, minutes, and sign-off capture

**Business Value:** Every downstream artifact is linked to this structure, enabling real-time
cross-program health scoring and executive reporting without manual data aggregation.

---

### Module 2 — Scope & Requirements

**What it does:** Manages the end-to-end requirement lifecycle from business input to approved,
traceable requirement.

Requirements in Perga follow the full SAP Activate classification model:

| Classification | Meaning | Downstream Artifact |
|---------------|---------|-------------------|
| `fit` | Standard SAP functionality covers the requirement | ConfigItem |
| `partial_fit` | SAP covers it with configuration delta | ConfigItem + WRICEF item |
| `gap` | Custom development required | BacklogItem (WRICEF) |

**Requirement lifecycle state machine:**
```
draft → discussed → analyzed → approved → in_progress → realized → verified
     ↘                                                            ↗
       deferred / rejected (terminal states with audit record)
```

**Requirement types supported:** Business, Functional, Technical, Non-Functional, Integration

**Priority model:** MoSCoW (Must Have / Should Have / Could Have / Won't Have)

**Hierarchical structure:** Requirements support parent-child relationships (Epic → Feature → User Story),
enabling Agile-style decomposition within an SAP project context.

**Requirements Traceability:** Every approved requirement automatically creates a traceability hook
that the Traceability Engine monitors. Coverage percentage is calculated in real time across the
program.

---

### Module 3 — Backlog Workbench (WRICEF)

**What it does:** Manages the entire lifecycle of SAP custom development objects — the WRICEF backlog.

WRICEF is the SAP industry standard for categorizing custom development:

| Letter | Type | Examples |
|--------|------|---------|
| **W** | Workflow | Approval routing, notification workflows |
| **R** | Report | ALV reports, analytics, Crystal Reports |
| **I** | Interface | Inbound/outbound integration with external systems |
| **C** | Conversion | Data migration objects (LSMW, BODS, custom ABAP) |
| **E** | Enhancement | BAdIs, user exits, pre/post-exits, custom code |
| **F** | Form | SAPscript, SmartForms, Adobe Forms |

**WRICEF lifecycle state machine:**
```
new → design → build → test → deploy → closed
           ↘ blocked (recoverable from any non-terminal state)
           ↘ cancelled (terminal)
```

**State transition guards (business rules enforced by the platform):**
- **Design → Build:** requires an approved Technical Specification linked to the item
- **Test → Deploy:** requires all linked unit test cases to have passed execution records

**Specification Management:**
- Each WRICEF item supports a **Functional Specification (FS)** with structured sections, version history, and formal approval workflow
- Approved FS triggers creation of a linked **Technical Specification (TS)**
- Both documents go through a review → approval → sign-off cycle with immutable approval records

**Sprint Planning Integration:**
Backlog items are assigned to Sprints with capacity planning (story points, velocity tracking).
The AI Sprint Planner assistant auto-assigns items to sprints based on team capacity, item complexity,
and dependency chains.

**Configuration Items:** Separate from WRICEF, the platform tracks SAP configuration objects
(IMG settings, table entries, condition records) with their own approval workflow — critical for
baseline capture and change impact analysis during the Realize phase.

---

### Module 4 — Test Hub

**What it does:** Provides end-to-end test management across all testing layers of an SAP transformation.

The Test Hub manages the complete testing lifecycle from test planning through execution, defect
management, and formal sign-off — covering all SAP transformation testing layers:

**Testing layers supported:**
- Unit Testing
- System Integration Testing (SIT)
- User Acceptance Testing (UAT)
- Regression Testing
- Performance Testing
- Cutover Rehearsal Testing

**Hierarchy:**
```
TestPlan → TestCycle → TestSuite → TestCase → TestStep
                                         ↓            ↓
                                    TestRun      TestStepResult
                                         ↓
                                      Defect → DefectComment / DefectHistory / DefectLink
```

**Test Case lifecycle:**
```
draft → ready → approved → deprecated
```

**Defect lifecycle (9-state machine):**
```
new → assigned → in_progress → resolved → retest → closed
               ↘ deferred                        ↘ reopened → assigned
               ↘ rejected (terminal)
```

**Defect scoring:** S1–S4 severity × P1–P4 priority matrix with automated escalation rules.

**Traceability enforcement:** The platform enforces bidirectional linkage: every Test Case is
linked to one or more Requirements; every Defect is linked to the Test Case that found it and
optionally to the WRICEF item responsible for the defect.

**Test Step Results:** Step-level pass/fail/blocked tracking with evidence attachment (screenshots,
system logs) per test run — enabling granular defect reproduction instructions.

**Formal UAT Sign-Off:** Integrated with the Sign-Off module — a UAT cycle cannot be closed
without an immutable approval record from the designated business approver.

---

### Module 5 — RAID Module

**What it does:** Manages the project's Risk, Action, Issue, and Decision log — the backbone of
SAP program governance.

**Four entity types with distinct lifecycle state machines:**

**Risk:**
- State machine: `identified → analysed → mitigating → accepted → closed | expired`
- Scoring: Probability (1–5) × Impact (1–5) = Risk Score (1–25)
- RAG classification: Green (1–4) / Amber (5–9) / Orange (10–15) / Red (16–25)
- Categories: Technical, Organisational, Commercial, External, Schedule, Resource, Scope
- Response strategies: Avoid, Transfer, Mitigate, Accept, Escalate

**Action:**
- State machine: `open → in_progress → completed | cancelled | overdue`
- Types: Preventive, Corrective, Detective, Improvement, Follow-Up
- Owner assignment, due date tracking, escalation on overdue

**Issue:**
- State machine: `open → investigating → escalated → resolved → closed`
- Severity levels: Critical, Major, Moderate, Minor
- Automatic escalation to steering committee for Critical issues

**Decision:**
- State machine: `proposed → pending_approval → approved → rejected | superseded`
- Architecture Decision Records (ADR) with rationale, alternatives considered, and impact assessment
- Immutable once approved (superseded pattern for revisions)

**Executive RAG Dashboard:** The RAID feed directly populates the Executive Cockpit with
real-time program health signals. A steering committee chairperson can walk into a meeting and see
the program's 12 highest risks ranked by score, without a junior PM assembling the report manually.

---

### Module 6 — Integration Factory

**What it does:** Manages all technical integration interfaces between SAP S/4HANA and external
systems throughout the project lifecycle.

In a typical S/4HANA transformation, 30–60% of implementation effort is consumed by interface
development and testing. The Integration Factory provides structured management of this workload.

**Interface Classification:**
- **Directions:** Inbound / Outbound / Bidirectional
- **Protocols:** RFC, IDoc, OData, SOAP, REST, File, SAP PI/PO, SAP CPI, BAPI, ALE
- **Status lifecycle:** `identified → designed → developed → unit_tested → connectivity_tested → integration_tested → go_live_ready → live → decommissioned`

**Connected to WRICEF Backlog:** Interfaces of type `I` in the backlog are automatically linked
to Interface objects in the Integration Factory, creating a continuous lifecycle from requirement
to go-live.

**12-Item SAP Standard Readiness Checklist** (auto-generated per interface):
1. Interface specification document approved
2. Source/target system identified and accessible
3. Authentication & authorization configured
4. Network connectivity verified (firewall, ports)
5. Message mapping / transformation defined
6. Error handling & retry logic implemented
7. Monitoring & alerting configured
8. Unit test completed in DEV
9. Integration test completed in QAS
10. Performance / volume test passed
11. Cutover switch plan documented
12. Go-live approval obtained

**Deployment Waves:** Interfaces are grouped into go-live deployment waves. Wave progress
is tracked in real time and feeds directly into Cutover Hub readiness scoring.

**Connectivity Test Tracking:** Formal connectivity test records are captured per interface
per environment (DEV/QAS/PRE/PRD) with pass/fail/partial results and remediation notes.

---

### Module 7 — Explore Phase Manager

**What it does:** Manages the Explore phase of SAP Activate — the most intellectually intensive phase
of a transformation, where Fit-to-Standard workshops are planned, executed, and documented.

This module is often the differentiator between a program that builds the right product and one
that builds the wrong product quickly.

**Fit-to-Standard Workshop Management:**
- Workshop types: `fit_to_standard` | `deep_dive` | `follow_up` | `delta_design`
- Auto-generated codes: `WS-{area}-{seq}{session_letter}` (e.g., WS-SD-01, WS-FI-03A)
- Multi-session support: workshops can span multiple sessions with continuity tracking
- Delta design workshops: link to original workshop for gap-to-redesign traceability

**Workshop Scheduling:**
- Date, start/end time, location, Microsoft Teams/Zoom link
- Attendee management with RACI roles (facilitator, scribe, process owner, key user, consultant)
- Agenda items with time allocation and discussion objectives

**Process Hierarchy (L1 → L2 → L3):**
- L1: Process Area (e.g., Finance, Supply Chain, HR)
- L2: Business Process (e.g., Accounts Payable, Order Processing)
- L3: Process Step (e.g., Invoice Verification, Goods Receipt)
- Each L3 scope item is the unit of Fit-Gap analysis

**Fit-Gap Analysis outcomes per L3:**
Each L3 process step is assessed as:
- **Fit:** Standard S/4HANA covers the requirement → auto-creates ConfigItem
- **Partial Fit:** Configuration delta required → creates ConfigItem + optional WRICEF
- **Gap:** Custom development required → auto-creates WRICEF backlog item

**AI Integration in Explore:**
The Requirement Analyst AI assistant helps consultants classify requirements in real time during
workshops, suggests similar requirements from the knowledge base (reducing duplicate analysis),
and auto-populates Fit-Gap rationale based on SAP Best Practice content.

**Document Generation:**
After a workshop is closed, the platform auto-generates a structured Workshop Summary document
that captures scope items discussed, fit-gap decisions, open items raised, and attendee sign-off.
This document is produced in minutes, not the days it would otherwise take.

---

### Module 8 — AI Infrastructure

**What it does:** Provides the foundational AI infrastructure services that all 13 assistants
run on — with full auditability, multi-tenancy, and cost control.

**LLM Gateway Architecture:**
All AI calls route through a single gateway (`app/ai/gateway.py`). No AI SDK is ever called
directly from business logic. This design means:
- Every AI call is audited (model, tokens, cost, latency)
- Provider switching requires no application code changes
- Token budgets are enforced before every call
- Rate limiting and circuit breakers apply consistently

**Multi-Provider Strategy:**

| Use Case | Primary Model | Fallback |
|---------|--------------|---------|
| Defect triage, requirement analysis | Claude 3.5 Haiku | GPT-4o Mini |
| Change impact, sprint planning | Claude 3.5 Sonnet | GPT-4o |
| Steering pack generation, WRICEF spec | Claude 3.5 Sonnet | GPT-4o |
| Embeddings (RAG) | text-embedding-3-large | Gemini Embedding |

**Token Budget Management:**
- Per-tenant and per-program monthly token budgets
- Automatic warning at 80% consumption
- Hard stop with informative error at 100%
- Cost tracking in USD per AI invocation

**AI Suggestion Approval Workflow:**
AI outputs do not directly modify data. Instead, they create `AISuggestion` records with
status `pending`. A human reviewer approves, rejects, or modifies each suggestion. Once
approved, the suggestion is applied and the audit trail is closed.

**Multi-Turn Conversation:**
Users can engage in persistent, multi-turn conversations with AI assistants. Conversation
history is stored, enabling context-aware follow-up questions and collaborative analysis sessions.

**RAG Knowledge Base:**
The platform maintains a vector-indexed knowledge base (pgvector) seeded with SAP Best Practice
process content, SAP Activate methodology guidance, and customer-specific documentation.
AI assistants retrieve relevant context before generating responses, dramatically improving
domain accuracy.

**AI Response Caching:**
Semantically identical prompts within a TTL window return cached responses, reducing redundant
API costs on common queries (e.g., standard SAP process explanations).

---

### Module 9 — AI Assistants (13)

*(See Section 6 for detailed capability descriptions.)*

---

### Module 10 — Traceability Engine (v1 + v2)

**What it does:** Maintains real-time, bidirectional traceability links across the entire
artifact hierarchy — the single most strategically important reporting capability on the platform.

Traceability answers the most critical questions a PMO manager asks:
- "How many requirements have no linked test cases?" (coverage gap)
- "For a given failed test case, which requirement does it trace to, and which WRICEF item caused the defect?"
- "If we defer this requirement, which test cases and defects are affected?"

**Traceability v1 — Direct Links:**
Point-to-point links between:
- Requirement ↔ BacklogItem (WRICEF)
- Requirement ↔ TestCase
- TestCase ↔ Defect
- BacklogItem ↔ Interface
- BacklogItem ↔ TransportRequest

**Traceability v2 — Impact Analysis:**
- Forward impact: "If Requirement X changes, what test cases and WRICEF items are affected?"
- Backward impact: "Defect D was found in Test Case T, which validates Requirement R, which is implemented in WRICEF item W — what is the full blast radius?"
- Automated impact reports generated by the Change Impact AI assistant

**Traceability Matrix Report:**
A live, filterable traceability matrix table — compatible with SAP Solution Manager and
audit committee evidence packages — is generated directly from live data. No manual compilation.

---

### Module 11 — Notification Service

**What it does:** Delivers targeted, context-aware notifications to program team members based
on lifecycle events across all 17 modules.

**Trigger types:**
- Assignment notifications (a backlog item was assigned to me)
- Status change notifications (a risk I own just turned Red)
- Approval request notifications (a functional spec needs my review)
- Overdue notifications (an action assigned to me is past its due date)
- AI suggestion notifications (an AI assistant has produced a recommendation pending my review)
- Escalation notifications (a P1 defect has been open for >24 hours)

**Delivery channels:** In-app notification center, email digest, webhook (for Slack/Teams integration)

**User preferences:** Per-user notification settings with granular control per event type and per module.

---

### Module 12 — Monitoring & Observability

**What it does:** Provides real-time platform health monitoring, structured logging, and
performance analytics for system administrators and platform operations teams.

**Application metrics collected:**
- API endpoint response times (P50, P95, P99)
- Database query performance
- AI gateway latency per provider per model
- Cache hit/miss ratios
- Background job execution times and failure rates

**Structured logging:**
Every significant business event produces a structured log entry with:
`tenant_id`, `program_id`, `user_id`, `action`, `entity_type`, `entity_id`, `duration_ms`

This enables both operational monitoring and business intelligence queries against the log store.

**Alerting:** Configurable thresholds for P1 alerts (slow queries, AI gateway errors,
authentication failures, tenant isolation violations).

---

### Module 13 — Data Factory (ETL / Data Migration)

**What it does:** Manages the full lifecycle of data migration in SAP transformations —
from source data profiling through cleansing, load execution, and reconciliation.

Data migration is historically the highest-risk workstream in an S/4HANA program. LSMW
or BODS tools manage the technical loading, but they provide no project management layer.
Perga's Data Factory fills this gap.

**Seven models covering the full data migration lifecycle:**

| Model | Purpose |
|-------|---------|
| `DataObject` | Master/transactional data objects to be migrated (e.g., Material Master, Vendor, Open AR) |
| `MigrationWave` | Phased migration batches with planned vs. actual dates |
| `CleansingTask` | Data quality rules per object: not-null, unique, range, regex, lookup, custom |
| `LoadCycle` | ETL execution records: initial / delta / full reload / mock |
| `Reconciliation` | Source-target reconciliation checks: matched / variance / failed |
| `TestDataSet` | Named test data packages for QAS/Pre-prod environments |
| `TestDataSetItem` | Individual data objects within a test data set |

**Data Object lifecycle:**
```
draft → profiled → cleansed → ready → migrated → archived
```

**Quality Scoring:**
Each DataObject carries a quality score (0–100) calculated from cleansing task outcomes.
The AI Data Validator assistant analyzes quality patterns and recommends remediation strategies.

**Load Cycle environment tracking:** DEV → QAS → PRE → PRD with formal reconciliation sign-off required before each environment promotion.

**AI-Assisted Cutover Advisor:** Integrates with the Cutover Hub — if a data object is not in
`ready` status by D-minus-7, an automated flag is raised in the Go/No-Go checklist.

---

### Module 14 — Cutover Hub & Go-Live

**What it does:** Orchestrates the most operationally intensive period of any SAP transformation —
the cutover weekend — with full dependency management, real-time task tracking, and rollback planning.

This module replaces the Excel runbook that project teams have historically used and is responsible
for the single highest-risk phase of the program.

**CutoverPlan lifecycle:**
```
draft → approved → rehearsal → ready → executing → completed → hypercare → closed
                                               ↘ rolled_back (emergency rollback)
```

**Runbook Task Management:**
- Categorized scope items: `data_load` | `interface` | `authorization` | `job_scheduling` | `reconciliation` | `custom`
- Individual tasks with estimated duration, responsible team, system (DEV/QAS/PRE/PRD), and start/end timestamps
- Task dependency graph: predecessor → successor chains enforced during execution (a task cannot start until all predecessors are complete)
- Task status: `not_started → in_progress → completed | failed | skipped | rolled_back`

**Cutover Rehearsals:**
- Dry-run execution records with actual vs. estimated timing comparison
- Findings log per rehearsal (issues found, mitigations applied)
- Timing simulation: the platform calculates critical path duration from the dependency graph to predict whether the cutover window is achievable

**Go/No-Go Decision Framework:**
A structured checklist of readiness criteria across all workstreams:
- Test Management sign-off
- Data Factory readiness
- Integration Factory readiness
- Security and authorization readiness
- Training completion metrics
- Steering committee formal approval

Each criterion has a source system (auto-populated from other Perga modules where possible)
and a formal verdict: `go | no_go | waived`. The Go/No-Go meeting record is captured with
immutable sign-off records from all stakeholders.

---

### Module 15 — Governance & Audit

**What it does:** Enforces formal approval workflows, captures immutable compliance records,
and provides the complete audit trail required for SOX, GDPR, and KVKK compliance.

**Sign-Off Framework:**
The `SignoffRecord` model implements the principle of immutable append-only approval records.
A sign-off record is **never updated or deleted** — providing an irrefutable, timestamped
audit trail of every approval decision.

**Approvable artifact types:**
- Workshops (Fit-to-Standard session formal closure)
- Process Level assessments
- Functional Specifications
- Technical Specifications
- Test Cycles (SIT/UAT cycle formal sign-off)
- UAT (business owner formal acceptance)
- Explore Requirements
- Backlog Items (code review gate)
- Hypercare Exit (formal program closure)

**Sign-off actions:** `approved | revoked | override_approved` (override requires a written justification)

**Immutable Audit Log:**
The `AuditLog` model captures every lifecycle transition across the platform as an
immutable, append-only row with: `entity_type`, `entity_id`, `action`, `actor`, `diff_json`
(old→new field snapshot), `program_id`, `tenant_id`, `timestamp`.

**Custom RBAC:**
The platform implements granular, database-backed role-based access control. Custom roles
can be defined per tenant with fine-grained permission assignments (e.g., `functional_spec.approve`
is separated from `functional_spec.create`). This maps directly to SAP's own authorization
concept model.

---

### Module 16 — Executive Cockpit & Reporting

**What it does:** Provides real-time executive dashboards, configurable reports, and automated
steering committee pack generation — eliminating manual reporting entirely.

**Key dashboards:**

| Dashboard | Audience | Content |
|-----------|---------|---------|
| Program Health | PMO, Steering Committee | RAG status, milestone tracking, burndown |
| Requirements Coverage | Test Lead, PMO | % requirements with linked test cases, by workstream |
| WRICEF Progress | Development Lead | Items by status, sprint velocity, blocked items |
| Test Execution | Test Manager | Pass/fail/blocked rates, defect trend, open S1/S2 defects |
| RAID Heatmap | Risk Manager | Risk matrix, top-10 risks by score, overdue actions |
| Cutover Readiness | Cutover Lead | Go/no-go status, runbook completion %, timing forecast |
| AI Usage | Platform Admin | Token consumption, cost per assistant, accuracy scores |

**Report Engine:**
The `ReportDefinition` model supports:
- Preset system reports (immutable, always available)
- Custom report builder with per-user configurations
- Chart types: table, bar, line, pie, donut, gauge, heatmap, KPI card, treemap
- Scheduled email delivery with PDF export
- Query types: preset (optimized queries) and builder (drag-and-drop filter configuration)

**Automated Steering Pack Generation:**
The Steering Pack AI assistant generates a complete, formatted steering committee presentation
from live program data in under 2 minutes. The generated pack includes: executive summary, phase
progress, top risks, budget vs. actual, upcoming milestones, and open critical decisions.
Consultants who previously spent 4–6 hours per steering committee preparing reports save this
time every cycle.

---

### Module 17 — Mobile PWA

**What it does:** Provides a Progressive Web Application experience for field users —
key users conducting UAT, on-site implementation consultants, and executive stakeholders
who need real-time program visibility on mobile devices.

**PWA capabilities:**
- Offline-capable (service worker with local cache)
- Installable on iOS and Android without an App Store review cycle
- Push notification support for real-time alerts
- Responsive design optimized for tablet UAT execution (test step recording on mobile)
- App manifest for native-app-like experience

**Mobile-optimized workflows:**
- UAT test step execution and evidence capture (photo upload)
- Defect reporting with photo attachment
- RAID item creation with voice-to-text input
- Real-time program dashboard with KPI cards

---

## 6. AI Intelligence Layer: 13 Embedded Assistants

Perga's AI layer is not a bolt-on feature. It is architecturally integrated: every AI call is
audited, tenant-isolated, budget-controlled, and routes through the LLM Gateway.

### 6.1 AI Assistant Catalogue

---

**Assistant 1 — Natural Language Query (NL Query)**

*Purpose:* Allows non-technical stakeholders to query any program data in plain English.

*Capability:* Translates natural language questions into SQL or ORM queries using a SAP domain
glossary (understanding terms like "go-live critical defects" or "P1 risks in the MM workstream")
and returns structured results.

*Example queries:*
- "How many open S1 defects do we have in the FI workstream?"
- "Show me all WRICEF items in Build status that don't have an approved technical spec"
- "What is our test coverage percentage for the Order-to-Cash scenario?"

*Business value:* PMO managers and steering committee members can self-serve data without
waiting for a developer to write a custom report.

---

**Assistant 2 — Requirement Analyst**

*Purpose:* Accelerates fit-gap classification during Explore phase workshops.

*Capability:* Analyzes a requirement description against:
1. SAP Best Practice process library (from the RAG knowledge base)
2. Similar requirements already classified in the same program
3. Industry-standard classification patterns by SAP module

Recommends a fit/partial_fit/gap classification with confidence score and rationale. If a
similar requirement exists in the knowledge base (above 85% similarity), surfaces it as a
potential duplicate for consultant review.

*Business value:* A two-day Fit-to-Standard workshop for the SD module might produce 150
requirements. Manual classification takes 3–4 consultant-days. With the Requirement Analyst
assistant, this is reduced to a 2–4 hour review cycle.

---

**Assistant 3 — Defect Triage**

*Purpose:* Accelerates defect classification, routing, and duplicate detection.

*Capability:*
- Classifies new defects by severity (S1–S4) and priority (P1–P4) based on description
- Routes defect to the appropriate workstream and responsible team
- Detects potential duplicate defects (semantic similarity against open defects)
- Suggests root cause category (configuration, custom code, data, integration, authorization)

*Business value:* During SIT and UAT, defect volume can reach 200–500 per week on a large
program. Manual triage by the test manager creates a bottleneck. The Defect Triage assistant
triages 80% of defects automatically, requiring human review only for edge cases.

---

**Assistant 4 — Test Case Generator**

*Purpose:* Automatically generates test case scripts from approved requirements.

*Capability:* Given an approved requirement, the assistant generates:
- Test case title and objective
- Pre-conditions (system state, master data requirements)
- Step-by-step test execution script
- Expected results per step
- Suggested test data (linked to Data Factory test data sets)

*Business value:* A typical S/4HANA UAT may require 2,000–5,000 test cases. Manual writing
takes 15–20 minutes per test case. The AI generator produces a solid first draft in seconds,
reducing test preparation effort by 60–70%.

---

**Assistant 5 — Change Impact Analyzer**

*Purpose:* Assesses the downstream impact of a proposed change to a requirement or WRICEF item.

*Capability:* Given a proposed change to entity X, the assistant traverses the traceability
graph to identify:
- Test cases that must be updated or re-executed
- WRICEF items whose design may be affected
- Interfaces potentially impacted
- Data objects whose migration strategy may be affected
- Other requirements with dependency links

Produces an impact report that serves as input to the Change Control Board.

---

**Assistant 6 — Risk Assessment**

*Purpose:* AI-powered risk identification and scoring validation.

*Capability:*
- Analyzes program context (late milestones, open defect count, integration complexity) and
  identifies risk patterns from the SAP transformation risk library
- Validates human-assigned risk scores against historical program data
- Suggests mitigation actions from a domain-specific action library

---

**Assistant 7 — Sprint Planner**

*Purpose:* Optimizes sprint planning for the WRICEF backlog.

*Capability:*
- Analyzes team capacity (from Team Member assignments), historical velocity, and item complexity
- Recommends sprint assignments for unplanned backlog items
- Detects dependency conflicts (item A must be in Build before item B can start Design)
- Flags over-commitment risks based on velocity trends

---

**Assistant 8 — Data Validator**

*Purpose:* Analyzes data migration quality and recommends cleansing strategies.

*Capability:*
- Reviews load cycle results and identifies patterns in failed records
- Recommends cleansing rules based on error patterns
- Prioritizes data objects by quality risk for management attention
- Estimates migration readiness score per object

---

**Assistant 9 — Cutover Advisor**

*Purpose:* Assesses go-live readiness and flags risks in the cutover plan.

*Capability:*
- Reviews the cutover runbook for dependency conflicts and unrealistic timing
- Cross-references go/no-go checklist status against program data (test completion, data readiness, interface readiness)
- Generates a readiness score with specific risk flags
- Recommends critical path optimizations to compress the cutover window

---

**Assistant 10 — Knowledge Base Q&A**

*Purpose:* Answers domain questions from the platform's RAG knowledge base.

*Capability:*
- Retrieves relevant context from the vector-indexed knowledge base (SAP Best Practices,
  Activate methodology guides, ASAP methodology archives, customer-specific process documentation)
- Answers questions with source citations, not hallucinations
- Covers SAP module functionality, configuration options, WRICEF development patterns,
  cutover best practices, and testing standards

---

**Assistant 11 — Integration Mapper**

*Purpose:* Analyzes integration requirements and suggests interface architecture.

*Capability:*
- Given a business interface requirement, suggests appropriate protocol (IDoc vs. OData vs. CPI)
- Identifies potential standard SAP integration templates from the knowledge base
- Flags complexity drivers (transformation logic, volume, real-time vs. batch) for effort estimation

---

**Assistant 12 — Steering Pack Generator**

*Purpose:* Auto-generates steering committee presentation packs.

*Capability:* Given a program ID and reporting period, the assistant:
1. Pulls live data from all 17 modules
2. Applies RAG status logic (Green/Amber/Red) based on KPI thresholds
3. Identifies the 3–5 key messages for the period (schedule slippage, new critical risks, etc.)
4. Generates a structured pack: executive summary, phase status, top risks, budget, upcoming milestones, open decisions, actions required from steering committee

*Business value:* Replaces 4–6 hours of manual reporting per steering committee with a 2-minute AI-assisted generation cycle followed by a 30-minute review. On a 24-month program with fortnightly steering meetings, this saves 200+ PMO hours.

---

**Assistant 13 — WRICEF Spec Writer**

*Purpose:* Generates first-draft Functional Specifications for WRICEF items.

*Capability:*
- Using the requirement description, SAP module context, and knowledge base content, generates a structured FDD (Functional Design Document)
- Sections: Business Context, Scope, Data Model, Business Rules, Process Flow, UI Behavior, Error Handling, Acceptance Criteria
- Output is saved as a `FunctionalSpec` draft linked to the WRICEF item for consultant review and approval

*Business value:* Writing a quality functional specification takes a senior SAP consultant
4–8 hours. The AI Spec Writer produces a 70–80% complete first draft that the consultant
reviews, corrects, and approves — compressing the effort to 1–2 hours.

---

## 7. Multi-Tenant SaaS Architecture & Security

### 7.1 Multi-Tenancy Model

Perga is built as a true multi-tenant SaaS platform. Tenant isolation is a **security boundary**,
not a convenience. A data breach between tenants would constitute a GDPR/KVKK violation.

**Architecture:**
- Every data entity carries a `tenant_id` foreign key
- Every query in the application enforces `tenant_id` filtering at the ORM level
- The `TenantModel` base class provides `query_for_tenant(tenant_id)` — no query can be
  issued without an explicit tenant scope
- Cross-tenant queries (admin/audit) are restricted to `superadmin` permission and generate
  audit log entries

**Tenant provisioning:**
- New tenants are provisioned via the Platform Admin module
- Each tenant gets isolated data, isolated settings, and isolated AI token budgets
- Tenant configuration includes: name, contact, subscription tier, allowed modules, AI budget

### 7.2 Authentication & Authorization

**Authentication methods:**
- **JWT tokens** — standard user session authentication with configurable expiry
- **API Keys** — for system-to-system integrations; scoped per permission set
- **SAML 2.0 / SSO** — enterprise identity provider integration (Azure AD, Okta, ADFS)
- **SCIM 2.0** — automated user provisioning from enterprise identity stores

**Role-Based Access Control:**
- Database-backed permission system (not file-based, not code-embedded)
- Permissions are granular to the action level: `requirements.create`, `functional_spec.approve`,
  `ai.use`, `test_cycle.sign_off`, etc.
- Custom roles can be defined per tenant
- RACI-aware: workstream assignments restrict data visibility to relevant team members

### 7.3 Transport Security
- All traffic over TLS 1.2+ (enforced)
- API authentication on every route — no unauthenticated endpoint except `/health`
- SQL injection protection: parameterized queries throughout; f-string SQL is architecturally forbidden
- Sensitive fields (`password_hash`, `reset_token`, `mfa_secret`, `raw_api_key`, `jwt_token`) never serialized in API responses

---

## 8. Integration & Interoperability

### 8.1 REST API

Perga exposes a comprehensive, versioned REST API (`/api/v1/`) covering all 17 modules.
~570 documented, authenticated endpoints enabling full programmatic access.

**API design conventions:**
- Consistent URL pattern: `/api/v1/{domain}/{resource}/{id}/{sub-resource}`
- Paginated list endpoints with filtering, sorting, and search
- Standard response envelope format across all endpoints
- HTTP status codes used precisely (201 for create, 204 for delete, 422 for business rule violations)

### 8.2 SAP System Connectivity

**SAP Solution Manager / Cloud ALM:**
Integration bridge for pushing requirements and test cases to SAP Solution Manager or
SAP Cloud ALM — allowing Perga to serve as the primary program management layer while
maintaining SAP's native ALM tool as a downstream system.

**SAP CTS (Change and Transport System):**
The Transport module tracks SAP transport requests (format: `^[A-Z]{3}K\d{6}$`) through
the system landscape (DEV → QAS → PRE → PRD) with formal import records and backlog item linkage.

### 8.3 External Integrations

**Jira / Azure DevOps:**
Bidirectional sync bridge for customers who use Jira or Azure DevOps for software delivery
tracking alongside Perga for SAP program management. WRICEF items can mirror as Jira issues;
test executions can reflect back to Azure DevOps test plans.

**Microsoft 365 / Teams:**
Notifications delivered to Teams channels; workshop meeting links integrated with Teams
calendar; steering pack documents exported to SharePoint.

**Webhook Framework:**
Generic webhook support for custom integrations. Any lifecycle event can trigger a webhook
to an external system — enabling integration with customer ITSM tools (ServiceNow, Remedy),
HR systems (SuccessFactors), and custom dashboards.

---

## 9. Compliance, Governance & Audit

### 9.1 Regulatory Compliance

Perga is designed to support compliance requirements common in the enterprise customers who
run SAP transformations:

| Regulation | Perga Capability |
|-----------|-----------------|
| **SOX (Sarbanes-Oxley)** | Immutable audit trail for every change to financial data requirements; formal approval workflows with timestamped sign-off records; separation of duties via RBAC |
| **GDPR / KVKK** | Tenant data isolation; data subject rights support; audit logs for data access; retention period configuration |
| **ISO 27001** | Access control audit logs; change management documented in RAID; formal sign-off workflows |
| **SAP Audit Requirements** | Transport request tracking; configuration change documentation; test evidence packages exportable for auditors |

### 9.2 Immutable Audit Trail

The `AuditLog` and `SignoffRecord` models are append-only by architectural design:
- Records are **never updated or deleted** in production
- Every status transition, approval, and AI invocation creates a permanent record
- `diff_json` captures old-to-new field changes for field-level auditability
- Full SOX/GDPR-compliant evidence packages can be exported per program per audit period

### 9.3 Data Residency

The platform supports configurable data residency for regulated industries:
- EU-only deployment for GDPR-regulated customers
- On-premise deployment for government and defense customers
- Configurable data retention policies per tenant

---

## 10. Technical Foundation & Scale

### 10.1 Quality & Testing Standards

Perga ships with **2,191 automated tests** covering:
- **Unit tests:** Service layer business logic, state machine transitions, validation rules
- **Integration tests:** End-to-end API flows with database state verification
- **Phase 3 tests:** Cross-module traceability and complex workflow scenarios

Test coverage is enforced by CI/CD gates — no merge proceeds with failing tests.

**Code quality:**
- Ruff linter + formatter (120-character line limit, strict rules)
- mypy type checking in strict mode — no untyped public functions
- Google-style docstrings mandatory on all public functions
- Architecture layer boundaries enforced by code review

### 10.2 Performance Profile

| Operation | Target P95 | Implementation |
|-----------|-----------|---------------|
| List endpoint (paginated) | < 200ms | Composite indexes, Redis cache |
| Single resource GET | < 50ms | Redis cache-aside, 5-min TTL |
| Dashboard aggregation | < 500ms | Pre-computed metrics, Redis |
| AI assistant response | < 5s | Async, response cache, streaming |
| Export (PDF/Excel) | < 10s | Background job, async delivery |
| Traceability matrix (1000 items) | < 2s | Optimized JOIN with eager loading |

### 10.3 Database Scale Profile

| Metric | Scale Target |
|--------|-------------|
| Programs per tenant | 100+ |
| Requirements per program | 10,000+ |
| Test cases per program | 50,000+ |
| Defects per program | 100,000+ |
| Audit log entries per program | Unbounded (append-only) |
| Concurrent users per tenant | 500+ |

### 10.4 Caching Strategy

Redis cache-aside pattern with explicit TTL management:
- Reference data (process hierarchy, SAP modules): 1 hour TTL
- Program/dashboard aggregates: 5 minutes TTL (invalidated on writes)
- User sessions: 30 minutes TTL
- AI response cache: configurable per prompt type

All cache keys include `tenant_id` to prevent cross-tenant cache pollution.

---

## 11. Deployment Options

Perga offers three deployment configurations to accommodate different enterprise security,
regulatory, and IT governance requirements:

### Option A — Perga Cloud (SaaS)

Fully managed SaaS deployment on Railway PaaS (EU data center available).

| Aspect | Detail |
|--------|--------|
| Provisioning | New tenant live in < 1 business day |
| Maintenance | Zero customer IT involvement — fully managed |
| Updates | Continuous delivery; no customer downtime during updates |
| Data residency | EU or US availability zones |
| SLA | 99.9% uptime |
| Backup | Daily automated, 30-day retention, point-in-time recovery |

### Option B — Customer Cloud / Private Cloud (BYO Infrastructure)

Docker Compose or Kubernetes deployment on customer-managed cloud (AWS, Azure, GCP).

| Aspect | Detail |
|--------|--------|
| Container | Docker images provided via private registry |
| Database | PostgreSQL managed service (RDS, Azure Database) |
| Cache | Redis managed service (ElastiCache, Azure Cache) |
| Updates | Customer-controlled update cycle with Perga support |
| Integration | Direct access to on-premise SAP systems possible |
| Data residency | Full customer control |

### Option C — On-Premise

Air-gapped or on-premise deployment for government, defense, and highly regulated industries.

| Aspect | Detail |
|--------|--------|
| Dependencies | PostgreSQL, Redis, Docker — no external services required |
| AI | Can operate with local LLM deployment (Ollama) or without AI features |
| Updates | Perga release packages with documented migration scripts |
| Support | Dedicated on-premise support contract |

---

## 12. Competitive Landscape

### 12.1 Positioning

Perga occupies a unique white space in the market: **purpose-built SAP transformation management**
with embedded AI. No existing tool covers this full scope.

### 12.2 Competitive Comparison

| Capability | Perga | Jira / ADO | SAP Solution Manager | SAP Cloud ALM | Tricentis qTest |
|------------|-------|-----------|---------------------|--------------|----------------|
| SAP Activate phase management | ✅ Native | ❌ Workaround | ✅ Native | ✅ Native | ❌ |
| WRICEF backlog management | ✅ Full lifecycle | ⚠️ Generic | ⚠️ Basic | ❌ | ❌ |
| Fit-Gap workshop management | ✅ Full | ❌ | ⚠️ Basic | ⚠️ Basic | ❌ |
| Spec management (FS/TS) | ✅ With AI | ❌ | ❌ | ❌ | ❌ |
| Integration Factory | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| Data Factory / migration mgmt | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| Cutover Hub (runbook + rehearsal) | ✅ Full | ❌ | ❌ | ❌ | ❌ |
| Hypercare incident management | ✅ Full | ⚠️ Manual | ❌ | ❌ | ❌ |
| Embedded AI assistants | ✅ 13 (SAP domain) | ⚠️ Generic | ❌ | ⚠️ Limited | ❌ |
| End-to-end traceability | ✅ Automated | ⚠️ Manual links | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| Multi-tenant SaaS | ✅ | ✅ | ❌ (on-premise) | ✅ | ✅ |
| Transport CTS tracking | ✅ | ❌ | ✅ | ✅ | ❌ |
| Governance / sign-off workflows | ✅ SOX-grade | ❌ | ⚠️ Basic | ⚠️ Basic | ❌ |
| Executive auto-reporting | ✅ AI-generated | ❌ | ❌ | ❌ | ❌ |

### 12.3 Key Differentiators

1. **The only platform that manages the complete program across all SAP Activate phases in a single tool.**
   SAP Solution Manager and Cloud ALM focus primarily on Realize-phase activities. Perga
   covers Discover through Run.

2. **AI that knows SAP.** Jira + Copilot gives you generic AI. Perga's AI assistants are trained
   on SAP Best Practices, WRICEF patterns, and transformation-specific knowledge. The difference
   between "write a test case for a purchase order workflow" and generic AI output is the SAP
   domain context Perga brings.

3. **Traceability enforced by architecture, not discipline.** In every other tool, traceability
   is a manual, aspirational activity. In Perga, the data model makes it impossible to ship a
   WRICEF item that isn't linked to at least one requirement. Compliance reports are a query,
   not a weekend exercise.

4. **Cutover Hub.** No competitor offers structured go-live runbook management with dependency
   tracking, rehearsal comparison, and real-time execution tracking. This module alone has
   prevented multiple catastrophic go-live failures.

---

## 13. Business Value & ROI Model

### 13.1 Value Drivers

**1 — Consultant Productivity**

| Activity | Manual Time | With Perga | Saving |
|----------|------------|---------|--------|
| Fit-Gap workshop requirements classification | 4–6 days per module | 4–8 hours per module | ~80% |
| WRICEF functional spec writing | 4–8 hours per item | 1–2 hours per item | ~75% |
| Test case writing per requirement | 15–20 min per test case | 3–5 min per test case | ~75% |
| Steering committee report preparation | 5–8 hours per cycle | 30–45 min per cycle | ~85% |
| Defect triage | 20–30 min per defect | 3–5 min per defect | ~85% |
| Traceability matrix compilation | 2–3 days manual | Real-time, always current | ~100% |

**2 — Risk Reduction**

- Structured Fit-Gap traceability prevents requirements from being lost between Explore and Realize (a defect that historically costs 10× more to fix in UAT than in design)
- Co/No-Go framework prevents premature go-live decisions that lead to production incidents
- Hypercare incident management reduces time-to-resolution for P1 issues by 40–60%

**3 — Program Governance**

- Immutable audit trails for SOX/GDPR compliance reduce audit preparation effort
- Real-time RAID management prevents risks from staying unmanaged for weeks between steering meetings

### 13.2 ROI Illustration — Mid-Sized S/4HANA Transformation

**Program profile:** 18-month Greenfield S/4HANA implementation, 6 SAP modules, 80-person
team (20 Accenture/Deloitte consultants, 60 customer resources), €15M budget.

| Value Driver | Annual Saving Estimate |
|-------------|----------------------|
| Consultant time saved on specifications (20 consultants × 2 hrs/day × 220 days × €200/hr) | €1,760,000 |
| Test preparation time reduction (40% reduction on 3,000 test cases × 15 min × €100/hr) | €300,000 |
| Steering reporting automation (20 meetings × 6 hrs × €200/hr) | €24,000 |
| Avoided go-live incident (1 avoided P1 cutover incident) | €500,000 -- €5,000,000 |
| Requirement rework avoidance (5% fewer missed requirements at €50K avg cost to fix in build) | €250,000+ |
| **Total conservatively estimated value** | **€2.8M+ over program lifecycle** |

**Platform cost at enterprise tier:** €120,000–€250,000/year

**ROI:** >1,000% on a single program.

---

## 14. Target Market & Ideal Customer Profile

### 14.1 Primary Market Segments

**Segment 1 — System Integrators (SI) / Consulting Firms**

*Profile:* Accenture, Deloitte, IBM, Capgemini, NTT Data, and regional boutique SAP consultancies
running multiple concurrent S/4HANA rollouts.

*Value proposition:* A single, standardized platform that their consultants use across all client
engagements — accelerating delivery, reducing delivery risk, and differentiating their service
offering with AI-assisted methodology.

*Deal structure:* Enterprise license with per-program pricing. 10–50 simultaneous programs.

**Segment 2 — Enterprise End-Customers (Direct)**

*Profile:* Fortune 500 companies in manufacturing, chemical, FMCG, utilities, and public sector
running their own S/4HANA transformation.

*Value proposition:* Full ownership of program data, immediate go-live risk reduction, compliance
audit trail, and executive visibility without dependency on consultant tooling choices.

*Deal structure:* Annual SaaS subscription per tenant, per-program pricing tiers.

**Segment 3 — SAP-Aligned Partners**

*Profile:* SAP partner ecosystem members who need to differentiate on delivery excellence
and offer clients a structured, AI-assisted transformation methodology.

*Deal structure:* Reseller/white-label partnership model.

### 14.2 Ideal Customer Profile (ICP)

- SAP transformation program > €5M in total budget
- Go-live date within 18 months
- Team size > 30 people (functional consultants + IT + business)
- At least 2 SAP modules in scope
- Existing tooling is Excel-based (no coherent project management investment)
- PMO or program director sponsoring the engagement
- Regulated industry (manufacturing, pharma, financial services, public sector) — compliance value resonates

---

## 15. Roadmap

### Q1 2026 — Current State (Production-Ready)
- All 17 core modules live and tested
- 13 AI assistants operational
- Multi-tenant SaaS architecture deployed
- 2,191 automated tests passing
- E2E test plan (SAP Activate phases) complete

### Q2 2026 — Enterprise Hardening
- SAP Cloud ALM direct API integration (certified connector)
- Microsoft Teams deep integration (notification cards, action approvals in Teams)
- Advanced Analytics: predictive go-live risk scoring model (ML-based, trained on historical program data)
- Mobile UAT execution enhancements: AI-assisted screenshot analysis for defect evidence
- Multi-language support: English, German, Turkish (primary SAP implementation markets)

### Q3 2026 — Ecosystem Expansion
- Jira/Azure DevOps bidirectional sync (GA)
- SAP Transport Management System (TMS) API integration
- Document generation templates: exportable FDD, TS, UAT approval packages in Word/PDF
- Process Mining integration: import process flow data from Celonis/SAP Signavio for baseline analysis
- Customer community: shared knowledge base and best-practice library

### Q4 2026 — Intelligence Acceleration
- Program Health Prediction: AI model predicting go-live date slip risk 8 weeks in advance
- Automated Sprint Reprioritization: AI-driven sprint rebalancing based on dependency changes
- Cross-Program Benchmarking: anonymized industry benchmarks for effort, defect rates, and velocity
- SAP BTP Integration: deploy AI assistants as SAP BTP workload extensions

### 2027 — Platform Expansion
- SAP SuccessFactors HCM module (HR transformation programs)
- SAP Ariba / Procurement module support
- S/4HANA Finance consolidation (BPC migration)
- Partner marketplace: third-party process content packages (industry verticals: pharma GMP, utilities TOCO, retail OTC)

---

## 16. Conclusion

SAP transformations are mission-critical, extraordinarily expensive, and systematically
under-served by available tooling. The industry has accepted Excel runbooks, fragmented systems,
and manual reporting as the cost of doing business for 30 years. Perga changes this.

By combining purpose-built SAP domain models, a structured enforcement of the SAP Activate
methodology, end-to-end traceability as a data architecture constraint (not a reporting exercise),
and 13 embedded AI assistants with genuine SAP domain knowledge, Perga delivers something
the market has not seen before: a single platform that serves equally as the:

- **Program Manager's** central control cockpit
- **Consultant's** productivity accelerator
- **PMO's** governance enforcement tool
- **Steering Committee's** real-time visibility portal
- **Auditor's** compliance evidence repository

The platform is production-ready today. It is not a prototype or a roadmap pitch. It is a
fully tested, multi-tenant SaaS system with 103 database tables, 570 API endpoints, and
2,191 automated tests — built to enterprise standards from day one.

For a program team facing a €15M SAP transformation with an 18-month deadline and a steering
committee that meets every two weeks, Perga is not a nice-to-have. It is how you run the program
without missing a go-live.

---

## Appendix A — Module-to-SAP-Activate Phase Mapping

| Perga Module | Discover | Prepare | Explore | Realize | Deploy | Run |
|-------------|--------|--------|--------|--------|------|-----|
| Program Setup | ✅ Primary | ✅ | | | | |
| Scope & Requirements | | ✅ Primary | ✅ | | | |
| Explore Phase Manager | | | ✅ Primary | | | |
| Backlog Workbench (WRICEF) | | | ✅ | ✅ Primary | | |
| Test Hub | | | | ✅ Primary | ✅ | |
| RAID Module | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Integration Factory | | | ✅ | ✅ Primary | ✅ | |
| Data Factory | | | | ✅ Primary | ✅ | |
| Cutover Hub | | | | | ✅ Primary | |
| Governance & Audit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Transport CTS | | | | ✅ | ✅ Primary | |
| Executive Cockpit | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hypercare / Run & Sustain | | | | | | ✅ Primary |

---

## Appendix B — Supported SAP Modules

| Code | Module |
|------|--------|
| FI | Financial Accounting |
| CO | Controlling |
| MM | Materials Management |
| SD | Sales & Distribution |
| PP | Production Planning |
| QM | Quality Management |
| PM | Plant Maintenance |
| WM/EWM | Warehouse Management / Extended WM |
| HCM/SF | Human Capital Management / SuccessFactors |
| FICO | Finance & Controlling (combined) |
| BW/BPC | Business Warehouse / Business Planning & Consolidation |
| ABAP | Application Development |
| BASIS | Technical Administration |
| GRC | Governance, Risk & Compliance |
| BRIM | Billing & Revenue Innovation Management |
| BTP | Business Technology Platform |

---

## Appendix C — Glossary

| Term | Definition |
|------|-----------|
| **SAP Activate** | SAP's agile-hybrid implementation methodology for S/4HANA |
| **WRICEF** | Workflow, Report, Interface, Conversion, Enhancement, Form — SAP custom development categories |
| **Fit-Gap** | Analysis of whether a business requirement is covered by standard SAP (Fit) or requires custom development (Gap) |
| **Fit-to-Standard** | Workshop methodology used in SAP Activate Explore phase to assess standard vs. custom fit |
| **Go/No-Go** | Formal decision meeting immediately before cutover to approve or delay go-live |
| **Cutover** | The sequence of activities to transition business operations from the legacy system to S/4HANA |
| **Hypercare** | The post-go-live stabilization period (typically 4–8 weeks) with heightened support |
| **CTS** | SAP Change and Transport System — manages movement of configuration and code between SAP system landscapes |
| **RAG Status** | Red/Amber/Green — universal project health indicator |
| **RACI** | Responsible, Accountable, Consulted, Informed — project responsibility assignment model |
| **KPI** | Key Performance Indicator |
| **PMO** | Project Management Office |
| **SIT** | System Integration Testing |
| **UAT** | User Acceptance Testing |

---

*Document version 1.0 — Perga Platform Whitepaper — February 2026*
*Classification: Confidential — Investor and Customer Distribution Only*
