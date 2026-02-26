"""
Phase 4 — Requirements, Traces, Process Mappings, Open Items
Company: Anadolu Food & Beverage Inc.

25 Requirement (business, functional, technical, integration, non_functional)
14 Traces (requirement -> phase / workstream / scenario)
8  Requirement-Process Mappings (requirement -> L3 process)
6  Open Items (question, decision, dependency)
"""

REQUIREMENTS = [
    # -- Business Requirements --------------------------------------------------
    {"code": "REQ-BIZ-001", "title": "TFRS/VUK parallel accounting reporting",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "FI",
     "description": "TFRS and VUK compliant parallel financial statement generation. Consolidated balance sheet, income statement.",
     "source": "CFO"},
    {"code": "REQ-BIZ-002", "title": "Real-time inventory visibility across 8 plants",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "MM",
     "description": "Instant stock levels across all warehouses and plants. Minimum stock and shelf life alerts.",
     "source": "Logistics Director"},
    {"code": "REQ-BIZ-003", "title": "End-to-end order-to-cash process automation",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "Seamless process from customer order to collection. Average O2C cycle time < 5 days.",
     "source": "Commercial Director"},
    {"code": "REQ-BIZ-004", "title": "Production planning and MRP optimization (food industry)",
     "req_type": "business", "priority": "must_have", "status": "in_progress", "module": "PP",
     "description": "Shelf life based MRP, HACCP control integration. MRP run < 1 hour.",
     "source": "Production Director"},
    {"code": "REQ-BIZ-005", "title": "HACCP and food safety quality management",
     "req_type": "business", "priority": "must_have", "status": "approved", "module": "QM",
     "description": "Tracking critical control points in SAP QM. Certificate management.",
     "source": "Quality Director"},

    # -- Functional Requirements ------------------------------------------------
    {"code": "REQ-FI-001", "title": "VAT tax code configuration (1%, 10%, 20%)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "FI",
     "description": "Turkey VAT rates, SCT, PCST definitions. Food industry exemptions."},
    {"code": "REQ-FI-002", "title": "Bank integration (XML ISO 20022 + EFT)",
     "req_type": "functional", "priority": "should_have", "status": "approved", "module": "FI",
     "description": "Automatic payment with 8 banks, bank statement (MT940/camt.053), reconciliation."},
    {"code": "REQ-MM-001", "title": "Procurement approval workflow (4-tier)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "MM",
     "description": "Amount-based 4-tier approval: <TRY 25K, <TRY 100K, <TRY 500K, >=TRY 500K."},
    {"code": "REQ-MM-002", "title": "MRP -> automatic purchase order",
     "req_type": "functional", "priority": "should_have", "status": "in_progress", "module": "MM",
     "description": "Automatic PO creation from MRP proposals by vendor."},
    {"code": "REQ-SD-001", "title": "Pricing schema (15+ condition types)",
     "req_type": "functional", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "Different discount/bonus schemas per dealer, retail, and export channels."},
    {"code": "REQ-SD-002", "title": "Credit limit management and automatic block",
     "req_type": "functional", "priority": "should_have", "status": "draft", "module": "SD",
     "description": "Customer-based credit limit, overdue balance check, automatic block."},
    {"code": "REQ-PP-001", "title": "BOM and routing management — food production",
     "req_type": "functional", "priority": "must_have", "status": "in_progress", "module": "PP",
     "description": "Formulation-based BOM, co-product/by-product, lot traceability."},

    # -- Technical Requirements -------------------------------------------------
    {"code": "REQ-TEC-001", "title": "SAP BTP CPI — 18 interface development",
     "req_type": "technical", "priority": "must_have", "status": "approved", "module": "BTP",
     "description": "ERP <-> MES, WMS, TMS, bank, e-Document, EDI 18 interfaces. BTP CPI iFlow."},
    {"code": "REQ-TEC-002", "title": "Data migration — 10 master objects (~15M records)",
     "req_type": "technical", "priority": "must_have", "status": "in_progress", "module": "Migration",
     "description": "Customer, vendor, material, BOM, open item, inventory balance, fixed asset migration."},
    {"code": "REQ-TEC-003", "title": "Authorization matrix (80 roles, SOD control)",
     "req_type": "technical", "priority": "must_have", "status": "draft", "module": "Basis",
     "description": "80 SAP roles, segregation of duties (SOD) controls. Fiori app-based authorization."},

    # -- Integration Requirements -----------------------------------------------
    {"code": "REQ-INT-001", "title": "e-Invoice / e-Waybill / e-Archive GIB integration",
     "req_type": "integration", "priority": "must_have", "status": "approved", "module": "SD",
     "description": "GIB e-Document integration. UBL-TR 1.2 format. Outbound and inbound."},
    {"code": "REQ-INT-002", "title": "MES <-> SAP PP production integration",
     "req_type": "integration", "priority": "should_have", "status": "in_progress", "module": "PP",
     "description": "Production confirmations from MES, scrap/waste, OEE data. OData + CPI."},
    {"code": "REQ-INT-003", "title": "WMS <-> EWM inventory synchronization",
     "req_type": "integration", "priority": "should_have", "status": "draft", "module": "EWM",
     "description": "Warehouse transfer, goods receipt/issue synchronization with external WMS."},
    {"code": "REQ-INT-004", "title": "EDI — Retail chain order integration",
     "req_type": "integration", "priority": "should_have", "status": "draft", "module": "SD",
     "description": "EDIFACT order/shipment/invoice exchange with major retail chains."},

    # -- Non-Functional Requirements --------------------------------------------
    {"code": "REQ-NFR-001", "title": "System response time < 2 seconds (P95)",
     "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis",
     "description": "Online transactions P95 < 2s. Batch process performance targets defined."},
    {"code": "REQ-NFR-002", "title": "System availability >= 99.5% (uptime SLA)",
     "req_type": "non_functional", "priority": "must_have", "status": "approved", "module": "Basis",
     "description": "99.5% continuous operation guarantee excluding annual planned maintenance."},
]

# -- Traces: Requirement -> Phase / Workstream / Scenario ----------------------
TRACES = [
    # Business -> Explore phase
    {"req_code": "REQ-BIZ-001", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-002", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-003", "target_type": "phase", "target_name": "Explore", "trace_type": "derived_from"},
    {"req_code": "REQ-BIZ-004", "target_type": "phase", "target_name": "Realize", "trace_type": "implements"},
    # Functional -> Workstreams
    {"req_code": "REQ-FI-001", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
    {"req_code": "REQ-FI-002", "target_type": "workstream", "target_name": "Finance (FI/CO)", "trace_type": "implements"},
    {"req_code": "REQ-MM-001", "target_type": "workstream", "target_name": "Materials Management (MM)", "trace_type": "implements"},
    {"req_code": "REQ-SD-001", "target_type": "workstream", "target_name": "Sales & Distribution (SD)", "trace_type": "implements"},
    {"req_code": "REQ-PP-001", "target_type": "workstream", "target_name": "Production Planning (PP/QM)", "trace_type": "implements"},
    # Technical -> Scenarios
    {"req_code": "REQ-TEC-001", "target_type": "scenario", "target_name": "Information Technology and Infrastructure", "trace_type": "related_to"},
    {"req_code": "REQ-TEC-002", "target_type": "scenario", "target_name": "Information Technology and Infrastructure", "trace_type": "related_to"},
    # Integration -> BTP workstream
    {"req_code": "REQ-INT-001", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
    {"req_code": "REQ-INT-002", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
    {"req_code": "REQ-INT-003", "target_type": "workstream", "target_name": "Integration (BTP)", "trace_type": "implements"},
]

# -- Requirement <-> L3 Process Code Mappings -----------------------------------
RPM_DATA = [
    {"req_code": "REQ-SD-001", "l3_code": "1OC", "coverage_type": "full", "notes": "Pricing within VA01"},
    {"req_code": "REQ-SD-001", "l3_code": "4OC", "coverage_type": "partial", "notes": "Invoice pricing"},
    {"req_code": "REQ-FI-001", "l3_code": "1RR", "coverage_type": "full", "notes": "Tax codes in GL posting"},
    {"req_code": "REQ-FI-002", "l3_code": "1RR", "coverage_type": "partial", "notes": "Bank reconciliation"},
    {"req_code": "REQ-MM-001", "l3_code": "1PP", "coverage_type": "full", "notes": "PO approval workflow"},
    {"req_code": "REQ-MM-002", "l3_code": "1PP", "coverage_type": "full", "notes": "MRP -> automatic PO"},
    {"req_code": "REQ-PP-001", "l3_code": "1PM", "coverage_type": "partial", "notes": "MRP BOM integration"},
    {"req_code": "REQ-BIZ-005", "l3_code": "3PM", "coverage_type": "full", "notes": "QM HACCP process"},
]

# -- Open Items -----------------------------------------------------------------
OI_DATA = [
    {"req_code": "REQ-FI-002", "title": "Bank format not yet determined",
     "item_type": "question", "owner": "Finance Team", "priority": "high", "blocker": True, "status": "open",
     "description": "Which of the 8 banks will use MT940 and which will use camt.053? Format confirmation pending."},
    {"req_code": "REQ-SD-002", "title": "Credit limit approval level decision",
     "item_type": "decision", "owner": "Commercial Director", "priority": "high", "blocker": True, "status": "open",
     "description": "Which management level will approve when credit limit is exceeded?"},
    {"req_code": "REQ-TEC-002", "title": "Legacy data cleansing rules",
     "item_type": "dependency", "owner": "Hakan Gunes", "priority": "critical", "blocker": True, "status": "open",
     "description": "Master data cleansing rules from ECC are still pending."},
    {"req_code": "REQ-INT-001", "title": "GIB e-Invoice test environment certificate",
     "item_type": "dependency", "owner": "Murat Celik", "priority": "high", "blocker": False, "status": "in_progress",
     "description": "Digital certificate application for GIB test portal submitted, awaiting approval."},
    {"req_code": "REQ-BIZ-004", "title": "MRP shelf life parameters",
     "item_type": "question", "owner": "Deniz Aydin", "priority": "medium", "blocker": False, "status": "in_progress",
     "description": "What should the minimum remaining shelf life threshold values be for food products?"},
    {"req_code": "REQ-BIZ-001", "title": "TFRS 16 lease accounting scope decision",
     "item_type": "decision", "owner": "CFO", "priority": "medium", "blocker": False, "status": "resolved",
     "resolution": "Deferred to Phase 2. Out of current scope."},
]
