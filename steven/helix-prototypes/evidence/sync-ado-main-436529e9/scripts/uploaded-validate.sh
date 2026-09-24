#!/bin/bash
# usage: uploaded-validate.sh STUDY [sync]   upload (job or sync) then try validation + freeze on it
A=http://127.0.0.1:8010/api/v1; S=$1
D=/Users/perk/src/Helix-adosync/steven/helix-prototypes/synthetic-e2e/data
if [ "$2" = sync ]; then
  args=(); for f in $D/study_data/*.csv $D/study_protocol_YZ389.docx; do args+=(-F "files=@$f"); done
  curl -s -o /dev/null -w "POST /studies (sync upload) -> HTTP %{http_code}\n" -X POST $A/studies "${args[@]}" -F study_id=$S -F "route=oral gavage" -F "protocol_version=YZ389 v1" -F "authorized_by=Live Acceptance"
fi
echo "validation-runs fixture:"; curl -s -w "\nHTTP %{http_code}\n" -X POST $A/studies/$S/validation-runs -H 'content-type: application/json' -d '{"planner":"fixture"}' | cut -c1-700
echo "validation-runs openai_compatible:"; curl -s -w "\nHTTP %{http_code}\n" -X POST $A/studies/$S/validation-runs -H 'content-type: application/json' -d '{"planner":"openai_compatible"}' | cut -c1-400
echo "pinned-runs freeze:"; curl -s -w "\nHTTP %{http_code}\n" -X POST $A/studies/$S/pinned-runs -H 'content-type: application/json' -d "{\"actor\":\"Live Acceptance\",\"idempotency_key\":\"live-freeze-$S\"}" | cut -c1-700
