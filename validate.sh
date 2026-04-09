#!/usr/bin/env bash
set -uo pipefail
PING_URL="${1:-}"
REPO_DIR="${2:-.}"
if [ -z "$PING_URL" ]; then echo "Usage: $0 <ping_url> [repo_dir]"; exit 1; fi
PING_URL="${PING_URL%/}"
PASS=0
echo "========================================"
echo "  OpenEnv Submission Validator"
echo "========================================"
echo "Repo: $REPO_DIR"
echo "Ping URL: $PING_URL"
echo ""

echo "Step 1/3: Pinging HF Space..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$PING_URL/reset" --max-time 30)
if [ "$HTTP_CODE" = "200" ]; then echo "PASSED -- HF Space is live"; PASS=$((PASS+1))
else echo "FAILED -- HTTP $HTTP_CODE"; exit 1; fi

echo "Step 2/3: Docker build..."
if docker build "$REPO_DIR" 2>&1 | tail -5; then echo "PASSED -- Docker build succeeded"; PASS=$((PASS+1))
else echo "FAILED -- Docker build failed"; exit 1; fi

echo "Step 3/3: openenv validate..."
if cd "$REPO_DIR" && openenv validate 2>&1; then echo "PASSED -- openenv validate passed"; PASS=$((PASS+1))
else echo "FAILED -- openenv validate failed"; exit 1; fi

echo "========================================"
echo "All 3/3 checks passed! Ready to submit."
echo "========================================"
