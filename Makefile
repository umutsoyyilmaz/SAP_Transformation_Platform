# ═══════════════════════════════════════════════════════════════════════════
# SAP Transformation Platform — Local Development Makefile
# ═══════════════════════════════════════════════════════════════════════════
#
# Kullanım:
#   make setup       → İlk kurulum (venv + deps + db + seed)
#   make run         → Uygulamayı başlat (http://localhost:5001)
#   make seed        → Demo veri yükle
#   make test        → Tüm testleri çalıştır
#   make reset       → DB sıfırla + yeniden seed
#   make deploy      → Sprint sonrası tam deploy (migrate + seed + test + run)
#
# ═══════════════════════════════════════════════════════════════════════════

PYTHON   := .venv/bin/python
PIP      := .venv/bin/pip
FLASK    := FLASK_APP=wsgi.py .venv/bin/flask
PYTEST   := .venv/bin/python -m pytest
DB_FILE  := instance/sap_platform_dev.db
PORT     := 5001

.PHONY: help setup venv deps db-init db-migrate db-upgrade seed seed-verbose \
        run test test-verbose reset clean deploy status

# ── Default ──────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  SAP Transformation Platform — Yerel Geliştirme Komutları"
	@echo "  ═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  İlk Kurulum:"
	@echo "    make setup          Tam kurulum (venv + bağımlılık + DB + seed data)"
	@echo ""
	@echo "  Günlük Kullanım:"
	@echo "    make run            Uygulamayı başlat (http://localhost:$(PORT))"
	@echo "    make test           Tüm testleri çalıştır"
	@echo "    make test-verbose   Detaylı test çıktısı"
	@echo "    make seed           Demo verileri yükle (mevcut veriyi temizler)"
	@echo "    make seed-verbose   Demo verileri yükle (detaylı çıktı)"
	@echo ""
	@echo "  Sprint Yönetimi:"
	@echo "    make deploy         Sprint deploy: migrate → seed → test → run"
	@echo "    make reset          DB sıfırla + yeniden oluştur + seed"
	@echo "    make status         Proje durumunu göster"
	@echo ""
	@echo "  Bakım:"
	@echo "    make db-migrate     Yeni migration oluştur"
	@echo "    make db-upgrade     Migration'ları uygula"
	@echo "    make clean          DB + cache dosyalarını temizle"
	@echo ""

# ── Virtual Environment ─────────────────────────────────────────────────
venv:
	@if [ ! -d .venv ]; then \
		echo "🐍 Virtual environment oluşturuluyor..."; \
		python3 -m venv .venv; \
		echo "   ✅ .venv oluşturuldu"; \
	else \
		echo "   ℹ️  .venv zaten mevcut"; \
	fi

# ── Dependencies ────────────────────────────────────────────────────────
deps: venv
	@echo "📦 Bağımlılıklar yükleniyor..."
	@$(PIP) install -r requirements.txt -q
	@echo "   ✅ Tüm bağımlılıklar yüklendi"

# ── Database ────────────────────────────────────────────────────────────
db-init: deps
	@echo "🗄️  Veritabanı oluşturuluyor..."
	@mkdir -p instance
	@$(FLASK) db upgrade
	@echo "   ✅ Veritabanı migration'ları uygulandı"

db-migrate: deps
	@echo "📋 Yeni migration oluşturuluyor..."
	@$(FLASK) db migrate -m "auto-migration"
	@echo "   ✅ Migration dosyası oluşturuldu"

db-upgrade: deps
	@echo "⬆️  Migration'lar uygulanıyor..."
	@$(FLASK) db upgrade
	@echo "   ✅ Veritabanı güncellendi"

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
	@echo "🚀 SAP Transformation Platform başlatılıyor..."
	@echo "   URL: http://localhost:$(PORT)"
	@echo "   Durdurmak için: Ctrl+C"
	@echo ""
	@$(FLASK) run --host=0.0.0.0 --port=$(PORT) --debug

# ── Tests ───────────────────────────────────────────────────────────────
test: deps
	@echo ""
	@echo "🧪 Testler çalıştırılıyor..."
	@GEMINI_API_KEY= $(PYTEST) tests/ -v --tb=short
	@echo ""

test-verbose: deps
	@echo ""
	@GEMINI_API_KEY= $(PYTEST) tests/ -v --tb=long -s
	@echo ""

# ── Full Setup (first time) ────────────────────────────────────────────
setup: deps db-init seed
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ KURULUM TAMAMLANDI!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Uygulamayı başlatmak için:"
	@echo "    make run"
	@echo ""
	@echo "  Testleri çalıştırmak için:"
	@echo "    make test"
	@echo ""
	@echo "  Tarayıcıda açın: http://localhost:$(PORT)"
	@echo ""

# ── Sprint Deploy ───────────────────────────────────────────────────────
deploy: deps db-upgrade seed test
	@echo ""
	@echo "═══════════════════════════════════════════════════════════"
	@echo "  ✅ SPRINT DEPLOY TAMAMLANDI!"
	@echo "═══════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Uygulamayı başlatmak için:"
	@echo "    make run"
	@echo ""

# ── Reset ───────────────────────────────────────────────────────────────
reset:
	@echo "♻️  Veritabanı sıfırlanıyor..."
	@rm -f $(DB_FILE)
	@echo "   🗑️  $(DB_FILE) silindi"
	@$(FLASK) db upgrade
	@echo "   ✅ Tablo yapısı yeniden oluşturuldu"
	@$(PYTHON) scripts/seed_demo_data.py
	@echo "   ✅ Demo veriler yüklendi"
	@echo ""
	@echo "   ♻️  Reset tamamlandı!"
	@echo ""

# ── Clean ───────────────────────────────────────────────────────────────
clean:
	@echo "🧹 Temizlik yapılıyor..."
	@rm -f $(DB_FILE)
	@find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -not -path './.venv/*' -delete 2>/dev/null || true
	@echo "   ✅ Temizlendi (DB + cache)"

# ── Status ──────────────────────────────────────────────────────────────
status:
	@echo ""
	@echo "  SAP Transformation Platform — Proje Durumu"
	@echo "  ═══════════════════════════════════════════"
	@echo ""
	@echo "  Python:      $$($(PYTHON) --version 2>&1)"
	@echo "  Flask:       $$($(PYTHON) -c 'import flask; print(flask.__version__)' 2>/dev/null || echo 'yüklü değil')"
	@echo "  SQLAlchemy:  $$($(PYTHON) -c 'import sqlalchemy; print(sqlalchemy.__version__)' 2>/dev/null || echo 'yüklü değil')"
	@echo "  DB dosyası:  $$([ -f $(DB_FILE) ] && echo '✅ $(DB_FILE) ('"$$(du -h $(DB_FILE) | cut -f1)"')' || echo '❌ Mevcut değil')"
	@echo "  Test sayısı: $$(grep -r 'def test_' tests/ | wc -l | tr -d ' ') test"
	@echo "  API endpoint: $$(grep -r '@.*_bp\.' app/blueprints/ | wc -l | tr -d ' ') endpoint"
	@echo ""
	@if [ -f $(DB_FILE) ]; then \
		echo "  DB Tablo Kayıt Sayıları:"; \
		$(PYTHON) scripts/db_status.py; \
	fi
	@echo ""
