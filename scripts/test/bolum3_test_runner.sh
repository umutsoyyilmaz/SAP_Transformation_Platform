#!/bin/bash
# Section 3 Test Runner — macOS compatible
# chmod +x scripts/test/bolum3_test_runner.sh && ./scripts/test/bolum3_test_runner.sh

REPORT="bolum3_test_report.txt"
echo "═══════════════════════════════════════════════════" > $REPORT
echo "  P0 Tenant Isolation — Section 3 Test Report" >> $REPORT
echo "  $(date)" >> $REPORT
echo "═══════════════════════════════════════════════════" >> $REPORT

run_suite() {
    local name="$1"
    local cmd="$2"

    echo "" >> $REPORT
    echo "━━━ $name ━━━" >> $REPORT

    OUTPUT=$(eval "$cmd" 2>&1) || true
    echo "$OUTPUT" | tail -30 >> $REPORT

    SUMMARY=$(echo "$OUTPUT" | grep -E "passed|failed|error" | tail -1)

    if echo "$SUMMARY" | grep -q "failed\|error"; then
        echo "❌ $name: $SUMMARY"
    elif echo "$SUMMARY" | grep -q "passed"; then
        echo "✅ $name: $SUMMARY"
    else
        echo "⚠️  $name: no pytest output — check report"
    fi
}

echo ""
echo "🧪 Running 5 test suites..."
echo ""

run_suite "Section 3 — Docs Isolation" \
    "python3 -m pytest tests/features/test_workshop_docs_isolation.py -v --tb=short"

run_suite "Section 2 — Session Isolation" \
    "python3 -m pytest tests/features/test_workshop_session_isolation.py -v --tb=short"

run_suite "Section 1 — Scoped Queries" \
    "python3 -m pytest tests/ -k 'scoped_quer' -v --tb=short"

run_suite "Workshop/Explore Regression" \
    "python3 -m pytest tests/ -k 'workshop or explore or document or minutes' -x --tb=short"

run_suite "Full Suite Smoke" \
    "python3 -m pytest tests/ -x --tb=short"

echo ""
echo "📄 Detailed report: cat $REPORT"
