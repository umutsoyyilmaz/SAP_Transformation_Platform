"""Sprint 23 — PWA & Mobile-First Tests

Covers: manifest.json, service-worker serving, offline page,
        PWA status API, cache-info API, mobile CSS, index.html PWA tags,
        responsive meta tags, icon files, and bottom-nav / hamburger DOM.
"""
import pytest
import json
import os

# ── helpers ────────────────────────────────────────────────────────────────

STATIC_ROOT = os.path.join(os.path.dirname(__file__), "..", "static")
TEMPLATE_ROOT = os.path.join(os.path.dirname(__file__), "..", "templates")


@pytest.fixture
def client(app):
    return app.test_client()


# ═══════════════════════════════════════════════════════════════════════════
# 1.  Manifest
# ═══════════════════════════════════════════════════════════════════════════

class TestManifest:
    """PWA Web App Manifest validation."""

    def test_manifest_file_exists(self):
        assert os.path.isfile(os.path.join(STATIC_ROOT, "manifest.json"))

    def test_manifest_valid_json(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        assert "name" in data
        assert "short_name" in data

    def test_manifest_display_standalone(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        assert data["display"] == "standalone"

    def test_manifest_has_icons(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        icons = data.get("icons", [])
        assert len(icons) >= 4
        sizes = [i["sizes"] for i in icons]
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_manifest_theme_color(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        assert data.get("theme_color") == "#354a5f"

    def test_manifest_start_url(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        assert data.get("start_url") in ("/", ".", "/index.html")

    def test_manifest_shortcuts(self):
        with open(os.path.join(STATIC_ROOT, "manifest.json")) as f:
            data = json.load(f)
        shortcuts = data.get("shortcuts", [])
        assert len(shortcuts) >= 1

    def test_manifest_served_via_http(self, client):
        resp = client.get("/static/manifest.json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "name" in data


# ═══════════════════════════════════════════════════════════════════════════
# 2.  Service Worker
# ═══════════════════════════════════════════════════════════════════════════

class TestServiceWorker:
    """Service Worker file validation."""

    def test_sw_file_exists(self):
        assert os.path.isfile(os.path.join(STATIC_ROOT, "sw.js"))

    def test_sw_served_via_http(self, client):
        resp = client.get("/static/sw.js")
        assert resp.status_code == 200
        assert b"addEventListener" in resp.data

    def test_sw_contains_precache_list(self):
        with open(os.path.join(STATIC_ROOT, "sw.js")) as f:
            content = f.read()
        assert "PRECACHE_URLS" in content
        assert "/static/css/main.css" in content

    def test_sw_contains_cache_strategies(self):
        with open(os.path.join(STATIC_ROOT, "sw.js")) as f:
            content = f.read()
        assert "cacheFirstStatic" in content
        assert "networkFirstApi" in content

    def test_sw_has_skip_waiting(self):
        with open(os.path.join(STATIC_ROOT, "sw.js")) as f:
            content = f.read()
        assert "skipWaiting" in content

    def test_sw_has_clients_claim(self):
        with open(os.path.join(STATIC_ROOT, "sw.js")) as f:
            content = f.read()
        assert "clients.claim" in content

    def test_sw_has_offline_fallback(self):
        with open(os.path.join(STATIC_ROOT, "sw.js")) as f:
            content = f.read()
        assert "/offline" in content


# ═══════════════════════════════════════════════════════════════════════════
# 3.  Icons
# ═══════════════════════════════════════════════════════════════════════════

class TestIcons:
    """PWA icon files."""

    REQUIRED_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

    @pytest.mark.parametrize("size", REQUIRED_SIZES)
    def test_icon_file_exists(self, size):
        path = os.path.join(STATIC_ROOT, "icons", f"icon-{size}.png")
        assert os.path.isfile(path), f"icon-{size}.png missing"

    def test_icon_192_served_via_http(self, client):
        resp = client.get("/static/icons/icon-192.png")
        assert resp.status_code == 200

    def test_icon_512_nonzero_size(self):
        path = os.path.join(STATIC_ROOT, "icons", "icon-512.png")
        assert os.path.getsize(path) > 100


# ═══════════════════════════════════════════════════════════════════════════
# 4.  Offline Page
# ═══════════════════════════════════════════════════════════════════════════

class TestOfflinePage:
    """Offline fallback page served by PWA blueprint."""

    def test_offline_returns_200(self, client):
        resp = client.get("/offline")
        assert resp.status_code == 200

    def test_offline_contains_message(self, client):
        resp = client.get("/offline")
        assert b"offline" in resp.data.lower()

    def test_offline_has_retry_button(self, client):
        resp = client.get("/offline")
        assert b"Try Again" in resp.data

    def test_offline_is_valid_html(self, client):
        resp = client.get("/offline")
        assert b"<!DOCTYPE html>" in resp.data
        assert b"</html>" in resp.data


# ═══════════════════════════════════════════════════════════════════════════
# 5.  PWA Status API
# ═══════════════════════════════════════════════════════════════════════════

class TestPWAStatusAPI:
    """PWA status and cache-info endpoints."""

    def test_pwa_status_endpoint(self, client):
        resp = client.get("/api/pwa/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["pwa_enabled"] is True

    def test_pwa_status_manifest_flag(self, client):
        resp = client.get("/api/pwa/status")
        data = resp.get_json()
        assert data["manifest"] is True

    def test_pwa_status_sw_flag(self, client):
        resp = client.get("/api/pwa/status")
        data = resp.get_json()
        assert data["service_worker"] is True

    def test_pwa_status_icon_count(self, client):
        resp = client.get("/api/pwa/status")
        data = resp.get_json()
        assert data["icons"] >= 8

    def test_pwa_status_features(self, client):
        resp = client.get("/api/pwa/status")
        data = resp.get_json()
        features = data["features"]
        assert features["install_prompt"] is True
        assert features["offline_indicator"] is True
        assert features["bottom_navigation"] is True

    def test_pwa_manifest_api(self, client):
        resp = client.get("/api/pwa/manifest")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data

    def test_pwa_cache_info(self, client):
        resp = client.get("/api/pwa/cache-info")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_assets"] > 0
        assert "css" in data["assets"]
        assert "js" in data["assets"]


# ═══════════════════════════════════════════════════════════════════════════
# 6.  Index.html PWA Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestIndexHtmlPWA:
    """Verify index.html includes all PWA-related tags."""

    @pytest.fixture(autouse=True)
    def _load_html(self):
        with open(os.path.join(TEMPLATE_ROOT, "index.html")) as f:
            self.html = f.read()

    def test_has_viewport_meta(self):
        assert 'name="viewport"' in self.html

    def test_has_manifest_link(self):
        assert 'rel="manifest"' in self.html
        assert "manifest.json" in self.html

    def test_has_theme_color_meta(self):
        assert 'name="theme-color"' in self.html
        assert "#354a5f" in self.html

    def test_has_apple_touch_icon(self):
        assert "apple-touch-icon" in self.html

    def test_has_apple_web_app_capable(self):
        assert "apple-mobile-web-app-capable" in self.html

    def test_includes_mobile_css(self):
        assert "mobile.css" in self.html

    def test_includes_pwa_js(self):
        assert "pwa.js" in self.html

    def test_includes_mobile_js(self):
        assert "mobile.js" in self.html

    def test_pwa_scripts_after_app_js(self):
        app_pos = self.html.index("app.js")
        pwa_pos = self.html.index("pwa.js")
        mobile_pos = self.html.index("mobile.js")
        assert pwa_pos > app_pos
        assert mobile_pos > pwa_pos


# ═══════════════════════════════════════════════════════════════════════════
# 7.  Mobile CSS
# ═══════════════════════════════════════════════════════════════════════════

class TestMobileCSS:
    """Verify mobile.css exists and contains key responsive rules."""

    @pytest.fixture(autouse=True)
    def _load_css(self):
        path = os.path.join(STATIC_ROOT, "css", "mobile.css")
        assert os.path.isfile(path), "mobile.css not found"
        with open(path) as f:
            self.css = f.read()

    def test_has_hamburger_styles(self):
        assert ".hamburger-btn" in self.css

    def test_has_bottom_nav_styles(self):
        assert ".bottom-nav" in self.css

    def test_has_install_banner_styles(self):
        assert ".pwa-install-banner" in self.css

    def test_has_offline_indicator_styles(self):
        assert ".offline-indicator" in self.css

    def test_has_sidebar_open_state(self):
        assert ".sidebar.open" in self.css

    def test_has_768px_breakpoint(self):
        assert "max-width: 768px" in self.css

    def test_has_480px_breakpoint(self):
        assert "max-width: 480px" in self.css

    def test_has_touch_target_rule(self):
        assert "min-height: 44px" in self.css

    def test_has_safe_area_support(self):
        assert "safe-area-inset" in self.css

    def test_has_dark_mode_media_query(self):
        assert "prefers-color-scheme: dark" in self.css

    def test_has_reduced_motion(self):
        assert "prefers-reduced-motion" in self.css

    def test_has_print_styles(self):
        assert "@media print" in self.css

    def test_has_standalone_display_mode(self):
        assert "display-mode: standalone" in self.css

    def test_has_sidebar_backdrop(self):
        assert ".sidebar-backdrop" in self.css


# ═══════════════════════════════════════════════════════════════════════════
# 8.  PWA.js
# ═══════════════════════════════════════════════════════════════════════════

class TestPWAJS:
    """Verify pwa.js (Service Worker registration, install prompt)."""

    @pytest.fixture(autouse=True)
    def _load_js(self):
        path = os.path.join(STATIC_ROOT, "js", "pwa.js")
        assert os.path.isfile(path), "pwa.js not found"
        with open(path) as f:
            self.js = f.read()

    def test_has_sw_registration(self):
        assert "serviceWorker.register" in self.js

    def test_has_install_prompt_listener(self):
        assert "beforeinstallprompt" in self.js

    def test_has_online_offline_detection(self):
        assert "navigator.onLine" in self.js
        assert "is-offline" in self.js

    def test_has_public_api(self):
        assert "promptInstall" in self.js
        assert "isOnline" in self.js
        assert "isInstalled" in self.js

    def test_has_update_detection(self):
        assert "updatefound" in self.js


# ═══════════════════════════════════════════════════════════════════════════
# 9.  Mobile.js (Touch Components)
# ═══════════════════════════════════════════════════════════════════════════

class TestMobileJS:
    """Verify mobile.js (hamburger, bottom nav, pull-to-refresh)."""

    @pytest.fixture(autouse=True)
    def _load_js(self):
        path = os.path.join(STATIC_ROOT, "js", "mobile.js")
        assert os.path.isfile(path), "mobile.js not found"
        with open(path) as f:
            self.js = f.read()

    def test_has_hamburger_toggle(self):
        assert "toggleSidebar" in self.js
        assert "hamburgerBtn" in self.js

    def test_has_bottom_nav_creation(self):
        assert "bottomNav" in self.js
        assert "bottom-nav__item" in self.js

    def test_has_pull_to_refresh(self):
        assert "pullRefreshIndicator" in self.js
        assert "touchstart" in self.js

    def test_has_swipe_navigation(self):
        assert "SWIPE_THRESHOLD" in self.js

    def test_has_sidebar_backdrop(self):
        assert "sidebarBackdrop" in self.js

    def test_has_resize_handler(self):
        assert "resize" in self.js

    def test_has_accessibility_attrs(self):
        assert "aria-label" in self.js
        assert "aria-expanded" in self.js

    def test_has_public_api(self):
        assert "openSidebar" in self.js
        assert "closeSidebar" in self.js
        assert "onViewChange" in self.js


# ═══════════════════════════════════════════════════════════════════════════
# 10.  SPA + PWA Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestSPAPWAIntegration:
    """End-to-end: SPA serves PWA resources correctly."""

    def test_root_serves_html_with_pwa_tags(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'rel="manifest"' in html
        assert "pwa.js" in html

    def test_all_precache_assets_accessible(self, client):
        """Every URL in the SW pre-cache list should return 200."""
        precache = [
            "/static/css/main.css",
            "/static/css/mobile.css",
            "/static/js/api.js",
            "/static/js/app.js",
            "/static/js/pwa.js",
            "/static/js/mobile.js",
            "/static/manifest.json",
            "/static/icons/icon-192.png",
            "/static/icons/icon-512.png",
        ]
        for url in precache:
            resp = client.get(url)
            assert resp.status_code == 200, f"{url} returned {resp.status_code}"

    def test_pwa_blueprint_registered(self, app):
        blueprints = list(app.blueprints.keys())
        assert "pwa" in blueprints
