"""Audit purpose readiness after suite_type removal.

Reports:
- suites with blank `purpose`
"""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.models import db
from app.models.testing import TestSuite


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Backfill blank purpose from legacy suite_type if present")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        suites = TestSuite.query.all()
        blank_purpose = 0
        updated = 0

        for suite in suites:
            purpose = (suite.purpose or "").strip()
            suite_type = str(getattr(suite, "suite_type", "") or "").strip()
            if not purpose:
                blank_purpose += 1
                if args.apply and suite_type:
                    suite.purpose = suite_type
                    updated += 1
                    purpose = suite_type
        if args.apply and updated:
            db.session.commit()

        print(
            {
                "total": len(suites),
                "blank_purpose": blank_purpose,
                "updated": updated,
                "apply": args.apply,
            }
        )


if __name__ == "__main__":
    main()
