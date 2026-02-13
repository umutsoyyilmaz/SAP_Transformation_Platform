#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  🧪 Perga SAP Transformation Platform — Production Smoke Test
#  Tarih: 2026-02-13
#  Kullanım: chmod +x smoke_test_production.sh && ./smoke_test_production.sh
#  Farklı URL: ./smoke_test_production.sh https://other-host.railway.app
#  Farklı şifre: SMOKE_USER=admin SMOKE_PASS=yenisifre ./smoke_test_production.sh
# ═══════════════════════════════════════════════════════════════

# ── Konfigürasyon ──────────────────────────────────────────────
BASE_URL="${1:-https://app.univer.com.tr}"
API="$BASE_URL/api/v1"

# Basic Auth credentials (Railway env vars)
AUTH_USER="${SMOKE_USER:-admin}"
AUTH_PASS="${SMOKE_PASS:-Perga2026!}"
AUTH="-u ${AUTH_USER}:${AUTH_PASS}"

# Renkler
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

PASS=0
FAIL=0
WARN=0
ERRORS=""

# ── Yardımcı Fonksiyonlar ─────────────────────────────────────

test_get() {
    local name="$1"
    local url="$2"
    local expected="${3:-200}"

    local response=$(curl -s --max-time 30 $AUTH -o /tmp/smoke_body -w "%{http_code}|%{time_total}" "$url" 2>/dev/null)
    local status=$(echo "$response" | cut -d'|' -f1)
    local time=$(echo "$response" | cut -d'|' -f2)

    if [ "$status" = "$expected" ]; then
        printf "  ${GREEN}✅${NC} %-45s ${CYAN}%s${NC} (%.2fs)\n" "$name" "$status" "$time"
        PASS=$((PASS+1))
    elif [ "$status" = "000" ]; then
        printf "  ${RED}❌${NC} %-45s ${RED}TIMEOUT / CONNECTION FAILED${NC}\n" "$name"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  ❌ $name → Timeout or connection failed"
    else
        printf "  ${RED}❌${NC} %-45s ${RED}%s${NC} (expected %s)\n" "$name" "$status" "$expected"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  ❌ $name → $status (expected $expected)"
    fi
}

test_post() {
    local name="$1"
    local url="$2"
    local data="$3"
    local expected="${4:-201}"

    local response=$(curl -s --max-time 30 $AUTH -o /tmp/smoke_body -w "%{http_code}|%{time_total}" \
        -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
    local status=$(echo "$response" | cut -d'|' -f1)
    local time=$(echo "$response" | cut -d'|' -f2)

    if [ "$status" = "$expected" ] || [ "$status" = "200" ] || [ "$status" = "201" ]; then
        printf "  ${GREEN}✅${NC} %-45s ${CYAN}%s${NC} (%.2fs)\n" "$name" "$status" "$time"
        PASS=$((PASS+1))
    else
        printf "  ${RED}❌${NC} %-45s ${RED}%s${NC} (expected %s)\n" "$name" "$status" "$expected"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  ❌ $name → $status (expected $expected)"
    fi
}

section() {
    echo ""
    printf "${BOLD}${YELLOW}── $1 ──${NC}\n"
}

# ═══════════════════════════════════════════════════════════════
echo ""
printf "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"
printf "${BOLD}  🧪 Perga — Production Smoke Test${NC}\n"
printf "${BOLD}  📍 Target: ${CYAN}$BASE_URL${NC}\n"
printf "${BOLD}  🔐 Auth:   ${CYAN}$AUTH_USER${NC}\n"
printf "${BOLD}  📅 $(date '+%Y-%m-%d %H:%M:%S')${NC}\n"
printf "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"

# ── 0. Bağlantı Kontrolü ──────────────────────────────────────
section "0. SERVER CONNECTIVITY"

HTTP_CODE=$(curl -s $AUTH -o /dev/null -w "%{http_code}" "$BASE_URL" 2>/dev/null)
if [ "$HTTP_CODE" = "000" ]; then
    printf "  ${RED}❌ Sunucuya bağlanılamadı! URL: $BASE_URL${NC}\n"
    printf "  ${YELLOW}   → DNS veya network sorunu olabilir${NC}\n"
    echo ""
    exit 1
fi

if [ "$HTTP_CODE" = "401" ]; then
    printf "  ${RED}❌ Basic Auth BAŞARISIZ! Homepage 401 döndü.${NC}\n"
    printf "  ${YELLOW}   → SMOKE_USER=admin SMOKE_PASS=yenisifre ./smoke_test_production.sh${NC}\n"
    echo ""
    exit 1
fi
printf "  ${GREEN}✅${NC} Server reachable (HTTP $HTTP_CODE)\n"

# Health check
test_get "GET /health" "$API/health" "200"
test_get "GET /health/live" "$API/health/live" "200"

# API auth check
API_AUTH_CODE=$(curl -s $AUTH -o /dev/null -w "%{http_code}" "$API/programs" 2>/dev/null)
if [ "$API_AUTH_CODE" = "401" ]; then
    printf "  ${RED}❌ API Auth BAŞARISIZ! Basic Auth geçti ama API 401 döndü.${NC}\n"
    echo ""
    exit 1
fi
printf "  ${GREEN}✅${NC} API Auth OK (user: $AUTH_USER)\n"

# SSL check
if echo "$BASE_URL" | grep -q "https"; then
    SSL_STATUS=$(curl -s $AUTH -o /dev/null -w "%{ssl_verify_result}" "$BASE_URL" 2>/dev/null)
    if [ "$SSL_STATUS" = "0" ]; then
        printf "  ${GREEN}✅${NC} SSL Certificate valid\n"
    else
        printf "  ${YELLOW}⚠️${NC}  SSL verification issue (code: $SSL_STATUS)\n"
        WARN=$((WARN+1))
    fi
fi

# ── 1. Frontend ────────────────────────────────────────────────
section "1. FRONTEND"

test_get "Homepage (HTML)" "$BASE_URL" "200"
test_get "app.js" "$BASE_URL/static/js/app.js" "200"
test_get "style.css" "$BASE_URL/static/css/style.css" "200"

# ── 2. Programs ───────────────────────────────────────────────
section "2. PROGRAMS"

test_get "GET /programs" "$API/programs" "200"

# Program ID'yi al
PROG_ID=$(curl -s $AUTH "$API/programs" 2>/dev/null | python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    items = data.get('items', data) if isinstance(data, dict) else data
    if isinstance(items, list) and len(items) > 0:
        print(items[0].get('id',''))
    else:
        print('')
except: print('')
" 2>/dev/null)

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    printf "  ${CYAN}ℹ️${NC}  İlk program ID: $PROG_ID\n"
    test_get "GET /programs/$PROG_ID (detail)" "$API/programs/$PROG_ID" "200"
    test_get "GET /programs/$PROG_ID/team" "$API/programs/$PROG_ID/team" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program bulunamadı — program-bağımlı testler atlanacak\n"
    WARN=$((WARN+1))
fi

# ── 3. Explore Module ─────────────────────────────────────────
section "3. EXPLORE MODULE"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /explore/workshops" "$API/explore/workshops?project_id=$PROG_ID" "200"
    test_get "GET /explore/workshops/stats" "$API/explore/workshops/stats?project_id=$PROG_ID" "200"
    test_get "GET /explore/requirements" "$API/explore/requirements?project_id=$PROG_ID" "200"
    test_get "GET /explore/requirements/stats" "$API/explore/requirements/stats?project_id=$PROG_ID" "200"
    test_get "GET /explore/open-items" "$API/explore/open-items?project_id=$PROG_ID" "200"
    test_get "GET /explore/open-items/stats" "$API/explore/open-items/stats?project_id=$PROG_ID" "200"
    test_get "GET /explore/process-levels" "$API/explore/process-levels?project_id=$PROG_ID" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program ID yok — explore testleri atlandı\n"
fi

# ── 4. Backlog & Delivery ─────────────────────────────────────
section "4. BACKLOG & DELIVERY"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /programs/$PROG_ID/backlog" "$API/programs/$PROG_ID/backlog" "200"
    test_get "GET /programs/$PROG_ID/backlog/stats" "$API/programs/$PROG_ID/backlog/stats" "200"
    test_get "GET /programs/$PROG_ID/config-items" "$API/programs/$PROG_ID/config-items" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program ID yok — backlog testleri atlandı\n"
fi

# ── 5. Testing Module ─────────────────────────────────────────
section "5. TESTING MODULE"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /testing/suites" "$API/programs/$PROG_ID/testing/suites" "200"
    test_get "GET /testing/defects" "$API/programs/$PROG_ID/testing/defects" "200"
    test_get "GET /testing/dashboard" "$API/programs/$PROG_ID/testing/dashboard" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program ID yok — testing testleri atlandı\n"
fi

# ── 6. Data Factory ───────────────────────────────────────────
section "6. DATA FACTORY"

test_get "GET /data-factory/objects" "$API/data-factory/objects" "200"

# ── 7. DB Diagnostic ──────────────────────────────────────────
section "7. DB DIAGNOSTIC"

test_get "GET /health/db-diag" "$API/health/db-diag" "200"

# Check program_detail_test specifically
DIAG=$(curl -s $AUTH "$API/health/db-diag" 2>/dev/null)
DIAG_STATUS=$(echo "$DIAG" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    pdt = d.get('program_detail_test', {})
    print(pdt.get('status', 'unknown'))
except: print('error')
" 2>/dev/null)
if [ "$DIAG_STATUS" = "ok" ]; then
    printf "  ${GREEN}✅${NC} Program detail (phases/gates) çalışıyor\n"
    PASS=$((PASS+1))
elif [ "$DIAG_STATUS" = "no_data" ]; then
    printf "  ${YELLOW}⚠️${NC}  No programs in DB — detail test skipped\n"
    WARN=$((WARN+1))
else
    printf "  ${RED}❌${NC} Program detail hatası: %s\n" "$DIAG_STATUS"
    FAIL=$((FAIL+1))
    ERRORS="$ERRORS\n  ❌ Program detail → $DIAG_STATUS (DB schema sorunu)"
fi

# ── 8. Performance ────────────────────────────────────────────
section "8. RESPONSE TIME CHECK"

echo "  Ortalama response time'ları kontrol ediliyor..."
TOTAL_TIME=0
COUNT=0
for EP in "/programs" "/health/live"; do
    T=$(curl -s $AUTH -o /dev/null -w "%{time_total}" "$API$EP" 2>/dev/null)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $T" | bc 2>/dev/null || echo "0")
    COUNT=$((COUNT+1))
    printf "  ⏱️  %-35s %.3fs\n" "$EP" "$T"
done

if [ "$COUNT" -gt 0 ] && command -v bc &> /dev/null; then
    AVG=$(echo "scale=3; $TOTAL_TIME / $COUNT" | bc 2>/dev/null)
    printf "\n  ${CYAN}📊 Ortalama: ${AVG}s${NC}\n"

    SLOW=$(echo "$AVG > 2.0" | bc 2>/dev/null)
    if [ "$SLOW" = "1" ]; then
        printf "  ${YELLOW}⚠️  Yanıt süreleri yüksek — cold start sorunu olabilir${NC}\n"
        WARN=$((WARN+1))
    fi
fi

# ═══════════════════════════════════════════════════════════════
# SONUÇLAR
# ═══════════════════════════════════════════════════════════════
echo ""
printf "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"
printf "${BOLD}  📊 SONUÇLAR${NC}\n"
printf "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"
echo ""
printf "  ${GREEN}✅ Passed:  $PASS${NC}\n"
printf "  ${RED}❌ Failed:  $FAIL${NC}\n"
printf "  ${YELLOW}⚠️  Warnings: $WARN${NC}\n"
echo ""

if [ $FAIL -gt 0 ]; then
    printf "${BOLD}${RED}── HATALAR ──${NC}\n"
    printf "$ERRORS\n"
    echo ""
    printf "${YELLOW}💡 Olası çözümler:${NC}\n"
    printf "  • 401 → SMOKE_USER=admin SMOKE_PASS=yenisifre ./smoke_test_production.sh\n"
    printf "  • 404 → Endpoint henüz deploy edilmemiş olabilir\n"
    printf "  • 500 → Backend hatası — Railway Logs + /health/db-diag kontrol et\n"
    printf "  • 502/503 → Sunucu yeniden başlıyor veya crash olmuş\n"
    echo ""
fi

if [ $FAIL -eq 0 ]; then
    printf "  ${GREEN}${BOLD}🎉 Tüm testler geçti! Platform sağlıklı.${NC}\n"
elif [ $FAIL -le 3 ]; then
    printf "  ${YELLOW}${BOLD}⚠️  Küçük sorunlar var ama platform çalışıyor.${NC}\n"
else
    printf "  ${RED}${BOLD}🚨 Ciddi sorunlar var — Railway dashboard'u kontrol et.${NC}\n"
fi

echo ""
printf "  📍 Test edilen: ${CYAN}$BASE_URL${NC}\n"
printf "  📅 $(date '+%Y-%m-%d %H:%M:%S')\n"
echo ""

[ $FAIL -eq 0 ] && exit 0 || exit 1
