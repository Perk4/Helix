#!/bin/bash
A=http://127.0.0.1:8010/api/v1; S=STUDY-HLX-028
RUN=$(curl -s $A/studies/$S/workspace | python3 -c 'import json,sys; print(json.load(sys.stdin)["journey"]["run"]["run_id"])')
echo "SSE replay frames: $(curl -s -N --max-time 3 $A/studies/$S/pinned-runs/$RUN/events | grep -c '^id:')"
curl -s -o /dev/null -w "POST disposition VR-005 -> %{http_code}\n" -X POST $A/studies/$S/validation-results/VR-005/dispositions -H "content-type: application/json" -d '{"decision":"corrected","reason":"lock check","reviewer":"lock check"}'
sleep 3
