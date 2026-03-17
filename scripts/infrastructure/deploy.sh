#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# SAP Transformation Platform — Staging / Production Deploy Script
# Sprint 14: CI/CD + Security Hardening
#
# Usage:
#   ./scripts/infrastructure/deploy.sh staging      Deploy to staging environment
#   ./scripts/infrastructure/deploy.sh production   Deploy to production environment
#
# Supports: Railway, Fly.io, Docker Compose
# ═══════════════════════════════════════════════════════════════════════════

set -euo pipefail

ENVIRONMENT="${1:-staging}"
APP_NAME="sap-transformation-platform"
VERSION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "═══════════════════════════════════════════════════════════════"
echo "  SAP Transformation Platform — Deploy"
echo "  Environment: ${ENVIRONMENT}"
echo "  Version:     ${VERSION}"
echo "  Timestamp:   ${TIMESTAMP}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Pre-flight checks ───────────────────────────────────────────────────
preflight() {
    echo "🔍 Pre-flight checks..."

    # Check required env vars for production
    if [ "$ENVIRONMENT" = "production" ]; then
        for var in DATABASE_URL SECRET_KEY; do
            if [ -z "${!var:-}" ]; then
                echo "❌ Required env var $var is not set"
                exit 1
            fi
        done
        echo "   ✅ Required env vars present"
    fi

    # Ensure no uncommitted changes
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        echo "   ⚠️  Uncommitted changes detected (continuing anyway)"
    else
        echo "   ✅ Working directory clean"
    fi

    echo ""
}

# ── Deploy via Railway ──────────────────────────────────────────────────
deploy_railway() {
    if command -v railway &>/dev/null; then
        echo "🚂 Deploying via Railway..."
        railway up --environment "$ENVIRONMENT" --detach
        echo "   ✅ Railway deploy triggered"
    else
        echo "❌ Railway CLI not found. Install: npm i -g @railway/cli"
        exit 1
    fi
}

# ── Deploy via Fly.io ──────────────────────────────────────────────────
deploy_flyio() {
    if command -v fly &>/dev/null; then
        echo "✈️  Deploying via Fly.io..."
        fly deploy --config fly.toml --strategy rolling
        echo "   ✅ Fly.io deploy triggered"
    else
        echo "❌ Fly CLI not found. Install: brew install flyctl"
        exit 1
    fi
}

# ── Deploy via Docker Compose ──────────────────────────────────────────
deploy_compose() {
    echo "🐳 Deploying via Docker Compose..."
    docker compose -f docker/docker-compose.yml build --no-cache
    docker compose -f docker/docker-compose.yml up -d
    echo "   ✅ Docker Compose deploy complete"
}

# ── Post-deploy health check ──────────────────────────────────────────
health_check() {
    local url="${DEPLOY_URL:-http://localhost:8080}"
    echo ""
    echo "🏥 Health check: ${url}/api/v1/health"

    local retries=5
    local wait=3
    for i in $(seq 1 $retries); do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${url}/api/v1/health" 2>/dev/null || echo "000")
        if [ "$STATUS" = "200" ]; then
            echo "   ✅ Health check passed (attempt ${i}/${retries})"
            return 0
        fi
        echo "   ⏳ Attempt ${i}/${retries} — HTTP ${STATUS}, retrying in ${wait}s..."
        sleep $wait
    done

    echo "   ❌ Health check failed after ${retries} attempts"
    return 1
}

# ── Main ────────────────────────────────────────────────────────────────
preflight

if [ -n "${DEPLOY_TOKEN:-}" ] && [ -z "${RAILWAY_TOKEN:-}" ]; then
    export RAILWAY_TOKEN="$DEPLOY_TOKEN"
fi

# Detect deployment method
if [ -n "${RAILWAY_TOKEN:-}" ] || [ -n "${DEPLOY_TOKEN:-}" ]; then
    deploy_railway
elif [ -f "fly.toml" ]; then
    deploy_flyio
else
    deploy_compose
fi

health_check

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Deploy complete — ${ENVIRONMENT} @ ${VERSION}"
echo "═══════════════════════════════════════════════════════════════"
