#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Frontend Smoke Test — validates static assets, API endpoints, and
#  error response shapes against a running server.
#
#  Usage:  bash tests/test_frontend_smoke.sh [base_url]
#  Default: http://localhost:5001
# ═══════════════════════════════════════════════════════════════════

BASE="${1:-http://localhost:5001}"
PASS=0
FAIL=0

check() {
    local name="$1" url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$status" = "200" ]; then
        echo "  ✅ $name"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $name (HTTP $status)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "═══════════════════════════════════════"
echo "  Frontend Smoke Test"
echo "  Server: $BASE"
echo "═══════════════════════════════════════"

echo ""
echo "--- Static Assets ---"
check "index.html"     "$BASE"
check "api.js"         "$BASE/static/js/api.js"
check "explore-api.js" "$BASE/static/js/explore-api.js"
check "constants.js"   "$BASE/static/js/constants.js"
check "main.css"       "$BASE/static/css/main.css"

echo ""
echo "--- API Endpoints (GET) ---"
check "Health"         "$BASE/api/v1/health"
check "Requirements"   "$BASE/api/v1/explore/requirements?project_id=1"
check "Workshops"      "$BASE/api/v1/explore/workshops?project_id=1"
check "Process Levels" "$BASE/api/v1/explore/process-levels?project_id=1&level=1"
check "Open Items"     "$BASE/api/v1/explore/open-items?project_id=1"
check "Scope Matrix"   "$BASE/api/v1/explore/scope-matrix?project_id=1"
check "Backlog"        "$BASE/api/v1/programs/1/backlog"
check "Test Catalog"   "$BASE/api/v1/programs/1/testing/catalog"
check "Team Members"   "$BASE/api/v1/programs/1/team-members"
check "RAID — Risks"   "$BASE/api/v1/programs/1/risks"

echo ""
echo "--- Error Shape Validation ---"

# 404 error shape
ERR_BODY=$(curl -s "$BASE/api/v1/explore/requirements/999999")
HAS_ERROR=$(echo "$ERR_BODY" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ok = 'error' in d and 'code' in d and d['code'].startswith('ERR_')
    print('ok' if ok else 'fail')
except:
    print('fail')
" 2>/dev/null)

if [ "$HAS_ERROR" = "ok" ]; then
    echo "  ✅ 404 error shape standard"
    PASS=$((PASS + 1))
else
    echo "  ❌ 404 error shape non-standard: $ERR_BODY"
    FAIL=$((FAIL + 1))
fi

# 400 error shape (missing project_id)
ERR_BODY2=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{"title":"smoke test"}' "$BASE/api/v1/explore/requirements")
HAS_ERROR2=$(echo "$ERR_BODY2" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ok = 'error' in d and 'code' in d
    print('ok' if ok else 'fail')
except:
    print('fail')
" 2>/dev/null)

if [ "$HAS_ERROR2" = "ok" ]; then
    echo "  ✅ 400 validation error shape standard"
    PASS=$((PASS + 1))
else
    echo "  ❌ 400 validation error shape: $ERR_BODY2"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "═══════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
