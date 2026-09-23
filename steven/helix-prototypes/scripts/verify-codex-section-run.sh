#!/usr/bin/env bash
set -euo pipefail

if [[ "${HELIX_CODEX_LIVE:-}" != "1" ]]; then
  echo "HELIX_CODEX_LIVE=1 is required for the real Codex SDK proof." >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
api_log="$tmp/api.log"
web_log="$tmp/web.log"
api_pid=""
web_pid=""
api_port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
web_port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"

cleanup() {
  status=$?
  [[ -n "$web_pid" ]] && kill "$web_pid" 2>/dev/null || true
  [[ -n "$api_pid" ]] && kill "$api_pid" 2>/dev/null || true
  if [[ $status -ne 0 ]]; then
    cat "$api_log" >&2
    cat "$web_log" >&2
  fi
  rm -rf "$tmp"
  exit "$status"
}
trap cleanup EXIT

(
  cd "$root/backend"
  HELIX_DATABASE_URL="sqlite+pysqlite:///$tmp/helix.db" \
    HELIX_CODEX_REPOSITORY_ROOT="$root" \
    HELIX_CORS_ORIGINS="[\"http://127.0.0.1:$web_port\"]" \
    exec uv run python -m uvicorn app.main:app --host 127.0.0.1 --port "$api_port"
) >"$api_log" 2>&1 &
api_pid=$!

(
  cd "$root/frontend"
  NEXT_PUBLIC_API_URL="http://127.0.0.1:$api_port/api/v1" \
    exec ./node_modules/.bin/next dev --hostname 127.0.0.1 --port "$web_port"
) >"$web_log" 2>&1 &
web_pid=$!

for _ in {1..90}; do
  if curl --fail --silent "http://127.0.0.1:$api_port/health" >/dev/null \
    && curl --fail --silent "http://127.0.0.1:$web_port" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl --fail --silent "http://127.0.0.1:$api_port/health" >/dev/null; then
  cat "$api_log" >&2
  exit 1
fi
if ! curl --fail --silent "http://127.0.0.1:$web_port" >/dev/null; then
  cat "$web_log" >&2
  exit 1
fi

cd "$root/frontend"
HELIX_CODEX_LIVE=1 \
  HELIX_API_URL="http://127.0.0.1:$api_port/api/v1" \
  HELIX_WEB_URL="http://127.0.0.1:$web_port" \
  npx playwright test tests/codex-section-run.spec.ts
