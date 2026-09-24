#!/bin/bash
# Writes through the base f5776828 API: a run with run events, a disposition, and an uploaded study.
A=http://127.0.0.1:8010/api/v1; S=STUDY-HLX-028; D=/Users/perk/src/Helix-adosync/steven/helix-prototypes/synthetic-e2e/data
curl -s -o /dev/null -w "POST validation-runs (freezes run, emits run events) -> %{http_code}\n" -X POST $A/studies/$S/validation-runs -H 'content-type: application/json' -d '{"planner":"fixture"}'
curl -s -o /dev/null -w "POST data-validation-packages -> %{http_code}\n" -X POST $A/studies/$S/data-validation-packages -H 'content-type: application/json' -d '{"actor":"Pre-Alembic","package_id":"validation.body_weight","idempotency_key":"pre-alembic-bw-0001"}'
curl -s -o /dev/null -w "POST disposition VR-004 -> %{http_code}\n" -X POST $A/studies/$S/validation-results/VR-004/dispositions -H 'content-type: application/json' -d '{"decision":"corrected","reason":"Pre-Alembic data survival check.","reviewer":"Pre-Alembic"}'
curl -s -o /dev/null -w "POST disposition VR-006 -> %{http_code}\n" -X POST $A/studies/$S/validation-results/VR-006/dispositions -H "content-type: application/json" -d "{\"decision\":\"approved_exception\",\"reason\":\"Pre-Alembic data survival check.\",\"reviewer\":\"Pre-Alembic\"}"
args=(); for f in $D/study_data/*.csv $D/study_protocol_YZ389.docx; do args+=(-F "files=@$f"); done
curl -s -o /dev/null -w "POST /studies (sync upload STUDY-YZ389-PRE) -> %{http_code}\n" -X POST $A/studies "${args[@]}" -F study_id=STUDY-YZ389-PRE -F "route=oral gavage" -F "protocol_version=YZ389 v1" -F "authorized_by=Pre-Alembic"
curl -s $A/studies/$S/workspace | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d["journey"]["run"]; print("journey.run:", r["run_id"], "latest_event_id", r["latest_event_id"], "| workflow", d["workflow_state"])'
