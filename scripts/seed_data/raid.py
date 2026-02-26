"""
Phase 7 — RAID: Risk, Action, Issue, Decision
Company: Anadolu Food & Beverage Inc.

 8 Risks     (probability x impact scoring, RAG)
10 Actions   (preventive, corrective, follow_up)
 6 Issues    (open, investigating, escalated, resolved, closed)
 8 Decisions (approved, pending_approval, proposed)
"""

# ═════════════════════════════════════════════════════════════════════════════
# RISKS — probability(1-5) x impact(1-5) -> score, rag_status auto-calculated
# ═════════════════════════════════════════════════════════════════════════════

RISK_DATA = [
    {"title": "Data migration delay risk — 60K material master data",
     "description": "Migration of 60,000 material records may not be completed within planned timeframe. BOM, recipe, shelf life data require complex transformation.",
     "status": "mitigating", "owner": "Hakan Gunes", "priority": "critical",
     "probability": 4, "impact": 5,
     "risk_category": "technical", "risk_response": "mitigate",
     "mitigation_plan": "Parallel migration approach: 3 teams, each handling 20K records. Delta migration strategy.",
     "contingency_plan": "Postpone go-live by 1 month. Migrate critical materials first.",
     "trigger_event": "If migration pilot test is below 80% at end of Sprint 3"},

    {"title": "GIB e-Invoice integration outage risk",
     "description": "e-Invoice/e-Waybill service may experience outages due to GIB infrastructure updates.",
     "status": "identified", "owner": "Zeynep Koc", "priority": "high",
     "probability": 3, "impact": 5,
     "risk_category": "external", "risk_response": "mitigate",
     "mitigation_plan": "Offline queue mechanism. During GIB outage, invoices queued and auto-sent when service returns.",
     "contingency_plan": "Prepare manual GIB portal invoice submission procedure.",
     "trigger_event": "GIB maintenance announcement or 30min+ timeout"},

    {"title": "Key user resource shortage",
     "description": "Key users cannot be freed from daily operations. Workshop attendance rate dropped to 65% during Explore phase.",
     "status": "mitigating", "owner": "Canan Ozturk", "priority": "high",
     "probability": 4, "impact": 4,
     "risk_category": "resource", "risk_response": "mitigate",
     "mitigation_plan": "Official management support letter. Key users 50% project allocation. Identify backup users.",
     "contingency_plan": "External consultant for key user support.",
     "trigger_event": "If workshop attendance rate drops below 70%"},

    {"title": "BTP CPI license and capacity limit risk",
     "description": "BTP CPI integration credits may be insufficient. 6 interfaces + e-Document heavy message traffic.",
     "status": "analysed", "owner": "Murat Celik", "priority": "medium",
     "probability": 2, "impact": 4,
     "risk_category": "commercial", "risk_response": "accept",
     "mitigation_plan": "Monitor current credit usage. Reduce message count via batch optimization.",
     "contingency_plan": "Purchase additional credit package (150K TRY budget reserved).",
     "trigger_event": "If credit usage exceeds 80%"},

    {"title": "Food regulation change — VAT rate update",
     "description": "Government may change food VAT rates. Updated 3 times in the last 2 years.",
     "status": "identified", "owner": "Ahmet Yildiz", "priority": "medium",
     "probability": 3, "impact": 3,
     "risk_category": "external", "risk_response": "accept",
     "mitigation_plan": "Tax codes designed as parameter-based. Change can be applied within 1 day.",
     "contingency_plan": "Emergency configuration change procedure and CAB fast approval flow.",
     "trigger_event": "If VAT rate change published in Official Gazette"},

    {"title": "Go-Live production freeze duration overrun risk",
     "description": "Production/shipping freeze during cutover may exceed planned 48 hours.",
     "status": "identified", "owner": "Kemal Erdogan", "priority": "critical",
     "probability": 3, "impact": 5,
     "risk_category": "schedule", "risk_response": "mitigate",
     "mitigation_plan": "2 cutover rehearsals planned. Duration optimized in each rehearsal. Parallel run scenario.",
     "contingency_plan": "Move go-live to extended holiday period (weekend + public holiday).",
     "trigger_event": "If cutover rehearsal 1 exceeds 48 hours"},

    {"title": "SOD (Segregation of Duties) violation risk",
     "description": "Segregation of duties principle may be violated in authorization role definitions. GRC analysis not yet started.",
     "status": "identified", "owner": "Murat Celik", "priority": "high",
     "probability": 3, "impact": 4,
     "risk_category": "organisational", "risk_response": "mitigate",
     "mitigation_plan": "GRC Access Control early implementation. SOD risk analysis to be completed mid-Realize phase.",
     "contingency_plan": "Define mitigating controls for temporary exceptions.",
     "trigger_event": "If high-risk SOD conflicts found in GRC analysis report"},

    {"title": "MES integration partner delay risk",
     "description": "MES-side API development done by 3rd party vendor. Timeline not under our control.",
     "status": "mitigating", "owner": "Zeynep Koc", "priority": "medium",
     "probability": 3, "impact": 3,
     "risk_category": "external", "risk_response": "mitigate",
     "mitigation_plan": "Weekly sync meeting with MES vendor. Parallel development with mock API.",
     "contingency_plan": "MES integration can be deferred to go-live+1 phase. Manual confirmation entry enabled.",
     "trigger_event": "If MES API milestone is delayed by 2 weeks"},
]

# ═════════════════════════════════════════════════════════════════════════════
# ACTIONS
# ═════════════════════════════════════════════════════════════════════════════

ACTION_DATA = [
    {"title": "Run data migration pilot — 1,000 materials",
     "description": "Pilot test of migration program with 1,000 records. Measure error rate and performance.",
     "status": "completed", "owner": "Hakan Gunes", "priority": "critical",
     "action_type": "preventive",
     "due_date": "2026-01-30", "completed_date": "2026-01-28"},

    {"title": "GIB test environment certificate renewal",
     "description": "GIB private integrator mTLS certificate expires 2026-02-28. Renewal application must be submitted.",
     "status": "in_progress", "owner": "Zeynep Koc", "priority": "high",
     "action_type": "preventive",
     "due_date": "2026-02-15"},

    {"title": "Key user allocation letter — management approval",
     "description": "Senior management approval letter for 50% project allocation of key users.",
     "status": "completed", "owner": "Canan Ozturk", "priority": "high",
     "action_type": "corrective",
     "due_date": "2026-01-15", "completed_date": "2026-01-12"},

    {"title": "Create BTP CPI credit usage dashboard",
     "description": "Monthly credit consumption monitoring dashboard. Alert threshold 80%.",
     "status": "open", "owner": "Murat Celik", "priority": "medium",
     "action_type": "detective",
     "due_date": "2026-02-28"},

    {"title": "Prepare cutover rehearsal 1 plan",
     "description": "First cutover rehearsal scenario. Step-by-step plan, success criteria, rollback procedure.",
     "status": "open", "owner": "Kemal Erdogan", "priority": "critical",
     "action_type": "preventive",
     "due_date": "2026-04-30"},

    {"title": "Create SOD risk matrix",
     "description": "SOD risk matrix with SAP GRC Access Control. Critical transaction conflicts.",
     "status": "open", "owner": "Murat Celik", "priority": "high",
     "action_type": "preventive",
     "due_date": "2026-03-31"},

    {"title": "MES API mock server setup",
     "description": "Parallel development with mock server until MES vendor API is ready.",
     "status": "completed", "owner": "Zeynep Koc", "priority": "medium",
     "action_type": "corrective",
     "due_date": "2026-01-20", "completed_date": "2026-01-18"},

    {"title": "Organize SIT Cycle 1 defect triage meeting",
     "description": "Root cause analysis and fix plan for P1/P2 defects after SIT C1.",
     "status": "completed", "owner": "Ayse Polat", "priority": "high",
     "action_type": "corrective",
     "due_date": "2026-03-22", "completed_date": "2026-03-22"},

    {"title": "UAT test scenario preparation — key user training",
     "description": "Training for key users on writing UAT test scenarios.",
     "status": "open", "owner": "Ayse Polat", "priority": "medium",
     "action_type": "preventive",
     "due_date": "2026-06-15"},

    {"title": "Training material preparation — end user guides",
     "description": "End user training guides for FI/MM/SD/PP modules (Turkish).",
     "status": "open", "owner": "Canan Ozturk", "priority": "medium",
     "action_type": "follow_up",
     "due_date": "2026-08-31"},
]

# ═════════════════════════════════════════════════════════════════════════════
# ISSUES
# ═════════════════════════════════════════════════════════════════════════════

ISSUE_DATA = [
    {"title": "QAS environment performance degradation — SIT slowness",
     "description": "Long-running HANA queries in QAS environment. SIT tests taking 2x the target duration.",
     "status": "investigating", "owner": "Murat Celik", "priority": "high",
     "severity": "major",
     "escalation_path": "Basis Lead -> SAP Support -> Architecture Board",
     "root_cause": "HANA memory allocation insufficient. Test data size close to production.",
     "resolution": ""},

    {"title": "e-Invoice GIB timeout issue — 60s exceeded",
     "description": "Continuous timeout on GIB test environment during SIT. Related to P1 defect (DEF-SD-001).",
     "status": "escalated", "owner": "Zeynep Koc", "priority": "critical",
     "severity": "critical",
     "escalation_path": "Integration Lead -> Architecture Board -> Steering Committee",
     "root_cause": "GIB test environment capacity limit + CPI retry mechanism missing",
     "resolution": ""},

    {"title": "Explore phase workshop decisions not documented",
     "description": "Decisions made in some Explore phase workshops not entered in official decision log. 8 workshops with gaps.",
     "status": "resolved", "owner": "Canan Ozturk", "priority": "medium",
     "severity": "moderate",
     "root_cause": "Workshop facilitators did not follow decision log procedure",
     "resolution": "Missing decisions documented retroactively. Procedure reminder training delivered.",
     "resolution_date": "2026-01-25"},

    {"title": "MES vendor API document missing — field mapping cannot be completed",
     "description": "API specification expected from MES vendor delayed by 2 weeks. INT-PP-001 blocked.",
     "status": "open", "owner": "Zeynep Koc", "priority": "high",
     "severity": "major",
     "escalation_path": "Integration Lead -> PMO -> Steering Committee"},

    {"title": "Vendor master data quality low — migration blocker",
     "description": "35% of 4,000 vendor records in ECC have missing or inconsistent address data.",
     "status": "investigating", "owner": "Hakan Gunes", "priority": "high",
     "severity": "major",
     "root_cause": "No data quality controls applied in ECC. 10+ years of dirty data accumulation."},

    {"title": "Fiori Launchpad access issue — some roles missing",
     "description": "30% of test users cannot access Fiori Launchpad. Catalog/group assignment missing.",
     "status": "resolved", "owner": "Murat Celik", "priority": "medium",
     "severity": "moderate",
     "root_cause": "Catalog reference missing in composite role definitions",
     "resolution": "Composite roles updated via PFCG, 12 catalog assignments added.",
     "resolution_date": "2026-02-05"},
]

# ═════════════════════════════════════════════════════════════════════════════
# DECISIONS
# ═════════════════════════════════════════════════════════════════════════════

DECISION_DATA = [
    {"title": "S/4HANA Cloud — Greenfield approach",
     "description": "Greenfield transformation selected over brownfield from existing ECC.",
     "status": "approved", "owner": "Kemal Erdogan", "priority": "critical",
     "decision_date": "2025-05-15", "decision_owner": "Osman Aydin (CEO)",
     "alternatives": "1. Brownfield (system conversion)\n2. Greenfield (new implementation)\n3. Selective data transition",
     "rationale": "15 years of ECC customization burden. Best practice processes with greenfield. Cloud roadmap alignment.",
     "impact_description": "All processes designed from scratch. Data migration required. 30% more effort but 40% lower TCO long-term.",
     "reversible": False},

    {"title": "e-Document integration: Via BTP CPI (direct GIB)",
     "description": "Direct GIB integration via BTP CPI instead of private integrator for e-Invoice/e-Waybill.",
     "status": "approved", "owner": "Zeynep Koc", "priority": "high",
     "decision_date": "2025-10-20", "decision_owner": "Zeynep Koc",
     "alternatives": "1. Private integrator (Foriba/Logo)\n2. BTP CPI direct GIB\n3. Hybrid (integrator + CPI)",
     "rationale": "No additional license cost. Full control. SAP roadmap alignment. Direct GIB UBL-TR 1.2.",
     "impact_description": "CPI development effort higher. However, 200K TRY annual integrator fee savings.",
     "reversible": True},

    {"title": "Production: Process type production order usage (PP-PI)",
     "description": "Process type production order (PP-PI) instead of discrete for food manufacturing.",
     "status": "approved", "owner": "Deniz Aydin", "priority": "high",
     "decision_date": "2025-11-10", "decision_owner": "Deniz Aydin",
     "alternatives": "1. Discrete production (PP)\n2. Process production (PP-PI)\n3. Mixed (some lines discrete, some process)",
     "rationale": "Food industry inherently process production. Recipe management, batch traceability, quality integration.",
     "impact_description": "PP-PI configuration complexity. Key user training additional 2 weeks.",
     "reversible": False},

    {"title": "Warehouse management: EWM usage (instead of WM)",
     "description": "Extended Warehouse Management (EWM) to be used instead of classic WM.",
     "status": "approved", "owner": "Gokhan Demir", "priority": "high",
     "decision_date": "2025-11-15", "decision_owner": "Gokhan Demir",
     "alternatives": "1. Stock Room Management (simple)\n2. Classic WM (compatibility mode)\n3. Embedded EWM (S/4 native)",
     "rationale": "8 warehouses, wave picking, put-away strategies required. WM deprecated in S/4. EWM is the future standard.",
     "impact_description": "EWM training period 3 weeks. However, S/4 roadmap alignment achieved.",
     "reversible": False},

    {"title": "Pricing: Channel-based condition type strategy",
     "description": "Channel-specific condition type structure for retail, wholesale, e-commerce channels.",
     "status": "approved", "owner": "Burak Sahin", "priority": "medium",
     "decision_date": "2025-12-01", "decision_owner": "Burak Sahin",
     "alternatives": "1. Single pricing procedure + condition table separation\n2. Separate procedure per channel\n3. Mixed: single procedure + channel condition types",
     "rationale": "Alternative 3 selected. Maintenance ease + channel flexibility. Reporting needs met.",
     "impact_description": "5 new custom condition types (ZK01-ZK05). Condition record maintenance by key users.",
     "reversible": True},

    {"title": "Data migration: LTMC (Migration Cockpit) usage",
     "description": "S/4 native Migration Cockpit (LTMC) to be used instead of LSMW for data migration.",
     "status": "approved", "owner": "Hakan Gunes", "priority": "medium",
     "decision_date": "2025-09-20", "decision_owner": "Hakan Gunes",
     "alternatives": "1. LSMW (legacy)\n2. LTMC / Migration Cockpit (native)\n3. 3rd party migration tool (SNP, Syniti)",
     "rationale": "LTMC is S/4 native, free, SAP supported. Standard templates available. LSMW deprecated in S/4.",
     "impact_description": "LTMC learning curve 2 weeks. However, fast start with standard templates.",
     "reversible": True},

    {"title": "Test management: In-platform test hub usage",
     "description": "In-platform test management module to be used instead of SAP Solution Manager.",
     "status": "approved", "owner": "Ayse Polat", "priority": "medium",
     "decision_date": "2025-10-05", "decision_owner": "Kemal Erdogan",
     "alternatives": "1. SAP Solution Manager Test Suite\n2. HP ALM / Micro Focus\n3. In-platform Test Hub module",
     "rationale": "Platform already manages test plan/cycle/case/execution/defect. No additional license needed.",
     "impact_description": "No additional integration required. SAP SolMan test reporting gap acceptable.",
     "reversible": True},

    {"title": "Authorization: Fiori Space/Page-based navigation",
     "description": "New Space/Page-based navigation instead of classic Fiori Group/Catalog.",
     "status": "pending_approval", "owner": "Murat Celik", "priority": "medium",
     "decision_date": None, "decision_owner": "Murat Celik",
     "alternatives": "1. Classic Fiori Catalog/Group\n2. Space/Page (new model)\n3. Hybrid: both together",
     "rationale": "SAP roadmap heading toward Space/Page. However, documentation still limited. Pilot start proposed.",
     "impact_description": "All roles must be redefined. Transition period requires 2 weeks additional effort.",
     "reversible": True},
]
