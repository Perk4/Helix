#!/bin/bash
A=http://127.0.0.1:8010/api/v1; S=STUDY-HLX-028
curl -s http://127.0.0.1:8010/health; echo
curl -s $A/studies | python3 -c 'import json,sys; print("studies:", [s["study_id"] for s in json.load(sys.stdin)])'
curl -s $A/studies/$S/workspace | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d["journey"]["run"]; print("journey.run:", r["run_id"], "latest_event_id", r["latest_event_id"], "| workflow", d["workflow_state"], "| approvals", [a["role"] for a in d["approvals"]], "| dispositions", len(d["dispositions"]))'
RUN=$(curl -s $A/studies/$S/workspace | python3 -c 'import json,sys; print(json.load(sys.stdin)["journey"]["run"]["run_id"])')
echo "SSE replay frames: $(curl -s -N --max-time 3 $A/studies/$S/pinned-runs/$RUN/events | grep -c '^id:')"
curl -s -o /dev/null -w "POST disposition VR-005 (new write after upgrade) -> %{http_code}\n" -X POST $A/studies/$S/validation-results/VR-005/dispositions -H "content-type: application/json" -d "{\"decision\":\"corrected\",\"reason\":\"Post-upgrade write check.\",\"reviewer\":\"Post-upgrade\"}"
/Users/perk/src/Helix-adosync/steven/helix-prototypes/backend/.venv/bin/python /tmp/live/upload_poll.py $A STUDY-YZ389-POST /tmp/live/post-upgrade-upload.txt | grep -E "^(POST|t=)"
