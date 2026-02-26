# ═══════════════════════════════════════════════════════════════════════════
# SAP Transformation Platform — Local Development Makefile
# ═══════════════════════════════════════════════════════════════════════════
#
# Usage:
#   make setup       → Initial setup (venv + deps + db + seed)
#   make run         → Start the application (http://localhost:5001)
#   make seed        → Load demo data
#   make test        → Run all tests
#   make reset       → Reset DB + re-seed
#   make deploy      → Full post-sprint deploy (migrate + seed + test + run)
#
# ═══════════════════════════════════════════════════════════════════════════

PYTHON   := .venv/bin/python
PIP      := .venv/bin/pip
FLASK    := FLASK_APP=wsgi.py .venv/bin/flask
PYTEST   := .venv/bin/python -m pytest
DB_FILE  := instance/sap_platform_dev.db
PORT     := 5001

.PHONY: help setup venv deps db-init db-migrate db-upgrade seed seed-verbose seed-demo \
	run run-debug test test-verbose lint lint-architecture format reset clean deploy status \
	tenant-list tenant-create tenant-init tenant-seed tenant-status \
	demo-reset demo-snapshot demo-restore vendor-assets

# ── Default ──────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  SAP Transformation Platform — Local Development Commands"
	@echo "  ═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Initial Setup:"
	@echo "    make setup          Full setup (venv + dependencies + DB + seed data)"
	@echo ""
	@echo "  Daily Usage:"
	@echo "    make run            Start the application (http://localhost:$(PORT))"
	@echo "    make run-debug      Start with Flask debugger (no auto-reload)"
	@echo "    make test           Run all tests"
	@echo "    make test-verbose   Verbose test output"
	@echo "    make lint           Code quality check (ruff)"
	@echo "    make lint-architecture  Architecture rules (fat controller, duplicate utility)"
	@echo "    make format         Code formatting (ruff format)"
	@echo "    make seed           Load demo data (clears existing data)"
	@echo "    make seed-verbose   Load demo data (verbose output)"
	@echo ""
	@echo "  Sprint Management:"
	@echo "    make deploy         Sprint deploy: migrate → seed → test → run"
	@echo "    make reset          Reset DB + recreate + seed"
	@echo "    make status         Show project status"
	@echo ""
	@echo "  Demo:"
	@echo "    make seed-demo      Quick demo environment (reset + seed, 3 min)"
	@echo "    make demo-reset     Full demo reset: reset DB + seed + save snapshot"
	@echo "    make demo-snapshot  Take a snapshot of the current DB"
	@echo "    make demo-restore   Restore from snapshot (<1 sec)"
	@echo "    make vendor-assets  Download vendor JS for offline demo"
	@echo ""
	@echo "  Tenant Management:"
	@echo "    make tenant-list    List registered tenants"
	@echo "    make tenant-status  Show tenant DB statuses"
	@echo "    make tenant-create ID=acme NAME='Acme Corp'  Create a new tenant"
	@echo "    make tenant-init ID=acme    Create tenant DB tables"
	@echo "    make tenant-seed ID=acme    Load demo data into tenant"
	@echo ""
	@echo "  Maintenance:"
	@echo "    make db-migrate     Create a new migration"
	@echo "    make db-upgrade     Apply migrations"
	@echo "    make clean          Clean DB + cache files"
	@echo ""

# ── Virtual Environment ─────────────────────────────────────────────────
venv:
	@if [ ! -d .venv ]; then \
		echo "🐍 Creating virtual environment..."; \
		python3 -m venv .venv; \
		echo "   ✅ .venv created"; \
	else \
		echo "   ℹ️  .venv already exists"; \
	fi

# ── Dependencies ────────────────────────────────────────────────────────
deps: venv
	@echo "📦 Installing dependencies..."
	@$(PIP) install -r requirements.txt -q
	@echo "   ✅ All dependencies installed"

# ── Database ────────────────────────────────────────────────────────────
db-init: deps
	@echo "🗄️  Creating database..."
	@mkdir -p instance
	@$(FLASK) db upgrade
	@echo "   ✅ Database migrations applied"

db-migrate: deps
	@echo "📋 Creating new migration..."
	@$(FLASK) db migrate -m "auto-migration"
	@echo "   ✅ Migration file created"

db-upgrade: deps
	@echo "⬆️  Applying migrations..."
	@$(FLASK) db upgrade
	@echo "   ✅ Database updated"

# ── Seed Data ───────────────────────────────────────────────────────────
seed: deps
	@echo ""
	@$(PYTHON) scripts/seed_demo_data.py
	@echo ""

seed-verbose: deps
	@echo ""
	@$(PYTHON) scripts/seed_demo_data.py --verbose
	@echo ""

seed-sap: deps
	@echo ""
	@$(PYTHON) scripts/seed_sap_knowledge.py
	@echo ""

# ── Run Application ─────────────────────────────────────────────────────
run: deps
	@echo ""
	@echo "🚀 Starting SAP Transformation Platform..."
	@echo "   URL: http://localhost:$(PORT)"
	@echo "   To stop: Ctrl+C"
	@echo ""
	@$(FLASK) run --host=0.0.0.0 --port=$(PORT)

run-debug: deps
	@echo ""
	@echo "🚀 Starting SAP Transformation Platform (debug mode)..."
	@echo "   URL: http://localhost:$(PORT)"
	@echo "   Note: auto-reload disabled for filesystem-compatibility"
	@echo "   To stop: Ctrl+C"
	@echo ""
	@$(FLASK) run --host=0.0.0.0 --port=$(PORT) --debug --no-reload

# ── Tests ───────────────────────────────────────────────────────────────
test: deps
	@echo ""
	@echo "🧪 Running tests..."
	@GEMINI_API_KEY= $(PYTEST) tests/ -v --tb=short
	@echo ""

test-verbose: deps
	@echo ""
	@GEMINI_API_KEY= $(PYTEST) tests/ -v --tb=long -s
	@echo ""

# ── Lint & Format ───────────────────────────────────────────────────────
lint: deps
	@$(PYTHON) -m ruff --version >/dev/null 2>&1 || (echo "⚠️  ruff is not installed. Install with 'pip install ruff'."; exit 1)
	@echo "🔍 Running ruff lint..."
	@$(PYTHON) -m ruff check .

format: deps
	@$(PYTHON) -m ruff --version >/dev/null 2>&1 || (echo "⚠️  ruff is not installed. Install with 'pip install ruff'."; exit 1)
	@echo "✨ Running ruff format..."
	@$(PYTHON) -m ruff format .

# ── Architecture Lint ───────────────────────────────────────────────────
lint-architecture:
	@echo "🏗️  Checking architecture rules..."
	@echo ""
	@echo "  1. Fat controller check (>1000 lines)..."
	@FAT=0; \
	for f in $$(find app/blueprints -name "*.py" -not -path "*/__pycache__/*"); do \
		lines=$$(wc -l < "$$f"); \
		if [ $$lines -gt 1000 ]; then \
			echo "     ⚠️  $$f: $$lines lines (limit: 1000)"; \
			FAT=$$((FAT+1)); \
		fi; \
	done; \
	if [ $$FAT -eq 0 ]; then echo "     ✅ All blueprints are under 1000 lines"; fi
	@echo ""
	@echo "  2. Duplicate utility check..."
	@if grep -rn "def _get_or_404\|def _parse_date" app/blueprints/ --include="*.py" 2>/dev/null | grep -v __pycache__; then \
		echo "     ❌ Duplicate utility functions found!"; \
		exit 1; \
	else \
		echo "     ✅ No duplicate utilities (helpers.py is used)"; \
	fi
	@echo ""
	@echo "  3. Generic except Exception count..."
	@COUNT=$$(grep -rn "except Exception" app/blueprints/ --include="*.py" | grep -v __pycache__ | wc -l | tr -d ' '); \
	echo "     ℹ️  $$COUNT 'except Exception' blocks (target: <60)"; \
	if [ $$COUNT -gt 60 ]; then \
		echo "     ⚠️  Above target!"; \
	else \
		echo "     ✅ Within target"; \
	fi
	@echo ""
	@echo "  🏗️  Architecture check completed."

# ── Full Setup (first time) ────────────────────────────────────────────
setup: deps db-init seed
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ SETUP COMPLETE!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  To start the application:"
	@echo "    make run"
	@echo ""
	@echo "  To run tests:"
	@echo "    make test"
	@echo ""
	@echo "  Open in browser: http://localhost:$(PORT)"
	@echo ""

# ── Sprint Deploy ───────────────────────────────────────────────────────
deploy: deps db-upgrade seed test
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ SPRINT DEPLOY COMPLETE!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  To start the application:"
	@echo "    make run"
	@echo ""

# ── Reset ───────────────────────────────────────────────────────────────
reset:
	@echo "♻️  Resetting database..."
	@rm -f $(DB_FILE)
	@echo "   🗑️  $(DB_FILE) deleted"
	@$(FLASK) db upgrade
	@echo "   ✅ Table structure recreated"
	@$(PYTHON) scripts/seed_demo_data.py
	@echo "   ✅ Demo data loaded"
	@echo ""
	@echo "   ♻️  Reset complete!"
	@echo ""

# ── Clean ───────────────────────────────────────────────────────────────
clean:
	@echo "🧹 Cleaning up..."
	@rm -f $(DB_FILE)
	@find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -not -path './.venv/*' -delete 2>/dev/null || true
	@echo "   ✅ Cleaned (DB + cache)"

# ── Status ──────────────────────────────────────────────────────────────
status:
	@echo ""
	@echo "  SAP Transformation Platform — Project Status"
	@echo "  ═══════════════════════════════════════════"
	@echo ""
	@echo "  Python:      $$($(PYTHON) --version 2>&1)"
	@echo "  Flask:       $$($(PYTHON) -c 'import flask; print(flask.__version__)' 2>/dev/null || echo 'not installed')"
	@echo "  SQLAlchemy:  $$($(PYTHON) -c 'import sqlalchemy; print(sqlalchemy.__version__)' 2>/dev/null || echo 'not installed')"
	@echo "  DB file:     $$([ -f $(DB_FILE) ] && echo '✅ $(DB_FILE) ('"$$(du -h $(DB_FILE) | cut -f1)"')' || echo '❌ Not found')"
	@echo "  Test count:  $$(grep -r 'def test_' tests/ | wc -l | tr -d ' ') tests"
	@echo "  API endpoint: $$(grep -r '@.*_bp\.' app/blueprints/ | wc -l | tr -d ' ') endpoints"
	@echo ""
	@if [ -f $(DB_FILE) ]; then \
		echo "  DB Table Record Counts:"; \
		$(PYTHON) scripts/db_status.py; \
	fi
	@echo ""

# ── Demo Environment ────────────────────────────────────────────────────
seed-demo: deps
	@echo ""
	@$(PYTHON) scripts/seed_quick_demo.py
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ DEMO ENVIRONMENT READY!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  To start the application:"
	@echo "    make run"
	@echo ""
	@echo "  Open in browser: http://localhost:$(PORT)"
	@echo ""

# ── Demo Reset & Snapshot ─────────────────────────────────────────────
demo-reset: deps
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  DEMO ENVIRONMENT RESET"
	@echo "═══════════════════════════════════════════════════════════"
	@rm -f $(DB_FILE)
	@mkdir -p instance
	@$(PYTHON) scripts/seed_demo_data.py
	@cp $(DB_FILE) $(DB_FILE).demo-snapshot
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ DEMO READY — snapshot saved"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Before demo:  make run"
	@echo "  After demo:   make demo-restore"
	@echo ""

demo-snapshot:
	@if [ ! -f $(DB_FILE) ]; then \
		echo "  ❌ DB file not found. Run 'make demo-reset' first."; exit 1; \
	fi
	@echo "📸 Saving demo snapshot..."
	@cp $(DB_FILE) $(DB_FILE).demo-snapshot
	@echo "   ✅ Snapshot saved: $(DB_FILE).demo-snapshot"

demo-restore:
	@if [ ! -f $(DB_FILE).demo-snapshot ]; then \
		echo "  ❌ Snapshot not found. Run 'make demo-reset' first."; exit 1; \
	fi
	@echo "♻️  Restoring demo snapshot..."
	@cp $(DB_FILE).demo-snapshot $(DB_FILE)
	@echo "   ✅ Demo data restored (<1 sec)"
	@echo ""
	@echo "  To start the application: make run"
	@echo ""

# ── Vendor Assets (offline demo) ─────────────────────────────────────
vendor-assets:
	@echo "📥 Downloading vendor JS libraries..."
	@mkdir -p static/vendor
	@curl -sL "https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js" -o static/vendor/chart.umd.min.js
	@curl -sL "https://cdn.jsdelivr.net/npm/frappe-gantt@0.6.1/dist/frappe-gantt.min.js" -o static/vendor/frappe-gantt.min.js
	@echo "   ✅ Vendor assets downloaded: static/vendor/"

# ── Tenant Management ──────────────────────────────────────────────────
tenant-list: deps
	@$(PYTHON) scripts/manage_tenants.py list

tenant-status: deps
	@$(PYTHON) scripts/manage_tenants.py status

tenant-create: deps
	@if [ -z "$(ID)" ]; then echo "  ❌ Usage: make tenant-create ID=acme NAME='Acme Corp'"; exit 1; fi
	@$(PYTHON) scripts/manage_tenants.py create $(ID) --name "$(NAME)"

tenant-init: deps
	@if [ -z "$(ID)" ]; then echo "  ❌ Usage: make tenant-init ID=acme"; exit 1; fi
	@$(PYTHON) scripts/manage_tenants.py init $(ID)

tenant-seed: deps
	@if [ -z "$(ID)" ]; then echo "  ❌ Usage: make tenant-seed ID=acme"; exit 1; fi
	@$(PYTHON) scripts/manage_tenants.py seed $(ID)
