"""
One-time script to link existing scope items to requirements
and create a new requirement for the user's 3XX scope item.
"""
from app import create_app
from app.models import db
from app.models.scope import ScopeItem
from app.models.requirement import Requirement

app = create_app("development")

with app.app_context():
    # 1) Create a Requirement for the 3XX Pricing Line scope item
    si_3xx = ScopeItem.query.filter_by(code="3XX").first()
    if si_3xx and not si_3xx.requirement_id:
        req = Requirement(
            program_id=1,
            code="REQ-SD-003",
            title="Pricing Line — " + si_3xx.name,
            description=si_3xx.description or "SAP pricing line requirement from process tree.",
            req_type="functional",
            priority="could_have",
            status="draft",
            source="process_tree",
            module=si_3xx.module or "SD",
            fit_gap="partial_fit",
            notes=si_3xx.notes or "",
        )
        db.session.add(req)
        db.session.flush()
        si_3xx.requirement_id = req.id
        print(f"Created REQ-SD-003 (id={req.id}) linked to ScopeItem 3XX (id={si_3xx.id})")
    else:
        print("3XX already linked or not found")

    # 2) Auto-link seed scope items to matching requirements by module
    links = [
        (1, 3),    # 1OC Standard Sales Order -> REQ-BIZ-003
        (2, 10),   # 2OC Third-Party Order -> REQ-SD-002
        (3, 9),    # 3OC Invoice Processing -> REQ-SD-001
        (4, 8),    # 1PP Standard PO -> REQ-MM-002
        (5, 7),    # 2PP Logistics Invoice -> REQ-MM-001
        (6, 1),    # 1RR GL Posting -> REQ-BIZ-001
        (7, 5),    # 2RR Fixed Asset -> REQ-FI-001
        (8, 4),    # 1PM MRP -> REQ-BIZ-004
        (9, 7),    # 1NN Direct Procurement -> REQ-MM-001
        (11, 8),   # 3MM Framework Orders -> REQ-MM-002
        (12, 8),   # 4PO Service Procurement -> REQ-MM-002
        (13, 19),  # 5GR 3-Way Matching -> REQ-INT-003
        (15, 1),   # J78 Parallel Accounting -> REQ-BIZ-001
        (16, 1),   # J79 Intercompany -> REQ-BIZ-001
        (17, 6),   # K01 Vendor Invoice -> REQ-FI-002
        (18, 20),  # K10 Customer Payment -> REQ-INT-004
        (19, 20),  # K11 Dunning -> REQ-INT-004
    ]
    for si_id, req_id in links:
        si = db.session.get(ScopeItem, si_id)
        if si and not si.requirement_id:
            si.requirement_id = req_id
            print(f"  Linked SI#{si_id} ({si.code}) -> REQ#{req_id}")

    db.session.commit()

    # Verify
    linked = ScopeItem.query.filter(ScopeItem.requirement_id.isnot(None)).count()
    total = ScopeItem.query.count()
    print(f"\nResult: {linked}/{total} scope items now linked to requirements")
