#!/usr/bin/env python3
"""
Meridian Industries A.Ş. — Comprehensive Seed Script
S/4HANA Greenfield | Chemical & Process Manufacturing | Turkey

Usage:
    python scripts/seed_meridian_data.py

Optional environment overrides:
    MERIDIAN_TENANT_ID=2
    MERIDIAN_PROGRAM_ID=7
    MERIDIAN_PROJECT_ID=9
    MERIDIAN_TENANT_NAME="Meridian Industries"
    MERIDIAN_PROGRAM_NAME="Meridian S/4HANA Program"
    MERIDIAN_PROJECT_NAME="Meridian Default Project"
"""
import os
import sys
import uuid
from datetime import date, datetime, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db

TENANT_ID = int(os.getenv("MERIDIAN_TENANT_ID")) if os.getenv("MERIDIAN_TENANT_ID") else None
PROGRAM_ID = int(os.getenv("MERIDIAN_PROGRAM_ID")) if os.getenv("MERIDIAN_PROGRAM_ID") else None
PROJECT_ID = int(os.getenv("MERIDIAN_PROJECT_ID")) if os.getenv("MERIDIAN_PROJECT_ID") else None
MERIDIAN_TENANT_SLUG = os.getenv("MERIDIAN_TENANT_SLUG", "meridian")
MERIDIAN_PROGRAM_CODE = os.getenv("MERIDIAN_PROGRAM_CODE", "MERIDIAN-S4")
MERIDIAN_PROJECT_CODE = os.getenv("MERIDIAN_PROJECT_CODE", "MERIDIAN-CORE")
EXPECTED_TENANT_NAME = os.getenv("MERIDIAN_TENANT_NAME", "Meridian Industries")
EXPECTED_PROGRAM_NAME = os.getenv("MERIDIAN_PROGRAM_NAME", "Meridian S/4HANA Program")
EXPECTED_PROJECT_NAME = os.getenv("MERIDIAN_PROJECT_NAME", "Meridian Default Project")
NOW = datetime.now(timezone.utc)
ADMIN_USER_ID = "1"  # stored as varchar in explore tables

def uid():
    return str(uuid.uuid4())

def run_sql(sql, params=()):
    db.session.execute(db.text(sql), params)


def fetch_one(sql, params):
    return db.session.execute(db.text(sql), params).mappings().first()


def ensure_target_context() -> None:
    global TENANT_ID, PROGRAM_ID, PROJECT_ID

    tenant = None
    if TENANT_ID is not None:
        tenant = fetch_one(
            "SELECT id, name, slug FROM tenants WHERE id = :tenant_id",
            {"tenant_id": TENANT_ID},
        )
    if tenant is None:
        tenant = fetch_one(
            "SELECT id, name, slug FROM tenants WHERE slug = :slug",
            {"slug": MERIDIAN_TENANT_SLUG},
        )
    if tenant is None:
        db.session.execute(
            db.text(
                """
                INSERT INTO tenants
                    (name, slug, plan, max_users, max_projects, is_active, settings, created_at, updated_at)
                VALUES
                    (:name, :slug, :plan, :max_users, :max_projects, :is_active, CAST(:settings AS JSON), :created_at, :updated_at)
                """
            ),
            {
                "name": EXPECTED_TENANT_NAME,
                "slug": MERIDIAN_TENANT_SLUG,
                "plan": "premium",
                "max_users": 250,
                "max_projects": 25,
                "is_active": True,
                "settings": "{}",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        db.session.flush()
        tenant = fetch_one(
            "SELECT id, name, slug FROM tenants WHERE slug = :slug",
            {"slug": MERIDIAN_TENANT_SLUG},
        )
    TENANT_ID = tenant["id"]

    program = None
    if PROGRAM_ID is not None:
        program = fetch_one(
            "SELECT id, name, tenant_id, code FROM programs WHERE id = :program_id",
            {"program_id": PROGRAM_ID},
        )
    if program is None:
        program = fetch_one(
            "SELECT id, name, tenant_id, code FROM programs WHERE tenant_id = :tenant_id AND code = :code",
            {"tenant_id": TENANT_ID, "code": MERIDIAN_PROGRAM_CODE},
        )
    if program is None:
        db.session.execute(
            db.text(
                """
                INSERT INTO programs
                    (tenant_id, name, description, project_type, methodology, status, priority,
                     sap_product, deployment_option, code, customer_name, customer_industry,
                     customer_country, sponsor_name, sponsor_title, program_director,
                     steerco_frequency, currency, overall_rag, created_at, updated_at)
                VALUES
                    (:tenant_id, :name, :description, :project_type, :methodology, :status, :priority,
                     :sap_product, :deployment_option, :code, :customer_name, :customer_industry,
                     :customer_country, :sponsor_name, :sponsor_title, :program_director,
                     :steerco_frequency, :currency, :overall_rag, :created_at, :updated_at)
                """
            ),
            {
                "tenant_id": TENANT_ID,
                "name": EXPECTED_PROGRAM_NAME,
                "description": "Meridian Industries SAP S/4HANA greenfield transformation program.",
                "project_type": "greenfield",
                "methodology": "sap_activate",
                "status": "active",
                "priority": "high",
                "sap_product": "S/4HANA",
                "deployment_option": "on_premise",
                "code": MERIDIAN_PROGRAM_CODE,
                "customer_name": EXPECTED_TENANT_NAME,
                "customer_industry": "Chemical & Process Manufacturing",
                "customer_country": "Turkey",
                "sponsor_name": "Kenan Caliskan",
                "sponsor_title": "CEO",
                "program_director": "Ahmet Yilmaz",
                "steerco_frequency": "monthly",
                "currency": "EUR",
                "overall_rag": "Amber",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        db.session.flush()
        program = fetch_one(
            "SELECT id, name, tenant_id, code FROM programs WHERE tenant_id = :tenant_id AND code = :code",
            {"tenant_id": TENANT_ID, "code": MERIDIAN_PROGRAM_CODE},
        )
    PROGRAM_ID = program["id"]

    project = None
    if PROJECT_ID is not None:
        project = fetch_one(
            "SELECT id, name, tenant_id, program_id, code FROM projects WHERE id = :project_id",
            {"project_id": PROJECT_ID},
        )
    if project is None:
        project = fetch_one(
            "SELECT id, name, tenant_id, program_id, code FROM projects WHERE program_id = :program_id AND code = :code",
            {"program_id": PROGRAM_ID, "code": MERIDIAN_PROJECT_CODE},
        )
    if project is None:
        db.session.execute(
            db.text(
                """
                INSERT INTO projects
                    (tenant_id, program_id, code, name, type, status, is_default, description,
                     wave_number, sap_product, project_type, methodology, deployment_option,
                     priority, project_rag, rag_scope, rag_timeline, rag_budget, rag_quality,
                     rag_resources, created_at, updated_at)
                VALUES
                    (:tenant_id, :program_id, :code, :name, :type, :status, :is_default, :description,
                     :wave_number, :sap_product, :project_type, :methodology, :deployment_option,
                     :priority, :project_rag, :rag_scope, :rag_timeline, :rag_budget, :rag_quality,
                     :rag_resources, :created_at, :updated_at)
                """
            ),
            {
                "tenant_id": TENANT_ID,
                "program_id": PROGRAM_ID,
                "code": MERIDIAN_PROJECT_CODE,
                "name": EXPECTED_PROJECT_NAME,
                "type": "implementation",
                "status": "active",
                "is_default": True,
                "description": "Default execution project for Meridian S/4HANA transformation scope.",
                "wave_number": 1,
                "sap_product": "S/4HANA",
                "project_type": "greenfield",
                "methodology": "sap_activate",
                "deployment_option": "on_premise",
                "priority": "high",
                "project_rag": "Amber",
                "rag_scope": "Amber",
                "rag_timeline": "Amber",
                "rag_budget": "Green",
                "rag_quality": "Green",
                "rag_resources": "Amber",
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        db.session.flush()
        project = fetch_one(
            "SELECT id, name, tenant_id, program_id, code FROM projects WHERE program_id = :program_id AND code = :code",
            {"program_id": PROGRAM_ID, "code": MERIDIAN_PROJECT_CODE},
        )
    PROJECT_ID = project["id"]


def validate_target_context():
    tenant = fetch_one(
        "SELECT id, name FROM tenants WHERE id = :tenant_id",
        {"tenant_id": TENANT_ID},
    )
    if not tenant:
        raise RuntimeError(f"Tenant {TENANT_ID} does not exist")

    program = fetch_one(
        "SELECT id, name, tenant_id FROM programs WHERE id = :program_id",
        {"program_id": PROGRAM_ID},
    )
    if not program:
        raise RuntimeError(f"Program {PROGRAM_ID} does not exist")

    project = fetch_one(
        "SELECT id, name, tenant_id, program_id FROM projects WHERE id = :project_id",
        {"project_id": PROJECT_ID},
    )
    if not project:
        raise RuntimeError(f"Project {PROJECT_ID} does not exist")

    if program["tenant_id"] != TENANT_ID:
        raise RuntimeError(
            f"Program {PROGRAM_ID} belongs to tenant {program['tenant_id']}, expected tenant {TENANT_ID}"
        )

    if project["tenant_id"] != TENANT_ID:
        raise RuntimeError(
            f"Project {PROJECT_ID} belongs to tenant {project['tenant_id']}, expected tenant {TENANT_ID}"
        )

    if project["program_id"] != PROGRAM_ID:
        raise RuntimeError(
            f"Project {PROJECT_ID} belongs to program {project['program_id']}, expected program {PROGRAM_ID}"
        )

    if EXPECTED_TENANT_NAME and tenant["name"] != EXPECTED_TENANT_NAME:
        raise RuntimeError(
            f"Tenant {TENANT_ID} name mismatch: {tenant['name']!r} != {EXPECTED_TENANT_NAME!r}"
        )

    if EXPECTED_PROGRAM_NAME and program["name"] != EXPECTED_PROGRAM_NAME:
        raise RuntimeError(
            f"Program {PROGRAM_ID} name mismatch: {program['name']!r} != {EXPECTED_PROGRAM_NAME!r}"
        )

    if EXPECTED_PROJECT_NAME and project["name"] != EXPECTED_PROJECT_NAME:
        raise RuntimeError(
            f"Project {PROJECT_ID} name mismatch: {project['name']!r} != {EXPECTED_PROJECT_NAME!r}"
        )

    print(
        "   Target context:",
        f"tenant={tenant['id']}:{tenant['name']}",
        f"program={program['id']}:{program['name']}",
        f"project={project['id']}:{project['name']}",
    )

# ─── Existing Process Step IDs (for explore_decisions FK) ────────────────────
EXISTING_STEPS = [
    "ead834a5-fcdb-4894-bac4-c4cf46cad848",
    "102a7f28-63d2-4629-b451-0d96c71e2820",
    "9066da96-81ef-4d78-8d0f-ff0b659b6795",
    "f652d4ae-4b87-4e54-9257-708d476a6e70",
    "0950289e-291a-46c7-8ae4-2976c9ebe517",
]

PL_CODE_MAP = {
    "L1_OTC": "L1-OTC",
    "L1_PTP": "L1-PTP",
    "L1_RTR": "L1-RTR",
    "L1_PTD": "L1-PTD",
    "L1_HCM": "L1-HCM",
    "L2_SD_SALES": "L2-SD-SALES",
    "L2_SD_SHIP": "L2-SD-SHIP",
    "L2_MM_PROC": "L2-MM-PROC",
    "L2_MM_INV": "L2-MM-INV",
    "L2_FI_GL": "L2-FI-GL",
    "L2_FI_AP": "L2-FI-AP",
    "L2_PP_PLAN": "L2-PP-PLAN",
    "L2_PP_EXEC": "L2-PP-EXEC",
    "L2_HR_PA": "L2-HR-PA",
    "L2_HR_TIME": "L2-HR-TIME",
}
PL: dict[str, str] = {}

PROCESS_LEVEL_SEED = [
    {"code": "L1-OTC", "parent_code": None, "level": 1, "name": "Order to Cash", "area": "SD", "wave": 1, "sort": 1},
    {"code": "L1-PTP", "parent_code": None, "level": 1, "name": "Procure to Pay", "area": "MM", "wave": 1, "sort": 2},
    {"code": "L1-RTR", "parent_code": None, "level": 1, "name": "Record to Report", "area": "FI", "wave": 1, "sort": 3},
    {"code": "L1-PTD", "parent_code": None, "level": 1, "name": "Plan to Deliver", "area": "PP", "wave": 2, "sort": 4},
    {"code": "L1-HCM", "parent_code": None, "level": 1, "name": "Hire to Retire", "area": "HR", "wave": 3, "sort": 5},
    {"code": "L2-SD-SALES", "parent_code": "L1-OTC", "level": 2, "name": "Sales Order Management", "area": "SD", "wave": 1, "sort": 1},
    {"code": "L2-SD-SHIP", "parent_code": "L1-OTC", "level": 2, "name": "Delivery & Shipping", "area": "SD", "wave": 1, "sort": 2},
    {"code": "L2-MM-PROC", "parent_code": "L1-PTP", "level": 2, "name": "Procurement", "area": "MM", "wave": 1, "sort": 1},
    {"code": "L2-MM-INV", "parent_code": "L1-PTP", "level": 2, "name": "Invoice Verification", "area": "MM", "wave": 2, "sort": 2},
    {"code": "L2-FI-GL", "parent_code": "L1-RTR", "level": 2, "name": "General Ledger", "area": "FI", "wave": 1, "sort": 1},
    {"code": "L2-FI-AP", "parent_code": "L1-RTR", "level": 2, "name": "Accounts Payable", "area": "FI", "wave": 2, "sort": 2},
    {"code": "L2-PP-PLAN", "parent_code": "L1-PTD", "level": 2, "name": "Production Planning", "area": "PP", "wave": 2, "sort": 1},
    {"code": "L2-PP-EXEC", "parent_code": "L1-PTD", "level": 2, "name": "Shop Floor Execution", "area": "PP", "wave": 2, "sort": 2},
    {"code": "L2-HR-PA", "parent_code": "L1-HCM", "level": 2, "name": "Personnel Administration", "area": "HR", "wave": 3, "sort": 1},
    {"code": "L2-HR-TIME", "parent_code": "L1-HCM", "level": 2, "name": "Time Management", "area": "HR", "wave": 3, "sort": 2},
]


def _process_level_uuid(code: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"meridian-process-{PROJECT_ID}-{code}"))


def ensure_process_hierarchy() -> None:
    created_by_code: dict[str, str] = {}

    for item in PROCESS_LEVEL_SEED:
        existing = fetch_one(
            "SELECT id FROM process_levels WHERE project_id = :project_id AND code = :code",
            {"project_id": PROJECT_ID, "code": item["code"]},
        )
        if existing:
            created_by_code[item["code"]] = existing["id"]
            continue

        parent_id = created_by_code.get(item["parent_code"]) if item["parent_code"] else None
        db.session.execute(
            db.text(
                """
                INSERT INTO process_levels
                    (id, tenant_id, program_id, project_id, parent_id, level, code, name,
                     description, scope_status, fit_status, bpmn_available,
                     process_area_code, wave, sort_order, consolidated_decision_override,
                     created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :program_id, :project_id, :parent_id, :level, :code, :name,
                     :description, :scope_status, :fit_status, :bpmn_available,
                     :process_area_code, :wave, :sort_order, :consolidated_decision_override,
                     :created_at, :updated_at)
                """
            ),
            {
                "id": _process_level_uuid(item["code"]),
                "tenant_id": TENANT_ID,
                "program_id": PROGRAM_ID,
                "project_id": PROJECT_ID,
                "parent_id": parent_id,
                "level": item["level"],
                "code": item["code"],
                "name": item["name"],
                "description": f"Meridian process hierarchy seed for {item['name']}",
                "scope_status": "in_scope",
                "fit_status": None,
                "bpmn_available": False,
                "process_area_code": item["area"],
                "wave": item["wave"],
                "sort_order": item["sort"],
                "consolidated_decision_override": False,
                "created_at": NOW,
                "updated_at": NOW,
            },
        )
        created_by_code[item["code"]] = _process_level_uuid(item["code"])

    for key, code in PL_CODE_MAP.items():
        row = fetch_one(
            "SELECT id FROM process_levels WHERE project_id = :project_id AND code = :code",
            {"project_id": PROJECT_ID, "code": code},
        )
        if not row:
            raise RuntimeError(f"Missing process level for code {code} in project {PROJECT_ID}")
        PL[key] = row["id"]



# ════════════════════════════════════════════════════════════════════
# 1. STAKEHOLDERS
# ════════════════════════════════════════════════════════════════════
def seed_stakeholders():
    print("  → Stakeholders...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM stakeholders WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if n >= 5:
        print(f"    ⏩ {n} already exist"); return
    rows = [
        ("Ahmet Yılmaz",   "CIO",                  "Meridian Industries",  "ahmet.yilmaz@meridian.com.tr",   "executive_sponsor",     "high",   "high",   "champion",    "supportive"),
        ("Zeynep Aksoy",   "CFO",                  "Meridian Industries",  "zeynep.aksoy@meridian.com.tr",   "key_decision_maker",    "high",   "high",   "engage",      "supportive"),
        ("Murat Kaya",     "VP Finance",            "Meridian Industries",  "murat.kaya@meridian.com.tr",     "key_user",              "high",   "high",   "collaborate", "supportive"),
        ("Elif Şahin",     "Supply Chain Director", "Meridian Industries",  "elif.sahin@meridian.com.tr",     "key_decision_maker",    "high",   "high",   "collaborate", "neutral"),
        ("Serkan Doğan",   "IT Director",           "Meridian Industries",  "serkan.dogan@meridian.com.tr",   "technical_lead",        "high",   "high",   "collaborate", "supportive"),
        ("Fatma Çelik",    "HR Director",           "Meridian Industries",  "fatma.celik@meridian.com.tr",    "key_decision_maker",    "medium", "high",   "engage",      "neutral"),
        ("Baran Arslan",   "Production Manager",    "Meridian - Gebze",     "baran.arslan@meridian.com.tr",   "key_user",              "medium", "high",   "involve",     "neutral"),
        ("Canan Öztürk",   "Plant Controller",      "Meridian - İzmir",     "canan.ozturk@meridian.com.tr",   "key_user",              "medium", "medium", "inform",      "neutral"),
        ("Deniz Polat",    "Procurement Manager",   "Meridian Industries",  "deniz.polat@meridian.com.tr",    "key_user",              "medium", "high",   "involve",     "supportive"),
        ("Emre Korkmaz",   "Sales Director",        "Meridian Industries",  "emre.korkmaz@meridian.com.tr",   "key_decision_maker",    "high",   "medium", "engage",      "resistant"),
        ("Gül Tekin",      "OCM Lead",              "Meridian Industries",  "gul.tekin@meridian.com.tr",      "change_agent",          "medium", "high",   "collaborate", "supportive"),
        ("Hakan Yıldız",   "Quality Manager",       "Meridian Industries",  "hakan.yildiz@meridian.com.tr",   "key_user",              "medium", "medium", "involve",     "neutral"),
        ("İpek Demir",     "Works Council Rep",     "Meridian Industries",  "ipek.demir@meridian.com.tr",     "union_rep",             "high",   "medium", "engage",      "resistant"),
        ("Jale Erdoğan",   "Regulatory Affairs",    "Meridian Industries",  "jale.erdogan@meridian.com.tr",   "subject_matter_expert", "low",    "high",   "inform",      "neutral"),
        ("Kenan Çalışkan", "CEO",                   "Meridian Industries",  "kenan.caliskan@meridian.com.tr", "executive_sponsor",     "high",   "low",    "inform",      "supportive"),
    ]
    for r in rows:
        run_sql("""
            INSERT INTO stakeholders
              (program_id, tenant_id, name, title, organization, email,
               stakeholder_type, influence_level, interest_level,
               engagement_strategy, current_sentiment, is_active, created_at, updated_at)
            VALUES (:prog,:t,:name,:title,:org,:email,:stype,:inf,:int,:eng,:sent,TRUE,:now,:now)
        """, dict(prog=PROGRAM_ID, t=TENANT_ID, name=r[0], title=r[1], org=r[2],
                  email=r[3], stype=r[4], inf=r[5], int=r[6], eng=r[7], sent=r[8], now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} stakeholders")


# ════════════════════════════════════════════════════════════════════
# 2. EXPLORE WORKSHOPS
# ════════════════════════════════════════════════════════════════════
NEW_WS_IDS = {}

def seed_workshops():
    print("  → Explore Workshops...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM explore_workshops WHERE project_id=:p"), {"p": PROJECT_ID}).scalar()
    if n >= 10:
        print(f"    ⏩ {n} already exist"); return
    rows = [
        ("WS-FI-02", "Accounts Payable",           "initial", "completed",   "2026-05-18", "FI", 2),
        ("WS-FI-03", "Accounts Receivable",         "initial", "completed",   "2026-05-25", "FI", 3),
        ("WS-FI-04", "Asset Accounting",            "initial", "in_progress", "2026-06-01", "FI", 4),
        ("WS-CO-01", "Cost Center Accounting",      "initial", "completed",   "2026-05-20", "CO", 1),
        ("WS-CO-02", "Product Costing",             "initial", "in_progress", "2026-06-03", "CO", 2),
        ("WS-MM-03", "Inventory Management",        "initial", "completed",   "2026-05-22", "MM", 3),
        ("WS-MM-04", "Warehouse Management",        "initial", "in_progress", "2026-06-05", "MM", 4),
        ("WS-SD-02", "Pricing & Conditions",        "initial", "completed",   "2026-05-15", "SD", 2),
        ("WS-SD-03", "Billing & Revenue",           "initial", "completed",   "2026-05-29", "SD", 3),
        ("WS-PP-01", "MRP & Production Planning",   "initial", "completed",   "2026-05-28", "PP", 1),
        ("WS-PP-02", "Shop Floor Control",          "initial", "in_progress", "2026-06-08", "PP", 2),
        ("WS-QM-01", "Quality Management",          "initial", "draft",       "2026-06-15", "QM", 1),
        ("WS-HCM-01","Personnel Administration",    "initial", "completed",   "2026-05-26", "HR", 1),
        ("WS-HCM-02","Payroll Turkey",              "initial", "in_progress", "2026-06-10", "HR", 2),
        ("WS-BASIS", "Authorization & Security",    "initial", "draft",       "2026-06-20", "BC", 1),
    ]
    for r in rows:
        code, name, wtype, status, dt, area, sess = r
        wid = uid()
        run_sql("""
            INSERT INTO explore_workshops
              (id, project_id, program_id, tenant_id, code, name, type, status,
               date, process_area, session_number, total_sessions,
               reopen_count, revision_number, created_at, updated_at)
            VALUES (:id,:proj,:prog,:t,:code,:name,:type,:status,
                    :date,:area,:sess,1,0,1,:now,:now)
        """, dict(id=wid, proj=PROJECT_ID, prog=PROGRAM_ID, t=TENANT_ID,
                  code=code, name=name, type=wtype, status=status,
                  date=dt, area=area, sess=sess, now=NOW))
        NEW_WS_IDS[code] = wid
    db.session.flush()

    # Process Steps for workshops (needed for decisions FK)
    step_ids = {}
    for code, wid in NEW_WS_IDS.items():
        pl_map = {
            "WS-FI-02": PL["L2_FI_AP"], "WS-FI-03": PL["L1_OTC"], "WS-FI-04": PL["L1_RTR"],
            "WS-CO-01": PL["L1_RTR"],   "WS-CO-02": PL["L2_PP_PLAN"],
            "WS-MM-03": PL["L2_MM_INV"],"WS-MM-04": PL["L2_MM_INV"],
            "WS-SD-02": PL["L2_SD_SALES"],"WS-SD-03": PL["L2_SD_SALES"],
            "WS-PP-01": PL["L2_PP_PLAN"],"WS-PP-02": PL["L2_PP_EXEC"],
            "WS-QM-01": PL["L2_PP_EXEC"],"WS-HCM-01":PL["L2_HR_PA"],
            "WS-HCM-02":PL["L2_HR_TIME"],"WS-BASIS": PL["L1_OTC"],
        }
        pl_id = pl_map.get(code, PL["L1_OTC"])
        sid = uid()
        run_sql("""
            INSERT INTO process_steps
              (id, workshop_id, process_level_id, sort_order, fit_decision,
               demo_shown, bpmn_reviewed, project_id, program_id, tenant_id)
            VALUES (:id,:w,:pl,0,'standard',FALSE,FALSE,:proj,:prog,:t)
        """, dict(id=sid, w=wid, pl=pl_id, proj=PROJECT_ID, prog=PROGRAM_ID, t=TENANT_ID))
        step_ids[code] = sid
        # Also scope item link
        run_sql("""
            INSERT INTO workshop_scope_items (id, workshop_id, process_level_id, sort_order, program_id, project_id, tenant_id)
            VALUES (:id,:w,:pl,1,:prog,:proj,:t)
        """, dict(id=uid(), w=wid, pl=pl_id, prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID))
    db.session.flush()
    NEW_WS_IDS["_steps"] = step_ids
    print(f"    ✅ {len(rows)} workshops + process steps")


# ════════════════════════════════════════════════════════════════════
# 3. EXPLORE REQUIREMENTS
# ════════════════════════════════════════════════════════════════════
def seed_explore_reqs():
    print("  → Explore Requirements...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM explore_requirements WHERE project_id=:p"), {"p": PROJECT_ID}).scalar()
    if n >= 10:
        print(f"    ⏩ {n} already exist"); return
    # (code, title, type, fit_status, status, sap_module, process_area, priority, pl_id, wricef)
    rows = [
        ("REQ-010","GL Account Master Data Configuration","functional","standard","approved","FI","FI","P1",PL["L2_FI_GL"],False),
        ("REQ-011","Parallel Ledger for IFRS & Local GAAP","enhancement","gap","in_review","FI","FI","P1",PL["L2_FI_GL"],True),
        ("REQ-012","Automatic Payment Program (F110)","functional","standard","approved","FI","FI","P1",PL["L2_FI_AP"],False),
        ("REQ-013","Bank Reconciliation Automation","enhancement","gap","in_review","FI","FI","P2",PL["L2_FI_AP"],True),
        ("REQ-014","Asset Capitalization from Projects","functional","standard","approved","FI","FI","P2",PL["L1_RTR"],False),
        ("REQ-015","Turkey e-Invoice (e-Fatura) via DRC","enhancement","gap","approved","FI","FI","P1",PL["L1_RTR"],True),
        ("REQ-016","Turkey e-Archive Integration","enhancement","gap","in_review","FI","FI","P1",PL["L1_RTR"],True),
        ("REQ-020","Cost Center Hierarchy Design","functional","standard","approved","CO","CO","P1",PL["L1_RTR"],False),
        ("REQ-021","Activity-Based Costing for Chemical Lines","enhancement","gap","in_review","CO","CO","P1",PL["L1_RTR"],True),
        ("REQ-022","Standard Cost Estimate for Chemical Products","functional","standard","approved","CO","CO","P1",PL["L2_PP_PLAN"],False),
        ("REQ-030","Hazardous Material Classification (UN GHS)","functional","standard","approved","MM","MM","P1",PL["L2_MM_PROC"],False),
        ("REQ-031","Source List & Scheduling Agreement","functional","standard","approved","MM","MM","P2",PL["L2_MM_PROC"],False),
        ("REQ-032","EWM Integration for Warehouse Movements","enhancement","gap","in_review","EWM","MM","P1",PL["L2_MM_INV"],True),
        ("REQ-033","Batch Management for Chemicals","functional","standard","approved","MM","MM","P1",PL["L2_MM_INV"],False),
        ("REQ-034","Shelf Life Management for Raw Materials","enhancement","gap","approved","MM","MM","P1",PL["L2_MM_INV"],True),
        ("REQ-040","Customer-Specific Pricing with Formulas","enhancement","gap","approved","SD","SD","P1",PL["L2_SD_SALES"],True),
        ("REQ-041","Dangerous Goods Processing in SD","functional","standard","approved","SD","SD","P1",PL["L2_SD_SALES"],False),
        ("REQ-042","Route Determination for Chemical Distribution","enhancement","gap","in_review","SD","SD","P2",PL["L2_SD_SHIP"],True),
        ("REQ-043","Output Management — Customer Documents","functional","standard","approved","SD","SD","P2",PL["L2_SD_SHIP"],False),
        ("REQ-044","EDI Integration for Top 10 Customers","enhancement","gap","in_review","SD","SD","P1",PL["L2_SD_SALES"],True),
        ("REQ-050","Recipe Management for Chemical Production","functional","standard","approved","PP","PP","P1",PL["L2_PP_PLAN"],False),
        ("REQ-051","Batch Classification for In-Process Control","functional","standard","approved","PP","PP","P1",PL["L2_PP_PLAN"],False),
        ("REQ-052","HACCP Compliance Quality Inspection","enhancement","gap","in_review","QM","PP","P1",PL["L2_PP_EXEC"],True),
        ("REQ-053","Capacity Planning — Reactor Lines","functional","standard","in_review","PP","PP","P1",PL["L2_PP_PLAN"],False),
        ("REQ-054","PM Integration for Equipment Maintenance","enhancement","gap","approved","PM","PP","P2",PL["L2_PP_EXEC"],True),
        ("REQ-060","Turkish Labor Law Payroll Configuration","functional","standard","approved","HCM","HR","P1",PL["L2_HR_PA"],False),
        ("REQ-061","Shift Planning for 3-Shift Production","functional","standard","approved","HCM","HR","P1",PL["L2_HR_TIME"],False),
        ("REQ-062","SGK Social Insurance Integration","enhancement","gap","approved","HCM","HR","P1",PL["L2_HR_PA"],True),
        ("REQ-063","Performance Management Cycle","enhancement","gap","in_review","HCM","HR","P2",PL["L2_HR_PA"],True),
        ("REQ-070","Fiori Launchpad Role-Based Tiles","functional","standard","approved","BC","BC","P1",PL["L1_OTC"],False),
        ("REQ-071","SSO Integration with Active Directory","enhancement","gap","approved","BC","BC","P1",PL["L1_OTC"],True),
    ]
    for r in rows:
        code, title, rtype, fit, status, sap_mod, area, priority, pl_id, wricef = r
        run_sql("""
            INSERT INTO explore_requirements
              (id, project_id, program_id, tenant_id, code, title, type,
               fit_status, status, sap_module, process_area, priority,
               process_level_id, wricef_candidate, created_by_id, alm_synced,
               created_at, updated_at)
            VALUES (:id,:proj,:prog,:t,:code,:title,:type,
                    :fit,:status,:mod,:area,:priority,
                                        :pl,:wricef,:creator,FALSE,:now,:now)
        """, dict(id=uid(), proj=PROJECT_ID, prog=PROGRAM_ID, t=TENANT_ID,
                  code=code, title=title, type=rtype, fit=fit, status=status,
                  mod=sap_mod, area=area, priority=priority, pl=pl_id,
                                    wricef=wricef, creator=ADMIN_USER_ID, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} explore requirements")


# ════════════════════════════════════════════════════════════════════
# 4. EXPLORE OPEN ITEMS
# ════════════════════════════════════════════════════════════════════
def seed_explore_open_items():
    print("  → Explore Open Items...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM explore_open_items WHERE project_id=:p"), {"p": PROJECT_ID}).scalar()
    if n >= 5:
        print(f"    ⏩ {n} already exist"); return
    # category values: clarification, question, risk, decision, assumption
    # priority values: P1, P2, P3
    rows = [
        ("OI-002","GL Account mapping for legacy ECC requires Finance sign-off","clarification","open","P1","FI"),
        ("OI-003","Parallel ledger currency decision (TRY + EUR + USD)","decision","open","P1","FI"),
        ("OI-004","e-Invoice go-live date alignment with GİB requirements","risk","open","P1","FI"),
        ("OI-005","Batch determination logic for chemical blending not defined","clarification","open","P1","PP"),
        ("OI-006","EWM putaway strategy for hazardous materials area","question","open","P1","MM"),
        ("OI-007","Customer pricing formula logic — confirmed by Sales Director?","clarification","open","P1","SD"),
        ("OI-008","SGK integration middleware selection (BTP vs. custom)","decision","open","P1","HR"),
        ("OI-009","Fiori tile authorization concept pending Basis decision","question","open","P2","BC"),
        ("OI-010","Turkish payroll retroactive calculation scope","clarification","open","P1","HR"),
        ("OI-011","HACCP inspection lot config requires QM consultant input","clarification","open","P1","PP"),
        ("OI-012","Transport route master data ownership SD vs. Logistics","question","open","P2","SD"),
        ("OI-013","Cost center hierarchy 3rd level approval from CFO pending","decision","open","P1","CO"),
        ("OI-014","EDI message types for Migros to be confirmed","clarification","open","P1","SD"),
        ("OI-015","Asset depreciation area configuration for IFRS15","clarification","open","P1","FI"),
        ("OI-016","Shelf life check config for export batches","question","open","P2","MM"),
    ]
    for r in rows:
        code, title, category, status, priority, area = r
        run_sql("""
            INSERT INTO explore_open_items
              (id, project_id, program_id, tenant_id, code, title, category,
               status, priority, process_area, created_by_id, created_at, updated_at)
            VALUES (:id,:proj,:prog,:t,:code,:title,:cat,
                    :status,:priority,:area,:creator,:now,:now)
        """, dict(id=uid(), proj=PROJECT_ID, prog=PROGRAM_ID, t=TENANT_ID,
                  code=code, title=title, cat=category, status=status,
                  priority=priority, area=area, creator=ADMIN_USER_ID, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} open items")


# ════════════════════════════════════════════════════════════════════
# 5. EXPLORE DECISIONS
# ════════════════════════════════════════════════════════════════════
def seed_explore_decisions():
    print("  → Explore Decisions...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM explore_decisions WHERE project_id=:p"), {"p": PROJECT_ID}).scalar()
    if n >= 5:
        print(f"    ⏩ {n} already exist"); return

    # Get step IDs — prefer newly created, fall back to existing
    steps = NEW_WS_IDS.get("_steps", {})
    step_list = list(steps.values()) if steps else EXISTING_STEPS
    if not step_list:
        step_list = EXISTING_STEPS
    def step(i):
        return step_list[i % len(step_list)]

    # category: process, config, scope, data, technical
    rows = [
        ("DEC-EXP-01","Standard batch management — no custom split logic","Umut Kaya","config","decided"),
        ("DEC-EXP-02","SAP BTP CPI for all external integrations","Serkan Doğan","technical","decided"),
        ("DEC-EXP-03","Parallel ledger: Extension Ledger for IFRS","Murat Kaya","config","decided"),
        ("DEC-EXP-04","Embedded EWM for Gebze and İzmir plants","Elif Şahin","config","decided"),
        ("DEC-EXP-05","Fiori-first UI — no SAP GUI for end users","Serkan Doğan","technical","decided"),
        ("DEC-EXP-06","e-Invoice via SAP DRC (Document & Reporting Compliance)","Serkan Doğan","technical","decided"),
        ("DEC-EXP-07","Single plant per company code — MER01 (TR) + MER02 (NL)","Murat Kaya","config","decided"),
        ("DEC-EXP-08","Payroll via SAP HCM on-premise — not SuccessFactors","Fatma Çelik","scope","proposed"),
        ("DEC-EXP-09","HACCP inspection points in QM — not standalone system","Hakan Yıldız","config","decided"),
        ("DEC-EXP-10","Customer pricing via condition technique — no CPQ","Emre Korkmaz","config","proposed"),
    ]
    for i, r in enumerate(rows):
        code, text, decided_by, category, status = r
        run_sql("""
            INSERT INTO explore_decisions
              (id, project_id, program_id, tenant_id, process_step_id,
               code, text, decided_by, category, status, created_at)
            VALUES (:id,:proj,:prog,:t,:step,
                    :code,:text,:by,:cat,:status,:now)
        """, dict(id=uid(), proj=PROJECT_ID, prog=PROGRAM_ID, t=TENANT_ID,
                  step=step(i), code=code, text=text, by=decided_by,
                  cat=category, status=status, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} explore decisions")


# ════════════════════════════════════════════════════════════════════
# 6. SPRINTS
# ════════════════════════════════════════════════════════════════════
SPRINT_IDS = []

def seed_sprints():
    print("  → Sprints...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM sprints WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if n >= 3:
        ids = db.session.execute(db.text("SELECT id FROM sprints WHERE program_id=:p ORDER BY id"), {"p": PROGRAM_ID}).fetchall()
        SPRINT_IDS.extend([r[0] for r in ids])
        print(f"    ⏩ {n} sprints exist"); return
    rows = [
        ("Sprint 1 — Foundation Config","FI/CO base config, org structure, master data","completed","2026-01-05","2026-01-30",80,78,1),
        ("Sprint 2 — Procurement & Inventory","MM procurement, inventory, EWM setup","completed","2026-02-02","2026-02-27",80,72,2),
        ("Sprint 3 — Sales & Billing","SD order-to-cash, pricing, billing","completed","2026-03-02","2026-03-27",80,68,3),
        ("Sprint 4 — Production & Quality","PP/QM recipe, MRP, inspection lots","in_progress","2026-03-30","2026-04-24",80,0,4),
        ("Sprint 5 — Integration & Data Migration","BTP CPI interfaces, LTMC wave 1, e-Invoice","not_started","2026-04-27","2026-05-22",80,0,5),
        ("Sprint 6 — HCM & Payroll","Turkish payroll, time management, SGK","not_started","2026-05-25","2026-06-19",80,0,6),
    ]
    for r in rows:
        name, goal, status, start, end, cap, vel, order = r
        res = db.session.execute(db.text("""
            INSERT INTO sprints
              (program_id, project_id, tenant_id, name, goal, status,
               start_date, end_date, capacity_points, velocity, "order", created_at, updated_at)
            VALUES (:prog,:proj,:t,:name,:goal,:status,:start,:end,:cap,:vel,:ord,:now,:now)
            RETURNING id
        """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, name=name,
                   goal=goal, status=status, start=start, end=end,
                   cap=cap, vel=vel, ord=order, now=NOW))
        SPRINT_IDS.append(res.fetchone()[0])
    db.session.flush()
    print(f"    ✅ {len(rows)} sprints")


# ════════════════════════════════════════════════════════════════════
# 7. BACKLOG ITEMS (WRICEF)
# ════════════════════════════════════════════════════════════════════
def seed_backlog():
    print("  → Backlog Items (WRICEF)...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM backlog_items WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if n >= 10:
        print(f"    ⏩ {n} already exist"); return
    sp = lambda i: SPRINT_IDS[i] if len(SPRINT_IDS) > i else None
    # (code, title, wricef_type, module, status, priority, complexity, pts, hrs, sprint_idx, tx)
    rows = [
        ("W-FI-001","e-Fatura/e-Arşiv Output via DRC","workflow","FI","done","critical","complex",13,80,0,""),
        ("W-FI-002","Parallel Ledger IFRS Posting Logic","enhancement","FI","done","high","medium",8,40,0,""),
        ("W-FI-003","F110 Payment Run — Bank File ISO20022","workflow","FI","done","high","complex",8,48,0,"F110"),
        ("W-CO-001","Activity-Based Costing Template Allocation","enhancement","CO","done","high","medium",5,32,0,"KB15N"),
        ("W-CO-002","Standard Cost Estimate Release Report","report","CO","in_progress","medium","simple",3,16,1,"CK40N"),
        ("W-MM-001","Hazardous Material Master Data Extension","enhancement","MM","done","critical","medium",8,40,1,"MM01"),
        ("W-MM-002","Batch Classification for UN GHS","configuration","MM","done","critical","complex",8,48,1,"MSC1N"),
        ("W-MM-003","EWM Putaway Strategy for Hazmat Zone","enhancement","EWM","in_progress","high","complex",13,64,1,""),
        ("W-MM-004","Shelf Life Check on GR (FEFO)","enhancement","MM","done","high","medium",5,24,1,"MIGO"),
        ("W-SD-001","Customer-Specific Price Formula","enhancement","SD","done","high","complex",13,72,2,"VK11"),
        ("W-SD-002","Dangerous Goods Document Output","report","SD","done","critical","medium",8,40,2,"VT01N"),
        ("W-SD-003","EDI ORDERS05 Inbound — Top Customers","interface","SD","in_progress","high","complex",13,80,2,""),
        ("W-SD-004","Billing Output — e-Invoice Link","workflow","SD","done","high","medium",5,32,2,"VF01"),
        ("W-SD-005","Route Determination Enhancement","enhancement","SD","in_progress","medium","medium",5,24,2,"VR01"),
        ("W-PP-001","Recipe Management Custom Validations","enhancement","PP","in_progress","critical","complex",13,64,3,"C201"),
        ("W-PP-002","Batch Classification for In-Process QM","configuration","PP","in_progress","high","medium",8,40,3,"CT04"),
        ("W-PP-003","HACCP Inspection Point Configuration","configuration","QM","not_started","critical","complex",8,48,3,"QS21"),
        ("W-PP-004","Capacity Leveling — Reactor Lines","enhancement","PP","not_started","high","complex",13,64,3,"CM21"),
        ("W-PP-005","PM Work Order Integration with PP","interface","PM","not_started","medium","medium",5,32,4,""),
        ("W-INT-001","BTP CPI: SAP ↔ Bank (ISO20022)","interface","BTP","in_progress","critical","complex",13,96,4,""),
        ("W-INT-002","BTP CPI: SAP ↔ Customs BEXIS","interface","BTP","in_progress","critical","complex",13,80,4,""),
        ("W-INT-003","BTP CPI: SAP ↔ EDI Platform","interface","BTP","not_started","high","complex",8,64,4,""),
        ("W-INT-004","BTP CPI: SAP ↔ MES (OPC-UA)","interface","BTP","not_started","high","complex",13,96,4,""),
        ("W-INT-005","BTP CPI: SAP ↔ Logistics Carrier API","interface","BTP","not_started","medium","medium",8,48,4,""),
        ("W-HCM-001","Turkish Payroll Schema Customization","enhancement","HCM","not_started","critical","complex",13,80,5,"PE01"),
        ("W-HCM-002","SGK Middleware Integration (SOAP)","interface","HCM","not_started","critical","complex",13,96,5,""),
        ("W-HCM-003","3-Shift Time Evaluation Schema","enhancement","HCM","not_started","high","complex",8,48,5,"PT60"),
        ("W-HCM-004","HR Self-Service Fiori (Leave, Payslip)","enhancement","HCM","not_started","medium","medium",8,40,5,""),
        ("W-DM-001","LTMC: Customer Master Migration","conversion","MM","in_progress","critical","complex",13,64,1,""),
        ("W-DM-002","LTMC: Vendor Master Migration","conversion","MM","in_progress","critical","medium",8,48,1,""),
        ("W-DM-003","LTMC: Material Master (6,500 SKUs)","conversion","MM","in_progress","critical","complex",13,80,1,""),
        ("W-DM-004","LTMC: Open Purchase Orders Migration","conversion","MM","not_started","high","medium",8,40,4,""),
        ("W-DM-005","LTMC: FI Open Items (AR/AP)","conversion","FI","not_started","critical","complex",13,64,4,""),
        ("W-DM-006","LTMC: Asset Migration (2,100 assets)","conversion","FI","not_started","high","complex",13,80,4,""),
        ("W-AUTH-001","Authorization Role Design — FI/CO","configuration","BC","done","high","complex",8,48,0,"PFCG"),
        ("W-AUTH-002","Authorization Role Design — MM/SD","configuration","BC","in_progress","high","complex",8,48,1,"PFCG"),
        ("W-AUTH-003","SSO SAML2 with Active Directory","interface","BC","not_started","high","complex",8,48,5,""),
        ("W-RPT-001","Management Report — Chemical KPIs","report","CO","not_started","high","medium",8,48,5,""),
        ("W-RPT-002","Regulatory Report — GHS Safety Data Sheet","report","MM","not_started","medium","medium",5,32,5,""),
        ("W-RPT-003","Financial Consolidation Report (TR + NL)","report","FI","not_started","high","complex",8,48,5,""),
    ]
    for idx, r in enumerate(rows):
        code, title, wtype, module, status, priority, complexity, pts, hrs, sp_idx, tx = r
        run_sql("""
            INSERT INTO backlog_items
              (program_id, project_id, tenant_id, code, title, wricef_type, module,
               transaction_code, status, priority, complexity, story_points,
               estimated_hours, sprint_id, board_order, created_at, updated_at)
            VALUES (:prog,:proj,:t,:code,:title,:wtype,:module,:tx,:status,
                    :priority,:complexity,:pts,:hrs,:sprint,:ord,:now,:now)
        """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                  wtype=wtype, module=module, tx=tx, status=status, priority=priority,
                  complexity=complexity, pts=pts, hrs=hrs, sprint=sp(sp_idx),
                  ord=idx+1, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} backlog items")


# ════════════════════════════════════════════════════════════════════
# 8. CONFIG ITEMS
# ════════════════════════════════════════════════════════════════════
def seed_config_items():
    print("  → Config Items...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM config_items WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if n >= 5:
        print(f"    ⏩ {n} already exist"); return
    rows = [
        ("CFG-FI-001","Company Code MER01 (Turkey)","FI","SPRO","done","critical","simple",8),
        ("CFG-FI-002","Fiscal Year Variant — Turkish Calendar","FI","OB29","done","high","simple",4),
        ("CFG-FI-003","Chart of Accounts MERI (Chemical)","FI","OB13","done","critical","medium",16),
        ("CFG-FI-004","Posting Period Variant","FI","OBBO","done","high","simple",4),
        ("CFG-FI-005","Document Number Ranges","FI","FBN1","done","high","simple",8),
        ("CFG-CO-001","Controlling Area MER1","CO","OKKP","done","critical","simple",4),
        ("CFG-CO-002","Cost Center Standard Hierarchy","CO","OKEON","done","critical","medium",16),
        ("CFG-CO-003","Profit Center Hierarchy","CO","KCH1","done","high","medium",12),
        ("CFG-CO-004","Internal Order Types","CO","KOT2","done","medium","simple",8),
        ("CFG-MM-001","Plants — 1000 Gebze / 2000 İzmir","MM","SPRO","done","critical","simple",4),
        ("CFG-MM-002","Storage Locations — All Plants","MM","SPRO","done","high","simple",8),
        ("CFG-MM-003","Material Types (CHEM/FERT/HAWA/ROH)","MM","OMS2","done","critical","medium",12),
        ("CFG-MM-004","Purchasing Organization","MM","SPRO","done","high","simple",4),
        ("CFG-MM-005","Batch Management Level: Material","MM","OMCE","done","critical","simple",8),
        ("CFG-SD-001","Sales Organization MER-TR / MER-EXPORT","SD","SPRO","done","critical","simple",4),
        ("CFG-SD-002","Pricing Procedure ZMERPRI","SD","SPRO","done","high","complex",32),
        ("CFG-SD-003","Output Types — Order/Delivery/Invoice","SD","NACE","done","high","medium",16),
        ("CFG-PP-001","Production Scheduling Profile","PP","SPRO","in_progress","high","medium",16),
        ("CFG-PP-002","MRP Parameters per Plant/MRP Area","PP","OMDU","in_progress","critical","complex",32),
        ("CFG-QM-001","Inspection Types 01/10/04/89","QM","SPRO","not_started","high","medium",16),
        ("CFG-HCM-001","Personnel Area/Subarea — Turkey","HCM","SPRO","not_started","critical","medium",16),
        ("CFG-HCM-002","Payroll Area — Monthly / Biweekly","HCM","OH11","not_started","critical","medium",12),
    ]
    for r in rows:
        code, title, module, tx, status, priority, complexity, hrs = r
        run_sql("""
            INSERT INTO config_items
              (program_id, project_id, tenant_id, code, title, module,
               transaction_code, status, priority, complexity, estimated_hours,
               created_at, updated_at)
            VALUES (:prog,:proj,:t,:code,:title,:module,:tx,:status,
                    :priority,:complexity,:hrs,:now,:now)
        """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                  module=module, tx=tx, status=status, priority=priority,
                  complexity=complexity, hrs=hrs, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} config items")


# ════════════════════════════════════════════════════════════════════
# 9. TESTING — Suites, Plan, Cycles, Cases, Steps, Runs, Defects
# ════════════════════════════════════════════════════════════════════
SUITE_IDS = {}
PLAN_ID = None
CYCLE_IDS = {}
TC_IDS = {}

def seed_testing():
    global PLAN_ID
    print("  → Test Suites...")
    ns = db.session.execute(db.text("SELECT COUNT(*) FROM test_suites WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if ns < 2:
        suite_rows = [
            ("Finance (FI/CO) Test Suite", "FI", "functional"),
            ("Materials Management Test Suite", "MM", "functional"),
            ("Sales & Distribution Test Suite", "SD", "functional"),
            ("Production Planning Test Suite", "PP", "functional"),
            ("Integration Test Suite", None, "integration"),
            ("Regression Test Suite — Core", None, "regression"),
            ("UAT Suite — End-to-End", None, "uat"),
            ("Performance & Load Suite", None, "performance"),
        ]
        keys = ["TS-FI","TS-MM","TS-SD","TS-PP","TS-INT","TS-REG","TS-UAT","TS-PERF"]
        for idx, (name, module, stype) in enumerate(suite_rows):
            res = db.session.execute(db.text("""
                INSERT INTO test_suites
                  (program_id, project_id, tenant_id, name, module, purpose,
                   status, sort_order, created_at, updated_at)
                VALUES (:prog,:proj,:t,:name,:mod,:purpose,'active',:ord,:now,:now)
                RETURNING id
            """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID,
                       name=name, mod=module, purpose=stype, ord=idx+1, now=NOW))
            SUITE_IDS[keys[idx]] = res.fetchone()[0]
        db.session.flush()
        print(f"    ✅ {len(suite_rows)} test suites")
    else:
        rows = db.session.execute(db.text("SELECT id FROM test_suites WHERE program_id=:p ORDER BY id"), {"p": PROGRAM_ID}).fetchall()
        for i, r in enumerate(rows[:8]):
            SUITE_IDS[["TS-FI","TS-MM","TS-SD","TS-PP","TS-INT","TS-REG","TS-UAT","TS-PERF"][i]] = r[0]
        print(f"    ⏩ {ns} suites exist")

    print("  → Test Plan...")
    np = db.session.execute(db.text("SELECT COUNT(*) FROM test_plans WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if np < 1:
        res = db.session.execute(db.text("""
            INSERT INTO test_plans
              (program_id, project_id, tenant_id, name, description, status,
               plan_type, environment, start_date, end_date, created_at, updated_at)
            VALUES (:prog,:proj,:t,
                    'Meridian S/4HANA — SIT Master Test Plan',
                    'System Integration Testing: FI, CO, MM, SD, PP, QM, HCM, BTP',
                                        'active','sit','QAS','2026-01-15','2026-06-30',:now,:now)
            RETURNING id
        """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, now=NOW))
        PLAN_ID = res.fetchone()[0]
        db.session.flush()
        print(f"    ✅ Test Plan id={PLAN_ID}")
    else:
        PLAN_ID = db.session.execute(db.text("SELECT id FROM test_plans WHERE program_id=:p ORDER BY id LIMIT 1"), {"p": PROGRAM_ID}).scalar()
        print(f"    ⏩ Plan exists id={PLAN_ID}")

    print("  → Test Cycles...")
    nc = db.session.execute(db.text("SELECT COUNT(*) FROM test_cycles WHERE plan_id=:p"), {"p": PLAN_ID}).scalar()
    if nc < 2:
        cycle_rows = [
            ("SIT Round 1 — FI/CO/MM","sit","DEV","completed","2026-01-15","2026-01-31"),
            ("SIT Round 2 — SD/PP/QM","sit","QAS","completed","2026-02-03","2026-02-21"),
            ("SIT Round 3 — Integration & Regression","integration","QAS","in_progress","2026-03-02","2026-03-28"),
            ("UAT Round 1 — Finance Users","uat","PRE","not_started","2026-07-01","2026-07-31"),
            ("UAT Round 2 — Operations Users","uat","PRE","not_started","2026-08-04","2026-08-29"),
            ("Performance — Load & Stress","performance","QAS","not_started","2026-09-01","2026-09-15"),
        ]
        ckeys = ["SIT-01","SIT-02","SIT-03","UAT-01","UAT-02","PERF-01"]
        for idx, (name, layer, env, status, start, end) in enumerate(cycle_rows):
            res = db.session.execute(db.text("""
                INSERT INTO test_cycles
                  (plan_id, tenant_id, name, test_layer, environment, status,
                   start_date, end_date, "order", created_at, updated_at)
                VALUES (:plan,:t,:name,:layer,:env,:status,:start,:end,:ord,:now,:now)
                RETURNING id
            """), dict(plan=PLAN_ID, t=TENANT_ID, name=name, layer=layer, env=env,
                       status=status, start=start, end=end, ord=idx+1, now=NOW))
            CYCLE_IDS[ckeys[idx]] = res.fetchone()[0]
        db.session.flush()
        print(f"    ✅ {len(cycle_rows)} test cycles")
    else:
        rows = db.session.execute(db.text("SELECT id FROM test_cycles WHERE plan_id=:p ORDER BY id"), {"p": PLAN_ID}).fetchall()
        for i, r in enumerate(rows[:6]):
            CYCLE_IDS[["SIT-01","SIT-02","SIT-03","UAT-01","UAT-02","PERF-01"][i]] = r[0]
        print(f"    ⏩ {nc} cycles exist")

    print("  → Test Cases...")
    ntc = db.session.execute(db.text("SELECT COUNT(*) FROM test_cases WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if ntc < 5:
        tc_rows = [
            ("TC-FI-001","Post GL Document — Standard Entry","FI","unit","functional","high","TS-FI","FB50"),
            ("TC-FI-002","GL Account Balance Report","FI","unit","functional","medium","TS-FI","FS10N"),
            ("TC-FI-003","Automatic Payment Run F110","FI","sit","functional","critical","TS-FI","F110"),
            ("TC-FI-004","e-Invoice Generation and Transmission","FI","sit","functional","critical","TS-INT",""),
            ("TC-FI-005","IFRS Parallel Ledger Posting Validation","FI","sit","functional","high","TS-FI","FB03"),
            ("TC-CO-001","Create Cost Center","CO","unit","functional","high","TS-FI","KS01"),
            ("TC-CO-002","Post Actual Costs to Cost Center","CO","unit","functional","high","TS-FI","KB15N"),
            ("TC-CO-003","Run Standard Cost Estimate for Product","CO","sit","functional","critical","TS-FI","CK11N"),
            ("TC-MM-001","Create Hazardous Material Master","MM","unit","functional","critical","TS-MM","MM01"),
            ("TC-MM-002","Create Purchase Order — Hazmat","MM","unit","functional","high","TS-MM","ME21N"),
            ("TC-MM-003","Goods Receipt with Batch Assignment","MM","sit","functional","critical","TS-MM","MIGO"),
            ("TC-MM-004","Shelf Life Check on Goods Receipt","MM","sit","functional","high","TS-MM","MIGO"),
            ("TC-MM-005","Batch Classification — GHS Attributes","MM","unit","functional","critical","TS-MM","MSC1N"),
            ("TC-MM-006","Invoice Verification — 3-Way Match","MM","sit","functional","high","TS-MM","MIRO"),
            ("TC-SD-001","Create Sales Order — Chemical Product","SD","unit","functional","critical","TS-SD","VA01"),
            ("TC-SD-002","Apply Customer-Specific Price Formula","SD","sit","functional","high","TS-SD","VK11"),
            ("TC-SD-003","Dangerous Goods Check on Delivery","SD","sit","functional","critical","TS-SD","VL01N"),
            ("TC-SD-004","Create Invoice and e-Invoice Output","SD","sit","functional","critical","TS-INT","VF01"),
            ("TC-SD-005","EDI Order Receipt — Inbound ORDERS05","SD","sit","integration","high","TS-INT",""),
            ("TC-PP-001","Create Production Order from MRP","PP","unit","functional","critical","TS-PP","MD04"),
            ("TC-PP-002","Goods Issue to Production Order","PP","sit","functional","high","TS-PP","MIGO"),
            ("TC-PP-003","Quality Inspection Lot — HACCP Check","PP","sit","functional","critical","TS-PP","QA01"),
            ("TC-PP-004","Goods Receipt from Production Order","PP","sit","functional","high","TS-PP","MIGO"),
            ("TC-INT-001","BTP CPI: Bank Payment File Generation","BTP","integration","integration","critical","TS-INT",""),
            ("TC-INT-002","BTP CPI: Customs BEXIS Outbound","BTP","integration","integration","critical","TS-INT",""),
            ("TC-INT-003","BTP CPI: MES Order Sync (OPC-UA)","BTP","integration","integration","high","TS-INT",""),
            ("TC-E2E-001","E2E: Procure-to-Pay Chemical Raw Material","MM","sit","end_to_end","critical","TS-REG",""),
            ("TC-E2E-002","E2E: Order-to-Cash with e-Invoice","SD","sit","end_to_end","critical","TS-REG",""),
            ("TC-E2E-003","E2E: Plan-to-Produce Chemical Batch","PP","sit","end_to_end","critical","TS-REG",""),
            ("TC-E2E-004","E2E: Record-to-Report Month-End Close","FI","uat","end_to_end","critical","TS-UAT",""),
        ]
        for tc in tc_rows:
            code, title, module, layer, ttype, priority, suite_key, tx = tc
            res = db.session.execute(db.text("""
                INSERT INTO test_cases
                  (program_id, project_id, tenant_id, code, title, module,
                   test_layer, test_type, transaction_code,
                   status, priority, created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:module,:layer,:ttype,
                        :tx,'active',:priority,:now,:now)
                RETURNING id
            """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID,
                       code=code, title=title, module=module, layer=layer, ttype=ttype,
                       tx=tx, priority=priority, now=NOW))
            tc_id = res.fetchone()[0]
            TC_IDS[code] = tc_id
            suite_id = SUITE_IDS.get(suite_key)
            if suite_id:
                run_sql("""
                    INSERT INTO test_case_suite_links
                      (tenant_id, test_case_id, suite_id, added_method, notes, created_at)
                    VALUES (:t,:tc,:suite,'seed','',:now)
                """, dict(t=TENANT_ID, tc=tc_id, suite=suite_id, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(tc_rows)} test cases")
    else:
        rows = db.session.execute(db.text("SELECT code, id FROM test_cases WHERE program_id=:p ORDER BY id"), {"p": PROGRAM_ID}).fetchall()
        for code, tcid in rows:
            TC_IDS[code] = tcid
        print(f"    ⏩ {ntc} test cases exist")

    # Test Steps
    nstep = db.session.execute(db.text("""
        SELECT COUNT(*) FROM test_steps
        WHERE test_case_id IN (SELECT id FROM test_cases WHERE program_id=:p)
    """), {"p": PROGRAM_ID}).scalar()
    if nstep < 3 and TC_IDS:
        step_data = {
            "TC-FI-001": [
                (1,"Navigate to FB50 — Enter G/L Account Document","FB50 screen opens","Company code MER01"),
                (2,"Enter posting date, document type SA","Header accepted","Date: 2026-03-10"),
                (3,"Enter debit line: GL 400000, amount 10,000 EUR","Line accepted",""),
                (4,"Enter credit line: GL 200000, amount 10,000 EUR","Document balanced",""),
                (5,"Post document","Document number assigned",""),
            ],
            "TC-MM-003": [
                (1,"Navigate to MIGO → GR → Purchase Order","MIGO screen opens","PO: 4500001001"),
                (2,"Enter PO number and press Enter","PO items appear",""),
                (3,"Enter batch number in batch field","Batch assigned","Batch: M2026-001"),
                (4,"Enter storage location","SLoc accepted","SLoc: 0001"),
                (5,"Set Item OK flag and post","Material document created",""),
            ],
            "TC-SD-001": [
                (1,"Navigate to VA01 — Create Sales Order","Order type screen opens","Order type: ZOR"),
                (2,"Enter sales org MER-TR, dist channel 10, division CH","Header screen opens",""),
                (3,"Enter sold-to party: customer 1000 (Migros)","Customer data populated",""),
                (4,"Enter material CHEM-001, qty 5,000 KG","Pricing determined",""),
                (5,"Check dangerous goods indicator set automatically","DG check active",""),
                (6,"Save order","Sales order number assigned",""),
            ],
            "TC-PP-003": [
                (1,"Navigate to QA01 — Create Inspection Lot","Inspection lot screen opens","Lot origin: 04"),
                (2,"Enter material, plant, batch","Lot created with characteristics","Material: CHEM-001"),
                (3,"Record HACCP: Temperature check","Result within limits","Spec: 60-80°C"),
                (4,"Record HACCP: pH check","Result within limits","Spec: 6.5-7.5"),
                (5,"Usage decision: Accept batch (UD: A)","Batch set to Unrestricted",""),
            ],
        }
        for tc_code, steps in step_data.items():
            tc_id = TC_IDS.get(tc_code)
            if not tc_id:
                continue
            for step_no, action, expected, data in steps:
                run_sql("""
                    INSERT INTO test_steps (test_case_id, tenant_id, step_no, action, expected_result, test_data, created_at, updated_at)
                    VALUES (:tc,:t,:no,:action,:exp,:data,:now,:now)
                """, dict(tc=tc_id, t=TENANT_ID, no=step_no, action=action, exp=expected, data=data, now=NOW))
        db.session.flush()
        print(f"    ✅ Test steps for {len(step_data)} test cases")

    # Test Runs
    nrun = db.session.execute(db.text("SELECT COUNT(*) FROM test_runs")).scalar()
    if nrun < 5 and CYCLE_IDS and TC_IDS:
        run_map = {
            "TC-FI-001":("passed","SIT-01"),"TC-FI-002":("passed","SIT-01"),
            "TC-FI-003":("failed","SIT-01"),"TC-CO-001":("passed","SIT-01"),
            "TC-CO-002":("failed","SIT-01"),"TC-MM-001":("passed","SIT-02"),
            "TC-MM-002":("passed","SIT-02"),"TC-MM-003":("passed","SIT-02"),
            "TC-MM-004":("blocked","SIT-02"),"TC-MM-005":("passed","SIT-02"),
            "TC-SD-001":("passed","SIT-02"),"TC-SD-002":("failed","SIT-02"),
            "TC-SD-003":("in_progress","SIT-03"),"TC-PP-001":("in_progress","SIT-03"),
            "TC-PP-002":("in_progress","SIT-03"),"TC-E2E-001":("failed","SIT-03"),
            "TC-E2E-002":("in_progress","SIT-03"),"TC-E2E-003":("not_started","SIT-03"),
        }
        testers = ["Ayşe Polat","Baran Yıldız","Canan Öztürk","Deniz Arslan","Emre Koç"]
        for i, (tc_code, (result, cycle_key)) in enumerate(run_map.items()):
            tc_id = TC_IDS.get(tc_code)
            cycle_id = CYCLE_IDS.get(cycle_key)
            if not tc_id or not cycle_id:
                continue
            actual = result if result in ("passed","failed","blocked") else None
            run_sql("""
                INSERT INTO test_runs
                  (cycle_id, test_case_id, tenant_id, run_type, status, result,
                   environment, tester, created_at, updated_at)
                VALUES (:cycle,:tc,:t,'manual',:status,:result,'QAS',:tester,:now,:now)
            """, dict(cycle=cycle_id, tc=tc_id, t=TENANT_ID, status=result,
                      result=actual, tester=testers[i % len(testers)], now=NOW))
        db.session.flush()
        print(f"    ✅ {len(run_map)} test runs")

    # Defects
    nd = db.session.execute(db.text("SELECT COUNT(*) FROM defects WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if nd < 5:
        defect_rows = [
            ("DFT-001","F110 bank file format error (ISO20022)","critical","high","open","FI","TC-FI-003"),
            ("DFT-002","Standard cost estimate not picking up activity prices","high","high","in_progress","CO","TC-CO-002"),
            ("DFT-003","Batch GHS fields not transferring to delivery","critical","high","open","MM","TC-MM-005"),
            ("DFT-004","Shelf life check bypassed for interim storage location","high","medium","in_progress","MM","TC-MM-004"),
            ("DFT-005","Customer price formula yielding negative net value","critical","high","open","SD","TC-SD-002"),
            ("DFT-006","Dangerous goods indicator not triggering hazmat document","critical","critical","open","SD","TC-SD-003"),
            ("DFT-007","E2E PTP: GR/IR clearing mismatch after 3-way match","high","high","in_progress","MM","TC-E2E-001"),
            ("DFT-008","MRP explosion ignoring planning calendar for reactors","high","medium","open","PP","TC-PP-001"),
            ("DFT-009","BTP CPI bank file encoding error on Turkish chars","critical","high","open","BTP","TC-INT-001"),
            ("DFT-010","HACCP inspection lot not auto-created on GR","medium","medium","open","QM","TC-PP-003"),
            ("DFT-011","GL document type SA blocked in period 3","low","low","resolved","FI","TC-FI-001"),
            ("DFT-012","Cost center missing in planning hierarchy","medium","medium","resolved","CO","TC-CO-001"),
        ]
        for d in defect_rows:
            code, title, severity, priority, status, module, tc_code = d
            tc_id = TC_IDS.get(tc_code)
            res = db.session.execute(db.text("""
                INSERT INTO defects
                  (program_id, project_id, tenant_id, code, title, severity, priority,
                   status, module, test_case_id, reported_by, assigned_to,
                   created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:severity,:priority,
                        :status,:module,:tc,'Ayşe Polat','Dev Team',:now,:now)
                RETURNING id
            """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                       severity=severity, priority=priority, status=status,
                       module=module, tc=tc_id, now=NOW))
            defect_id = res.fetchone()[0]
            if status == "open":
                run_sql("""
                    INSERT INTO defect_comments (defect_id, tenant_id, author, body, created_at, updated_at)
                    VALUES (:d,:t,'Ayşe Polat','Confirmed in QA. Assigned for analysis.',:now,:now)
                """, dict(d=defect_id, t=TENANT_ID, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(defect_rows)} defects")


# ════════════════════════════════════════════════════════════════════
# 10. RAID
# ════════════════════════════════════════════════════════════════════
def seed_raid():
    print("  → RAID...")
    nr = db.session.execute(db.text("SELECT COUNT(*) FROM risks WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if nr < 8:
        # probability & impact: 1-5 integers; risk_score = prob * impact; rag_status: red/amber/green
        risks = [
            ("RSK-006","e-Invoice DRC config delay — GİB approval pending","regulatory",4,5,20,"red","identified","Serkan Doğan"),
            ("RSK-007","BTP CPI license capacity insufficient for peak load","technical",3,4,12,"amber","mitigated","Serkan Doğan"),
            ("RSK-008","Turkish payroll law changes effective Jan 2027","regulatory",4,3,12,"amber","identified","Fatma Çelik"),
            ("RSK-009","Data migration: 35% vendor masters have duplicates","data",4,4,16,"red","identified","Hakan Yıldız"),
            ("RSK-010","UAT resource conflict with Finance month-end close","resource",3,4,12,"amber","identified","Zeynep Aksoy"),
            ("RSK-011","MES integration scope creep (OPC-UA vs REST)","technical",3,3,9,"amber","identified","Serkan Doğan"),
            ("RSK-012","Works Council approval for HCM changes pending","organizational",4,3,12,"amber","identified","Fatma Çelik"),
            ("RSK-013","Cutover weekend conflicts with plant shutdown schedule","schedule",4,5,20,"red","identified","Baran Arslan"),
            ("RSK-014","QM lab system integration not in original scope","scope",3,3,9,"amber","identified","Hakan Yıldız"),
            ("RSK-015","SAP kernel patch 6-week freeze window impact","technical",2,3,6,"green","mitigated","Serkan Doğan"),
        ]
        for r in risks:
            code, title, cat, prob, impact, score, rag, status, owner = r
            run_sql("""
                INSERT INTO risks
                  (program_id, project_id, tenant_id, code, title, risk_category,
                   probability, impact, risk_score, rag_status, status, owner,
                   created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:cat,:prob,:impact,:score,
                        :rag,:status,:owner,:now,:now)
            """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                      cat=cat, prob=prob, impact=impact, score=score, rag=rag,
                      status=status, owner=owner, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(risks)} new risks")
    else:
        print(f"    ⏩ {nr} risks exist")

    na = db.session.execute(db.text("SELECT COUNT(*) FROM actions WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if na < 8:
        actions = [
            ("ACT-004","Escalate e-Invoice DRC issue to SAP Product Support","open","2026-03-25","critical","Serkan Doğan"),
            ("ACT-005","Vendor master data quality workshop","in_progress","2026-03-31","high","Deniz Polat"),
            ("ACT-006","Align UAT schedule with Finance month-end calendar","open","2026-04-10","high","Zeynep Aksoy"),
            ("ACT-007","Present BTP CPI architecture to Works Council","open","2026-04-15","high","Fatma Çelik"),
            ("ACT-008","Confirm cutover weekend with Plant Management","open","2026-04-30","critical","Baran Arslan"),
            ("ACT-009","Obtain GİB test environment access","in_progress","2026-03-20","critical","Serkan Doğan"),
            ("ACT-010","Define MES integration API spec with Siemens","open","2026-04-20","high","Serkan Doğan"),
        ]
        for r in actions:
            code, title, status, due, priority, owner = r
            run_sql("""
                INSERT INTO actions
                  (program_id, project_id, tenant_id, code, title, status,
                   due_date, priority, owner, created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:status,:due,:priority,:owner,:now,:now)
            """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                      status=status, due=due, priority=priority, owner=owner, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(actions)} new actions")

    ni = db.session.execute(db.text("SELECT COUNT(*) FROM issues WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if ni < 5:
        issues = [
            ("ISS-003","BTP CPI dev license expired — integration testing blocked","open","critical","Serkan Doğan"),
            ("ISS-004","Authorization role for MM power user missing in transport","open","high","Basis Team"),
            ("ISS-005","QAS refresh failed — data inconsistency in test system","in_progress","high","Basis Team"),
            ("ISS-006","GİB portal downtime blocking e-Invoice validation tests","open","critical","Serkan Doğan"),
            ("ISS-007","Customer price list (1,200 conditions) not migrated","in_progress","high","Emre Korkmaz"),
        ]
        for r in issues:
            code, title, status, severity, owner = r
            run_sql("""
                INSERT INTO issues
                  (program_id, project_id, tenant_id, code, title, status,
                   severity, owner, created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:status,:sev,:owner,:now,:now)
            """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                      status=status, sev=severity, owner=owner, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(issues)} new issues")

    nd = db.session.execute(db.text("SELECT COUNT(*) FROM decisions WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if nd < 5:
        decisions = [
            ("DEC-003","Go-live date: 1 November 2026 — single big-bang cutover","approved","Kenan Çalışkan","Kenan Çalışkan"),
            ("DEC-004","Embedded EWM — decentralized rejected","approved","Elif Şahin","Elif Şahin"),
            ("DEC-005","SAP BTP CPI as sole integration middleware","approved","Serkan Doğan","Serkan Doğan"),
            ("DEC-006","HCM on-premise payroll — not SuccessFactors","approved","Fatma Çelik","Fatma Çelik"),
            ("DEC-007","Legacy ECC archiving deferred to Phase 2","proposed","Ahmet Yılmaz","Ahmet Yılmaz"),
            ("DEC-008","Fiori-first — SAP GUI restricted to Basis/Power Users","approved","Serkan Doğan","Serkan Doğan"),
        ]
        for r in decisions:
            code, title, status, owner, dec_owner = r
            run_sql("""
                INSERT INTO decisions
                  (program_id, project_id, tenant_id, code, title, status,
                   owner, decision_owner, created_at, updated_at)
                VALUES (:prog,:proj,:t,:code,:title,:status,:owner,:downer,:now,:now)
            """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, code=code, title=title,
                      status=status, owner=owner, downer=dec_owner, now=NOW))
        db.session.flush()
        print(f"    ✅ {len(decisions)} new decisions")


# ════════════════════════════════════════════════════════════════════
# 11. INTEGRATION
# ════════════════════════════════════════════════════════════════════
def seed_integration():
    print("  → Integration Waves & Interfaces...")
    ni = db.session.execute(db.text("SELECT COUNT(*) FROM interfaces WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if ni >= 5:
        print(f"    ⏩ {ni} interfaces exist"); return

    wave_ids = {}
    for name, desc, status, order, start, end in [
        ("Wave 1","Core Financial & Procurement","in_progress",1,"2026-01-15","2026-04-30"),
        ("Wave 2","Supply Chain & Manufacturing","not_started",2,"2026-05-01","2026-07-31"),
        ("Wave 3","External Partner & Regulatory","not_started",3,"2026-08-01","2026-10-15"),
    ]:
        res = db.session.execute(db.text("""
            INSERT INTO waves (program_id, project_id, tenant_id, name, description, status,
                               "order", planned_start, planned_end, created_at, updated_at)
            VALUES (:prog,:proj,:t,:name,:desc,:status,:ord,:start,:end,:now,:now) RETURNING id
        """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, name=name, desc=desc,
                   status=status, ord=order, start=start, end=end, now=NOW))
        wave_ids[name] = res.fetchone()[0]
    db.session.flush()

    w1, w2, w3 = wave_ids["Wave 1"], wave_ids["Wave 2"], wave_ids["Wave 3"]
    ifaces = [
        ("INT-001","SAP ↔ Bank (ISO20022 Pain.001/Camt.054)","outbound","rest","SAP BTP CPI","S/4HANA","Bank Gateway","daily","FI","in_progress","critical","complex",80,w1),
        ("INT-002","SAP ↔ GİB (e-Invoice/e-Archive via DRC)","bidirectional","soap","SAP DRC","S/4HANA","GİB Portal","real_time","FI","in_progress","critical","complex",96,w1),
        ("INT-003","SAP ↔ Customs System (BEXIS)","outbound","rest","SAP BTP CPI","S/4HANA","BEXIS API","on_demand","MM","in_progress","critical","complex",80,w1),
        ("INT-004","SAP ↔ EDI Platform (Migros ORDERS05)","bidirectional","as2","SAP BTP CPI","S/4HANA","Migros EDI","event","SD","in_progress","high","complex",80,w1),
        ("INT-005","SAP ↔ Logistics Carrier API (DHL)","outbound","rest","SAP BTP CPI","S/4HANA","Carrier API","real_time","SD","not_started","medium","medium",48,w2),
        ("INT-006","SAP ↔ MES (Siemens OPC-UA)","bidirectional","opcua","SAP BTP CPI","S/4HANA","Siemens MES","real_time","PP","not_started","high","complex",96,w2),
        ("INT-007","SAP ↔ Quality Lab System (LIMS)","bidirectional","rest","SAP BTP CPI","S/4HANA","LIMS","event","QM","not_started","high","medium",48,w2),
        ("INT-008","SAP ↔ PM Tool (IBM Maximo)","bidirectional","soap","SAP BTP CPI","S/4HANA","Maximo","batch","PM","not_started","medium","complex",64,w2),
        ("INT-009","SAP ↔ SGK Social Security (HR)","outbound","soap","SAP BTP CPI","S/4HANA","SGK Portal","monthly","HCM","not_started","critical","complex",96,w3),
        ("INT-010","SAP ↔ İŞKUR Employment Agency","outbound","rest","SAP BTP CPI","S/4HANA","İŞKUR API","monthly","HCM","not_started","medium","simple",24,w3),
        ("INT-011","SAP ↔ Active Directory (SSO SAML2)","bidirectional","saml","SAP ID Service","S/4HANA","AD","real_time","BC","not_started","high","medium",40,w3),
        ("INT-012","SAP ↔ Credit Insurer (Euler Hermes)","outbound","rest","SAP BTP CPI","S/4HANA","Euler Hermes","on_demand","SD","not_started","medium","simple",24,w3),
        ("INT-013","SAP ↔ GHG Reporting Platform","outbound","rest","SAP BTP CPI","S/4HANA","GHG Platform","monthly","FI","not_started","low","simple",16,w3),
    ]
    for r in ifaces:
        code, name, direction, protocol, mw, src, tgt, freq, module, status, priority, complexity, hrs, wave_id = r
        run_sql("""
            INSERT INTO interfaces
              (program_id, project_id, tenant_id, wave_id, code, name, direction,
               protocol, middleware, source_system, target_system, frequency,
               module, interface_type, status, priority, complexity,
               estimated_hours, created_at, updated_at)
            VALUES (:prog,:proj,:t,:wave,:code,:name,:dir,:proto,:mw,
                    :src,:tgt,:freq,:module,'standard',
                    :status,:priority,:complexity,:hrs,:now,:now)
        """, dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, wave=wave_id, code=code,
                  name=name, dir=direction, proto=protocol, mw=mw, src=src, tgt=tgt,
                  freq=freq, module=module, status=status, priority=priority,
                  complexity=complexity, hrs=hrs, now=NOW))
    db.session.flush()
    print(f"    ✅ 3 waves + {len(ifaces)} interfaces")


# ════════════════════════════════════════════════════════════════════
# 12. DATA FACTORY
# ════════════════════════════════════════════════════════════════════
def seed_data_factory():
    print("  → Data Factory...")
    nd = db.session.execute(db.text("SELECT COUNT(*) FROM data_objects WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if nd >= 3:
        print(f"    ⏩ {nd} data objects exist"); return

    # Migration Waves (wave_number required, no order col)
    mwave_ids = {}
    for wave_no, name, status, start, end in [
        (1,"DM-Wave-1: Master Data — Org & Finance","in_progress","2026-02-01","2026-04-30"),
        (2,"DM-Wave-2: Master Data — Logistics & Production","not_started","2026-05-01","2026-07-31"),
        (3,"DM-Wave-3: Open Items & Balances Cutover","not_started","2026-09-01","2026-10-31"),
    ]:
        res = db.session.execute(db.text("""
            INSERT INTO migration_waves
              (program_id, tenant_id, wave_number, name, status, planned_start, planned_end, created_at, updated_at)
            VALUES (:prog,:t,:wno,:name,:status,:start,:end,:now,:now) RETURNING id
        """), dict(prog=PROGRAM_ID, t=TENANT_ID, wno=wave_no, name=name,
                   status=status, start=start, end=end, now=NOW))
        mwave_ids[wave_no] = res.fetchone()[0]
    db.session.flush()

    # Data Objects
    do_rows = [
        ("Customer Master","ECC SD","customers",4200,76.5,"in_progress"),
        ("Vendor Master","ECC MM","vendors",1850,68.2,"in_progress"),
        ("Material Master","ECC MM","materials",6500,82.1,"in_progress"),
        ("GL Account Master","ECC FI","gl_accounts",1200,91.3,"in_progress"),
        ("Cost Center Master","ECC CO","cost_centers",340,95.0,"completed"),
        ("Profit Center Master","ECC CO","profit_centers",120,97.5,"completed"),
        ("Fixed Assets","ECC FI-AA","assets",2100,71.8,"not_started"),
        ("Bill of Materials","ECC PP","bom",3200,84.6,"not_started"),
        ("Work Centers","ECC PP","work_centers",85,92.3,"not_started"),
        ("Batch Master","ECC MM","batches",18000,55.4,"not_started"),
        ("Open Purchase Orders","ECC MM","open_po",1400,88.0,"not_started"),
        ("Open Sales Orders","ECC SD","open_so",920,85.5,"not_started"),
        ("AR Open Items","ECC FI","ar_items",6800,79.2,"not_started"),
        ("AP Open Items","ECC FI","ap_items",4100,81.0,"not_started"),
        ("GL Balances Cutover","ECC FI","gl_balances",2400,94.0,"not_started"),
    ]
    do_ids = []
    for r in do_rows:
        name, src, tgt, count, quality, status = r
        res = db.session.execute(db.text("""
            INSERT INTO data_objects
              (program_id, tenant_id, name, source_system, target_table,
               record_count, quality_score, status, created_at, updated_at)
            VALUES (:prog,:t,:name,:src,:tgt,:count,:quality,:status,:now,:now) RETURNING id
        """), dict(prog=PROGRAM_ID, t=TENANT_ID, name=name, src=src, tgt=tgt,
                   count=count, quality=quality, status=status, now=NOW))
        do_ids.append(res.fetchone()[0])
    db.session.flush()

    # Cleansing Tasks — link to data_object_id with rule_type + rule_expression
    if do_ids:
        ct_rows = [
            (do_ids[1], "deduplication", "BP_MERGE_ON_TAX_NUMBER", "Deduplicate vendor master on Tax ID"),
            (do_ids[0], "standardize",   "ADDR_NORMALIZE_CAPS",    "Cleanse customer address fields"),
            (do_ids[2], "validate",      "UOM_CONSISTENCY_CHECK",  "Material master UoM harmonization"),
            (do_ids[3], "map",           "GL_ACCOUNT_MAPPING_MERI","GL account mapping to new CoA"),
            (do_ids[6], "validate",      "ASSET_NBV_VALIDATION",   "Fixed asset net book value validation"),
            (do_ids[9], "validate",      "BATCH_SLED_POPULATION",  "Batch master shelf life date check"),
            (do_ids[7], "validate",      "BOM_SCRAP_FACTOR_CHECK", "BOM scrap factor validation per line"),
            (do_ids[10],"filter",        "PO_CLOSED_CLEANUP",      "Remove cancelled/closed open POs"),
            (do_ids[12],"validate",      "AR_DISPUTED_RESOLUTION", "AR open items — disputed invoices"),
            (do_ids[14],"reconcile",     "GL_IC_NETTING_CHECK",    "GL balances intercompany netting"),
        ]
        for r in ct_rows:
            do_id, rule_type, rule_expr, desc = r
            run_sql("""
                INSERT INTO cleansing_tasks
                  (data_object_id, tenant_id, rule_type, rule_expression, description, status, created_at)
                VALUES (:do,:t,:rtype,:rexpr,:desc,'pending',:now)
            """, dict(do=do_id, t=TENANT_ID, rtype=rule_type, rexpr=rule_expr, desc=desc, now=NOW))
        db.session.flush()

    print(f"    ✅ 3 migration waves + {len(do_rows)} data objects + {len(ct_rows)} cleansing tasks")


# ════════════════════════════════════════════════════════════════════
# 13. CUTOVER
# ════════════════════════════════════════════════════════════════════
def seed_cutover():
    print("  → Cutover Plan...")
    nc = db.session.execute(db.text("SELECT COUNT(*) FROM cutover_plans WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if nc >= 1:
        print(f"    ⏩ {nc} cutover plans exist"); return

    res = db.session.execute(db.text("""
        INSERT INTO cutover_plans
          (program_id, project_id, tenant_id, code, name, description, status, version,
           planned_start, planned_end, cutover_manager, environment, rollback_deadline,
           rollback_decision_by, hypercare_start, hypercare_end,
           hypercare_duration_weeks, hypercare_manager, created_at, updated_at)
        VALUES (:prog,:proj,:t,'CUT-001',
                'Meridian S/4HANA Go-Live Cutover Plan',
                'Big-bang cutover ECC 6.0 → S/4HANA. Single weekend, all plants.',
                'draft',1,
                '2026-10-30 18:00:00','2026-11-01 06:00:00',
                'Umut Kaya','production','2026-10-31 06:00:00','Kenan Çalışkan',
                '2026-11-01 06:00:00','2026-11-29 23:59:00',4,'Gül Tekin',
                :now,:now)
        RETURNING id
    """), dict(prog=PROGRAM_ID, proj=PROJECT_ID, t=TENANT_ID, now=NOW))
    cut_id = res.fetchone()[0]
    db.session.flush()

    # Cutover Scope Items — name + category + order
    # Valid categories: data_load, interface, authorization, job_scheduling, reconciliation, custom
    scope_rows = [
        ("System downtime announcement — OCM","custom",1),
        ("ECC production system freeze","custom",2),
        ("ECC month-end balance extract","reconciliation",3),
        ("LTMC: Customer & Vendor master load","data_load",4),
        ("LTMC: Material master load (6,500 SKUs)","data_load",5),
        ("LTMC: Open PO & Sales Order migration","data_load",6),
        ("LTMC: AR/AP open item migration","data_load",7),
        ("LTMC: GL balance migration","data_load",8),
        ("LTMC: Fixed asset migration","data_load",9),
        ("Authorization role activation in production","authorization",10),
        ("BTP CPI interface activation — production","interface",11),
        ("e-Invoice DRC production configuration","interface",12),
        ("Smoke test — FI: Post GL document","reconciliation",13),
        ("Smoke test — MM: Create PO and GR","reconciliation",14),
        ("Smoke test — SD: Create SO and invoice","reconciliation",15),
        ("Smoke test — PP: Create production order","reconciliation",16),
        ("Smoke test — e-Invoice: Send to GİB","interface",17),
        ("Go/No-Go decision (Steering Committee)","custom",18),
        ("ECC system shutdown — archive mode","job_scheduling",19),
        ("S/4HANA open to all users","authorization",20),
        ("Hypercare war room activation — Day 1","custom",21),
        ("Daily hypercare call — 08:00 & 17:00","custom",22),
        ("First payroll run validation (November)","reconciliation",23),
        ("First month-end close in S/4HANA","reconciliation",24),
        ("Hypercare exit criteria evaluation","custom",25),
    ]
    scope_item_ids = []
    for name, category, order in scope_rows:
        r = db.session.execute(db.text("""
            INSERT INTO cutover_scope_items
              (cutover_plan_id, tenant_id, name, category, "order", created_at, updated_at)
            VALUES (:cut,:t,:name,:cat,:ord,:now,:now) RETURNING id
        """), dict(cut=cut_id, t=TENANT_ID, name=name, cat=category, ord=order, now=NOW))
        scope_item_ids.append(r.fetchone()[0])
    db.session.flush()

    # Runbook Tasks — reference scope_item_id (first scope item for simplicity)
    if scope_item_ids:
        ref_si = scope_item_ids[0]  # attach to first scope item as umbrella
        runbook_rows = [
            ("T-001","Broadcast downtime notification","not_started",60,True,"Gül Tekin"),
            ("T-002","Lock users except migration team in ECC","not_started",30,True,"Serkan Doğan"),
            ("T-003","Period-end balance carry-forward (ECC)","not_started",120,True,"Murat Kaya"),
            ("T-004","LTMC Run 1: Customer master + validation","not_started",240,True,"Hakan Yıldız"),
            ("T-005","LTMC Run 2: Vendor master + validation","not_started",180,True,"Hakan Yıldız"),
            ("T-006","LTMC Run 3: Material master + validation","not_started",360,True,"Hakan Yıldız"),
            ("T-007","LTMC Run 4: BOM and routing load","not_started",240,False,"Baran Arslan"),
            ("T-008","LTMC Run 5: Open PO migration","not_started",180,True,"Hakan Yıldız"),
            ("T-009","LTMC Run 6: Open SO migration","not_started",180,True,"Hakan Yıldız"),
            ("T-010","LTMC Run 7: AR/AP open item migration","not_started",240,True,"Murat Kaya"),
            ("T-011","LTMC Run 8: GL balance + asset migration","not_started",300,True,"Murat Kaya"),
            ("T-012","Activate BTP CPI production routes","not_started",60,True,"Serkan Doğan"),
            ("T-013","Configure e-Invoice DRC production","not_started",120,True,"Serkan Doğan"),
            ("T-014","Execute smoke test suite (30 critical TCs)","not_started",240,True,"Ayşe Polat"),
            ("T-015","Go/No-Go decision checkpoint","not_started",60,True,"Umut Kaya"),
            ("T-016","Open S/4HANA to all users","not_started",30,True,"Serkan Doğan"),
            ("T-017","Activate hypercare monitoring dashboards","not_started",30,False,"Gül Tekin"),
            ("T-018","Monitor Day-1 posting volumes (FI/MM/SD)","not_started",480,True,"Umut Kaya"),
            ("T-019","Confirm first e-Invoice successfully sent","not_started",60,True,"Serkan Doğan"),
            ("T-020","Confirm BTP CPI all interfaces green","not_started",60,True,"Serkan Doğan"),
        ]
        for code, title, status, dur_min, is_cp, responsible in runbook_rows:
            run_sql("""
                INSERT INTO runbook_tasks
                  (scope_item_id, tenant_id, code, title, status,
                   planned_duration_min, is_critical_path, responsible, created_at, updated_at)
                VALUES (:si,:t,:code,:title,:status,:dur,:cp,:resp,:now,:now)
            """, dict(si=ref_si, t=TENANT_ID, code=code, title=title, status=status,
                      dur=dur_min, cp=is_cp, resp=responsible, now=NOW))
    db.session.flush()

    # Go/No-Go Items — uses criterion + verdict + source_domain
    gng_rows = [
        ("testing","All SIT test cases passed (P1/P2 zero open defects)",None),
        ("testing","UAT signed off by all workstream leads",None),
        ("data","Data migration validation 100% complete",None),
        ("integration","e-Invoice GİB integration tested and certified",None),
        ("integration","All critical BTP CPI interfaces tested in PRD",None),
        ("security","Authorization concept approved and fully tested",None),
        ("cutover","Cutover rehearsal 2 completed with <36h duration",None),
        ("training","End-user training completion >90% per module",None),
        ("operations","Hypercare team on-site and on-call confirmed",None),
        ("cutover","Rollback plan reviewed and rehearsed",None),
    ]
    for source, criterion, verdict in gng_rows:
        run_sql("""
            INSERT INTO go_no_go_items
              (cutover_plan_id, tenant_id, source_domain, criterion, verdict, created_at, updated_at)
            VALUES (:cut,:t,:src,:crit,:verdict,:now,:now)
        """, dict(cut=cut_id, t=TENANT_ID, src=source, crit=criterion, verdict=verdict, now=NOW))

    # Rehearsals — rehearsal_number (int), findings_summary, actual_duration_min
    rehearsal_rows = [
        (1,"Cutover Rehearsal 1","completed","2026-09-12 08:00","2026-09-13 22:00",2280,
         "Duration exceeded by 6h. LTMC runs need parallelization. 3 failed tasks rescheduled."),
        (2,"Cutover Rehearsal 2","planned","2026-10-10 08:00","2026-10-11 20:00",2160,None),
    ]
    for rno, name, status, start, end, dur_min, findings in rehearsal_rows:
        run_sql("""
            INSERT INTO rehearsals
              (cutover_plan_id, tenant_id, rehearsal_number, name, status,
               planned_start, planned_end, actual_duration_min, findings_summary,
               created_at, updated_at)
            VALUES (:cut,:t,:rno,:name,:status,:start,:end,:dur,:findings,:now,:now)
        """, dict(cut=cut_id, t=TENANT_ID, rno=rno, name=name, status=status,
                  start=start, end=end, dur=dur_min if status == "completed" else None,
                  findings=findings, now=NOW))
    db.session.flush()
    print(f"    ✅ 1 cutover plan + {len(scope_rows)} scope items + {len(runbook_rows)} runbook tasks + {len(gng_rows)} go/no-go items + {len(rehearsal_rows)} rehearsals")


# ════════════════════════════════════════════════════════════════════
# 14. COMMUNICATION PLAN
# ════════════════════════════════════════════════════════════════════
def seed_communication():
    print("  → Communication Plan...")
    n = db.session.execute(db.text("SELECT COUNT(*) FROM communication_plan_entries WHERE program_id=:p"), {"p": PROGRAM_ID}).scalar()
    if n >= 5:
        print(f"    ⏩ {n} entries exist"); return
    rows = [
        ("Monthly Steering Committee Report","Steering Committee","status_report","email+presentation","monthly","realize","2026-03-31","planned"),
        ("Weekly Project Status Update","All Workstream Leads","status_report","teams","weekly","realize",None,"planned"),
        ("Fit-to-Standard Workshop Outcomes","Key Users & Super Users","workshop","email","ad_hoc","explore","2026-04-15","planned"),
        ("Go-Live Readiness — All Staff","All Employees","announcement","email+intranet","one_time","deploy","2026-10-01","planned"),
        ("Change Impact Assessment Results","Department Heads","presentation","teams","one_time","realize","2026-04-30","planned"),
        ("Super User Training Schedule","Super Users (80 people)","training","email","one_time","realize","2026-06-01","planned"),
        ("End-User Training Dashboard","HR & Dept Managers","dashboard","sharepoint","weekly","deploy",None,"planned"),
        ("Cutover Plan Review with Plant Managers","Gebze & İzmir Plant Mgmt","presentation","meeting","one_time","deploy","2026-10-15","planned"),
        ("Hypercare War Room Daily Standup","Core Project Team","meeting","teams","daily","run",None,"planned"),
        ("Post-Go-Live Lessons Learned","All Stakeholders","presentation","workshop","one_time","run","2026-12-01","planned"),
        ("Works Council Consultation — HCM","Works Council Rep","consultation","meeting","one_time","realize","2026-05-15","planned"),
        ("Executive Dashboard — Program KPIs","CIO, CFO, CEO","dashboard","email","monthly","realize",None,"planned"),
    ]
    for r in rows:
        subject, audience, ctype, channel, freq, phase, planned, status = r
        run_sql("""
            INSERT INTO communication_plan_entries
              (program_id, tenant_id, subject, audience_group, communication_type,
               channel, frequency, sap_activate_phase, planned_date, status,
               created_at, updated_at)
            VALUES (:prog,:t,:sub,:aud,:ctype,:channel,:freq,:phase,:planned,:status,:now,:now)
        """, dict(prog=PROGRAM_ID, t=TENANT_ID, sub=subject, aud=audience, ctype=ctype,
                  channel=channel, freq=freq, phase=phase, planned=planned,
                  status=status, now=NOW))
    db.session.flush()
    print(f"    ✅ {len(rows)} communication plan entries")


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════
def main():
    app = create_app()
    with app.app_context():
        print("\n🚀 Meridian Industries A.Ş. — Comprehensive Data Seed")
        print("=" * 60)
        ensure_target_context()
        validate_target_context()
        ensure_process_hierarchy()

        seed_stakeholders()
        seed_workshops()
        seed_explore_reqs()
        seed_explore_open_items()
        seed_explore_decisions()
        seed_sprints()
        seed_backlog()
        seed_config_items()
        seed_testing()
        seed_raid()
        seed_integration()
        seed_data_factory()
        seed_cutover()
        seed_communication()

        db.session.commit()
        print("\n✅ All committed to database")
        print("=" * 60)

        print("\n📊 Final Record Counts:")
        checks = [
            ("Stakeholders",           "stakeholders WHERE program_id=:program_id"),
            ("Explore Workshops",      "explore_workshops WHERE project_id=:project_id"),
            ("Explore Requirements",   "explore_requirements WHERE project_id=:project_id"),
            ("Explore Open Items",     "explore_open_items WHERE project_id=:project_id"),
            ("Explore Decisions",      "explore_decisions WHERE project_id=:project_id"),
            ("Sprints",                "sprints WHERE program_id=:program_id"),
            ("Backlog Items (WRICEF)", "backlog_items WHERE program_id=:program_id"),
            ("Config Items",           "config_items WHERE program_id=:program_id"),
            ("Test Suites",            "test_suites WHERE program_id=:program_id"),
            ("Test Cases",             "test_cases WHERE program_id=:program_id"),
            ("Test Runs",              "test_runs"),
            ("Defects",                "defects WHERE program_id=:program_id"),
            ("Risks",                  "risks WHERE program_id=:program_id"),
            ("Actions",                "actions WHERE program_id=:program_id"),
            ("Issues",                 "issues WHERE program_id=:program_id"),
            ("Decisions",              "decisions WHERE program_id=:program_id"),
            ("Interfaces",             "interfaces WHERE program_id=:program_id"),
            ("Data Objects",           "data_objects WHERE program_id=:program_id"),
            ("Cleansing Tasks",        "cleansing_tasks WHERE tenant_id=:tenant_id"),
            ("Cutover Scope Items",    "cutover_scope_items WHERE tenant_id=:tenant_id"),
            ("Runbook Tasks",          "runbook_tasks WHERE tenant_id=:tenant_id"),
            ("Go/No-Go Items",         "go_no_go_items WHERE tenant_id=:tenant_id"),
            ("Rehearsals",             "rehearsals WHERE tenant_id=:tenant_id"),
            ("Comm. Plan Entries",     "communication_plan_entries WHERE program_id=:program_id"),
            ("Stakeholders",           "stakeholders WHERE program_id=:program_id"),
        ]
        for label, clause in checks:
            try:
                n = db.session.execute(
                    db.text(f"SELECT COUNT(*) FROM {clause}"),
                    {
                        "tenant_id": TENANT_ID,
                        "program_id": PROGRAM_ID,
                        "project_id": PROJECT_ID,
                    },
                ).scalar()
                print(f"   {label:30s}: {n}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
