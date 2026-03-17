"""Ad hoc seed + smoke helper for local development.

This is intentionally kept outside `tests/` so it does not pollute the
automated suite namespace.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.models import db
from app.models.auth import Tenant

app = create_app()

def seed_tests():
    with app.app_context():
        # 1. Tenant Control
        tenant = Tenant.query.filter_by(slug='default').first()
        if not tenant:
            print("Creating default tenant to fix Login screen...")
            tenant = Tenant(name="Default Tenant", slug="default", plan="enterprise", is_active=True)
            db.session.add(tenant)
            db.session.commit()
            print("✅ Default Tenant created.")
        else:
            print("✅ Default Tenant already exists.")

        client = app.test_client()

        # 2. Block 0 Smoke Test via Test Client
        print("\n=== BLOCK 0: SMOKE TESTS ===")
        endpoints = [
            "/api/v1/projects", "/api/v1/scenarios", "/api/v1/explore/workshops",
        ]
        passed = 0
        for ep in endpoints:
            resp = client.get(ep)
            if resp.status_code in [200, 401, 403, 404]:  # Acceptance criteria for smoke
                print(f"  [OK] {ep} -> {resp.status_code}")
                passed += 1
            else:
                print(f"  [FAIL] {ep} -> {resp.status_code}")

        # 3. Block 1 Program & Project Create
        print("\n=== BLOCK 1: PROGRAM & PROJECT ===")
        prog_resp = client.post("/api/v1/programs", json={
            "name": "ACME Global Transformation",
            "code": "ACME-GTX",
            "description": "Global SAP S/4HANA 2023 FPS02.",
            "status": "active"
        })
        if prog_resp.status_code == 201:
            program_id = prog_resp.json["id"]
            print(f"✅ Program Created: {program_id}")

            proj_resp = client.post("/api/v1/projects", json={
                "name": "ACME Turkey S/4HANA Greenfield",
                "code": "ACME-TR-S4H",
                "description": "Turkey pilot.",
                "customer": "ACME Manufacturing A.Ş.",
                "program_id": program_id,
                "sap_product": "S/4HANA 2023 FPS02",
                "methodology": "SAP Activate",
                "status": "active",
                "start_date": "2026-03-01",
                "target_go_live": "2027-10-01"
            })
            if proj_resp.status_code == 201:
                print(f"✅ Project Created: {proj_resp.json['id']}")
            else:
                print(f"❌ Project failed: {proj_resp.data}")
        else:
            print(f"❌ Program failed: {prog_resp.data}")

if __name__ == "__main__":
    seed_tests()
    print("\n🎉 Seed and Test flow completed! You can now start 'flask run'.")
