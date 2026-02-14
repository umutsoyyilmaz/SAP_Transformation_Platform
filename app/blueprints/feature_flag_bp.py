"""
Feature Flag Blueprint — Sprint 9 (Item 4.1)

Admin API for managing feature flags and tenant overrides.
Also serves the feature flags admin UI.
"""

from flask import Blueprint, jsonify, request, render_template_string

from app.services import feature_flag_service as svc

feature_flag_bp = Blueprint("feature_flag", __name__, url_prefix="/api/v1/admin/feature-flags")
feature_flag_ui_bp = Blueprint("feature_flag_ui", __name__)


# ═══════════════════════════════════════════════════════════════
# Global flag CRUD
# ═══════════════════════════════════════════════════════════════

@feature_flag_bp.route("", methods=["GET"])
def list_flags():
    """List all feature flags."""
    return jsonify(svc.list_flags()), 200


@feature_flag_bp.route("", methods=["POST"])
def create_flag():
    """Create a new feature flag."""
    data = request.get_json(silent=True) or {}
    if not data.get("key"):
        return jsonify({"error": "key is required"}), 400
    flag, err = svc.create_flag(data)
    if err:
        return jsonify({"error": err}), 409
    return jsonify(flag.to_dict()), 201


@feature_flag_bp.route("/<int:flag_id>", methods=["GET"])
def get_flag(flag_id):
    """Get a single feature flag."""
    flag = svc.get_flag(flag_id)
    if not flag:
        return jsonify({"error": "Flag not found"}), 404
    return jsonify(flag.to_dict()), 200


@feature_flag_bp.route("/<int:flag_id>", methods=["PUT"])
def update_flag(flag_id):
    """Update a feature flag."""
    data = request.get_json(silent=True) or {}
    flag, err = svc.update_flag(flag_id, data)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(flag.to_dict()), 200


@feature_flag_bp.route("/<int:flag_id>", methods=["DELETE"])
def delete_flag(flag_id):
    """Delete a feature flag."""
    ok, err = svc.delete_flag(flag_id)
    if not ok:
        return jsonify({"error": err}), 404
    return jsonify({"message": "Deleted"}), 200


# ═══════════════════════════════════════════════════════════════
# Tenant override endpoints
# ═══════════════════════════════════════════════════════════════

@feature_flag_bp.route("/tenant/<int:tenant_id>", methods=["GET"])
def get_tenant_flags(tenant_id):
    """List all flags with their effective state for a tenant."""
    return jsonify(svc.get_tenant_flags(tenant_id)), 200


@feature_flag_bp.route("/tenant/<int:tenant_id>/<int:flag_id>", methods=["PUT"])
def set_tenant_flag(tenant_id, flag_id):
    """Set a tenant-level feature flag override."""
    data = request.get_json(silent=True) or {}
    if "is_enabled" not in data:
        return jsonify({"error": "is_enabled is required"}), 400
    override, err = svc.set_tenant_flag(tenant_id, flag_id, data["is_enabled"])
    if err:
        return jsonify({"error": err}), 404
    return jsonify(override.to_dict()), 200


@feature_flag_bp.route("/tenant/<int:tenant_id>/<int:flag_id>", methods=["DELETE"])
def remove_tenant_flag(tenant_id, flag_id):
    """Remove tenant override — fall back to global default."""
    ok, err = svc.remove_tenant_flag(tenant_id, flag_id)
    if not ok:
        return jsonify({"error": err}), 404
    return jsonify({"message": "Override removed"}), 200


# ═══════════════════════════════════════════════════════════════
# Check endpoint (for use by application code)
# ═══════════════════════════════════════════════════════════════

@feature_flag_bp.route("/check/<flag_key>", methods=["GET"])
def check_flag(flag_key):
    """Check if a flag is enabled for the specified tenant."""
    tenant_id = request.args.get("tenant_id", type=int)
    if not tenant_id:
        return jsonify({"error": "tenant_id query param required"}), 400
    enabled = svc.is_enabled(flag_key, tenant_id)
    return jsonify({"key": flag_key, "tenant_id": tenant_id, "enabled": enabled}), 200


# ═══════════════════════════════════════════════════════════════
# Admin UI
# ═══════════════════════════════════════════════════════════════

FEATURE_FLAGS_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feature Flags — Admin</title>
<link rel="stylesheet" href="/static/css/style.css">
<style>
body{font-family:system-ui;margin:0;padding:20px;background:#f5f5f5}
.container{max-width:960px;margin:0 auto}
h1{color:#1a365d}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1)}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid #e2e8f0}
th{background:#2d3748;color:#fff;font-weight:600}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600}
.badge-on{background:#c6f6d5;color:#22543d}
.badge-off{background:#fed7d7;color:#822727}
.btn{padding:6px 12px;border:none;border-radius:4px;cursor:pointer;font-size:.85rem}
.btn-primary{background:#3182ce;color:#fff}
.btn-danger{background:#e53e3e;color:#fff}
.btn-sm{padding:4px 8px;font-size:.75rem}
.form-row{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.form-row input,.form-row select{padding:6px 10px;border:1px solid #cbd5e0;border-radius:4px}
.form-row input[type=text]{flex:1;min-width:160px}
#msg{padding:8px 12px;margin-bottom:12px;border-radius:4px;display:none}
.msg-ok{background:#c6f6d5;color:#22543d;display:block!important}
.msg-err{background:#fed7d7;color:#822727;display:block!important}
</style>
</head>
<body>
<div class="container">
<h1>🚩 Feature Flags</h1>
<p style="color:#4a5568;margin-bottom:16px;line-height:1.6">
  Feature Flags, platformdaki özelliklerin tenant bazında açılıp kapatılmasını sağlar.
  Yeni özellikler kademeli olarak yayınlanabilir (gradual rollout), A/B testleri yapılabilir
  ve belirli müşterilere özel fonksiyonlar sunulabilir.
  <strong>Örnek:</strong> AI Assistant, Beta Dashboard, Advanced Reporting gibi özellikleri
  belirli tenant'lara açabilir, diğerlerinde kapalı tutabilirsiniz.
</p>
<div id="msg"></div>
<h3>Create Flag</h3>
<div class="form-row">
  <input type="text" id="ff-key" placeholder="Flag key (e.g. ai_assistant)">
  <input type="text" id="ff-name" placeholder="Display name">
  <select id="ff-cat"><option value="general">General</option><option value="ai">AI</option><option value="beta">Beta</option><option value="experimental">Experimental</option></select>
  <label><input type="checkbox" id="ff-default"> Default ON</label>
  <button class="btn btn-primary" onclick="createFlag()">Create</button>
</div>
<table>
<thead><tr><th>Key</th><th>Name</th><th>Category</th><th>Default</th><th>Actions</th></tr></thead>
<tbody id="flags-body"></tbody>
</table>
</div>
<script>
const API='/api/v1/admin/feature-flags';
const msg=document.getElementById('msg');
function showMsg(t,ok){msg.textContent=t;msg.className=ok?'msg-ok':'msg-err';setTimeout(()=>msg.style.display='none',3000)}
async function load(){
  const r=await fetch(API);const data=await r.json();
  const tb=document.getElementById('flags-body');tb.innerHTML='';
  data.forEach(f=>{
    const tr=document.createElement('tr');
    tr.innerHTML=`<td>${f.key}</td><td>${f.display_name}</td><td>${f.category}</td>
      <td><span class="badge ${f.default_enabled?'badge-on':'badge-off'}">${f.default_enabled?'ON':'OFF'}</span></td>
      <td><button class="btn btn-sm btn-primary" onclick="toggleDefault(${f.id},${!f.default_enabled})">Toggle</button>
          <button class="btn btn-sm btn-danger" onclick="deleteFlag(${f.id})">Delete</button></td>`;
    tb.appendChild(tr);
  });
}
async function createFlag(){
  const key=document.getElementById('ff-key').value.trim();
  if(!key)return showMsg('Key required',false);
  const r=await fetch(API,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key,display_name:document.getElementById('ff-name').value||key,
      category:document.getElementById('ff-cat').value,
      default_enabled:document.getElementById('ff-default').checked})});
  if(r.ok){showMsg('Created',true);document.getElementById('ff-key').value='';document.getElementById('ff-name').value='';load()}
  else{const e=await r.json();showMsg(e.error||'Error',false)}
}
async function toggleDefault(id,val){
  await fetch(API+'/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({default_enabled:val})});load();
}
async function deleteFlag(id){
  if(!confirm('Delete this flag?'))return;
  await fetch(API+'/'+id,{method:'DELETE'});load();
}
load();
</script>
</body>
</html>
"""


@feature_flag_ui_bp.route("/feature-flags")
def feature_flags_admin():
    return FEATURE_FLAGS_UI
