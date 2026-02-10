"""
SEED-003 — Project Role Assignments for Explore Phase RBAC
Company: Anadolu Gıda ve İçecek A.Ş.

Maps users to project-level roles with optional process area scoping.
Consumed by the ProjectRole model (app/models/explore.py).

Team Members:
  usr-001  Mehmet Kaya       PM
  usr-002  Burak Şahin       SD Module Lead / Facilitator
  usr-003  Elif Demir        MM Module Lead
  usr-004  Ahmet Yıldız      FI/CO Module Lead
  usr-005  Zeynep Arslan     PP/QM Module Lead
  usr-006  Hakan Çelik       WM Module Lead
  usr-007  Ayşe Yılmaz       HR Module Lead
  usr-008  Can Özdemir       Tech Lead
  usr-009  Fatma Koç         Test Lead
  usr-010  Emre Aydın        BPO (Sales & Procurement)
"""

PROJECT_ROLES = [
    # ── Programme Manager (all areas) ────────────────────────────────────
    {"project_id": 1, "user_id": "usr-001", "role": "pm",
     "process_area": None},

    # ── Module Leads (area-specific) ─────────────────────────────────────
    {"project_id": 1, "user_id": "usr-002", "role": "module_lead",
     "process_area": "SD"},
    {"project_id": 1, "user_id": "usr-003", "role": "module_lead",
     "process_area": "MM"},
    {"project_id": 1, "user_id": "usr-004", "role": "module_lead",
     "process_area": "FI"},
    {"project_id": 1, "user_id": "usr-005", "role": "module_lead",
     "process_area": "PP"},
    {"project_id": 1, "user_id": "usr-006", "role": "module_lead",
     "process_area": "WM"},
    {"project_id": 1, "user_id": "usr-007", "role": "module_lead",
     "process_area": "HR"},

    # ── Facilitators (also run workshops) ────────────────────────────────
    {"project_id": 1, "user_id": "usr-002", "role": "facilitator",
     "process_area": "SD"},
    {"project_id": 1, "user_id": "usr-004", "role": "facilitator",
     "process_area": "FI"},

    # ── Business Process Owners ──────────────────────────────────────────
    {"project_id": 1, "user_id": "usr-010", "role": "bpo",
     "process_area": "SD"},
    {"project_id": 1, "user_id": "usr-010", "role": "bpo",
     "process_area": "MM"},

    # ── Tech Lead (all areas) ────────────────────────────────────────────
    {"project_id": 1, "user_id": "usr-008", "role": "tech_lead",
     "process_area": None},

    # ── Tester (all areas) ───────────────────────────────────────────────
    {"project_id": 1, "user_id": "usr-009", "role": "tester",
     "process_area": None},

    # ── Viewer (stakeholder read-only) ───────────────────────────────────
    {"project_id": 1, "user_id": "usr-011", "role": "viewer",
     "process_area": None},
]
