"""
Phase 6 — Functional Specs, Technical Specs, Test Plans/Cycles/Cases,
           Test Suites, Test Steps, Test Executions, Defects
Company: Anadolu Food & Beverage Inc.

10 Functional Specs  (for WRICEF & Config items)
 8 Technical Specs   (1:1 linked to FS)
 2 Test Plans        (SIT, UAT)
 4 Test Cycles       (SIT-C1, SIT-C2, UAT-C1, Regression)
 3 Test Suites       (SIT-Finance, UAT-Logistics, Regression-Core)
18 Test Cases        (module-based, assigned to suites)
36 Test Steps        (2 detailed steps per TC)
18 Test Executions   (for SIT-C1 cycle)
 8 Defects           (P1->P4)
"""

# ═════════════════════════════════════════════════════════════════════════════
# FUNCTIONAL SPECS — linked via backlog_code or config_code
# ═════════════════════════════════════════════════════════════════════════════

FS_DATA = [
    # ── WRICEF Functional Specs ──
    {"backlog_code": "WF-MM-001", "config_code": None,
     "title": "FS — Purchase Order Approval Workflow",
     "description": "4-tier amount-based approval WF. SAP Business Workflow + BRF+ rules engine.",
     "content": "## 1. Overview\n4-tier purchase order approval...\n## 2. Business Rules\n- <25K TRY: Automatic\n- <100K TRY: Department Manager\n- <500K TRY: Director\n- >=500K TRY: CEO",
     "version": "2.0", "status": "approved", "author": "Elif Kara",
     "reviewer": "Deniz Aydin", "approved_by": "Kemal Erdogan"},
    {"backlog_code": "INT-SD-001", "config_code": None,
     "title": "FS — e-Invoice / e-Waybill GIB Interface",
     "description": "GIB e-Document interface in UBL-TR 1.2 format. BTP CPI iFlow design.",
     "content": "## 1. Interface Summary\nGIB e-Invoice/e-Waybill outbound/inbound...\n## 2. Message Structure\nUBL-TR Invoice 2.1\n## 3. Error Handling\nGIB timeout -> retry 3x",
     "version": "1.1", "status": "approved", "author": "Zeynep Koc",
     "reviewer": "Burak Sahin", "approved_by": "Kemal Erdogan"},
    {"backlog_code": "ENH-FI-001", "config_code": None,
     "title": "FS — Automatic Tax Calculation BAdI",
     "description": "VAT + SCT + PCST calculation. VAT 1%/10% distinction for food products.",
     "content": "## 1. Tax Rules\n- Basic food: VAT 1%\n- Processed food: VAT 10%\n- Beverages: VAT 20% + PCST\n## 2. BAdI: TAX_CALC_ENHANCE",
     "version": "1.0", "status": "approved", "author": "Ahmet Yildiz",
     "reviewer": "Elif Kara", "approved_by": "Kemal Erdogan"},
    {"backlog_code": "RPT-FI-001", "config_code": None,
     "title": "FS — Consolidated Balance Sheet Report (TFRS/VUK)",
     "description": "Multi-company code consolidation. TFRS and VUK parallel reporting.",
     "content": "## 1. Reporting Requirements\n3 company code consolidation\n## 2. Parameters\nCompany code, period, reporting standard",
     "version": "1.0", "status": "in_review", "author": "Ahmet Yildiz",
     "reviewer": "Kemal Erdogan"},
    {"backlog_code": "CNV-MD-001", "config_code": None,
     "title": "FS — Customer Master Data Migration",
     "description": "ECC KNA1/KNVV -> S/4 Business Partner. 15,000 active customers.",
     "content": "## 1. Source System\nECC — KNA1, KNVV, KNB1, KNVK\n## 2. Target\nS/4 BP — BUT000, BUT020, BUT050\n## 3. Conversion Rules\n- KUNNR -> BP_NUMBER\n- Customer group -> BP Role",
     "version": "1.0", "status": "approved", "author": "Hakan Gunes",
     "reviewer": "Burak Sahin", "approved_by": "Kemal Erdogan"},
    {"backlog_code": "INT-PP-001", "config_code": None,
     "title": "FS — MES -> SAP PP Production Confirmation Interface",
     "description": "Production confirmation and scrap reporting from MES. OData API + BTP CPI.",
     "content": "## 1. Interface Type\nMES -> SAP (inbound)\n## 2. Protocol\nOData V4 API\n## 3. Data\nProduction order no, operation, quantity, scrap, lot",
     "version": "1.0", "status": "draft", "author": "Zeynep Koc",
     "reviewer": "Deniz Aydin"},
    {"backlog_code": "ENH-MM-001", "config_code": None,
     "title": "FS — Shelf Life Control FIFO/FEFO",
     "description": "Automatic FIFO/FEFO lot selection rules for food products.",
     "content": "## 1. Rule\nShelf life < 25% remaining -> block\n## 2. Lot Selection\nFEFO: Nearest expiry date first\n## 3. Alert\nExpiry < 30 days -> automatic alert",
     "version": "1.0", "status": "in_review", "author": "Elif Kara",
     "reviewer": "Gokhan Demir"},

    # ── Config Functional Specs ──
    {"backlog_code": None, "config_code": "CFG-FI-003",
     "title": "FS — VAT Tax Codes Configuration",
     "description": "VAT 1%, 10%, 20%, exempt tax codes IMG configuration document.",
     "content": "## 1. Tax Codes\n- V1: VAT 1% (basic food)\n- V2: VAT 10% (processed food)\n- V3: VAT 20%\n- V0: VAT exempt",
     "version": "1.0", "status": "approved", "author": "Ahmet Yildiz",
     "reviewer": "Elif Kara", "approved_by": "Kemal Erdogan"},
    {"backlog_code": None, "config_code": "CFG-SD-002",
     "title": "FS — Pricing Procedure ZPRC01",
     "description": "Food industry pricing procedure. Channel-based condition types.",
     "content": "## 1. Procedure\nZPRC01 — Anadolu Food Pricing\n## 2. Condition Types\nZPR0: Base price\nZK01: Channel discount\nZM01: Quantity discount\nMWST: VAT",
     "version": "1.0", "status": "draft", "author": "Burak Sahin",
     "reviewer": "Deniz Aydin"},
    {"backlog_code": None, "config_code": "CFG-BASIS-001",
     "title": "FS — Authorization Role Definition (Fiori + SOD)",
     "description": "Fiori Launchpad roles, SOD control, catalog/group structure.",
     "content": "## 1. Role Structure\nSingle: Z_FI_*, Z_MM_*, Z_SD_*\nComposite: Z_COMP_*\n## 2. Fiori\nCatalog -> Group -> Space/Page\n## 3. SOD\nGRC risk analysis rules",
     "version": "1.0", "status": "draft", "author": "Murat Celik",
     "reviewer": "Zeynep Koc"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TECHNICAL SPECS — fs_key = backlog_code or config_code (matches FS)
# ═════════════════════════════════════════════════════════════════════════════

TS_DATA = [
    {"fs_key": "WF-MM-001",
     "title": "TS — Purchase Approval WF Technical Design",
     "description": "Workflow template WS9900, BRF+ application ZMM_APPROVAL_RULES.",
     "content": "## Objects\n- WF Template: WS99000001\n- BRF+ App: ZMM_APPROVAL_RULES\n- Task: TS99000001 (approval decision)\n## Unit Test\nSWEL monitoring active, 4-tier test scenario",
     "version": "1.0", "status": "approved", "author": "Elif Kara",
     "objects_list": "WS99000001, TS99000001, ZMM_APPROVAL_RULES, ZCL_MM_WF_HANDLER",
     "unit_test_evidence": "SWEL log — 12 test case pass"},
    {"fs_key": "INT-SD-001",
     "title": "TS — e-Invoice GIB Interface Technical Design",
     "description": "BTP CPI iFlow, IDoc -> UBL-TR conversion, GIB API integration.",
     "content": "## Objects\n- iFlow: IF_EINVOICE_OUT, IF_EINVOICE_IN\n- Mapping: MM_IDOC2UBL, MM_UBL2IDOC\n## Security\nmTLS certificate, GIB test environment",
     "version": "1.0", "status": "approved", "author": "Zeynep Koc",
     "objects_list": "IF_EINVOICE_OUT, IF_EINVOICE_IN, MM_IDOC2UBL, ZSD_EINVOICE_PROXY",
     "unit_test_evidence": "CPI monitoring — 50 test message pass"},
    {"fs_key": "ENH-FI-001",
     "title": "TS — Tax Calculation BAdI Technical Design",
     "description": "Enhancement implementation: ZCL_TAX_CALC, BAdI TAX_CALC_ENHANCE.",
     "content": "## Objects\n- BAdI Impl: ZCL_TAX_CALC\n- Tax Procedure: ZTAXTR\n## Table\n- ZTAX_FOOD_MAP: Material group -> VAT rate",
     "version": "1.0", "status": "approved", "author": "Ahmet Yildiz",
     "objects_list": "ZCL_TAX_CALC, ZTAXTR, ZTAX_FOOD_MAP, ZFM_TAX_DETERMINE",
     "unit_test_evidence": "ABAP Unit — 8 method, 24 assert pass"},
    {"fs_key": "RPT-FI-001",
     "title": "TS — Consolidated Balance Sheet Report Technical Design",
     "description": "CDS View + Fiori Elements analytical list page.",
     "content": "## Objects\n- CDS: ZI_BALANCE_SHEET, ZC_BALANCE_CONS\n- OData: ZSB_BALANCESHEET\n- Fiori App: zfi_balance_cons",
     "version": "1.0", "status": "in_review", "author": "Ahmet Yildiz",
     "objects_list": "ZI_BALANCE_SHEET, ZC_BALANCE_CONS, ZSB_BALANCESHEET"},
    {"fs_key": "CNV-MD-001",
     "title": "TS — Customer Master Data Migration Technical Design",
     "description": "LTMC template, migration cockpit, mapping program.",
     "content": "## Objects\n- LTMC Project: ZMIG_CUSTOMER\n- Template: S4_BP_CUSTOMER\n- Mapping: ZCL_MIG_CUST_MAP",
     "version": "1.0", "status": "approved", "author": "Hakan Gunes",
     "objects_list": "ZMIG_CUSTOMER, ZCL_MIG_CUST_MAP, ZTMP_CUSTOMER_STG",
     "unit_test_evidence": "100 record dry-run — 98 successful, 2 errors fixed"},
    {"fs_key": "INT-PP-001",
     "title": "TS — MES Production Confirmation Interface Technical Design",
     "description": "Custom OData API + CPI iFlow. MES XML -> SAP JSON conversion.",
     "content": "## Objects\n- OData: ZAPI_PRODCONFIRM\n- CPI iFlow: IF_MES_PRODCONF\n- BAPI: BAPI_PRODORDCONF_CREATE_TT",
     "version": "1.0", "status": "draft", "author": "Zeynep Koc",
     "objects_list": "ZAPI_PRODCONFIRM, IF_MES_PRODCONF"},
    {"fs_key": "CFG-FI-003",
     "title": "TS — VAT Tax Codes Technical Configuration",
     "description": "Tax procedure ZTAXTR condition records details.",
     "content": "## Configuration Steps\n- FTXP: V1, V2, V3, V0 codes\n- Tax Procedure: ZTAXTR\n- Condition: MWST -> V1/V2/V3/V0",
     "version": "1.0", "status": "approved", "author": "Ahmet Yildiz",
     "objects_list": "ZTAXTR, V1, V2, V3, V0"},
    {"fs_key": "ENH-MM-001",
     "title": "TS — Shelf Life FIFO/FEFO Technical Design",
     "description": "EWM lot selection strategy + shelf life BAdI.",
     "content": "## Objects\n- BAdI: ZCL_SHELF_LIFE_CHECK\n- EWM Strategy: ZFEFO\n- Alert: ZSHELF_LIFE_WARN",
     "version": "1.0", "status": "draft", "author": "Elif Kara",
     "objects_list": "ZCL_SHELF_LIFE_CHECK, ZFEFO"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST PLANS + CYCLES
# ═════════════════════════════════════════════════════════════════════════════

TEST_PLAN_DATA = [
    {
        "name": "SIT Master Plan — Integrated System Test",
        "description": "System Integration Test. Integrated test plan covering all E2E processes.",
        "status": "active",
        "test_strategy": "Module-based SIT -> cross-module integration. P1/P2 defect zero target.",
        "entry_criteria": "Unit tests pass, configuration complete, test data ready",
        "exit_criteria": "P1/P2=0, pass rate >= 95%, all E2E scenarios tested",
        "start_date": "2026-03-01", "end_date": "2026-05-31",
        "cycles": [
            {"name": "SIT Cycle 1 — Core Flows", "test_layer": "sit",
             "status": "completed", "start_date": "2026-03-01", "end_date": "2026-03-21"},
            {"name": "SIT Cycle 2 — Bug Fix & Regression", "test_layer": "sit",
             "status": "in_progress", "start_date": "2026-03-24", "end_date": "2026-04-11"},
        ],
    },
    {
        "name": "UAT Plan — User Acceptance Test",
        "description": "Business scenario-based acceptance test by end users.",
        "status": "draft",
        "test_strategy": "Business scenario-based test. Key users manage.",
        "entry_criteria": "SIT completed, P1/P2=0, training delivered",
        "exit_criteria": "All business scenarios approved, UAT sign-off signed",
        "start_date": "2026-07-01", "end_date": "2026-08-31",
        "cycles": [
            {"name": "UAT Cycle 1 — Business Scenarios", "test_layer": "uat",
             "status": "planning", "start_date": "2026-07-01", "end_date": "2026-07-31"},
            {"name": "Regression Cycle — Pre Go-Live", "test_layer": "regression",
             "status": "planning", "start_date": "2026-10-01", "end_date": "2026-10-15"},
        ],
    },
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST CASES — linked to requirement via req_code
# ═════════════════════════════════════════════════════════════════════════════

TEST_CASE_DATA = [
    # ── FI ──
    {"code": "TC-FI-001", "title": "Purchase invoice posting and 3-way matching",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-FI-001",
     "preconditions": "Vendor, material, PO, GR exist",
     "test_steps": "1. Enter invoice via MIRO\n2. Match with PO and GR\n3. Amount variance check\n4. Account posting verification",
     "expected_result": "Invoice approved via 3-way match, accounting entries correct",
     "is_regression": True},
    {"code": "TC-FI-002", "title": "VAT calculation — food products 1% / 10% / 20%",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-FI-001",
     "preconditions": "Tax codes V1/V2/V3 configured",
     "test_steps": "1. Sales invoice with basic food (1%)\n2. Processed food (10%)\n3. Beverage (20% + PCST)\n4. Exempt product",
     "expected_result": "Correct VAT rate calculated for each product type",
     "is_regression": True},
    {"code": "TC-FI-003", "title": "Consolidated balance sheet report — 3 company codes",
     "module": "FI", "test_layer": "sit", "status": "approved", "priority": "high",
     "req_code": "REQ-BIZ-001",
     "preconditions": "FI entries exist in 3 company codes",
     "test_steps": "1. Run report (TFRS)\n2. Consolidation check\n3. VUK version\n4. Currency conversion validation",
     "expected_result": "Consolidated balance correct, TFRS/VUK parallel"},

    # ── MM ──
    {"code": "TC-MM-001", "title": "Purchase order creation and 4-tier approval",
     "module": "MM", "test_layer": "sit", "status": "approved", "priority": "critical",
     "req_code": "REQ-MM-001",
     "preconditions": "Vendor, material, info record exist, WF active",
     "test_steps": "1. Create PO via ME21N (<25K TRY)\n2. Verify automatic approval\n3. Create 200K TRY PO -> director approval\n4. 600K TRY PO -> CEO approval",
     "expected_result": "Routed to correct approver at each amount tier",
     "is_regression": True},
    {"code": "TC-MM-002", "title": "Shelf life control — FEFO lot selection",
     "module": "MM", "test_layer": "sit", "status": "approved", "priority": "high",
     "req_code": "REQ-MM-002",
     "preconditions": "Lots with different expiry dates in stock",
     "test_steps": "1. Select material for shipment\n2. Suggest lot via FEFO rule\n3. Expiry < 30 days -> block check\n4. FIFO alternative",
     "expected_result": "Nearest expiry lot suggested first, short expiry blocked"},
    {"code": "TC-MM-003", "title": "Material master data migration validation (60K records)",
     "module": "MM", "test_layer": "sit", "status": "ready", "priority": "critical",
     "req_code": "REQ-TEC-002",
     "preconditions": "Migration program executed, staging table loaded",
     "test_steps": "1. Validate record count\n2. Material type mapping check\n3. BOM validation\n4. Recipe validation",
     "expected_result": "60K records migrated successfully, error rate < 0.5%"},

    # ── SD ──
    {"code": "TC-SD-001", "title": "Order-to-Cash E2E — order -> delivery -> invoice",
     "module": "SD", "test_layer": "uat", "status": "approved", "priority": "critical",
     "req_code": "REQ-SD-001",
     "preconditions": "Customer, material, pricing conditions exist",
     "test_steps": "1. VA01 sales order\n2. VL01N delivery\n3. PGI goods issue\n4. VF01 invoice\n5. Accounting entry check",
     "expected_result": "Order->delivery->invoice->accounting flow seamless",
     "is_regression": True},
    {"code": "TC-SD-002", "title": "e-Invoice GIB submission and response check",
     "module": "SD", "test_layer": "uat", "status": "approved", "priority": "critical",
     "req_code": "REQ-INT-001",
     "preconditions": "GIB test environment connection active, certificate valid",
     "test_steps": "1. Create invoice via VF01\n2. Trigger e-Invoice\n3. UBL-TR XML check\n4. GIB response (accept/reject)\n5. Waybill submission",
     "expected_result": "Successful submission to GIB, acceptance response received",
     "is_regression": True},
    {"code": "TC-SD-003", "title": "Channel-based pricing conditions",
     "module": "SD", "test_layer": "uat", "status": "in_review", "priority": "high",
     "req_code": "REQ-SD-001",
     "preconditions": "ZPRC01 procedure, channel condition types configured",
     "test_steps": "1. Retail channel order (ZK01)\n2. Wholesale channel order\n3. E-commerce channel\n4. Discount calculation",
     "expected_result": "Correct price and discount applied per channel"},

    # ── PP/QM ──
    {"code": "TC-PP-001", "title": "Plan-to-Produce E2E — MRP -> production order -> confirmation",
     "module": "PP", "test_layer": "uat", "status": "in_review", "priority": "critical",
     "req_code": "REQ-PP-001",
     "preconditions": "BOM, recipe, work center, MRP parameters ready",
     "test_steps": "1. Run MD01 MRP\n2. Planned order -> production order\n3. Release order\n4. Enter confirmation\n5. Cost calculation",
     "expected_result": "MRP creates correct planned order, production order completed"},
    {"code": "TC-PP-002", "title": "MES -> SAP production confirmation interface test",
     "module": "PP", "test_layer": "e2e", "status": "ready", "priority": "high",
     "req_code": "REQ-INT-002",
     "preconditions": "MES connection active, test production order released",
     "test_steps": "1. Send confirmation message from MES\n2. Create confirmation via BAPI in SAP\n3. Verify scrap quantity\n4. Error message check",
     "expected_result": "MES confirmation successfully transferred to SAP"},
    {"code": "TC-QM-001", "title": "HACCP checkpoint inspection triggering",
     "module": "QM", "test_layer": "e2e", "status": "draft", "priority": "high",
     "req_code": "REQ-NFR-001",
     "preconditions": "Inspection plan, HACCP checkpoints defined",
     "test_steps": "1. Post goods receipt (food raw material)\n2. Automatic inspection lot check\n3. Enter HACCP result\n4. Accept/reject decision",
     "expected_result": "Automatic inspection triggered on food raw material receipt"},

    # ── EWM ──
    {"code": "TC-EWM-001", "title": "Warehouse shipping process — wave picking",
     "module": "EWM", "test_layer": "e2e", "status": "draft", "priority": "high",
     "req_code": "REQ-BIZ-003",
     "preconditions": "Warehouse structure, shelf types, strategies defined",
     "test_steps": "1. Create outbound delivery\n2. Assign wave\n3. Start picking task\n4. Confirmation and PGI",
     "expected_result": "Wave picking works correctly, stock movement reflected in SAP"},

    # ── Integration ──
    {"code": "TC-INT-001", "title": "Bank statement (MT940) import test",
     "module": "FI", "test_layer": "e2e", "status": "in_review", "priority": "medium",
     "req_code": "REQ-INT-003",
     "preconditions": "Bank connection configured, electronic bank statement active",
     "test_steps": "1. Upload MT940 file\n2. Run automatic matching\n3. Check unmatched items\n4. Account balance validation",
     "expected_result": "MT940 parsed successfully, automatic matching >= 90%"},

    # ── Cross-Module (E2E) ──
    {"code": "TC-E2E-001", "title": "Procure-to-Pay full flow integration test",
     "module": "MM", "test_layer": "regression", "status": "approved", "priority": "critical",
     "req_code": "REQ-MM-001",
     "preconditions": "All MM/FI configuration completed",
     "test_steps": "1. Purchase requisition\n2. Create PO + approval WF\n3. Goods receipt\n4. Invoice receipt (MIRO)\n5. Payment (F110)\n6. Accounting check",
     "expected_result": "PR->PO->GR->IR->Payment flow seamless",
     "is_regression": True},
    {"code": "TC-E2E-002", "title": "Record-to-Report month-end closing test",
     "module": "FI", "test_layer": "regression", "status": "ready", "priority": "high",
     "req_code": "REQ-FI-002",
     "preconditions": "Intra-month FI entries exist",
     "test_steps": "1. Accrual entries\n2. Run depreciation\n3. FX revaluation\n4. Period close\n5. Reporting check",
     "expected_result": "Month-end closing procedure < 4 hours, reports correct"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTIONS — SIT Cycle 1 results
# ═════════════════════════════════════════════════════════════════════════════

EXECUTION_DATA = [
    {"tc_code": "TC-FI-001", "result": "pass", "executed_by": "Ahmet Yildiz",
     "duration_minutes": 25, "notes": "3-way match worked without issues"},
    {"tc_code": "TC-FI-002", "result": "pass", "executed_by": "Ahmet Yildiz",
     "duration_minutes": 30, "notes": "VAT 1%/10%/20% all calculated correctly"},
    {"tc_code": "TC-FI-003", "result": "fail", "executed_by": "Ahmet Yildiz",
     "duration_minutes": 45, "notes": "2nd company code currency conversion error -> DEF-FI-001"},
    {"tc_code": "TC-MM-001", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 35, "notes": "4-tier approval completed"},
    {"tc_code": "TC-MM-002", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 20, "notes": "FEFO lot selection working correctly"},
    {"tc_code": "TC-MM-003", "result": "blocked", "executed_by": "Hakan Gunes",
     "duration_minutes": 10, "notes": "Migration data not yet loaded -> blocked"},
    {"tc_code": "TC-SD-001", "result": "pass", "executed_by": "Burak Sahin",
     "duration_minutes": 40, "notes": "OTC E2E completed without issues"},
    {"tc_code": "TC-SD-002", "result": "fail", "executed_by": "Zeynep Koc",
     "duration_minutes": 60, "notes": "GIB response timeout -> DEF-SD-001"},
    {"tc_code": "TC-SD-003", "result": "pass", "executed_by": "Burak Sahin",
     "duration_minutes": 25, "notes": "Channel pricing correct"},
    {"tc_code": "TC-PP-001", "result": "pass", "executed_by": "Deniz Aydin",
     "duration_minutes": 50, "notes": "MRP -> production order -> confirmation flow complete"},
    {"tc_code": "TC-PP-002", "result": "fail", "executed_by": "Zeynep Koc",
     "duration_minutes": 30, "notes": "MES scrap quantity came negative -> DEF-PP-001"},
    {"tc_code": "TC-QM-001", "result": "pass", "executed_by": "Deniz Aydin",
     "duration_minutes": 20, "notes": "HACCP inspection triggered automatically"},
    {"tc_code": "TC-EWM-001", "result": "pass", "executed_by": "Gokhan Demir",
     "duration_minutes": 35, "notes": "Wave picking seamless"},
    {"tc_code": "TC-INT-001", "result": "deferred", "executed_by": "Zeynep Koc",
     "duration_minutes": 5, "notes": "Bank test environment not yet ready"},
    {"tc_code": "TC-E2E-001", "result": "pass", "executed_by": "Elif Kara",
     "duration_minutes": 55, "notes": "P2P full flow successful"},
    {"tc_code": "TC-E2E-002", "result": "fail", "executed_by": "Ahmet Yildiz",
     "duration_minutes": 40, "notes": "Depreciation calculation deviation -> DEF-FI-002"},
    {"tc_code": "TC-FI-001", "result": "pass", "executed_by": "Ayse Polat",
     "duration_minutes": 20, "notes": "Regression — approved"},
    {"tc_code": "TC-SD-001", "result": "pass", "executed_by": "Ayse Polat",
     "duration_minutes": 35, "notes": "Regression — OTC retest"},
]

# ═════════════════════════════════════════════════════════════════════════════
# DEFECTS — linked to test case via tc_code
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_DATA = [
    {"code": "DEF-FI-001", "title": "Consolidated balance sheet — 2nd company code currency conversion error",
     "tc_code": "TC-FI-003", "module": "FI", "severity": "S2", "status": "resolved",
     "environment": "QAS",
     "description": "Company code 2000 (USD-based) currency conversion uses wrong exchange rate.",
     "steps_to_reproduce": "1. Run ZFI_BALANCE\n2. Select company code 2000\n3. Consolidate -> EUR line incorrect",
     "reported_by": "Ahmet Yildiz", "assigned_to": "Ahmet Yildiz",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "CDS view ZI_BALANCE_SHEET exchange rate conversion logic fixed",
     "root_cause": "Fixed exchange rate used instead of TCURR exchange rate table",
     "reopen_count": 0},
    {"code": "DEF-SD-001", "title": "e-Invoice GIB response timeout — 60s exceeded",
     "tc_code": "TC-SD-002", "module": "SD", "severity": "S1", "status": "in_progress",
     "environment": "QAS",
     "description": "60 second timeout on e-invoice submission to GIB test environment.",
     "steps_to_reproduce": "1. Create invoice via VF01\n2. Trigger e-Invoice\n3. Wait 60 seconds -> timeout error",
     "reported_by": "Zeynep Koc", "assigned_to": "Zeynep Koc",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-PP-001", "title": "MES scrap quantity sending negative value",
     "tc_code": "TC-PP-002", "module": "PP", "severity": "S2", "status": "new",
     "environment": "QAS",
     "description": "Scrap quantity field from MES system contains negative value.",
     "steps_to_reproduce": "1. Send production confirmation from MES\n2. Scrap = -5 received\n3. BAPI returned error",
     "reported_by": "Zeynep Koc", "assigned_to": "Deniz Aydin",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-FI-002", "title": "Depreciation calculation deviation — rounding error",
     "tc_code": "TC-E2E-002", "module": "FI", "severity": "S3", "status": "resolved",
     "environment": "QAS",
     "description": "0.01 TRY rounding difference in fixed asset depreciation.",
     "steps_to_reproduce": "1. Run AFAB\n2. Check asset 10001 -> 0.01 difference",
     "reported_by": "Ahmet Yildiz", "assigned_to": "Ahmet Yildiz",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "Rounding rule updated to ROUND_HALF_UP",
     "root_cause": "Python-style banker's rounding was being used",
     "reopen_count": 0},
    {"code": "DEF-MM-001", "title": "FEFO lot selection — no prioritization for lots with same expiry",
     "tc_code": "TC-MM-002", "module": "MM", "severity": "S4", "status": "new",
     "environment": "QAS",
     "description": "When 2 lots have the same expiry date, random selection occurs, FIFO secondary rule not applied.",
     "reported_by": "Elif Kara", "assigned_to": "Gokhan Demir",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-SD-002", "title": "Delivery note form barcode not printing",
     "tc_code": "TC-SD-001", "module": "SD", "severity": "S3", "status": "retest",
     "environment": "QAS",
     "description": "EAN-13 barcode field empty in Adobe Form delivery note.",
     "steps_to_reproduce": "1. Create delivery via VL01N\n2. Print delivery note\n3. Barcode field empty",
     "reported_by": "Burak Sahin", "assigned_to": "Burak Sahin",
     "found_in_cycle": "SIT Cycle 1",
     "resolution": "Barcode font mapping added in Adobe Form",
     "root_cause": "BC417 barcode font not uploaded to server"},
    {"code": "DEF-EWM-001", "title": "Wave picking — large order split error",
     "tc_code": "TC-EWM-001", "module": "EWM", "severity": "S3", "status": "new",
     "environment": "QAS",
     "description": "Wave split not working properly for orders with 500+ items.",
     "reported_by": "Gokhan Demir", "assigned_to": "Gokhan Demir",
     "found_in_cycle": "SIT Cycle 1"},
    {"code": "DEF-INT-001", "title": "CPI iFlow — retry mechanism not working",
     "tc_code": "TC-SD-002", "module": "BC", "severity": "S2", "status": "in_progress",
     "environment": "QAS",
     "description": "Retry mechanism not triggered after GIB timeout in BTP CPI iFlow.",
     "steps_to_reproduce": "1. Send e-Invoice\n2. GIB timeout\n3. Retry 0/3 — retry not triggered",
     "reported_by": "Zeynep Koc", "assigned_to": "Zeynep Koc",
     "found_in_cycle": "SIT Cycle 1"},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITES — Test Case groups  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

SUITE_DATA = [
    {"name": "SIT-Finance — Finance Integration Package",
     "description": "Main suite containing FI module SIT test cases. 3-way match, VAT, consolidation.",
     "suite_type": "SIT", "status": "active", "module": "FI",
     "owner": "Ahmet Yildiz",
     "tags": "finance,sit,fi",
     "tc_codes": ["TC-FI-001", "TC-FI-002", "TC-FI-003", "TC-INT-001"]},
    {"name": "UAT-Logistics — Logistics Acceptance Package",
     "description": "MM/SD/PP/EWM UAT test cases. End-to-end supply chain validation.",
     "suite_type": "UAT", "status": "draft", "module": "MM",
     "owner": "Elif Kara",
     "tags": "logistics,uat,mm,sd,pp",
     "tc_codes": ["TC-MM-001", "TC-MM-002", "TC-MM-003", "TC-SD-001", "TC-SD-002",
                   "TC-SD-003", "TC-PP-001", "TC-PP-002", "TC-QM-001", "TC-EWM-001"]},
    {"name": "Regression-Core — Pre Go-Live Regression",
     "description": "Pre Go-Live critical E2E regression suite. TCs with is_regression=True.",
     "suite_type": "Regression", "status": "draft", "module": "CROSS",
     "owner": "Deniz Aydin",
     "tags": "regression,e2e,golive",
     "tc_codes": ["TC-FI-001", "TC-FI-002", "TC-MM-001", "TC-SD-001",
                   "TC-SD-002", "TC-E2E-001", "TC-E2E-002"]},
]

# ═════════════════════════════════════════════════════════════════════════════
# TEST STEPS — Detailed steps per TC  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

STEP_DATA = [
    # ── TC-FI-001 ──
    {"tc_code": "TC-FI-001", "step_no": 1,
     "action": "Enter purchase invoice via MIRO (reference PO number)",
     "expected_result": "Invoice header created, PO line item fetched automatically",
     "test_data": "PO: 4500001234, Amount: 125,000 TRY"},
    {"tc_code": "TC-FI-001", "step_no": 2,
     "action": "Perform 3-way matching check (PO-GR-IR)",
     "expected_result": "Amount variance within tolerance, accounting entries created automatically",
     "test_data": "Tolerance: +/-2%"},
    # ── TC-FI-002 ──
    {"tc_code": "TC-FI-002", "step_no": 1,
     "action": "Create sales invoice with basic food product (V1 tax code)",
     "expected_result": "VAT 1% calculated automatically",
     "test_data": "Material: MAT-FOOD-001, Tax code: V1"},
    {"tc_code": "TC-FI-002", "step_no": 2,
     "action": "Create sales invoice with beverage product (V3 + PCST)",
     "expected_result": "VAT 20% + PCST calculated correctly, tax lines shown separately",
     "test_data": "Material: MAT-BEV-001, Tax code: V3"},
    # ── TC-FI-003 ──
    {"tc_code": "TC-FI-003", "step_no": 1,
     "action": "Run ZFI_BALANCE report — select 3 company codes (TFRS)",
     "expected_result": "Consolidated balance sheet report generated, currency conversion correct",
     "test_data": "Company codes: 1000/2000/3000, Period: 2026-03"},
    {"tc_code": "TC-FI-003", "step_no": 2,
     "action": "Compare with VUK version",
     "expected_result": "TFRS and VUK balances shown in parallel, differences explained"},
    # ── TC-MM-001 ──
    {"tc_code": "TC-MM-001", "step_no": 1,
     "action": "Create PO with 200K TRY amount via ME21N",
     "expected_result": "PO created, approval WF triggered — routed to Director approval",
     "test_data": "Vendor: 100001, Material: MAT-RAW-001, Amount: 200,000 TRY"},
    {"tc_code": "TC-MM-001", "step_no": 2,
     "action": "Complete approval WF through all 4 tiers",
     "expected_result": "Routed to correct approver at each tier, PO released"},
    # ── TC-MM-002 ──
    {"tc_code": "TC-MM-002", "step_no": 1,
     "action": "Create 3 lots with different expiry dates in stock and enter shipment request",
     "expected_result": "Nearest expiry lot suggested via FEFO rule",
     "test_data": "Lot A: Expiry 2026-04-15, Lot B: Expiry 2026-05-01, Lot C: Expiry 2026-06-30"},
    {"tc_code": "TC-MM-002", "step_no": 2,
     "action": "Check block for lot with expiry < 30 days",
     "expected_result": "Short shelf life lot automatically blocked, warning message"},
    # ── TC-MM-003 ──
    {"tc_code": "TC-MM-003", "step_no": 1,
     "action": "Run migration program, load from staging table",
     "expected_result": "60,000 records processed, error log generated",
     "test_data": "Staging table: ZTMP_MAT_STG, Record count: 60,000"},
    {"tc_code": "TC-MM-003", "step_no": 2,
     "action": "Validate material type mapping and BOM",
     "expected_result": "Error rate < 0.5%, all material types matched correctly"},
    # ── TC-SD-001 ──
    {"tc_code": "TC-SD-001", "step_no": 1,
     "action": "Run VA01 -> VL01N -> VF01 full flow",
     "expected_result": "Order -> delivery -> invoice flow completed seamlessly",
     "test_data": "Customer: 200001, Material: MAT-FG-001, Quantity: 100 EA"},
    {"tc_code": "TC-SD-001", "step_no": 2,
     "action": "Check accounting entries (revenue/cost/VAT)",
     "expected_result": "FI entries created automatically, balance correct"},
    # ── TC-SD-002 ──
    {"tc_code": "TC-SD-002", "step_no": 1,
     "action": "Create invoice via VF01 and trigger e-Invoice",
     "expected_result": "UBL-TR XML generated, submitted to GIB",
     "test_data": "Invoice type: ZF1, GIB environment: TEST"},
    {"tc_code": "TC-SD-002", "step_no": 2,
     "action": "Check GIB response (accept/reject)",
     "expected_result": "Acceptance response received, status updated to 'Approved'"},
    # ── TC-SD-003 ──
    {"tc_code": "TC-SD-003", "step_no": 1,
     "action": "Enter order via retail channel (ZK01 condition)",
     "expected_result": "Channel discount applied automatically",
     "test_data": "Channel: Retail, Discount: 5%"},
    {"tc_code": "TC-SD-003", "step_no": 2,
     "action": "Enter same product order via wholesale and e-commerce channel, compare prices",
     "expected_result": "Different price/discount correctly applied per channel"},
    # ── TC-PP-001 ──
    {"tc_code": "TC-PP-001", "step_no": 1,
     "action": "Run MD01 MRP, convert planned order -> production order",
     "expected_result": "Planned order created with correct quantity and date",
     "test_data": "Material: MAT-FG-001, Demand: 500 EA"},
    {"tc_code": "TC-PP-001", "step_no": 2,
     "action": "Release production order, enter confirmation, calculate cost",
     "expected_result": "Order completed, actual cost calculated"},
    # ── TC-PP-002 ──
    {"tc_code": "TC-PP-002", "step_no": 1,
     "action": "Send production confirmation message from MES (OData API)",
     "expected_result": "Confirmation record created via BAPI in SAP",
     "test_data": "Production order: 1000001, Operation: 0010, Quantity: 100, Scrap: 5"},
    {"tc_code": "TC-PP-002", "step_no": 2,
     "action": "Validate scrap quantity and check error messages",
     "expected_result": "Scrap quantity positive, confirmation saved successfully"},
    # ── TC-QM-001 ──
    {"tc_code": "TC-QM-001", "step_no": 1,
     "action": "Post goods receipt for food raw material (MIGO)",
     "expected_result": "Automatic inspection lot created, HACCP checkpoint triggered",
     "test_data": "Material: MAT-RAW-FOOD-01, Inspection plan: QP-001"},
    {"tc_code": "TC-QM-001", "step_no": 2,
     "action": "Enter HACCP result and make accept/reject decision",
     "expected_result": "Accept -> stock released, Reject -> blocked stock"},
    # ── TC-EWM-001 ──
    {"tc_code": "TC-EWM-001", "step_no": 1,
     "action": "Create outbound delivery and assign wave",
     "expected_result": "Wave created, picking task started automatically",
     "test_data": "Warehouse: WH01, Area: PICK-01"},
    {"tc_code": "TC-EWM-001", "step_no": 2,
     "action": "Enter picking confirmation and perform PGI",
     "expected_result": "Stock movement reflected in SAP, delivery note printable"},
    # ── TC-INT-001 ──
    {"tc_code": "TC-INT-001", "step_no": 1,
     "action": "Upload MT940 bank statement file to system",
     "expected_result": "File parsed successfully, statement items listed",
     "test_data": "Bank: AKBANK, Account: TR12 0004 6001"},
    {"tc_code": "TC-INT-001", "step_no": 2,
     "action": "Run automatic matching, check unmatched items",
     "expected_result": "Matching rate >= 90%, remaining items flagged"},
    # ── TC-E2E-001 ──
    {"tc_code": "TC-E2E-001", "step_no": 1,
     "action": "Run PR -> PO -> GR -> IR full flow",
     "expected_result": "Purchase requisition -> order -> goods receipt -> invoice flow seamless",
     "test_data": "Vendor: 100002, Material: MAT-RAW-002, Amount: 75,000 TRY"},
    {"tc_code": "TC-E2E-001", "step_no": 2,
     "action": "Run F110 payment and validate accounting entries",
     "expected_result": "Payment completed, bank account balance updated"},
    # ── TC-E2E-002 ──
    {"tc_code": "TC-E2E-002", "step_no": 1,
     "action": "Run accrual and depreciation on intra-month FI entries",
     "expected_result": "Accrual entries created, depreciation calculated correctly",
     "test_data": "Period: 2026-03, Company code: 1000"},
    {"tc_code": "TC-E2E-002", "step_no": 2,
     "action": "Period closing procedure and reporting check",
     "expected_result": "Closing < 4 hours, balance sheet/income statement correct"},
]

# ═════════════════════════════════════════════════════════════════════════════
# CYCLE <-> SUITE assignment  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

CYCLE_SUITE_DATA = [
    # SIT Cycle 1 <- SIT-Finance suite
    {"cycle_name": "SIT Cycle 1 — Core Flows",
     "suite_name": "SIT-Finance — Finance Integration Package", "order": 1},
    # SIT Cycle 2 <- SIT-Finance suite (regression)
    {"cycle_name": "SIT Cycle 2 — Bug Fix & Regression",
     "suite_name": "SIT-Finance — Finance Integration Package", "order": 1},
    # UAT Cycle 1 <- UAT-Logistics suite
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "suite_name": "UAT-Logistics — Logistics Acceptance Package", "order": 1},
    # Regression Cycle <- Regression-Core suite
    {"cycle_name": "Regression Cycle — Pre Go-Live",
     "suite_name": "Regression-Core — Pre Go-Live Regression", "order": 1},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUNS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

TEST_RUN_DATA = [
    {"cycle_name": "SIT Cycle 1 — Core Flows",
     "tc_code": "TC-FI-001", "run_type": "manual", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Ahmet Yildiz",
     "notes": "All checkpoints successful", "duration_minutes": 35},
    {"cycle_name": "SIT Cycle 1 — Core Flows",
     "tc_code": "TC-FI-002", "run_type": "manual", "status": "completed",
     "result": "fail", "environment": "SIT", "tester": "Ahmet Yildiz",
     "notes": "VAT calculation discrepancy found", "duration_minutes": 28},
    {"cycle_name": "SIT Cycle 1 — Core Flows",
     "tc_code": "TC-MM-001", "run_type": "manual", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Zeynep Koc",
     "notes": "PR -> PO flow seamless", "duration_minutes": 40},
    {"cycle_name": "SIT Cycle 1 — Core Flows",
     "tc_code": "TC-SD-001", "run_type": "automated", "status": "completed",
     "result": "pass", "environment": "SIT", "tester": "Automation",
     "notes": "Tested order-to-invoice via Selenium", "duration_minutes": 12},
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "tc_code": "TC-WM-001", "run_type": "manual", "status": "in_progress",
     "result": "not_run", "environment": "UAT", "tester": "Hakan Gunes",
     "notes": "Warehouse transfer scenario in progress"},
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "tc_code": "TC-PP-001", "run_type": "manual", "status": "not_started",
     "result": "not_run", "environment": "UAT", "tester": "Elif Kara"},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

STEP_RESULT_DATA = [
    # Exec 0 (TC-FI-001, pass) — 2 steps
    {"exec_index": 0, "step_no": 1, "result": "pass",
     "actual_result": "Chart of accounts loaded correctly, balances consistent"},
    {"exec_index": 0, "step_no": 2, "result": "pass",
     "actual_result": "BKPF/BSEG entries validated"},
    # Exec 1 (TC-FI-002, pass) — 2 steps
    {"exec_index": 1, "step_no": 1, "result": "pass",
     "actual_result": "Invoice created"},
    {"exec_index": 1, "step_no": 2, "result": "pass",
     "actual_result": "VAT calculation correct"},
    # Exec 2 (TC-FI-003, fail) — 2 steps
    {"exec_index": 2, "step_no": 1, "result": "pass",
     "actual_result": "Consolidated balance sheet report ran successfully"},
    {"exec_index": 2, "step_no": 2, "result": "fail",
     "actual_result": "2nd company code currency conversion error — exchange rate difference exists",
     "notes": "DEF-FI-001 opened"},
    # Exec 3 (TC-MM-001, pass) — 2 steps
    {"exec_index": 3, "step_no": 1, "result": "pass",
     "actual_result": "PR created automatically, amount limit correct"},
    {"exec_index": 3, "step_no": 2, "result": "pass",
     "actual_result": "PO approval flow completed through 4 tiers"},
    # Exec 6 (TC-SD-001, pass) — 2 steps
    {"exec_index": 6, "step_no": 1, "result": "pass",
     "actual_result": "Order to delivery flow successful"},
    {"exec_index": 6, "step_no": 2, "result": "pass",
     "actual_result": "Invoice and accounting entries matched"},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENTS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_COMMENT_DATA = [
    # Defect index 0 (P1 blocker — VAT discrepancy)
    {"defect_index": 0, "author": "Ahmet Yildiz",
     "body": "VAT calculated as 10% instead of 18% in SIT environment. Food category mapping table should be checked."},
    {"defect_index": 0, "author": "Elif Kara",
     "body": "Condition type rule missing in BAdI TAX_CALC_ENHANCE. Fix branch created."},
    {"defect_index": 0, "author": "Kemal Erdogan",
     "body": "Fix transported via transport K900123. Retest pending."},
    # Defect index 1 (PO approval)
    {"defect_index": 1, "author": "Zeynep Koc",
     "body": "PO approval timeout structure to be checked in BRF+. SLA 24 hours."},
    # Defect index 3 (Batch management)
    {"defect_index": 3, "author": "Hakan Gunes",
     "body": "FIFO should be applied for records with same batch date in FEFO sorting."},
    {"defect_index": 3, "author": "Deniz Aydin",
     "body": "Additional sort criterion added to user exit ZFEFO_SORT."},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_HISTORY_DATA = [
    # Defect index 0 lifecycle
    {"defect_index": 0, "field": "status", "old_value": "open",
     "new_value": "in_progress", "changed_by": "Elif Kara"},
    {"defect_index": 0, "field": "assigned_to", "old_value": "",
     "new_value": "Elif Kara", "changed_by": "Deniz Aydin"},
    {"defect_index": 0, "field": "status", "old_value": "in_progress",
     "new_value": "resolved", "changed_by": "Elif Kara"},
    {"defect_index": 0, "field": "resolution", "old_value": "",
     "new_value": "BAdI condition type fixed", "changed_by": "Elif Kara"},
    # Defect index 2 (GR-IR)
    {"defect_index": 2, "field": "severity", "old_value": "medium",
     "new_value": "high", "changed_by": "Kemal Erdogan"},
    {"defect_index": 2, "field": "status", "old_value": "open",
     "new_value": "in_progress", "changed_by": "Ahmet Yildiz"},
]


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINKS  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

DEFECT_LINK_DATA = [
    # Defect 0 <-> Defect 1: related (VAT + PO approval both Finance)
    {"source_index": 0, "target_index": 1,
     "link_type": "related", "notes": "Both detected in SIT-Finance package"},
    # Defect 3 <-> Defect 4: related (Batch + MES)
    {"source_index": 3, "target_index": 4,
     "link_type": "related", "notes": "Both related to inventory management"},
    # Defect 5 blocks Defect 6 (E2E -> Consolidation)
    {"source_index": 5, "target_index": 6,
     "link_type": "blocks", "notes": "Consolidation test cannot run until E2E flow is closed"},
]


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFFS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

UAT_SIGNOFF_DATA = [
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "process_area": "Finance", "scope_item_id": None,
     "signed_off_by": "Kemal Erdogan", "role": "PM",
     "status": "approved", "comments": "All finance scenarios tested successfully"},
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "process_area": "Logistics", "scope_item_id": None,
     "signed_off_by": "Elif Kara", "role": "BPO",
     "status": "approved", "comments": "Supply chain processes approved"},
    {"cycle_name": "UAT Cycle 1 — Business Scenarios",
     "process_area": "Production", "scope_item_id": None,
     "signed_off_by": "Deniz Aydin", "role": "BPO",
     "status": "pending", "comments": "Waiting for MES integration"},
]


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

PERF_RESULT_DATA = [
    {"tc_code": "TC-FI-001", "run_index": 0,
     "response_time_ms": 1200, "throughput_rps": 85.5,
     "concurrent_users": 50, "target_response_ms": 2000,
     "target_throughput_rps": 80.0, "environment": "PERF",
     "notes": "Invoice posting performance within target"},
    {"tc_code": "TC-SD-001", "run_index": 3,
     "response_time_ms": 3500, "throughput_rps": 45.2,
     "concurrent_users": 100, "target_response_ms": 3000,
     "target_throughput_rps": 50.0, "environment": "PERF",
     "notes": "OTC E2E performance above target — optimization needed"},
    {"tc_code": "TC-MM-001", "run_index": 2,
     "response_time_ms": 800, "throughput_rps": 120.0,
     "concurrent_users": 50, "target_response_ms": 1500,
     "target_throughput_rps": 100.0, "environment": "PERF",
     "notes": "PO creation performance excellent"},
]


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOTS  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

SNAPSHOT_DATA = [
    {"snapshot_date": "2026-03-10", "cycle_name": "SIT Cycle 1 — Core Flows",
     "wave": "Wave 1", "total_cases": 18, "passed": 10, "failed": 3,
     "blocked": 1, "not_run": 4,
     "open_defects_s1": 1, "open_defects_s2": 2,
     "open_defects_s3": 3, "open_defects_s4": 1, "closed_defects": 1},
    {"snapshot_date": "2026-03-15", "cycle_name": "SIT Cycle 1 — Core Flows",
     "wave": "Wave 1", "total_cases": 18, "passed": 14, "failed": 2,
     "blocked": 0, "not_run": 2,
     "open_defects_s1": 0, "open_defects_s2": 1,
     "open_defects_s3": 2, "open_defects_s4": 1, "closed_defects": 4},
    {"snapshot_date": "2026-03-20", "cycle_name": "SIT Cycle 1 — Core Flows",
     "wave": "Wave 1", "total_cases": 18, "passed": 16, "failed": 1,
     "blocked": 0, "not_run": 1,
     "open_defects_s1": 0, "open_defects_s2": 0,
     "open_defects_s3": 1, "open_defects_s4": 1, "closed_defects": 6},
]
