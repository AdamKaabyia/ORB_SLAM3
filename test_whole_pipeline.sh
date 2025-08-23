#!/usr/bin/env bash
set -euo pipefail

# Config (override via env or args)
USER_NAME="${USER_NAME:-adamkaabyia}"
REPO_NAME="${REPO_NAME:-ORB_SLAM3}"
PAGES_URL="https://${USER_NAME}.github.io/${REPO_NAME}/"

# Compare versions (args default)
V1="${1:-upstream-v1.0}"
V2="${2:-optimized}"

# Ensure we are at repo root
cd "$(git rev-parse --show-toplevel)"

# 1) Run the unified CLI: one-shot FULL (11), then export-pages (12), then quit (0)
#    Feeds the required inputs:
#      - Option 11
#      - Version A = $V1
#      - Version B = $V2
#      - Press Enter to continue
#      - Option 12 (export pages)
#      - Press Enter to continue
#      - Option 0 (quit)
export PYTHONUNBUFFERED=1
export RICH_FORCE_TERMINAL=1
printf "11\n%s\n%s\n\n12\n\n0\n" "$V1" "$V2" | python3 orbslam3_cli.py | cat

# 2) Verify we have a site in docs/
if [[ ! -f docs/index.html ]]; then
  echo "ERROR: docs/index.html not found; export-pages likely failed."
  exit 1
fi

# 3) Publish docs/ to gh-pages (HTML only)
old_branch="$(git rev-parse --abbrev-ref HEAD)"
tmpdir="$(mktemp -d)"
cp -R docs/* "$tmpdir"/

# Create/switch gh-pages and replace content with docs/
if git show-ref --verify --quiet refs/heads/gh-pages; then
  git switch gh-pages
else
  git switch --orphan gh-pages
fi

# Clean branch and copy site
git rm -rf . || true
git clean -fdx || true
cp -R "$tmpdir"/* .
# Ensure no Jekyll processing
[[ -f .nojekyll ]] || touch .nojekyll

git add -A
git commit -m "Publish dashboards (${V1} vs ${V2}) $(date -Iseconds)" || echo "No changes to commit"
git push -u origin gh-pages

# Return to previous branch
git switch "$old_branch"

# 4) Curl GitHub Pages URL to confirm availability
echo "Checking site at: ${PAGES_URL}"
# Show HTTP status and first lines of index
curl -s -o /dev/null -w "HTTP %{http_code}\n" "${PAGES_URL}"
curl -s "${PAGES_URL}" | head -n 20

echo
echo "Done. Visit: ${PAGES_URL}"
