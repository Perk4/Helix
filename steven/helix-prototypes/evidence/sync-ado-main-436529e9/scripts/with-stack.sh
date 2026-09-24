#!/bin/bash
# usage: with-stack.sh REPO_ROOT DB_URL BACKEND_LOG [web|noweb] -- command...
# Starts the backend (and the prebuilt .next-e2e frontend) for the duration of the command.
R=$1; DB=$2; LOG=$3; WEB=$4; shift 5
if lsof -nP -iTCP:8010 -iTCP:3010 -sTCP:LISTEN >/dev/null; then echo "ports 8010/3010 busy" >&2; exit 97; fi
( cd $R/backend && exec env HELIX_DATABASE_URL="$DB" HELIX_SEED_PATH=$R/synthetic-e2e/helix-synthetic-bundle.json HELIX_CORS_ORIGINS='["http://127.0.0.1:3010"]' HELIX_RUN_EVENT_STREAM_SECONDS=${STREAM_SECONDS:-600} PYTHONUNBUFFERED=1 \
  $R/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 >>"$LOG" 2>&1 ) &
API=$!
WEBPID=""
if [ "$WEB" = web ]; then
  ( cd $R/frontend && exec env NEXT_PUBLIC_API_URL=http://127.0.0.1:8010/api/v1 NEXT_DIST_DIR=.next-e2e npx next start --hostname 127.0.0.1 --port 3010 >>"${LOG%.log}-web.log" 2>&1 ) &
  WEBPID=$!
fi
for i in $(seq 60); do curl -sf http://127.0.0.1:8010/health >/dev/null && { [ "$WEB" != web ] || curl -sf -o /dev/null http://127.0.0.1:3010; } && break; sleep 1; done
cd /tmp/live
"$@"; rc=$?
[ -n "$WEBPID" ] && { pkill -P $WEBPID; kill $WEBPID; } 2>/dev/null
kill $API 2>/dev/null; wait $API 2>/dev/null
for i in $(seq 20); do lsof -nP -iTCP:8010 -iTCP:3010 -sTCP:LISTEN >/dev/null || break; sleep 0.5; done
exit $rc
