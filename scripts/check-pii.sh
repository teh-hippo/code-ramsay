#!/usr/bin/env bash
# Pre-publish PII scrub: greps the working tree for known leakage patterns.
# Run before pushing. Exits non-zero if any match is found.
#
# Patterns scanned:
#   - ha-suno         (the original real-world fixture, never to land here)
#   - /home/sena      (developer home path leak from baselines)
#   - /tmp/ramsay-    (workroot leak from baseline captures)
#   - michaelsena     (developer username leak)
#   - copilot-plugins/ (path from prior dotfiles-nested layout)
#
# Excludes the eval virtualenv and pyc caches; otherwise everything tracked
# (or trackable) by git is in scope.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

PATTERNS=(
    "ha-suno"
    "ha_suno"
    "/home/sena"
    "/tmp/ramsay-"
    "michaelsena"
    "copilot-plugins/"
)

EXCLUDE_DIRS=(
    "eval/.venv"
    ".venv"
    "__pycache__"
    ".pytest_cache"
    ".ruff_cache"
    ".git"
    "scripts"
)

EXCLUDE_ARGS=()
for d in "${EXCLUDE_DIRS[@]}"; do
    EXCLUDE_ARGS+=(--exclude-dir="$d")
done

failed=0
for pattern in "${PATTERNS[@]}"; do
    matches=$(grep -rln "${EXCLUDE_ARGS[@]}" -- "$pattern" . 2>/dev/null || true)
    if [[ -n "$matches" ]]; then
        echo "FAIL: pattern '$pattern' found in:"
        echo "$matches" | sed 's/^/  /'
        echo
        failed=1
    fi
done

if [[ "$failed" -ne 0 ]]; then
    echo "Pre-publish scrub failed. Resolve the matches above before pushing."
    exit 1
fi

echo "Pre-publish scrub passed. No PII patterns detected."
