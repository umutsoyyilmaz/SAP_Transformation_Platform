"""Sprint 23 — PWA Blueprint: offline fallback, Service Worker scope, PWA health."""
from flask import Blueprint, jsonify, send_from_directory, render_template_string
import os, json

pwa_bp = Blueprint("pwa", __name__)

# ── Offline fallback page ──────────────────────────────────────────────

OFFLINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Offline — SAP Transformation Platform</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Inter',-apple-system,system-ui,sans-serif;display:flex;
       align-items:center;justify-content:center;min-height:100vh;
       background:#f5f6f7;color:#32363a;text-align:center;padding:24px}
  .wrap{max-width:420px}
  .icon{font-size:72px;margin-bottom:24px}
  h1{font-size:22px;margin-bottom:8px;color:#354a5f}
  p{font-size:14px;color:#6a6d70;line-height:1.6;margin-bottom:24px}
  .btn{display:inline-block;padding:10px 28px;background:#0070f2;color:#fff;
       border:none;border-radius:8px;font-size:14px;font-weight:600;
       cursor:pointer;text-decoration:none}
  .btn:hover{background:#0054b5}
</style>
</head>
<body>
<div class="wrap">
  <div class="icon">📡</div>
  <h1>You are offline</h1>
  <p>The SAP Transformation Platform requires an internet connection for most features.
     Some cached pages may still be available.</p>
  <a class="btn" href="/" onclick="window.location.reload();return false;">Try Again</a>
</div>
</body>
</html>"""


@pwa_bp.route("/offline")
def offline():
    """Serve offline fallback page."""
    return render_template_string(OFFLINE_HTML), 200


# ── PWA status endpoint ────────────────────────────────────────────────

@pwa_bp.route("/api/pwa/status")
def pwa_status():
    """Return PWA configuration status."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    manifest_exists = os.path.isfile(os.path.join(static_dir, "manifest.json"))
    sw_exists = os.path.isfile(os.path.join(static_dir, "sw.js"))
    icons_dir = os.path.join(static_dir, "icons")
    icon_count = len([f for f in os.listdir(icons_dir) if f.endswith(".png")]) if os.path.isdir(icons_dir) else 0

    return jsonify({
        "pwa_enabled": True,
        "manifest": manifest_exists,
        "service_worker": sw_exists,
        "icons": icon_count,
        "offline_page": True,
        "features": {
            "install_prompt": True,
            "offline_indicator": True,
            "bottom_navigation": True,
            "pull_to_refresh": True,
            "swipe_navigation": True,
            "dark_mode_support": True,
        },
    })


# ── PWA manifest endpoint (dynamic, if needed) ────────────────────────

@pwa_bp.route("/api/pwa/manifest")
def pwa_manifest():
    """Return manifest.json content for inspection."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    manifest_path = os.path.join(static_dir, "manifest.json")
    if os.path.isfile(manifest_path):
        with open(manifest_path, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "manifest not found"}), 404


# ── Cache management endpoint ──────────────────────────────────────────

@pwa_bp.route("/api/pwa/cache-info")
def cache_info():
    """Return info about cacheable static assets."""
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    assets = {"css": [], "js": [], "icons": []}
    for root, _dirs, files in os.walk(static_dir):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), static_dir)
            if fn.endswith(".css"):
                assets["css"].append(f"/static/{rel}")
            elif fn.endswith(".js"):
                assets["js"].append(f"/static/{rel}")
            elif fn.endswith(".png"):
                assets["icons"].append(f"/static/{rel}")

    return jsonify({
        "total_assets": sum(len(v) for v in assets.values()),
        "assets": assets,
    })
