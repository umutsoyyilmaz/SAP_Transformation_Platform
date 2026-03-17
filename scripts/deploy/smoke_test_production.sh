#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  🧪  PERGA SAP Transformation Platform — E2E Production Smoke Test
#  ─────────────────────────────────────────────────────────────────────────────
#  SAP Activate Lifecycle: Discover → Prepare → Explore → Realize → Deploy → Run
#
#  This test connects to the live system from scratch, creates a new program,
#  and tests all SAP Activate phases end-to-end.
#
#  Usage:
#    chmod +x scripts/deploy/smoke_test_production.sh
#    ./scripts/deploy/smoke_test_production.sh                       # default URL
#    ./scripts/deploy/smoke_test_production.sh https://custom.url    # custom URL
#    SMOKE_USER=admin SMOKE_PASS=xxx ./scripts/deploy/smoke_test_production.sh
#
#  Date: 2026-02-14
# ═══════════════════════════════════════════════════════════════════════════════

set -o pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL="${1:-https://app.univer.com.tr}"
API="$BASE_URL/api/v1"
AUTH_USER="${SMOKE_USER:-admin}"
AUTH_PASS="${SMOKE_PASS:-Perga2026!}"
AUTH="-u ${AUTH_USER}:${AUTH_PASS}"
TIMEOUT=30
BODY="/tmp/smoke_body_$$"
TS=$(date +%s)                    # for generating unique names
PROG_NAME="SmokeTest-$TS"

# Colors
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'

PASS=0; FAIL=0; WARN=0; SKIP=0; TOTAL=0
ERRORS=""

# ── Helper Functions ──────────────────────────────────────────────────────────

_curl_get() {
    curl -s --max-time "$TIMEOUT" $AUTH -o "$BODY" -w "%{http_code}|%{time_total}" "$1" 2>/dev/null
}

_curl_post() {
    curl -s --max-time "$TIMEOUT" $AUTH -o "$BODY" -w "%{http_code}|%{time_total}" \
        -X POST -H "Content-Type: application/json" -d "$2" "$1" 2>/dev/null
}

_curl_put() {
    curl -s --max-time "$TIMEOUT" $AUTH -o "$BODY" -w "%{http_code}|%{time_total}" \
        -X PUT -H "Content-Type: application/json" -d "$2" "$1" 2>/dev/null
}

_curl_delete() {
    curl -s --max-time "$TIMEOUT" $AUTH -o "$BODY" -w "%{http_code}|%{time_total}" \
        -X DELETE "$1" 2>/dev/null
}

_parse() { echo "$1" | cut -d'|' -f"$2"; }

# JSON field extraction — dependency-free
_json_val() {
    python3 -c "
import sys,json
try:
    d=json.load(open('$BODY'))
    keys='$1'.split('.')
    for k in keys:
        if isinstance(d, list): d=d[int(k)]
        else: d=d[k]
    print(d)
except: print('')
" 2>/dev/null
}

_json_first_id() {
    python3 -c "
import sys,json
try:
    d=json.load(open('$BODY'))
    items=d.get('items',d) if isinstance(d,dict) else d
    if isinstance(items,list) and len(items)>0:
        print(items[0].get('id',''))
    else: print('')
except: print('')
" 2>/dev/null
}

# ── Test Functions ────────────────────────────────────────────────────────────

test_get() {
    local name="$1"; local url="$2"; local expected="${3:-200}"
    TOTAL=$((TOTAL+1))
    local raw=$(_curl_get "$url")
    local code=$(_parse "$raw" 1); local time=$(_parse "$raw" 2)

    if [ "$code" = "$expected" ]; then
        printf "  ${GREEN}✅${NC} %-50s ${CYAN}%s${NC} ${DIM}(%.2fs)${NC}\n" "$name" "$code" "$time"
        PASS=$((PASS+1))
    elif [ "$code" = "000" ]; then
        printf "  ${RED}❌${NC} %-50s ${RED}TIMEOUT${NC}\n" "$name"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → timeout"
    else
        printf "  ${RED}❌${NC} %-50s ${RED}%s${NC} (expected %s)\n" "$name" "$code" "$expected"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → $code (expected $expected)"
    fi
}

test_post() {
    local name="$1"; local url="$2"; local data="$3"; local expected="${4:-201}"
    TOTAL=$((TOTAL+1))
    local raw=$(_curl_post "$url" "$data")
    local code=$(_parse "$raw" 1); local time=$(_parse "$raw" 2)

    if [ "$code" = "$expected" ] || [ "$code" = "200" ] || [ "$code" = "201" ]; then
        printf "  ${GREEN}✅${NC} %-50s ${CYAN}%s${NC} ${DIM}(%.2fs)${NC}\n" "$name" "$code" "$time"
        PASS=$((PASS+1))
    elif [ "$code" = "000" ]; then
        printf "  ${RED}❌${NC} %-50s ${RED}TIMEOUT${NC}\n" "$name"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → timeout"
    else
        printf "  ${RED}❌${NC} %-50s ${RED}%s${NC} (expected %s)\n" "$name" "$code" "$expected"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → $code"
        # Show error details
        local detail=$(python3 -c "import json; d=json.load(open('$BODY')); print(d.get('error','')[:120])" 2>/dev/null)
        [ -n "$detail" ] && printf "       ${DIM}↳ %s${NC}\n" "$detail"
    fi
}

test_put() {
    local name="$1"; local url="$2"; local data="$3"; local expected="${4:-200}"
    TOTAL=$((TOTAL+1))
    local raw=$(_curl_put "$url" "$data")
    local code=$(_parse "$raw" 1); local time=$(_parse "$raw" 2)

    if [ "$code" = "$expected" ] || [ "$code" = "200" ]; then
        printf "  ${GREEN}✅${NC} %-50s ${CYAN}%s${NC} ${DIM}(%.2fs)${NC}\n" "$name" "$code" "$time"
        PASS=$((PASS+1))
    elif [ "$code" = "000" ]; then
        printf "  ${RED}❌${NC} %-50s ${RED}TIMEOUT${NC}\n" "$name"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → timeout"
    else
        printf "  ${RED}❌${NC} %-50s ${RED}%s${NC} (expected %s)\n" "$name" "$code" "$expected"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → $code"
    fi
}

test_delete() {
    local name="$1"; local url="$2"; local expected="${3:-200}"
    TOTAL=$((TOTAL+1))
    local raw=$(_curl_delete "$url")
    local code=$(_parse "$raw" 1); local time=$(_parse "$raw" 2)

    if [ "$code" = "$expected" ] || [ "$code" = "200" ] || [ "$code" = "204" ]; then
        printf "  ${GREEN}✅${NC} %-50s ${CYAN}%s${NC} ${DIM}(%.2fs)${NC}\n" "$name" "$code" "$time"
        PASS=$((PASS+1))
    else
        printf "  ${RED}❌${NC} %-50s ${RED}%s${NC} (expected %s)\n" "$name" "$code" "$expected"
        FAIL=$((FAIL+1)); ERRORS="$ERRORS\n  ❌ $name → $code"
    fi
}

skip_test() {
    local name="$1"; local reason="$2"
    TOTAL=$((TOTAL+1)); SKIP=$((SKIP+1))
    printf "  ${YELLOW}⏭️${NC}  %-50s ${DIM}%s${NC}\n" "$name" "$reason"
}

section() {
    echo ""
    printf "${BOLD}${YELLOW}━━ %s ━━${NC}\n" "$1"
}

subsection() {
    printf "\n  ${BOLD}%s${NC}\n" "$1"
}

# ═══════════════════════════════════════════════════════════════════════════════
#  START
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
printf "${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}\n"
printf "${BOLD}║  🧪 PERGA — SAP Activate E2E Production Smoke Test          ║${NC}\n"
printf "${BOLD}║  📍 Target:  ${CYAN}%-46s${NC}${BOLD}║${NC}\n" "$BASE_URL"
printf "${BOLD}║  🔐 Auth:    ${CYAN}%-46s${NC}${BOLD}║${NC}\n" "$AUTH_USER"
printf "${BOLD}║  📅 $(date '+%Y-%m-%d %H:%M:%S')                                       ║${NC}\n"
printf "${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}\n"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 0 — INFRASTRUCTURE & CONNECTIVITY"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

subsection "0.1 Server Health"

# Connection check
HTTP_CODE=$(curl -s --max-time 15 $AUTH -o /dev/null -w "%{http_code}" "$BASE_URL" 2>/dev/null)
if [ "$HTTP_CODE" = "000" ]; then
    printf "  ${RED}❌ Could not connect to server: $BASE_URL${NC}\n"; exit 1
fi
if [ "$HTTP_CODE" = "401" ]; then
    printf "  ${RED}❌ Basic Auth error (401)${NC}\n"; exit 1
fi

test_get  "GET  /health"                "$API/health"
test_get  "GET  /health/live"           "$API/health/live"
test_get  "GET  /health/ready"          "$API/health/ready"
test_get  "GET  /health/db-diag"        "$API/health/db-diag"
test_get  "GET  /health/db-columns"     "$API/health/db-columns"

subsection "0.2 Frontend Assets"
test_get  "GET  / (SPA)"               "$BASE_URL"
test_get  "GET  /static/js/app.js"     "$BASE_URL/static/js/app.js"
test_get  "GET  /static/css/style.css" "$BASE_URL/static/css/style.css"

subsection "0.3 Observability"
test_get  "GET  /metrics/requests"      "$API/metrics/requests"
test_get  "GET  /metrics/errors"        "$API/metrics/errors"
test_get  "GET  /audit"                 "$API/audit"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 1 — DISCOVER & PREPARE (Program Setup)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

subsection "1.1 Create Program (SAP Activate = automatic 6 phases)"
test_post "POST /programs (new program)" \
    "$API/programs" \
    "{\"name\":\"$PROG_NAME\",\"description\":\"E2E smoke test $(date +%Y%m%d)\",\"project_type\":\"greenfield\",\"methodology\":\"sap_activate\"}"
PID=$(_json_val "id")
if [ -z "$PID" ] || [ "$PID" = "" ]; then
    printf "  ${RED}⛔ Could not create program — remaining tests cancelled${NC}\n"
    PID=""
fi

if [ -n "$PID" ]; then
    printf "  ${CYAN}ℹ️${NC}  Program ID: ${BOLD}$PID${NC}\n"

    subsection "1.2 Program Detail & Auto-Created Phases"
    test_get "GET  /programs/$PID (detail)" "$API/programs/$PID"
    PHASE_COUNT=$(_json_val "phases.0.id" && echo "yes" || echo "")

    test_get "GET  /programs/$PID/phases"   "$API/programs/$PID/phases"

    subsection "1.3 Governance Structure"
    test_post "POST /programs/$PID/workstreams" \
        "$API/programs/$PID/workstreams" \
        "{\"name\":\"FI/CO Workstream\",\"ws_type\":\"functional\",\"lead_name\":\"Ahmet Yilmaz\"}"
    WS_ID=$(_json_val "id")

    test_post "POST /programs/$PID/committees" \
        "$API/programs/$PID/committees" \
        "{\"name\":\"Steering Committee\",\"committee_type\":\"steering\",\"meeting_frequency\":\"bi-weekly\"}"

    test_post "POST /programs/$PID/committees" \
        "$API/programs/$PID/committees" \
        "{\"name\":\"Change Advisory Board\",\"committee_type\":\"change_advisory\",\"meeting_frequency\":\"weekly\"}"

    subsection "1.4 Team Onboarding"
    test_post "POST /programs/$PID/team (PM)" \
        "$API/programs/$PID/team" \
        "{\"name\":\"Mehmet Kaya\",\"email\":\"mehmet@perga.com.tr\",\"role\":\"project_manager\"}"

    test_post "POST /programs/$PID/team (Dev Lead)" \
        "$API/programs/$PID/team" \
        "{\"name\":\"Elif Demir\",\"email\":\"elif@perga.com.tr\",\"role\":\"technical_lead\"}"

    test_post "POST /programs/$PID/team (Func.)" \
        "$API/programs/$PID/team" \
        "{\"name\":\"Ayse Celik\",\"email\":\"ayse@perga.com.tr\",\"role\":\"functional_consultant\"}"

    test_get  "GET  /programs/$PID/team"       "$API/programs/$PID/team"
    test_get  "GET  /programs/$PID/workstreams" "$API/programs/$PID/workstreams"
    test_get  "GET  /programs/$PID/committees"  "$API/programs/$PID/committees"

    subsection "1.5 Sprint Planning"
    test_post "POST /programs/$PID/sprints" \
        "$API/programs/$PID/sprints" \
        "{\"name\":\"Sprint 1 — Core Config\",\"goal\":\"Core FI/CO/MM configurations\",\"status\":\"planning\"}"
    test_post "POST /programs/$PID/sprints" \
        "$API/programs/$PID/sprints" \
        "{\"name\":\"Sprint 2 — Integration\",\"goal\":\"Integration development\",\"status\":\"planning\"}"
    test_get  "GET  /programs/$PID/sprints" "$API/programs/$PID/sprints"

fi  # PID check

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 2 — EXPLORE (Fit-to-Standard)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -n "$PID" ]; then

    subsection "2.1 Process Hierarchy (L1→L4)"
    test_post "POST process-level L1 (Finance)" \
        "$API/explore/process-levels" \
        "{\"project_id\":$PID,\"level\":1,\"name\":\"Finance & Controlling\",\"code\":\"ST-L1-FI\",\"process_area_code\":\"FI\"}"
    L1_ID=$(_json_val "id")

    if [ -n "$L1_ID" ] && [ "$L1_ID" != "" ]; then
        test_post "POST process-level L2 (GL)" \
            "$API/explore/process-levels" \
            "{\"project_id\":$PID,\"level\":2,\"name\":\"General Ledger\",\"code\":\"ST-L2-GL\",\"parent_id\":\"$L1_ID\",\"process_area_code\":\"FI\"}"
        L2_ID=$(_json_val "id")

        if [ -n "$L2_ID" ] && [ "$L2_ID" != "" ]; then
            test_post "POST process-level L3 (Journal Entry)" \
                "$API/explore/process-levels" \
                "{\"project_id\":$PID,\"level\":3,\"name\":\"Journal Entry Processing\",\"code\":\"ST-L3-JE\",\"parent_id\":\"$L2_ID\",\"scope_item_code\":\"J58\"}"
            L3_ID=$(_json_val "id")

            if [ -n "$L3_ID" ] && [ "$L3_ID" != "" ]; then
                test_post "POST process-level L4 (Manual JE)" \
                    "$API/explore/process-levels" \
                    "{\"project_id\":$PID,\"level\":4,\"name\":\"Manual Journal Entry\",\"code\":\"ST-L4-MJE\",\"parent_id\":\"$L3_ID\",\"fit_status\":\"fit\"}"
                test_post "POST process-level L4 (Recurring JE)" \
                    "$API/explore/process-levels" \
                    "{\"project_id\":$PID,\"level\":4,\"name\":\"Recurring Journal Entry\",\"code\":\"ST-L4-RJE\",\"parent_id\":\"$L3_ID\",\"fit_status\":\"gap\"}"
            fi
        fi
    fi

    test_get  "GET  /explore/process-levels" "$API/explore/process-levels?project_id=$PID"
    test_get  "GET  /explore/process-levels (flat)" "$API/explore/process-levels?project_id=$PID&flat=true"

    subsection "2.2 Fit-to-Standard Workshops"
    test_post "POST workshop (FI F2S)" \
        "$API/explore/workshops" \
        "{\"project_id\":$PID,\"process_area\":\"FI\",\"name\":\"FI Fit-to-Standard Workshop\",\"type\":\"fit_to_standard\",\"status\":\"scheduled\"}"
    WS_ID=$(_json_val "id")

    test_post "POST workshop (MM F2S)" \
        "$API/explore/workshops" \
        "{\"project_id\":$PID,\"process_area\":\"MM\",\"name\":\"MM Procurement Workshop\",\"type\":\"fit_to_standard\",\"status\":\"scheduled\"}"

    test_get  "GET  /explore/workshops"       "$API/explore/workshops?project_id=$PID"
    test_get  "GET  /explore/workshops/stats"  "$API/explore/workshops/stats?project_id=$PID"

    subsection "2.3 Requirements (Gap Analysis)"
    # requirement with scope_item_id
    REQ_SCOPE=""
    if [ -n "$L3_ID" ] && [ "$L3_ID" != "" ]; then
        REQ_SCOPE=",\"scope_item_id\":\"$L3_ID\""
    fi
    test_post "POST requirement (FI gap)" \
        "$API/explore/requirements" \
        "{\"project_id\":$PID,\"title\":\"Custom recurring JE report\",\"type\":\"functional\",\"priority\":\"P2\"$REQ_SCOPE}"
    REQ_ID=$(_json_val "id")

    test_post "POST requirement (MM gap)" \
        "$API/explore/requirements" \
        "{\"project_id\":$PID,\"title\":\"Vendor evaluation custom scoring\",\"type\":\"functional\",\"priority\":\"P3\",\"workshop_id\":\"$WS_ID\"}"

    test_post "POST requirement (technical)" \
        "$API/explore/requirements" \
        "{\"project_id\":$PID,\"title\":\"API gateway integration\",\"type\":\"technical\",\"priority\":\"P1\",\"workshop_id\":\"$WS_ID\"}"

    test_get  "GET  /explore/requirements"       "$API/explore/requirements?project_id=$PID"
    test_get  "GET  /explore/requirements/stats"  "$API/explore/requirements/stats?project_id=$PID"

    subsection "2.4 Open Items"
    test_post "POST open-item (process)" \
        "$API/explore/open-items" \
        "{\"project_id\":$PID,\"title\":\"Clarify intercompany elimination logic\",\"priority\":\"P1\",\"category\":\"process\"}"
    OI_ID=$(_json_val "id")

    test_post "POST open-item (technical)" \
        "$API/explore/open-items" \
        "{\"project_id\":$PID,\"title\":\"Confirm middleware version compatibility\",\"priority\":\"P2\",\"category\":\"technical\"}"

    test_get  "GET  /explore/open-items"       "$API/explore/open-items?project_id=$PID"
    test_get  "GET  /explore/open-items/stats"  "$API/explore/open-items/stats?project_id=$PID"

else
    skip_test "EXPLORE phase" "No Program ID"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 3 — REALIZE (Build & Configuration)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -n "$PID" ]; then

    subsection "3.1 Backlog / WRICEF"
    test_post "POST backlog (Interface)" \
        "$API/programs/$PID/backlog" \
        "{\"title\":\"Vendor master replication BAPI\",\"wricef_type\":\"interface\",\"priority\":\"high\",\"module\":\"MM\",\"status\":\"new\"}"
    BL_ID=$(_json_val "id")

    test_post "POST backlog (Report)" \
        "$API/programs/$PID/backlog" \
        "{\"title\":\"Custom GL reconciliation report\",\"wricef_type\":\"report\",\"priority\":\"medium\",\"module\":\"FI\"}"

    test_post "POST backlog (Enhancement)" \
        "$API/programs/$PID/backlog" \
        "{\"title\":\"PO approval workflow extension\",\"wricef_type\":\"enhancement\",\"priority\":\"high\",\"module\":\"MM\"}"

    test_post "POST backlog (Conversion)" \
        "$API/programs/$PID/backlog" \
        "{\"title\":\"Chart of Accounts migration\",\"wricef_type\":\"conversion\",\"priority\":\"critical\",\"module\":\"FI\"}"

    test_get  "GET  /programs/$PID/backlog"       "$API/programs/$PID/backlog"
    test_get  "GET  /programs/$PID/backlog/stats"  "$API/programs/$PID/backlog/stats"

    subsection "3.2 Functional & Technical Specs"
    if [ -n "$BL_ID" ] && [ "$BL_ID" != "" ]; then
        test_post "POST functional-spec" \
            "$API/backlog/$BL_ID/functional-spec" \
            "{\"title\":\"FS — Vendor Master BAPI\",\"description\":\"Functional specification for vendor replication interface\",\"author\":\"Elif Demir\"}"
        FS_ID=$(_json_val "id")

        if [ -n "$FS_ID" ] && [ "$FS_ID" != "" ]; then
            test_post "POST technical-spec" \
                "$API/functional-specs/$FS_ID/technical-spec" \
                "{\"title\":\"TS — Vendor Master BAPI\",\"author\":\"Ahmet Kaya\",\"objects_list\":\"ZCL_VENDOR_SYNC, ZIF_VENDOR\"}"
        else
            skip_test "POST technical-spec" "No FS_ID"
        fi
    else
        skip_test "POST functional-spec" "No BL_ID"
        skip_test "POST technical-spec" "No BL_ID"
    fi

    subsection "3.3 Configuration Items"
    test_post "POST config-item (FI)" \
        "$API/programs/$PID/config-items" \
        "{\"title\":\"Company Code Configuration (OBY6)\",\"module\":\"FI\",\"config_key\":\"OBY6\",\"priority\":\"critical\"}"
    CI_ID=$(_json_val "id")

    test_post "POST config-item (MM)" \
        "$API/programs/$PID/config-items" \
        "{\"title\":\"Purchase Org Assignment (SPRO)\",\"module\":\"MM\",\"config_key\":\"OME4\",\"priority\":\"high\"}"

    test_post "POST config-item (SD)" \
        "$API/programs/$PID/config-items" \
        "{\"title\":\"Sales Area Determination\",\"module\":\"SD\",\"config_key\":\"OVX5\",\"priority\":\"medium\"}"

    test_get  "GET  /programs/$PID/config-items" "$API/programs/$PID/config-items"

    subsection "3.4 RAID Management"

    test_post "POST risk (technical)" \
        "$API/programs/$PID/risks" \
        "{\"title\":\"Data migration delay risk — vendor master data quality\",\"probability\":4,\"impact\":3,\"risk_category\":\"technical\",\"risk_response\":\"mitigate\",\"owner\":\"Mehmet Kaya\"}"
    RISK_ID=$(_json_val "id")

    test_post "POST risk (organizational)" \
        "$API/programs/$PID/risks" \
        "{\"title\":\"Key user availability during UAT\",\"probability\":3,\"impact\":4,\"risk_category\":\"organizational\",\"risk_response\":\"mitigate\",\"owner\":\"PMO\"}"

    test_post "POST issue" \
        "$API/programs/$PID/issues" \
        "{\"title\":\"DEV environment not provisioned\",\"severity\":\"major\",\"priority\":\"critical\",\"owner\":\"Basis Lead\"}"
    ISSUE_ID=$(_json_val "id")

    test_post "POST action" \
        "$API/programs/$PID/actions" \
        "{\"title\":\"Escalate DEV env provisioning to infra team\",\"action_type\":\"corrective\",\"priority\":\"high\",\"owner\":\"PM\",\"due_date\":\"2026-03-01\"}"
    ACTION_ID=$(_json_val "id")

    test_post "POST decision" \
        "$API/programs/$PID/decisions" \
        "{\"title\":\"Approve S/4HANA 2023 FPS02 as target release\",\"decision_owner\":\"Steering Committee\",\"priority\":\"high\",\"status\":\"approved\"}"

    test_get  "GET  /programs/$PID/risks"     "$API/programs/$PID/risks"
    test_get  "GET  /programs/$PID/issues"    "$API/programs/$PID/issues"
    test_get  "GET  /programs/$PID/actions"   "$API/programs/$PID/actions"
    test_get  "GET  /programs/$PID/decisions" "$API/programs/$PID/decisions"
    test_get  "GET  /programs/$PID/raid/stats" "$API/programs/$PID/raid/stats"

    subsection "3.5 Integration Factory"
    test_post "POST interface (outbound)" \
        "$API/programs/$PID/interfaces" \
        "{\"name\":\"Vendor Master → CRM\",\"direction\":\"outbound\",\"protocol\":\"idoc\",\"source_system\":\"S/4HANA\",\"target_system\":\"CRM\",\"module\":\"MM\"}"
    IFACE_ID=$(_json_val "id")

    test_post "POST interface (inbound)" \
        "$API/programs/$PID/interfaces" \
        "{\"name\":\"Bank Statement Import\",\"direction\":\"inbound\",\"protocol\":\"file\",\"source_system\":\"Bank\",\"target_system\":\"S/4HANA\",\"module\":\"FI\"}"

    test_get  "GET  /programs/$PID/interfaces"       "$API/programs/$PID/interfaces"
    test_get  "GET  /programs/$PID/interfaces/stats"  "$API/programs/$PID/interfaces/stats"

    subsection "3.6 Data Factory"
    test_post "POST data-object (Vendor)" \
        "$API/data-factory/objects" \
        "{\"program_id\":$PID,\"name\":\"Vendor Master (LFA1/LFB1)\",\"source_system\":\"SAP ECC\",\"target_table\":\"LFA1\",\"record_count\":8500}"
    DO_ID=$(_json_val "id")

    test_post "POST data-object (Material)" \
        "$API/data-factory/objects" \
        "{\"program_id\":$PID,\"name\":\"Material Master (MARA/MARC)\",\"source_system\":\"SAP ECC\",\"target_table\":\"MARA\",\"record_count\":42000}"

    test_post "POST data-object (GL Balance)" \
        "$API/data-factory/objects" \
        "{\"program_id\":$PID,\"name\":\"GL Account Balances\",\"source_system\":\"SAP ECC\",\"target_table\":\"BSEG\",\"record_count\":1200000}"

    test_post "POST migration-wave" \
        "$API/data-factory/waves" \
        "{\"program_id\":$PID,\"wave_number\":1,\"name\":\"Wave 1 — Master Data\",\"status\":\"planned\"}"
    WAVE_ID=$(_json_val "id")

    # Cleansing + load cycle
    if [ -n "$DO_ID" ] && [ "$DO_ID" != "" ]; then
        test_post "POST cleansing-task" \
            "$API/data-factory/objects/$DO_ID/tasks" \
            "{\"rule_type\":\"duplicate_check\",\"rule_expression\":\"SELECT LIFNR,COUNT(*) FROM LFA1 GROUP BY LIFNR HAVING COUNT(*)>1\",\"description\":\"Vendor duplicate check\"}"

        if [ -n "$WAVE_ID" ] && [ "$WAVE_ID" != "" ]; then
            test_post "POST load-cycle (DEV)" \
                "$API/data-factory/objects/$DO_ID/loads" \
                "{\"wave_id\":$WAVE_ID,\"environment\":\"DEV\",\"load_type\":\"initial\"}"
        else
            skip_test "POST load-cycle" "No WAVE_ID"
        fi
    else
        skip_test "POST cleansing-task" "No DO_ID"
        skip_test "POST load-cycle" "No DO_ID"
    fi

    test_get  "GET  /data-factory/objects" "$API/data-factory/objects?program_id=$PID"
    test_get  "GET  /data-factory/waves"   "$API/data-factory/waves?program_id=$PID"

else
    skip_test "REALIZE phase" "No Program ID"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 4 — TESTING (SIT / UAT)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -n "$PID" ]; then

    subsection "4.1 Test Planning"
    test_post "POST test-plan (SIT)" \
        "$API/programs/$PID/testing/plans" \
        "{\"name\":\"SIT — System Integration Testing\",\"description\":\"Cross-module integration test plan\",\"status\":\"draft\"}"
    TP_ID=$(_json_val "id")

    if [ -n "$TP_ID" ] && [ "$TP_ID" != "" ]; then
        test_post "POST test-cycle" \
            "$API/testing/plans/$TP_ID/cycles" \
            "{\"name\":\"SIT Cycle 1\",\"test_layer\":\"sit\",\"status\":\"planning\"}"
        TC_ID=$(_json_val "id")
    else
        skip_test "POST test-cycle" "No TP_ID"
        TC_ID=""
    fi

    test_get  "GET  /programs/$PID/testing/plans" "$API/programs/$PID/testing/plans"

    subsection "4.2 Test Suite & Catalog"
    test_post "POST test-suite (FI)" \
        "$API/programs/$PID/testing/suites" \
        "{\"name\":\"FI Regression Suite\",\"suite_type\":\"SIT\",\"module\":\"FI\"}"

    test_post "POST test-case (GL Post)" \
        "$API/programs/$PID/testing/catalog" \
        "{\"title\":\"Verify GL posting with FB50\",\"test_layer\":\"sit\",\"module\":\"FI\",\"priority\":\"high\",\"test_steps\":\"1. Login\\n2. Tcode FB50\\n3. Enter JE\\n4. Post\",\"expected_result\":\"Document posted successfully\"}"
    TCASE_ID=$(_json_val "id")

    test_post "POST test-case (Vendor Create)" \
        "$API/programs/$PID/testing/catalog" \
        "{\"title\":\"Create vendor via XK01\",\"test_layer\":\"sit\",\"module\":\"MM\",\"priority\":\"high\",\"test_steps\":\"1. XK01\\n2. Enter data\\n3. Save\",\"expected_result\":\"Vendor created\"}"

    test_get  "GET  /programs/$PID/testing/suites"  "$API/programs/$PID/testing/suites"
    test_get  "GET  /programs/$PID/testing/catalog"  "$API/programs/$PID/testing/catalog"

    subsection "4.3 Test Execution & Defects"
    if [ -n "$TC_ID" ] && [ "$TC_ID" != "" ] && [ -n "$TCASE_ID" ] && [ "$TCASE_ID" != "" ]; then
        test_post "POST test-execution (pass)" \
            "$API/testing/cycles/$TC_ID/executions" \
            "{\"test_case_id\":$TCASE_ID,\"result\":\"pass\",\"executed_by\":\"Tester1\"}"
    else
        skip_test "POST test-execution" "No TC_ID or TCASE_ID"
    fi

    test_post "POST defect (S2)" \
        "$API/programs/$PID/testing/defects" \
        "{\"title\":\"GL posting fails for intercompany transactions\",\"severity\":\"S2\",\"priority\":\"P2\",\"module\":\"FI\",\"status\":\"new\"}"
    DEFECT_ID=$(_json_val "id")

    test_post "POST defect (S3)" \
        "$API/programs/$PID/testing/defects" \
        "{\"title\":\"Vendor search by tax ID not working\",\"severity\":\"S3\",\"priority\":\"P3\",\"module\":\"MM\",\"status\":\"new\"}"

    test_get  "GET  /programs/$PID/testing/defects"    "$API/programs/$PID/testing/defects"
    test_get  "GET  /programs/$PID/testing/dashboard"  "$API/programs/$PID/testing/dashboard"

else
    skip_test "TESTING phase" "No Program ID"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 5 — DEPLOY (Cutover & Go-Live)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -n "$PID" ]; then

    subsection "5.1 Cutover Plan"
    test_post "POST cutover-plan" \
        "$API/cutover/plans" \
        "{\"program_id\":$PID,\"name\":\"Go-Live Cutover Plan — $PROG_NAME\",\"environment\":\"PRD\",\"cutover_manager\":\"Mehmet Kaya\"}"
    CO_ID=$(_json_val "id")

    if [ -n "$CO_ID" ] && [ "$CO_ID" != "" ]; then
        printf "  ${CYAN}ℹ️${NC}  Cutover Plan ID: ${BOLD}$CO_ID${NC}\n"

        subsection "5.2 Scope Items"
        test_post "POST scope-item (data)" \
            "$API/cutover/plans/$CO_ID/scope-items" \
            "{\"name\":\"Data Migration Tasks\",\"category\":\"data_load\",\"owner\":\"DM Lead\"}"
        SI_DATA=$(_json_val "id")

        test_post "POST scope-item (technical)" \
            "$API/cutover/plans/$CO_ID/scope-items" \
            "{\"name\":\"Technical Cutovers\",\"category\":\"interface\",\"owner\":\"Basis\"}"
        SI_TECH=$(_json_val "id")

        subsection "5.3 Runbook Tasks"
        if [ -n "$SI_DATA" ] && [ "$SI_DATA" != "" ]; then
            test_post "POST runbook-task (vendor load)" \
                "$API/cutover/scope-items/$SI_DATA/tasks" \
                "{\"title\":\"Load vendor master to PRD\",\"responsible\":\"Data Team\",\"environment\":\"PRD\",\"planned_duration_min\":120}"

            test_post "POST runbook-task (material load)" \
                "$API/cutover/scope-items/$SI_DATA/tasks" \
                "{\"title\":\"Load material master to PRD\",\"responsible\":\"Data Team\",\"environment\":\"PRD\",\"planned_duration_min\":180}"

            test_post "POST runbook-task (GL balance)" \
                "$API/cutover/scope-items/$SI_DATA/tasks" \
                "{\"title\":\"Load GL opening balances\",\"responsible\":\"FI Team\",\"environment\":\"PRD\",\"planned_duration_min\":240}"
        else
            skip_test "POST runbook-tasks (data)" "No SI_DATA"
        fi

        if [ -n "$SI_TECH" ] && [ "$SI_TECH" != "" ]; then
            test_post "POST runbook-task (RFC check)" \
                "$API/cutover/scope-items/$SI_TECH/tasks" \
                "{\"title\":\"Verify all RFC connections to PRD\",\"responsible\":\"Basis Team\",\"environment\":\"PRD\",\"planned_duration_min\":60}"

            test_post "POST runbook-task (job scheduling)" \
                "$API/cutover/scope-items/$SI_TECH/tasks" \
                "{\"title\":\"Configure batch job scheduling\",\"responsible\":\"Basis Team\",\"environment\":\"PRD\",\"planned_duration_min\":90}"
        else
            skip_test "POST runbook-tasks (tech)" "No SI_TECH"
        fi

        subsection "5.4 Rehearsal"
        test_post "POST rehearsal" \
            "$API/cutover/plans/$CO_ID/rehearsals" \
            "{\"name\":\"Dress Rehearsal 1\",\"environment\":\"QAS\"}"

        test_get  "GET  /cutover/plans (list)"   "$API/cutover/plans?program_id=$PID"

    else
        skip_test "Cutover details" "No CO_ID"
    fi

else
    skip_test "DEPLOY phase" "No Program ID"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 6 — RUN / SUSTAIN (Hypercare & Handover)"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if [ -n "$CO_ID" ] && [ "$CO_ID" != "" ]; then

    subsection "6.1 Hypercare Incidents"
    test_post "POST hypercare-incident" \
        "$API/cutover/plans/$CO_ID/incidents" \
        "{\"title\":\"GL posting error in cross-company code scenario\",\"severity\":\"P2\",\"category\":\"functional\",\"reported_by\":\"FI Key User\"}"

    test_post "POST hypercare-incident (perf)" \
        "$API/cutover/plans/$CO_ID/incidents" \
        "{\"title\":\"MRP run exceeding 4 hour SLA\",\"severity\":\"P1\",\"category\":\"performance\",\"reported_by\":\"PP Key User\"}"

    subsection "6.2 Knowledge Transfer"
    test_post "POST knowledge-transfer" \
        "$API/run-sustain/plans/$CO_ID/knowledge-transfer" \
        "{\"title\":\"FI Period Close Procedure\",\"topic_area\":\"functional\",\"format\":\"workshop\",\"trainer\":\"FI Lead\",\"audience\":\"Support Team\"}"

    test_post "POST knowledge-transfer (tech)" \
        "$API/run-sustain/plans/$CO_ID/knowledge-transfer" \
        "{\"title\":\"Basis Monitoring & Alerting\",\"topic_area\":\"technical\",\"format\":\"hands_on\",\"trainer\":\"Basis Lead\",\"audience\":\"IT Operations\"}"

    test_get  "GET  /run-sustain/.../knowledge-transfer" "$API/run-sustain/plans/$CO_ID/knowledge-transfer"

    subsection "6.3 Handover Items"
    test_post "POST handover-item (doc)" \
        "$API/run-sustain/plans/$CO_ID/handover-items" \
        "{\"title\":\"FI Configuration Guide v3.0\",\"category\":\"documentation\",\"responsible\":\"FI Consultant\",\"priority\":\"high\"}"

    test_post "POST handover-item (access)" \
        "$API/run-sustain/plans/$CO_ID/handover-items" \
        "{\"title\":\"Support team SAP access provisioning\",\"category\":\"access_control\",\"responsible\":\"Security Lead\",\"priority\":\"high\"}"

    test_post "POST handover-item (monitoring)" \
        "$API/run-sustain/plans/$CO_ID/handover-items" \
        "{\"title\":\"Solution Manager monitoring setup\",\"category\":\"monitoring\",\"responsible\":\"Basis\",\"priority\":\"high\"}"

    test_get  "GET  /run-sustain/.../handover-items" "$API/run-sustain/plans/$CO_ID/handover-items"

else
    skip_test "RUN/SUSTAIN phase" "No CO_ID (cutover plan required)"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 7 — CROSS-CUTTING CONCERNS"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

subsection "7.1 Notifications"
test_post "POST notification" \
    "$API/notifications" \
    "{\"title\":\"E2E smoke test completed\",\"message\":\"All phases tested at $(date +%H:%M)\",\"category\":\"system\",\"severity\":\"info\"}"
test_get  "GET  /notifications"              "$API/notifications"
test_get  "GET  /notifications/unread-count" "$API/notifications/unread-count"

subsection "7.2 Reporting"
if [ -n "$PID" ]; then
    test_get "GET  /reports/program-health/$PID" "$API/reports/program-health/$PID"
    test_get "GET  /reports/weekly/$PID"          "$API/reports/weekly/$PID"
fi

subsection "7.3 Traceability Chain"
if [ -n "$PID" ]; then
    if [ -n "$BL_ID" ] && [ "$BL_ID" != "" ]; then
        test_get "GET  traceability (backlog_item)" "$API/traceability/backlog_item/$BL_ID"
    fi
    if [ -n "$REQ_ID" ] && [ "$REQ_ID" != "" ]; then
        test_get "GET  traceability (explore_requirement)" "$API/traceability/explore_requirement/$REQ_ID"
    fi
    if [ -n "$CI_ID" ] && [ "$CI_ID" != "" ]; then
        test_get "GET  traceability (config_item)" "$API/traceability/config_item/$CI_ID"
    fi
fi

subsection "7.4 AI & Knowledge Base"
if [ -n "$PID" ]; then
    test_get  "GET  /ai/admin/dashboard"          "$API/ai/admin/dashboard"
    test_get  "GET  /ai/prompts"                   "$API/ai/prompts"
    test_get  "GET  /ai/kb/versions"               "$API/ai/kb/versions"
    test_get  "GET  /ai/suggestions/stats"         "$API/ai/suggestions/stats"
fi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
section "PHASE 8 — PERFORMANCE BASELINE"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

echo ""
PERF_ENDPOINTS="/health/live /programs"
if [ -n "$PID" ]; then
    PERF_ENDPOINTS="$PERF_ENDPOINTS /programs/$PID /explore/process-levels?project_id=$PID"
fi

TOTAL_TIME=0; COUNT=0
for EP in $PERF_ENDPOINTS; do
    T=$(curl -s --max-time 30 $AUTH -o /dev/null -w "%{time_total}" "$API$EP" 2>/dev/null)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $T" | bc 2>/dev/null || echo "0")
    COUNT=$((COUNT+1))
    printf "  ⏱️  %-50s ${CYAN}%.3fs${NC}\n" "$EP" "$T"
done

if [ "$COUNT" -gt 0 ] && command -v bc &> /dev/null; then
    AVG=$(echo "scale=3; $TOTAL_TIME / $COUNT" | bc 2>/dev/null)
    printf "\n  ${BOLD}📊 Average response time: ${CYAN}${AVG}s${NC}\n"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
printf "${BOLD}╔═══════════════════════════════════════════════════════════════╗${NC}\n"
printf "${BOLD}║  📊 RESULTS                                                 ║${NC}\n"
printf "${BOLD}╠═══════════════════════════════════════════════════════════════╣${NC}\n"
printf "${BOLD}║  ${GREEN}✅ Passed:   %-5s${NC}${BOLD}                                        ║${NC}\n" "$PASS"
printf "${BOLD}║  ${RED}❌ Failed:   %-5s${NC}${BOLD}                                        ║${NC}\n" "$FAIL"
printf "${BOLD}║  ${YELLOW}⏭️  Skipped:  %-5s${NC}${BOLD}                                        ║${NC}\n" "$SKIP"
printf "${BOLD}║  📝 Total:    %-5s                                        ║${NC}\n" "$TOTAL"
printf "${BOLD}╚═══════════════════════════════════════════════════════════════╝${NC}\n"
echo ""

if [ $FAIL -gt 0 ]; then
    printf "${BOLD}${RED}━━ ERRORS ━━${NC}\n"
    printf "$ERRORS\n"
    echo ""
fi

RATE=0
if [ "$TOTAL" -gt 0 ] && command -v bc &>/dev/null; then
    RATE=$(echo "scale=1; $PASS * 100 / ($PASS + $FAIL)" | bc 2>/dev/null)
fi

if [ $FAIL -eq 0 ]; then
    printf "  ${GREEN}${BOLD}🎉 %s/%s tests passed (%s%%). Platform fully operational!${NC}\n" "$PASS" "$TOTAL" "$RATE"
elif [ $FAIL -le 3 ]; then
    printf "  ${YELLOW}${BOLD}⚠️  %s/%s passed (%s%%). Minor issues found.${NC}\n" "$PASS" "$TOTAL" "$RATE"
else
    printf "  ${RED}${BOLD}🚨 %s/%s passed (%s%%). Critical issues detected!${NC}\n" "$PASS" "$TOTAL" "$RATE"
fi

echo ""
printf "  📍 Test: ${CYAN}$BASE_URL${NC}\n"
printf "  🔑 Auth: ${CYAN}$AUTH_USER${NC}\n"
if [ -n "$PID" ]; then
    printf "  🏗  Program: ${CYAN}$PROG_NAME (ID: $PID)${NC}\n"
fi
printf "  📅 $(date '+%Y-%m-%d %H:%M:%S')\n"
echo ""

# Cleanup
rm -f "$BODY" 2>/dev/null

[ $FAIL -eq 0 ] && exit 0 || exit 1
