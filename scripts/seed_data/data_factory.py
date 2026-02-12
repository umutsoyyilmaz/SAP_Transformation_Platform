"""
SEED-003 — Data Factory Demo Data
Company: Anadolu Gıda ve İçecek A.Ş.

Provides seed data for the Data Factory module:
  - 15 DataObjects across 3 source systems
  - 4 MigrationWaves
  - 30 CleansingTasks (2 per object)
  - 20 LoadCycles
  - 15 Reconciliations
"""

DATA_OBJECTS = [
    # ── SAP ECC core data ────────────────────────────────────────────────
    {"name": "Customer Master",     "source_system": "SAP ECC", "target_table": "BP_CUSTOMER",
     "record_count": 125000, "quality_score": 87.5,  "status": "cleansed", "owner": "Mehmet Kaya",
     "description": "KNA1/KNB1 customer master records"},
    {"name": "Vendor Master",       "source_system": "SAP ECC", "target_table": "BP_VENDOR",
     "record_count":  45000, "quality_score": 92.3,  "status": "ready",    "owner": "Ayşe Demir",
     "description": "LFA1/LFB1 vendor master records"},
    {"name": "Material Master",     "source_system": "SAP ECC", "target_table": "MARA_PRODUCT",
     "record_count": 340000, "quality_score": 78.1,  "status": "profiled", "owner": "Hasan Yılmaz",
     "description": "MARA/MARC/MVKE material records"},
    {"name": "GL Account Master",   "source_system": "SAP ECC", "target_table": "SKA1_GLACCOUNT",
     "record_count":   8200, "quality_score": 95.0,  "status": "migrated", "owner": "Fatma Çelik",
     "description": "SKA1/SKB1 chart of accounts"},
    {"name": "Cost Center Master",  "source_system": "SAP ECC", "target_table": "CSKS_COSTCTR",
     "record_count":   3500, "quality_score": 91.2,  "status": "ready",    "owner": "Fatma Çelik",
     "description": "CSKS/CSKT cost center master"},
    {"name": "Profit Center Master","source_system": "SAP ECC", "target_table": "CEPC_PROFITCTR",
     "record_count":   1200, "quality_score": 94.8,  "status": "ready",    "owner": "Fatma Çelik",
     "description": "CEPC profit center master"},

    # ── SAP ECC transactional data ───────────────────────────────────────
    {"name": "Sales Orders",        "source_system": "SAP ECC", "target_table": "VBAK_SALESORDER",
     "record_count": 2500000, "quality_score": 82.4, "status": "profiled", "owner": "Ali Öztürk",
     "description": "VBAK/VBAP historical sales orders (3 years)"},
    {"name": "Purchase Orders",     "source_system": "SAP ECC", "target_table": "EKKO_PURCHORDER",
     "record_count": 1800000, "quality_score": 85.1, "status": "profiled", "owner": "Ayşe Demir",
     "description": "EKKO/EKPO historical purchase orders"},
    {"name": "FI Documents",        "source_system": "SAP ECC", "target_table": "BKPF_JOURNAL",
     "record_count": 8700000, "quality_score": 76.3, "status": "draft",    "owner": "Fatma Çelik",
     "description": "BKPF/BSEG financial journal entries (5 years)"},

    # ── Legacy HR system ────────────────────────────────────────────────
    {"name": "Employee Master",     "source_system": "Legacy HR", "target_table": "PA0001_EMPLOYEE",
     "record_count":   5200, "quality_score": 70.5,  "status": "cleansed", "owner": "Zeynep Arslan",
     "description": "Employee master from legacy HR system"},
    {"name": "Payroll History",     "source_system": "Legacy HR", "target_table": "PAYROLL_HIST",
     "record_count": 640000, "quality_score": 65.2,  "status": "draft",    "owner": "Zeynep Arslan",
     "description": "24 months payroll transaction history"},
    {"name": "Time Records",        "source_system": "Legacy HR", "target_table": "CATSDB_TIMESHEET",
     "record_count": 1200000, "quality_score": None,  "status": "draft",   "owner": "Zeynep Arslan",
     "description": "Time recording entries from legacy system"},

    # ── External/Warehouse system ───────────────────────────────────────
    {"name": "Warehouse Stocks",    "source_system": "WMS IntraLog", "target_table": "MARD_STOCK",
     "record_count":  89000, "quality_score": 88.7,  "status": "cleansed", "owner": "Hasan Yılmaz",
     "description": "Current stock levels from WMS"},
    {"name": "Bin Locations",       "source_system": "WMS IntraLog", "target_table": "LAGP_STORAGE",
     "record_count":  12400, "quality_score": 93.1,  "status": "ready",    "owner": "Hasan Yılmaz",
     "description": "Storage bin master from WMS"},
    {"name": "BOM Headers",         "source_system": "SAP ECC", "target_table": "STKO_BOM",
     "record_count":  67000, "quality_score": 81.3,  "status": "profiled", "owner": "Hasan Yılmaz",
     "description": "STKO/STPO bill of material headers and items"},
]


MIGRATION_WAVES = [
    {"wave_number": 1, "name": "Wave 1 — Master Data (Core)",
     "description": "Customer, vendor, material, GL accounts, cost/profit centers",
     "planned_start": "2026-03-01", "planned_end": "2026-04-15",
     "status": "in_progress"},
    {"wave_number": 2, "name": "Wave 2 — Organizational & HR",
     "description": "Employee master, org units, payroll history",
     "planned_start": "2026-04-16", "planned_end": "2026-05-31",
     "status": "planned"},
    {"wave_number": 3, "name": "Wave 3 — Transactional Data",
     "description": "Open sales orders, purchase orders, FI documents (cutover)",
     "planned_start": "2026-06-01", "planned_end": "2026-07-31",
     "status": "planned"},
    {"wave_number": 4, "name": "Wave 4 — Warehouse & BOM",
     "description": "Stock balances, bin locations, BOM structures",
     "planned_start": "2026-08-01", "planned_end": "2026-09-15",
     "status": "planned"},
]


# 2 cleansing tasks per data object (index-referenced)
CLEANSING_TASKS = [
    # Customer Master (idx 0)
    {"obj_index": 0,  "rule_type": "not_null", "rule_expression": "NAME1 IS NOT NULL AND LAND1 IS NOT NULL",
     "description": "Ensure customer name and country are populated",
     "pass_count": 124500, "fail_count": 500, "status": "passed"},
    {"obj_index": 0,  "rule_type": "unique",   "rule_expression": "KUNNR UNIQUE",
     "description": "Validate customer number uniqueness",
     "pass_count": 125000, "fail_count": 0,   "status": "passed"},

    # Vendor Master (idx 1)
    {"obj_index": 1,  "rule_type": "not_null", "rule_expression": "NAME1 IS NOT NULL",
     "description": "Vendor name must not be null",
     "pass_count": 45000, "fail_count": 0,  "status": "passed"},
    {"obj_index": 1,  "rule_type": "regex",    "rule_expression": r"STCD1 MATCHES '^\d{10,11}$'",
     "description": "Tax number format validation",
     "pass_count": 44200, "fail_count": 800, "status": "failed"},

    # Material Master (idx 2)
    {"obj_index": 2,  "rule_type": "not_null", "rule_expression": "MAKTX IS NOT NULL AND MTART IS NOT NULL",
     "description": "Material description and type required",
     "pass_count": 335000, "fail_count": 5000, "status": "failed"},
    {"obj_index": 2,  "rule_type": "lookup",   "rule_expression": "MTART IN VALID_MATERIAL_TYPES",
     "description": "Material type must exist in target table",
     "pass_count": 339500, "fail_count": 500,  "status": "passed"},

    # GL Account (idx 3)
    {"obj_index": 3,  "rule_type": "unique",   "rule_expression": "SAKNR UNIQUE",
     "description": "GL account number uniqueness",
     "pass_count": 8200,  "fail_count": 0,  "status": "passed"},
    {"obj_index": 3,  "rule_type": "range",    "rule_expression": "SAKNR BETWEEN 100000 AND 999999",
     "description": "GL account number valid range",
     "pass_count": 8200,  "fail_count": 0,  "status": "passed"},

    # Cost Center (idx 4)
    {"obj_index": 4,  "rule_type": "not_null", "rule_expression": "KOSTL IS NOT NULL AND BUKRS IS NOT NULL",
     "description": "Cost center and company code required",
     "pass_count": 3500,  "fail_count": 0,  "status": "passed"},
    {"obj_index": 4,  "rule_type": "lookup",   "rule_expression": "BUKRS IN VALID_COMPANY_CODES",
     "description": "Company code must be valid",
     "pass_count": 3500,  "fail_count": 0,  "status": "passed"},

    # Profit Center (idx 5)
    {"obj_index": 5,  "rule_type": "unique",   "rule_expression": "PRCTR UNIQUE PER KOKRS",
     "description": "Profit center unique per controlling area",
     "pass_count": 1200,  "fail_count": 0,  "status": "passed"},
    {"obj_index": 5,  "rule_type": "not_null", "rule_expression": "KTEXT IS NOT NULL",
     "description": "Profit center description required",
     "pass_count": 1180,  "fail_count": 20, "status": "failed"},

    # Sales Orders (idx 6)
    {"obj_index": 6,  "rule_type": "not_null", "rule_expression": "AUART IS NOT NULL AND KUNNR IS NOT NULL",
     "description": "Order type and customer required",
     "pass_count": 2499000, "fail_count": 1000, "status": "passed"},
    {"obj_index": 6,  "rule_type": "range",    "rule_expression": "ERDAT BETWEEN '2023-01-01' AND '2026-12-31'",
     "description": "Order date within migration scope",
     "pass_count": 2500000, "fail_count": 0, "status": "passed"},

    # Purchase Orders (idx 7)
    {"obj_index": 7,  "rule_type": "not_null", "rule_expression": "BSART IS NOT NULL AND LIFNR IS NOT NULL",
     "description": "PO type and vendor required",
     "pass_count": 1798000, "fail_count": 2000, "status": "passed"},
    {"obj_index": 7,  "rule_type": "lookup",   "rule_expression": "LIFNR IN VALID_VENDORS",
     "description": "Vendor must exist in vendor master migration scope",
     "pass_count": 1795000, "fail_count": 5000, "status": "failed"},

    # FI Documents (idx 8)
    {"obj_index": 8,  "rule_type": "not_null", "rule_expression": "BUKRS IS NOT NULL AND BLART IS NOT NULL",
     "description": "Company code and document type required",
     "pass_count": None, "fail_count": None, "status": "pending"},
    {"obj_index": 8,  "rule_type": "range",    "rule_expression": "BUDAT BETWEEN '2021-01-01' AND '2026-12-31'",
     "description": "Posting date within 5-year scope",
     "pass_count": None, "fail_count": None, "status": "pending"},

    # Employee Master (idx 9)
    {"obj_index": 9,  "rule_type": "not_null", "rule_expression": "PERNR IS NOT NULL AND NACHN IS NOT NULL",
     "description": "Employee number and surname required",
     "pass_count": 5200,  "fail_count": 0,  "status": "passed"},
    {"obj_index": 9,  "rule_type": "regex",    "rule_expression": r"TCKNO MATCHES '^\d{11}$'",
     "description": "Turkish ID number format",
     "pass_count": 5100,  "fail_count": 100, "status": "failed"},

    # Payroll (idx 10)
    {"obj_index": 10, "rule_type": "not_null", "rule_expression": "PERNR IS NOT NULL AND LGART IS NOT NULL",
     "description": "Employee and wage type required",
     "pass_count": None, "fail_count": None, "status": "pending"},
    {"obj_index": 10, "rule_type": "range",    "rule_expression": "FPBEG BETWEEN '2024-01-01' AND '2026-12-31'",
     "description": "Pay period within scope",
     "pass_count": None, "fail_count": None, "status": "pending"},

    # Time (idx 11)
    {"obj_index": 11, "rule_type": "not_null", "rule_expression": "PERNR IS NOT NULL AND WORKDATE IS NOT NULL",
     "description": "Employee and work date required",
     "pass_count": None, "fail_count": None, "status": "pending"},
    {"obj_index": 11, "rule_type": "range",    "rule_expression": "CATSHOURS BETWEEN 0 AND 24",
     "description": "Working hours within valid range",
     "pass_count": None, "fail_count": None, "status": "pending"},

    # Warehouse Stocks (idx 12)
    {"obj_index": 12, "rule_type": "not_null", "rule_expression": "MATNR IS NOT NULL AND WERKS IS NOT NULL",
     "description": "Material and plant required",
     "pass_count": 88500, "fail_count": 500, "status": "passed"},
    {"obj_index": 12, "rule_type": "range",    "rule_expression": "LABST >= 0",
     "description": "Stock quantity non-negative",
     "pass_count": 89000, "fail_count": 0,   "status": "passed"},

    # Bin Locations (idx 13)
    {"obj_index": 13, "rule_type": "unique",   "rule_expression": "LGPLA UNIQUE PER LGNUM+LGTYP",
     "description": "Bin unique per warehouse and storage type",
     "pass_count": 12400, "fail_count": 0,  "status": "passed"},
    {"obj_index": 13, "rule_type": "not_null", "rule_expression": "LGNUM IS NOT NULL",
     "description": "Warehouse number required",
     "pass_count": 12400, "fail_count": 0,  "status": "passed"},

    # BOM (idx 14)
    {"obj_index": 14, "rule_type": "not_null", "rule_expression": "STLNR IS NOT NULL AND MATNR IS NOT NULL",
     "description": "BOM number and material required",
     "pass_count": 66500, "fail_count": 500, "status": "passed"},
    {"obj_index": 14, "rule_type": "lookup",   "rule_expression": "MATNR IN MATERIAL_MASTER_SCOPE",
     "description": "BOM header material in migration scope",
     "pass_count": 65000, "fail_count": 2000, "status": "failed"},
]


# LoadCycles: obj_index, wave_index, environment, load_type, records, status
LOAD_CYCLES = [
    # Wave 1 — Master data in DEV
    {"obj_index": 0, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded": 125000, "failed": 0,    "status": "completed"},
    {"obj_index": 1, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded":  45000, "failed": 0,    "status": "completed"},
    {"obj_index": 2, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded": 335000, "failed": 5000, "status": "completed"},
    {"obj_index": 3, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded":   8200, "failed": 0,    "status": "completed"},
    {"obj_index": 4, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded":   3500, "failed": 0,    "status": "completed"},
    {"obj_index": 5, "wave_index": 0, "env": "DEV", "type": "initial",     "loaded":   1200, "failed": 0,    "status": "completed"},
    # Wave 1 — Customer master delta in DEV
    {"obj_index": 0, "wave_index": 0, "env": "DEV", "type": "delta",       "loaded":    500, "failed": 0,    "status": "completed"},
    # Wave 1 — QAS loads
    {"obj_index": 0, "wave_index": 0, "env": "QAS", "type": "initial",     "loaded": 125000, "failed": 3,    "status": "completed"},
    {"obj_index": 1, "wave_index": 0, "env": "QAS", "type": "initial",     "loaded":  45000, "failed": 0,    "status": "completed"},
    {"obj_index": 3, "wave_index": 0, "env": "QAS", "type": "initial",     "loaded":   8200, "failed": 0,    "status": "completed"},
    # Wave 1 — Material master QAS (failed)
    {"obj_index": 2, "wave_index": 0, "env": "QAS", "type": "initial",     "loaded": 280000, "failed": 55000,"status": "failed",
     "error_log": "MARA mapping error: 55000 records with invalid MTART conversion"},
    # Retry material in QAS
    {"obj_index": 2, "wave_index": 0, "env": "QAS", "type": "full_reload", "loaded": 340000, "failed": 0,    "status": "completed"},
    # Wave 2 — HR DEV
    {"obj_index": 9,  "wave_index": 1, "env": "DEV", "type": "initial",    "loaded":   5200, "failed": 0,    "status": "completed"},
    # Wave 4 — WMS DEV
    {"obj_index": 12, "wave_index": 3, "env": "DEV", "type": "initial",    "loaded":  89000, "failed": 0,    "status": "completed"},
    {"obj_index": 13, "wave_index": 3, "env": "DEV", "type": "initial",    "loaded":  12400, "failed": 0,    "status": "completed"},
    # BOM mock load in DEV
    {"obj_index": 14, "wave_index": 3, "env": "DEV", "type": "mock",       "loaded":   1000, "failed": 50,   "status": "completed"},
    # Running & pending
    {"obj_index": 0,  "wave_index": 0, "env": "PRE", "type": "initial",    "loaded": None,   "failed": None, "status": "running"},
    {"obj_index": 6,  "wave_index": 2, "env": "DEV", "type": "initial",    "loaded": None,   "failed": None, "status": "pending"},
    {"obj_index": 7,  "wave_index": 2, "env": "DEV", "type": "initial",    "loaded": None,   "failed": None, "status": "pending"},
    {"obj_index": 8,  "wave_index": 2, "env": "DEV", "type": "initial",    "loaded": None,   "failed": None, "status": "pending"},
]


# Reconciliations: cycle_index, source, target, match, status
RECONCILIATIONS = [
    {"cycle_index": 0,  "source": 125000, "target": 125000, "match": 125000, "status": "matched"},
    {"cycle_index": 1,  "source":  45000, "target":  45000, "match":  45000, "status": "matched"},
    {"cycle_index": 2,  "source": 340000, "target": 335000, "match": 335000, "status": "variance",
     "notes": "5000 records failed cleansing; excluded from initial load"},
    {"cycle_index": 3,  "source":   8200, "target":   8200, "match":   8200, "status": "matched"},
    {"cycle_index": 4,  "source":   3500, "target":   3500, "match":   3500, "status": "matched"},
    {"cycle_index": 5,  "source":   1200, "target":   1200, "match":   1200, "status": "matched"},
    {"cycle_index": 7,  "source": 125000, "target": 125000, "match": 124997, "status": "variance",
     "notes": "3 records failed validation in QAS; under investigation"},
    {"cycle_index": 8,  "source":  45000, "target":  45000, "match":  45000, "status": "matched"},
    {"cycle_index": 9,  "source":   8200, "target":   8200, "match":   8200, "status": "matched"},
    {"cycle_index": 10, "source": 340000, "target": 280000, "match": 280000, "status": "variance",
     "notes": "55000 records failed due to MTART mapping; full_reload performed"},
    {"cycle_index": 11, "source": 340000, "target": 340000, "match": 340000, "status": "matched"},
    {"cycle_index": 12, "source":   5200, "target":   5200, "match":   5200, "status": "matched"},
    {"cycle_index": 13, "source":  89000, "target":  89000, "match":  89000, "status": "matched"},
    {"cycle_index": 14, "source":  12400, "target":  12400, "match":  12400, "status": "matched"},
    {"cycle_index": 15, "source":   1000, "target":    950, "match":    950, "status": "variance",
     "notes": "50 BOM records failed; mock load for validation purposes"},
]


SEED_SUMMARY = {
    "data_objects": len(DATA_OBJECTS),
    "migration_waves": len(MIGRATION_WAVES),
    "cleansing_tasks": len(CLEANSING_TASKS),
    "load_cycles": len(LOAD_CYCLES),
    "reconciliations": len(RECONCILIATIONS),
}

if __name__ == "__main__":
    for k, v in SEED_SUMMARY.items():
        print(f"  {k}: {v}")
