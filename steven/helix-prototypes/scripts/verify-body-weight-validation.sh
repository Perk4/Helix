#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="$(mktemp -t helix-dvp).db"
API_LOG="$(mktemp -t helix-dvp-api).log"
API_PID=""

cleanup() {
  if [[ -n "$API_PID" ]]; then
    pkill -P "$API_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
  fi
  rm -f "$DB" "$API_LOG"
}
trap cleanup EXIT

cd "$ROOT/backend"
HELIX_DATABASE_URL="sqlite+pysqlite:///$DB" \
HELIX_SEED_PATH="$ROOT/synthetic-e2e/helix-synthetic-bundle.json" \
uv run uvicorn app.main:app --host 127.0.0.1 --port 8011 >"$API_LOG" 2>&1 &
API_PID=$!

ready=false
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8011/health >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != true ]]; then
  cat "$API_LOG"
  exit 1
fi

FIRST="$(curl -sf -X POST http://127.0.0.1:8011/api/v1/studies/STUDY-HLX-028/data-validation-packages \
  -H 'Content-Type: application/json' \
  -d '{"actor":"HELIX verify","package_id":"validation.body_weight","idempotency_key":"verify-body-weight-v1"}')"
REPLAY="$(curl -sf -X POST http://127.0.0.1:8011/api/v1/studies/STUDY-HLX-028/data-validation-packages \
  -H 'Content-Type: application/json' \
  -d '{"actor":"HELIX verify","package_id":"validation.body_weight","idempotency_key":"verify-body-weight-v1"}')"

python3 - "$FIRST" "$REPLAY" "$ROOT/evidence/body-weight-validation-api.json" <<'PY'
import json, sys
first = json.loads(sys.argv[1])
replay = json.loads(sys.argv[2])
target = sys.argv[3]
receipt = first["receipt"]
assert receipt["package_id"] == "validation.body_weight"
assert receipt["executor_id"] == "body-weight-summary"
assert receipt["source_artifact_id"] == "A-BW"
assert receipt["status"] == "passed"
assert replay["receipt"]["idempotent_replay"] is True
assert replay["receipt"]["receipt_id"] == receipt["receipt_id"]
assert {item["claim_id"] for item in first["section_references"]} == {"C-BW-HIGH"}
assert len(first["section_references"]) == 2
claim = next(item for item in first["claims"] if item["claim_id"] == "C-BW-HIGH")
assert claim["value"] == 286.2
assert claim["grain"] == "dose_group"
assert claim["source_hashes"]
open(target, "w").write(json.dumps(first, indent=2) + "\n")
print(target)
PY
