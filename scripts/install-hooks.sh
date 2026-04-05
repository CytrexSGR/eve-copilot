#!/usr/bin/env bash
# Installiert Git Hooks für EVE Copilot
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"

echo "Installing Git hooks..."

# Pre-Push Hook
cat > "$HOOK_DIR/pre-push" << 'HOOKEOF'
#!/usr/bin/env bash
# Pre-Push Hook: Führt alle Tests aus bevor gepusht wird.
# Bypass mit: git push --no-verify

echo ""
echo "=== Pre-Push: Running tests ==="
echo ""

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ -x "$REPO_ROOT/scripts/test-all.sh" ]; then
  "$REPO_ROOT/scripts/test-all.sh"
  if [ $? -ne 0 ]; then
    echo ""
    echo "Tests failed — push blocked."
    echo "   Fix the failing tests or use 'git push --no-verify' to bypass."
    exit 1
  fi
  echo ""
  echo "All tests passed — pushing."
else
  echo "scripts/test-all.sh not found or not executable — skipping tests."
fi
HOOKEOF

chmod +x "$HOOK_DIR/pre-push"
echo "  pre-push hook installed"

echo ""
echo "Done! Hooks installed in $HOOK_DIR"
