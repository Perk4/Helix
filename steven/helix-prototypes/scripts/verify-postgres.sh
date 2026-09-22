#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POSTGRES_BIN="${POSTGRES_BIN:-/opt/homebrew/opt/postgresql@16/bin}"
DATA_DIR="$(mktemp -d -t helix-postgres)"
PG_LOG="$(mktemp -t helix-postgres).log"
API_LOG="$(mktemp -t helix-postgres-api).log"
API_PID=""
PG_STARTED=false

cleanup() {
  if [[ -n "$API_PID" ]]; then
    pkill -P "$API_PID" 2>/dev/null || true
    kill "$API_PID" 2>/dev/null || true
  fi
  if [[ "$PG_STARTED" == true ]]; then
    "$POSTGRES_BIN/pg_ctl" -D "$DATA_DIR" -m fast stop >/dev/null 2>&1 || true
  fi
  rm -rf "$DATA_DIR"
  rm -f "$PG_LOG" "$API_LOG"
}
trap cleanup EXIT

if [[ ! -x "$POSTGRES_BIN/initdb" ]]; then
  echo "PostgreSQL 16 binaries were not found at $POSTGRES_BIN" >&2
  exit 1
fi

LC_ALL=C "$POSTGRES_BIN/initdb" -D "$DATA_DIR" -U helix -A trust -E UTF8 --locale=C >/dev/null
"$POSTGRES_BIN/pg_ctl" -D "$DATA_DIR" -l "$PG_LOG" -o "-h 127.0.0.1 -p 55432" start >/dev/null
PG_STARTED=true
"$POSTGRES_BIN/createdb" -h 127.0.0.1 -p 55432 -U helix helix

cd "$ROOT/backend"
HELIX_DATABASE_URL="postgresql+psycopg://helix@127.0.0.1:55432/helix" \
HELIX_SEED_PATH="$ROOT/synthetic-e2e/helix-synthetic-bundle.json" \
uv run uvicorn app.main:app --host 127.0.0.1 --port 8020 >"$API_LOG" 2>&1 &
API_PID=$!

ready=false
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8020/health >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != true ]]; then
  cat "$PG_LOG"
  cat "$API_LOG"
  exit 1
fi

HEALTH="$(curl -sf http://127.0.0.1:8020/health)"
[[ "$HEALTH" == *'"storage":"postgresql"'* ]]

WORKSPACE="$(curl -sf http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/workspace)"
python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["summary"]["record_count"] == 1662; assert d["release_gate"]["status"] == "blocked"' <<<"$WORKSPACE"

VALIDATION="$(curl -sf -X POST http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/validation-runs \
  -H 'content-type: application/json' \
  -d '{"planner":"fixture"}')"
BLOCKERS="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(" ".join(r["result_id"] for r in d["results"] if r["status"] == "fail" and r["severity"] == "blocker"))' <<<"$VALIDATION")"

for result_id in $BLOCKERS; do
  decision=corrected
  if [[ "$result_id" == "VR-006" ]]; then
    decision=approved_exception
  fi
  curl -sf -X POST "http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/validation-results/$result_id/dispositions" \
    -H 'content-type: application/json' \
    -d "{\"decision\":\"$decision\",\"reason\":\"Synthetic PostgreSQL verification for $result_id.\",\"reviewer\":\"PostgreSQL Verifier\"}" >/dev/null
done

for approval in \
  'pathologist|Dr. Avery Pathologist|Scientific review complete' \
  'peer_reviewer|Dr. Priya Reviewer|Independent peer review complete' \
  'qau|Morgan QA|Quality assurance statement recorded' \
  'study_director|Dr. Sam Director|Final report approval'; do
  IFS='|' read -r role reviewer meaning <<<"$approval"
  curl -sf -X POST http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/approvals \
    -H 'content-type: application/json' \
    -d "{\"role\":\"$role\",\"reviewer\":\"$reviewer\",\"meaning\":\"$meaning\"}" >/dev/null
done

EXPORT_BODY='{"actor":"Dr. Sam Director","idempotency_key":"postgres-export-001"}'
FIRST_EXPORT="$(curl -sf -X POST http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/exports -H 'content-type: application/json' -d "$EXPORT_BODY")"
SECOND_EXPORT="$(curl -sf -X POST http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/exports -H 'content-type: application/json' -d "$EXPORT_BODY")"
python3 -c 'import json,sys; first=json.loads(sys.argv[1]); second=json.loads(sys.argv[2]); assert first["idempotent_replay"] is False; assert second["idempotent_replay"] is True; assert all(a["checksum"].startswith("sha256:") for a in first["artifacts"])' "$FIRST_EXPORT" "$SECOND_EXPORT"
REPORT_FILE="$DATA_DIR/repeat-dose-study-report.pdf"
curl -sf http://127.0.0.1:8020/api/v1/studies/STUDY-HLX-028/exports/OUT-REPORT >"$REPORT_FILE"
python3 -c 'import hashlib,json,sys; receipt=json.loads(sys.argv[1]); expected=next(a["checksum"] for a in receipt["artifacts"] if a["artifact_id"] == "OUT-REPORT"); actual="sha256:"+hashlib.sha256(open(sys.argv[2],"rb").read()).hexdigest(); assert actual == expected' "$FIRST_EXPORT" "$REPORT_FILE"

RECORD_COUNT="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT sum(jsonb_array_length(value)) FROM study_packages, jsonb_each(data->'records')")"
JSON_TYPE="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT data_type FROM information_schema.columns WHERE table_name='study_packages' AND column_name='data'")"
RUN_COUNT="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT count(*) FROM validation_runs")"
WORKFLOW_STATE="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT data->>'workflow_state' FROM study_packages")"
EXPORT_EVENT_COUNT="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT count(*) FROM audit_events WHERE event_type='explicit_export'")"
EXPORT_FILE_COUNT="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT count(*) FROM export_files")"
EXPORT_CONTENT_TYPE="$("$POSTGRES_BIN/psql" -h 127.0.0.1 -p 55432 -U helix -d helix -Atc "SELECT data_type FROM information_schema.columns WHERE table_name='export_files' AND column_name='content'")"

[[ "$RECORD_COUNT" == "1662" ]]
[[ "$JSON_TYPE" == "jsonb" ]]
[[ "$RUN_COUNT" == "1" ]]
[[ "$WORKFLOW_STATE" == "exported" ]]
[[ "$EXPORT_EVENT_COUNT" == "1" ]]
[[ "$EXPORT_FILE_COUNT" == "4" ]]
[[ "$EXPORT_CONTENT_TYPE" == "bytea" ]]

printf '{"storage":"postgresql","records":%s,"json_type":"%s","validation_runs":%s,"workflow":"%s","export_events":%s,"export_files":%s,"export_type":"%s"}\n' "$RECORD_COUNT" "$JSON_TYPE" "$RUN_COUNT" "$WORKFLOW_STATE" "$EXPORT_EVENT_COUNT" "$EXPORT_FILE_COUNT" "$EXPORT_CONTENT_TYPE"
