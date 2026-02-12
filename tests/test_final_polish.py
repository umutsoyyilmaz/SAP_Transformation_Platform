"""
S24 — Final Polish & Platform v1.0  test suite.

Validates all changes made during the final polish sprint:
  1. Error handlers (404/500/405/429)
  2. Query.get() → db.session.get() migration
  3. Rate limiter configuration
  4. Infrastructure files (LICENSE, .env.example, docker-compose.prod.yml, backup_db.sh)
  5. JS error handler integration
  6. N+1 query optimisation (fit_propagation cache)
  7. README updates
  8. Boolean filter fix (.is_(False))
"""

import os
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════════════
# 1. ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorHandler404:
    """404 returns JSON for API paths and HTML for browser paths."""

    def test_api_404_json(self, client):
        resp = client.get("/api/v1/nonexistent-route-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "Not found"

    def test_browser_404_html(self, client):
        resp = client.get(
            "/nonexistent-page",
            headers={"Accept": "text/html"},
        )
        # SPA fallback: serves index.html with 200 for client-side routing
        assert resp.status_code == 200
        assert b"<!DOCTYPE html>" in resp.data or b"<html" in resp.data

    def test_api_404_has_path(self, client):
        resp = client.get("/api/v1/does-not-exist-abc")
        data = resp.get_json()
        assert "path" in data


class TestErrorHandler405:
    """405 Method Not Allowed."""

    def test_method_not_allowed(self, client):
        # POST to health endpoint which only accepts GET
        resp = client.post("/api/v1/health")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data["error"] == "Method not allowed"


class TestErrorHandler500:
    """500 returns JSON for API paths."""

    # We can't easily trigger a real 500 in tests without mocking,
    # but we verify the handler is registered.
    def test_500_handler_registered(self, app):
        handlers = app.error_handler_spec.get(None, {})
        assert 500 in handlers


class TestErrorHandler429:
    """429 handler is registered."""

    def test_429_handler_registered(self, app):
        handlers = app.error_handler_spec.get(None, {})
        assert 429 in handlers


# ═══════════════════════════════════════════════════════════════════════════
# 2. QUERY.GET() MIGRATION
# ═══════════════════════════════════════════════════════════════════════════


class TestNoDeprecatedQueryGet:
    """Ensure no deprecated Model.query.get() calls remain in the codebase."""

    def test_no_query_get_in_app(self):
        app_dir = ROOT / "app"
        violations = []
        for py_file in app_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for i, line in enumerate(content.splitlines(), 1):
                if ".query.get(" in line and "db.session.get" not in line:
                    violations.append(f"{py_file.relative_to(ROOT)}:{i}")
        assert violations == [], f"Deprecated .query.get() calls found:\n" + "\n".join(violations)


# ═══════════════════════════════════════════════════════════════════════════
# 3. RATE LIMITER CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════


class TestRateLimiterConfig:
    """Rate limiter should use REDIS_URL env var, falling back to memory://."""

    def test_limiter_uses_env_var(self):
        init_path = ROOT / "app" / "__init__.py"
        content = init_path.read_text(encoding="utf-8")
        # Should reference REDIS_URL from env, not hardcoded memory://
        assert 'os.getenv("REDIS_URL"' in content or 'app.config.get("REDIS_URL"' in content
        # Should not have bare memory:// as the only option
        assert 'storage_uri="memory://"' not in content


# ═══════════════════════════════════════════════════════════════════════════
# 4. INFRASTRUCTURE FILES
# ═══════════════════════════════════════════════════════════════════════════


class TestInfrastructureFiles:
    """Critical infrastructure files exist with expected content."""

    def test_license_exists(self):
        license_path = ROOT / "LICENSE"
        assert license_path.exists(), "LICENSE file is missing"
        content = license_path.read_text(encoding="utf-8")
        assert "MIT" in content
        assert "Umut Soyyilmaz" in content

    def test_env_example_exists(self):
        env_path = ROOT / ".env.example"
        assert env_path.exists(), ".env.example is missing"
        content = env_path.read_text(encoding="utf-8")
        assert "SECRET_KEY" in content
        assert "DATABASE_URL" in content

    def test_docker_compose_prod_exists(self):
        prod_path = ROOT / "docker" / "docker-compose.prod.yml"
        assert prod_path.exists(), "docker-compose.prod.yml is missing"
        content = prod_path.read_text(encoding="utf-8")
        assert "deploy" in content or "resources" in content

    def test_backup_script_exists(self):
        script_path = ROOT / "scripts" / "backup_db.sh"
        assert script_path.exists(), "backup_db.sh is missing"
        assert os.access(script_path, os.X_OK), "backup_db.sh is not executable"

    def test_backup_script_uses_pg_dump(self):
        content = (ROOT / "scripts" / "backup_db.sh").read_text(encoding="utf-8")
        assert "pg_dump" in content

    def test_ci_workflow_exists(self):
        ci_path = ROOT / ".github" / "workflows" / "ci.yml"
        assert ci_path.exists(), "ci.yml is missing"
        content = ci_path.read_text(encoding="utf-8")
        assert "pytest" in content


# ═══════════════════════════════════════════════════════════════════════════
# 5. JS ERROR HANDLER INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════


class TestJSErrorHandler:
    """Global JS error handler is created and linked in index.html."""

    def test_error_handler_js_exists(self):
        js_path = ROOT / "static" / "js" / "error-handler.js"
        assert js_path.exists()
        content = js_path.read_text(encoding="utf-8")
        assert "window.onerror" in content or "addEventListener" in content

    def test_error_handler_linked_in_html(self):
        html_path = ROOT / "templates" / "index.html"
        content = html_path.read_text(encoding="utf-8")
        assert "error-handler.js" in content

    def test_error_handler_loaded_before_app(self):
        """error-handler.js should appear before app.js in index.html."""
        html_path = ROOT / "templates" / "index.html"
        content = html_path.read_text(encoding="utf-8")
        eh_pos = content.index('src="/static/js/error-handler.js"')
        app_pos = content.index('src="/static/js/app.js"')
        assert eh_pos < app_pos, "error-handler.js must load before app.js"


# ═══════════════════════════════════════════════════════════════════════════
# 6. N+1 QUERY FIX — FIT PROPAGATION CACHE
# ═══════════════════════════════════════════════════════════════════════════


class TestFitPropagationCache:
    """Fit propagation should use pre-loaded cache instead of per-step queries."""

    def test_no_session_get_in_propagation_loop(self):
        fp_path = ROOT / "app" / "services" / "fit_propagation.py"
        content = fp_path.read_text(encoding="utf-8")
        # The loop section should use levels_cache/parent_cache, not db.session.get
        # Find the "for step in steps:" block
        loop_start = content.index("for step in steps:")
        loop_section = content[loop_start:]
        assert "db.session.get" not in loop_section
        assert "levels_cache" in content
        assert "parent_cache" in content


# ═══════════════════════════════════════════════════════════════════════════
# 7. README QUALITY
# ═══════════════════════════════════════════════════════════════════════════


class TestReadmeQuality:
    """README should have English content and up-to-date metrics."""

    def test_readme_has_english_quick_start(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "Quick Start" in content
        assert "make setup" in content
        assert "make run" in content

    def test_readme_has_docker_section(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "docker" in content.lower()
        assert "docker-compose.prod.yml" in content

    def test_readme_references_license(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "MIT" in content
        assert "LICENSE" in content

    def test_readme_has_current_module_count(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "17" in content  # 17 modules


# ═══════════════════════════════════════════════════════════════════════════
# 8. BOOLEAN FILTER FIX
# ═══════════════════════════════════════════════════════════════════════════


class TestBooleanFilterFix:
    """ai_bp.py should use .is_(False) instead of == False."""

    def test_no_bare_equality_false(self):
        ai_bp_path = ROOT / "app" / "blueprints" / "ai_bp.py"
        content = ai_bp_path.read_text(encoding="utf-8")
        # Should not have == False (even with noqa)
        assert "== False" not in content, "Should use .is_(False) instead of == False"
        # Should have .is_(False)
        assert ".is_(False)" in content


# ═══════════════════════════════════════════════════════════════════════════
# 9. ERROR HANDLER SPA FALLBACK
# ═══════════════════════════════════════════════════════════════════════════


class TestSPAFallback:
    """Unknown browser paths should serve SPA index.html for client-side routing."""

    def test_spa_fallback_returns_index(self, client):
        resp = client.get(
            "/some/client/route",
            headers={"Accept": "text/html"},
        )
        # SPA fallback: unknown browser paths serve index.html with 200
        assert resp.status_code == 200
        body = resp.data.decode("utf-8")
        assert "SAP" in body or "<!DOCTYPE" in body

    def test_api_path_does_not_fallback(self, client):
        resp = client.get("/api/v1/nonexistent")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data is not None  # JSON, not HTML


# ═══════════════════════════════════════════════════════════════════════════
# 10. SKIP_PERMISSION DOCUMENTATION
# ═══════════════════════════════════════════════════════════════════════════


class TestSkipPermissionAnnotated:
    """skip_permission=True should be annotated, not left as TODO."""

    def test_no_todo_remove_in_skip_permission(self):
        for rel_path in [
            "app/blueprints/explore/requirements.py",
            "app/blueprints/explore/open_items.py",
        ]:
            full = ROOT / rel_path
            content = full.read_text(encoding="utf-8")
            if "skip_permission" in content:
                assert "TODO: remove" not in content, (
                    f"{rel_path} still has TODO on skip_permission"
                )


# ═══════════════════════════════════════════════════════════════════════════
# 11. DOCKER PRODUCTION HARDENING
# ═══════════════════════════════════════════════════════════════════════════


class TestDockerProdCompose:
    """Production compose should enforce required env vars and limits."""

    def test_no_source_volume_mount(self):
        content = (ROOT / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
        assert "../:/app" not in content, "Prod compose should not mount source code"

    def test_resource_limits_defined(self):
        content = (ROOT / "docker" / "docker-compose.prod.yml").read_text(encoding="utf-8")
        assert "cpus" in content or "memory" in content


# ═══════════════════════════════════════════════════════════════════════════
# 12. PWA MANIFEST (from S23 — regression check)
# ═══════════════════════════════════════════════════════════════════════════


class TestPWARegression:
    """PWA manifest and service worker still intact after S24 edits."""

    def test_manifest_exists(self):
        assert (ROOT / "static" / "manifest.json").exists()

    def test_service_worker_exists(self):
        assert (ROOT / "static" / "sw.js").exists()

    def test_manifest_linked_in_html(self):
        content = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
        assert 'rel="manifest"' in content
