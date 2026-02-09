#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Git Hook Installer — SAP Transformation Platform
#
# Installs pre-commit and commit-msg hooks + sets commit template.
#
# Usage: bash scripts/hooks/install.sh
# ──────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

GREEN='\033[0;32m'
NC='\033[0m'

echo "Installing git hooks..."

# Copy hooks
cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/pre-commit"
echo -e "  ${GREEN}✓${NC} pre-commit hook installed"

cp "$SCRIPT_DIR/commit-msg" "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/commit-msg"
echo -e "  ${GREEN}✓${NC} commit-msg hook installed"

# Set commit template
git config --local commit.template "$REPO_ROOT/.gitmessage"
echo -e "  ${GREEN}✓${NC} Commit template configured (.gitmessage)"

echo ""
echo "Done! Hooks are active. Override with: git commit --no-verify"
