"""Dev helper to provision/reset the default admin user.

This is intentionally kept outside `tests/` so it is not mistaken for
an automated regression asset.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.models import db
from app.models.auth import User, Tenant

app = create_app()

from app.utils.crypto import hash_password

def create_admin():
    with app.app_context():
        tenant = Tenant.query.filter_by(slug='default').first()
        if not tenant:
            print("❌ Hata: Default tenant bulunamadı. Lütfen önce seed_and_smoke.py çalıştırın.")
            return

        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            print("Creating administrative user...")
            admin = User(
                email="admin@example.com",
                full_name="Admin User",
                tenant_id=tenant.id,
                status="active",
                password_hash=hash_password("password")
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin@example.com / password")
        else:
            # Şifreyi her ihtimale karşı sıfırla
            admin.password_hash = hash_password("password")
            db.session.commit()
            print("✅ Admin user already exists. Password reset to: password")

if __name__ == "__main__":
    create_admin()
