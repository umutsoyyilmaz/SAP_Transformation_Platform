#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  🧪 Perga SAP Transformation Platform — Production Smoke Test
#  Tarih: 2026-02-13
#  Kullanım: chmod +x smoke_test_production.sh && ./smoke_test_production.sh
# ═══════════════════════════════════════════════════════════════

# ── Konfigürasyon ──────────────────────────────────────────────
# İstersen BASE_URL'i değiştir:
BASE_URL="${1:-https://app.univer.com.tr}"
API="$BASE_URL/api/v1"

# Renkler
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
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
    
    local response=$(curl -s -o /tmp/smoke_body -w "%{http_code}|%{time_total}" "$url" 2>/dev/null)
    local status=$(echo "$response" | cut -d'|' -f1)
    local time=$(echo "$response" | cut -d'|' -f2)
    
    if [ "$status" = "$expected" ]; then
        printf "  ${GREEN}✅${NC} %-45s ${CYAN}%s${NC} (%.2fs)\n" "$name" "$status" "$time"
        PASS=$((PASS+1))
    elif [ "$status" = "000" ]; then
        printf "  ${RED}❌${NC} %-45s ${RED}CONNECTION FAILED${NC}\n" "$name"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  ❌ $name → Connection failed (sunucu erişilemez)"
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
    local expected="${4:-200}"
    
    local response=$(curl -s -o /tmp/smoke_body -w "%{http_code}|%{time_total}" \
        -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null)
    local status=$(echo "$response" | cut -d'|' -f1)
    local time=$(echo "$response" | cut -d'|' -f2)
    
    if [ "$status" = "$expected" ] || [ "$status" = "200" ] || [ "$status" = "201" ]; then
        printf "  ${GREEN}✅${NC} %-45s ${CYAN}%s${NC} (%.2fs)\n" "$name" "$status" "$time"
        PASS=$((PASS+1))
    else
        printf "  ${RED}❌${NC} %-45s ${RED}%s${NC}\n" "$name" "$status"
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n  ❌ $name → $status"
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
printf "${BOLD}  📅 $(date '+%Y-%m-%d %H:%M:%S')${NC}\n"
printf "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"

# ── 0. Bağlantı Kontrolü ──────────────────────────────────────
section "0. SERVER CONNECTIVITY"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL" 2>/dev/null)
if [ "$HTTP_CODE" = "000" ]; then
    printf "  ${RED}❌ Sunucuya bağlanılamadı! URL: $BASE_URL${NC}\n"
    printf "  ${YELLOW}   → DNS veya network sorunu olabilir${NC}\n"
    printf "  ${YELLOW}   → nslookup app.univer.com.tr 8.8.8.8 dene${NC}\n"
    echo ""
    exit 1
fi
printf "  ${GREEN}✅${NC} Server reachable (HTTP $HTTP_CODE)\n"

SSL_CHECK=$(curl -sI "$BASE_URL" 2>&1 | grep -i "SSL\|certificate" | head -1)
if echo "$BASE_URL" | grep -q "https"; then
    SSL_STATUS=$(curl -s -o /dev/null -w "%{ssl_verify_result}" "$BASE_URL" 2>/dev/null)
    if [ "$SSL_STATUS" = "0" ]; then
        printf "  ${GREEN}✅${NC} SSL Certificate valid\n"
    else
        printf "  ${YELLOW}⚠️${NC}  SSL verification issue (code: $SSL_STATUS)\n"
        WARN=$((WARN+1))
    fi
fi

# ── 1. Frontend Yükleniyor mu? ────────────────────────────────
section "1. FRONTEND"

test_get "Homepage (HTML)" "$BASE_URL" "200"

# Static assets
test_get "app.js" "$BASE_URL/static/js/app.js" "200"
test_get "explore-api.js" "$BASE_URL/static/js/explore-api.js" "200"
test_get "style.css (varsa)" "$BASE_URL/static/css/style.css" "200"

# ── 2. Explore Module ─────────────────────────────────────────
section "2. EXPLORE MODULE"

test_get "GET /explore/workshops" "$API/explore/workshops" "200"
test_get "GET /explore/workshops/stats" "$API/explore/workshops/stats" "200"
test_get "GET /explore/requirements" "$API/explore/requirements" "200"
test_get "GET /explore/requirements/stats" "$API/explore/requirements/stats" "200"
test_get "GET /explore/open-items" "$API/explore/open-items" "200"
test_get "GET /explore/open-items/stats" "$API/explore/open-items/stats" "200"
test_get "GET /explore/decisions" "$API/explore/decisions" "200"
test_get "GET /explore/process-levels" "$API/explore/process-levels" "200"

# ── 3. Program / Project ──────────────────────────────────────
section "3. PROGRAMS & PROJECTS"

test_get "GET /programs" "$API/programs" "200"

# Program ID'yi al (ilk program)
PROG_ID=$(curl -s "$API/programs" 2>/dev/null | python3 -c "
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
    test_get "GET /programs/$PROG_ID" "$API/programs/$PROG_ID" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program bulunamadı — program-bağımlı testler atlanacak\n"
    WARN=$((WARN+1))
fi

# ── 4. Backlog Module ─────────────────────────────────────────
section "4. BACKLOG & DELIVERY"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /programs/$PROG_ID/backlog" "$API/programs/$PROG_ID/backlog" "200"
    test_get "GET /programs/$PROG_ID/backlog/stats" "$API/programs/$PROG_ID/backlog/stats" "200"
    test_get "GET /programs/$PROG_ID/backlog/config-items" "$API/programs/$PROG_ID/backlog/config-items" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program ID yok — backlog testleri atlandı\n"
fi

# ── 5. Testing Module ─────────────────────────────────────────
section "5. TESTING MODULE"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /programs/$PROG_ID/testing/suites" "$API/programs/$PROG_ID/testing/suites" "200"
    test_get "GET /programs/$PROG_ID/testing/defects" "$API/programs/$PROG_ID/testing/defects" "200"
else
    printf "  ${YELLOW}⚠️${NC}  Program ID yok — testing testleri atlandı\n"
fi

# ── 6. Traceability ───────────────────────────────────────────
section "6. TRACEABILITY"

# Traceability endpoint — yeni unified endpoint
test_get "GET /traceability/requirement/1" "$API/traceability/requirement/1"
test_get "GET /traceability/backlog_item/1" "$API/traceability/backlog_item/1"

# Eski trace endpoint (fallback)
test_get "GET /trace/requirement/REQ-001" "$API/trace/requirement/REQ-001"

# ── 7. AI Module ──────────────────────────────────────────────
section "7. AI MODULE"

test_get "GET /ai/status (varsa)" "$API/ai/status"
test_get "GET /ai/assistants (varsa)" "$API/ai/assistants"

# ── 8. Auth & User ────────────────────────────────────────────
section "8. AUTH & TEAM"

test_get "GET /team-members" "$API/team-members" "200"

# ── 9. Data Factory ───────────────────────────────────────────
section "9. DATA FACTORY"

if [ -n "$PROG_ID" ] && [ "$PROG_ID" != "" ]; then
    test_get "GET /programs/$PROG_ID/data-factory/objects" "$API/programs/$PROG_ID/data-factory/objects"
fi

# ── 10. Performance ───────────────────────────────────────────
section "10. RESPONSE TIME CHECK"

echo "  Ortalama response time'ları kontrol ediliyor..."
TOTAL_TIME=0
COUNT=0
for EP in "/explore/workshops" "/explore/requirements" "/programs"; do
    T=$(curl -s -o /dev/null -w "%{time_total}" "$API$EP" 2>/dev/null)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $T" | bc 2>/dev/null || echo "0")
    COUNT=$((COUNT+1))
    printf "  ⏱️  %-35s %.3fs\n" "$EP" "$T"
done

if [ "$COUNT" -gt 0 ] && command -v bc &> /dev/null; then
    AVG=$(echo "scale=3; $TOTAL_TIME / $COUNT" | bc 2>/dev/null)
    printf "\n  ${CYAN}📊 Ortalama: ${AVG}s${NC}\n"
    
    # 2 saniyeden uzunsa uyarı
    SLOW=$(echo "$AVG > 2.0" | bc 2>/dev/null)
    if [ "$SLOW" = "1" ]; then
        printf "  ${YELLOW}⚠️  Yanıt süreleri yüksek — DB veya cold start sorunu olabilir${NC}\n"
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
    printf "  • 404 → Endpoint henüz deploy edilmemiş olabilir\n"
    printf "  • 500 → Backend hatası — Railway Logs'u kontrol et\n"
    printf "  • 502/503 → Sunucu yeniden başlıyor veya crash olmuş\n"
    printf "  • Connection Failed → DNS propagasyon veya Railway down\n"
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

# Çıkış kodu
[ $FAIL -eq 0 ] && exit 0 || exit 1
