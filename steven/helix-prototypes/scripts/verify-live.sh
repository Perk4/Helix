#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$(mktemp -t helix-e2e).db"
API_LOG="$(mktemp -t helix-api).log"
WEB_LOG="$(mktemp -t helix-web).log"
API_PID=""
WEB_PID=""

cleanup() {
  if [[ -n "$WEB_PID" ]]; then
    pkill -P "$WEB_PID" 2>/dev/null || true
    kill "$WEB_PID" 2>/dev/null || true
  fi
  if [[ -n "$API_PID" ]]; then
    pkill -P "$API_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
  fi
  rm -f "$DB" "$API_LOG" "$WEB_LOG"
  rm -rf "$ROOT/frontend/.next-e2e"
}
trap cleanup EXIT

cd "$ROOT/backend"
HELIX_DATABASE_URL="sqlite+pysqlite:///$DB" \
HELIX_SEED_PATH="$ROOT/synthetic-e2e/helix-synthetic-bundle.json" \
HELIX_CORS_ORIGINS='["http://127.0.0.1:3010"]' \
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 >"$API_LOG" 2>&1 &
API_PID=$!

cd "$ROOT/frontend"
if ! NEXT_PUBLIC_API_URL="http://127.0.0.1:8010/api/v1" \
  NEXT_DIST_DIR=".next-e2e" \
  npx next build >"$WEB_LOG" 2>&1; then
  cat "$WEB_LOG"
  exit 1
fi
NEXT_PUBLIC_API_URL="http://127.0.0.1:8010/api/v1" \
NEXT_DIST_DIR=".next-e2e" \
npx next start --hostname 127.0.0.1 --port 3010 >>"$WEB_LOG" 2>&1 &
WEB_PID=$!

ready=false
for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8010/health >/dev/null && curl -sf http://127.0.0.1:3010 >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != true ]]; then
  cat "$API_LOG"
  cat "$WEB_LOG"
  exit 1
fi

if ! HELIX_WEB_URL="http://127.0.0.1:3010" \
  HELIX_API_URL="http://127.0.0.1:8010/api/v1" \
  npm run test:e2e; then
  cat "$API_LOG"
  cat "$WEB_LOG"
  exit 1
fi

curl -sf http://127.0.0.1:8010/health
