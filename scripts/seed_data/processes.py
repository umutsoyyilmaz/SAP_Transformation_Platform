"""
Phase 3 — Process Hierarchy (Signavio L2->L3->L4) + Analysis
Company: Anadolu Food & Beverage Inc.

_area key maps each L2 tree to its parent Scenario's process_area.
Hierarchy:
  L2 = Process Area (scope_confirmation)
  L3 = E2E Process  (scope_decision, fit_gap, cloud_alm_ref, test_scope)
  L4 = Sub Process  (activate_output, wricef_type, test_levels)
"""

from datetime import date

# ===============================================================================
# ORDER-TO-CASH  (maps to Scenario L1.3)
# ===============================================================================

_OTC_1 = {
    "_area": "order_to_cash",
    "name": "Sales Order Management", "level": "L2", "module": "SD",
    "process_id_code": "O2C-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Standard Sales Order", "level": "L3", "module": "SD", "order": 1,
         "code": "1OC", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1OC", "sap_tcode": "VA01", "priority": "critical",
         "cloud_alm_ref": "CALM-OTC-001", "test_scope": "full",
         "analyses": [
             {"name": "Sales Order Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "fit",
              "decision": "Standard SAP configuration is sufficient.",
              "attendees": "Burak Sahin, Sales Manager", "date": date(2025, 9, 18)},
         ],
         "children": [
             {"name": "Order Creation", "level": "L4", "module": "SD", "order": 1,
              "code": "1OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "wricef_type": "", "test_levels": "unit,sit,uat"},
             {"name": "Pricing Calculation", "level": "L4", "module": "SD", "order": 2,
              "code": "1OC-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Credit Check", "level": "L4", "module": "SD", "order": 3,
              "code": "1OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "wricef", "wricef_type": "workflow", "test_levels": "unit,sit,uat"},
             {"name": "ATP Check", "level": "L4", "module": "SD", "order": 4,
              "code": "1OC-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "wricef_type": "", "test_levels": "sit,uat"},
         ]},
        {"name": "Consignment Sales", "level": "L3", "module": "SD", "order": 2,
         "code": "2OC", "scope_decision": "deferred", "priority": "low",
         "sap_reference": "BP-2OC", "cloud_alm_ref": "CALM-OTC-002"},
    ],
}

_OTC_2 = {
    "_area": "order_to_cash",
    "name": "Delivery and Shipment", "level": "L2", "module": "SD",
    "process_id_code": "O2C-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Standard Delivery Process", "level": "L3", "module": "SD", "order": 1,
         "code": "3OC", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3OC", "sap_tcode": "VL01N", "priority": "high",
         "cloud_alm_ref": "CALM-OTC-003", "test_scope": "full",
         "children": [
             {"name": "Delivery Creation", "level": "L4", "module": "SD", "order": 1,
              "code": "3OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Goods Issue (GI)", "level": "L4", "module": "SD", "order": 2,
              "code": "3OC-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Delivery Note Printing", "level": "L4", "module": "SD", "order": 3,
              "code": "3OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "form", "wricef_type": "form", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_OTC_3 = {
    "_area": "order_to_cash",
    "name": "Billing and Collection", "level": "L2", "module": "SD",
    "process_id_code": "O2C-03", "order": 3, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Invoice Processing", "level": "L3", "module": "SD", "order": 1,
         "code": "4OC", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-4OC", "sap_tcode": "VF01", "priority": "critical",
         "cloud_alm_ref": "CALM-OTC-004", "test_scope": "full",
         "analyses": [
             {"name": "Billing Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "GIB integration required for e-Invoice/e-Waybill.",
              "attendees": "Burak Sahin, Accounting", "date": date(2025, 9, 20)},
         ],
         "children": [
             {"name": "Invoice Creation", "level": "L4", "module": "SD", "order": 1,
              "code": "4OC-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "e-Invoice GIB Integration", "level": "L4", "module": "SD", "order": 2,
              "code": "4OC-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "e-Waybill GIB Integration", "level": "L4", "module": "SD", "order": 3,
              "code": "4OC-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "Collection and Reconciliation", "level": "L4", "module": "FI", "order": 4,
              "code": "4OC-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
    ],
}

# ===============================================================================
# PROCURE-TO-PAY  (maps to Scenario L1.4)
# ===============================================================================

_P2P_1 = {
    "_area": "procure_to_pay",
    "name": "Procurement Process", "level": "L2", "module": "MM",
    "process_id_code": "P2P-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Direct Material Procurement", "level": "L3", "module": "MM", "order": 1,
         "code": "1PP", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1PP", "sap_tcode": "ME21N", "priority": "critical",
         "cloud_alm_ref": "CALM-P2P-001", "test_scope": "full",
         "analyses": [
             {"name": "Procurement Fit-Gap Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "fit",
              "decision": "Standard SAP procurement process will be used.",
              "attendees": "Elif Kara, Procurement Manager", "date": date(2025, 9, 20)},
         ],
         "children": [
             {"name": "Purchase Requisition (PR)", "level": "L4", "module": "MM", "order": 1,
              "code": "1PP-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Request for Quotation (RFQ)", "level": "L4", "module": "MM", "order": 2,
              "code": "1PP-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit"},
             {"name": "PO Approval Workflow", "level": "L4", "module": "MM", "order": 3,
              "code": "1PP-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "workflow_config", "wricef_type": "workflow", "test_levels": "unit,sit,uat"},
             {"name": "Goods Receipt (GR)", "level": "L4", "module": "MM", "order": 4,
              "code": "1PP-04", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Invoice Verification (IV)", "level": "L4", "module": "MM", "order": 5,
              "code": "1PP-05", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
        {"name": "Service Procurement", "level": "L3", "module": "MM", "order": 2,
         "code": "2PP", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2PP", "sap_tcode": "ME23N", "priority": "medium",
         "cloud_alm_ref": "CALM-P2P-002", "test_scope": "regression",
         "children": [
             {"name": "Service Entry Sheet", "level": "L4", "module": "MM", "order": 1,
              "code": "2PP-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
         ]},
    ],
}

_P2P_2 = {
    "_area": "procure_to_pay",
    "name": "Inventory Management", "level": "L2", "module": "MM",
    "process_id_code": "P2P-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Stock Transfer and Counting", "level": "L3", "module": "MM", "order": 1,
         "code": "3PP", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3PP", "sap_tcode": "MB1B", "priority": "high",
         "cloud_alm_ref": "CALM-P2P-003", "test_scope": "full",
         "children": [
             {"name": "Inter-Plant Transfer", "level": "L4", "module": "MM", "order": 1,
              "code": "3PP-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Physical Inventory Count (MI01)", "level": "L4", "module": "MM", "order": 2,
              "code": "3PP-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Stock Valuation Report", "level": "L4", "module": "MM", "order": 3,
              "code": "3PP-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "report", "wricef_type": "report", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

# ===============================================================================
# RECORD-TO-REPORT  (maps to Scenario L1.2 — Financial Accounting)
# ===============================================================================

_R2R_1 = {
    "_area": "record_to_report",
    "name": "General Ledger (GL)", "level": "L2", "module": "FI",
    "process_id_code": "R2R-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "GL Posting and Period Close", "level": "L3", "module": "FI", "order": 1,
         "code": "1RR", "scope_decision": "in_scope", "fit_gap": "gap",
         "sap_reference": "BP-1RR", "sap_tcode": "FB50", "priority": "critical",
         "cloud_alm_ref": "CALM-R2R-001", "test_scope": "full",
         "analyses": [
             {"name": "FI General Ledger Fit-Gap", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "gap",
              "decision": "Additional development required for VUK compliance. TFRS parallel reporting.",
              "attendees": "Ahmet Yildiz, CFO, CPA", "date": date(2025, 9, 15)},
         ],
         "children": [
             {"name": "GL Posting Entry", "level": "L4", "module": "FI", "order": 1,
              "code": "1RR-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "VUK Compliance Reports", "level": "L4", "module": "FI", "order": 2,
              "code": "1RR-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "report", "wricef_type": "report", "test_levels": "unit,sit,uat"},
             {"name": "Period Close", "level": "L4", "module": "FI", "order": 3,
              "code": "1RR-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Bank Reconciliation", "level": "L4", "module": "FI", "order": 4,
              "code": "1RR-04", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_R2R_2 = {
    "_area": "record_to_report",
    "name": "Accounts Payable / Receivable", "level": "L2", "module": "FI",
    "process_id_code": "R2R-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Vendor Invoice and Payment", "level": "L3", "module": "FI", "order": 1,
         "code": "2RR", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-2RR", "sap_tcode": "FB60", "priority": "high",
         "cloud_alm_ref": "CALM-R2R-002", "test_scope": "full",
         "children": [
             {"name": "Incoming Invoice Posting", "level": "L4", "module": "FI", "order": 1,
              "code": "2RR-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Automatic Payment (F110)", "level": "L4", "module": "FI", "order": 2,
              "code": "2RR-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Bank Payment File", "level": "L4", "module": "FI", "order": 3,
              "code": "2RR-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Fixed Asset Management", "level": "L3", "module": "FI", "order": 2,
         "code": "3RR", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-3RR", "sap_tcode": "AS01", "priority": "high",
         "cloud_alm_ref": "CALM-R2R-003", "test_scope": "regression"},
    ],
}

# ===============================================================================
# PLAN-TO-PRODUCE  (maps to Scenario L1.5)
# ===============================================================================

_P2M_1 = {
    "_area": "plan_to_produce",
    "name": "Production Planning (MRP)", "level": "L2", "module": "PP",
    "process_id_code": "P2M-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "MRP and Demand Planning", "level": "L3", "module": "PP", "order": 1,
         "code": "1PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-1PM", "sap_tcode": "MD01", "priority": "critical",
         "cloud_alm_ref": "CALM-P2M-001", "test_scope": "full",
         "analyses": [
             {"name": "PP MRP Fit-Gap Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "MRP parameters to be adapted for food industry. Shelf life control requires additional development.",
              "attendees": "Deniz Aydin, Production Manager, Planning Supervisor", "date": date(2025, 10, 15)},
         ],
         "children": [
             {"name": "MRP Run", "level": "L4", "module": "PP", "order": 1,
              "code": "1PM-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Production Order Creation", "level": "L4", "module": "PP", "order": 2,
              "code": "1PM-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "Capacity Planning", "level": "L4", "module": "PP", "order": 3,
              "code": "1PM-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "wricef", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

_P2M_2 = {
    "_area": "plan_to_produce",
    "name": "Production Execution", "level": "L2", "module": "PP",
    "process_id_code": "P2M-02", "order": 2, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Production Confirmation and Consumption", "level": "L3", "module": "PP", "order": 1,
         "code": "2PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2PM", "sap_tcode": "CO11N", "priority": "high",
         "cloud_alm_ref": "CALM-P2M-002", "test_scope": "full",
         "children": [
             {"name": "Production Confirmation", "level": "L4", "module": "PP", "order": 1,
              "code": "2PM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
             {"name": "MES Integration", "level": "L4", "module": "PP", "order": 2,
              "code": "2PM-02", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "interface", "wricef_type": "interface", "test_levels": "unit,sit,uat"},
             {"name": "Scrap and Waste Reporting", "level": "L4", "module": "PP", "order": 3,
              "code": "2PM-03", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Quality Control (QM)", "level": "L3", "module": "QM", "order": 2,
         "code": "3PM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-3PM", "sap_tcode": "QA01", "priority": "high",
         "cloud_alm_ref": "CALM-P2M-003", "test_scope": "full",
         "analyses": [
             {"name": "QM HACCP Workshop", "analysis_type": "fit_gap",
              "status": "completed", "fit_gap_result": "partial_fit",
              "decision": "HACCP control points to be configured. Additional certificate report required.",
              "attendees": "Deniz Aydin, Quality Director, HACCP Officer", "date": date(2025, 10, 22)},
         ],
         "children": [
             {"name": "Quality Inspection Order", "level": "L4", "module": "QM", "order": 1,
              "code": "3PM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "HACCP Control Point", "level": "L4", "module": "QM", "order": 2,
              "code": "3PM-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
             {"name": "Quality Certificate Printing", "level": "L4", "module": "QM", "order": 3,
              "code": "3PM-03", "scope_decision": "in_scope", "fit_gap": "gap",
              "activate_output": "form", "wricef_type": "form", "test_levels": "unit,sit,uat"},
         ]},
    ],
}

# ===============================================================================
# WAREHOUSE MANAGEMENT  (maps to Scenario L1.6)
# ===============================================================================

_WM_1 = {
    "_area": "warehouse_mgmt",
    "name": "Intra-Warehouse Operations", "level": "L2", "module": "EWM",
    "process_id_code": "WM-01", "order": 1, "scope_confirmation": "confirmed",
    "children": [
        {"name": "Goods Receipt and Putaway", "level": "L3", "module": "EWM", "order": 1,
         "code": "1WM", "scope_decision": "in_scope", "fit_gap": "fit",
         "sap_reference": "BP-1WM", "priority": "high",
         "cloud_alm_ref": "CALM-WM-001", "test_scope": "full",
         "children": [
             {"name": "Goods Receipt (Inbound)", "level": "L4", "module": "EWM", "order": 1,
              "code": "1WM-01", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Bin Assignment (Putaway)", "level": "L4", "module": "EWM", "order": 2,
              "code": "1WM-02", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "custom_logic", "wricef_type": "enhancement", "test_levels": "unit,sit,uat"},
         ]},
        {"name": "Picking and Shipment", "level": "L3", "module": "EWM", "order": 2,
         "code": "2WM", "scope_decision": "in_scope", "fit_gap": "partial_fit",
         "sap_reference": "BP-2WM", "priority": "high",
         "cloud_alm_ref": "CALM-WM-002", "test_scope": "full",
         "children": [
             {"name": "Wave Picking", "level": "L4", "module": "EWM", "order": 1,
              "code": "2WM-01", "scope_decision": "in_scope", "fit_gap": "partial_fit",
              "activate_output": "configuration", "test_levels": "sit,uat"},
             {"name": "Loading and Dispatch", "level": "L4", "module": "EWM", "order": 2,
              "code": "2WM-02", "scope_decision": "in_scope", "fit_gap": "fit",
              "activate_output": "std_process", "test_levels": "sit,uat"},
         ]},
    ],
}


# ===============================================================================
# ASSEMBLED LIST
# ===============================================================================

PROCESS_SEED = [
    # Order-to-Cash
    _OTC_1, _OTC_2, _OTC_3,
    # Procure-to-Pay
    _P2P_1, _P2P_2,
    # Record-to-Report
    _R2R_1, _R2R_2,
    # Plan-to-Produce
    _P2M_1, _P2M_2,
    # Warehouse
    _WM_1,
]
