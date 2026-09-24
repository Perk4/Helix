#!/bin/bash
A=http://127.0.0.1:8010/api/v1; S=STUDY-HLX-028; Q="/tmp/live/q 55441 helix_agents"
echo "## hybrid validation, planner=openai_compatible (LLM; needs HELIX_LLM_API_KEY)"
curl -s -w "\nHTTP %{http_code}\n" -X POST $A/studies/$S/validation-runs -H 'content-type: application/json' -d '{"planner":"openai_compatible"}' | cut -c1-600
echo; echo "## hybrid validation, planner=fixture (deterministic tool-contract planner)"
curl -s -X POST $A/studies/$S/validation-runs -H 'content-type: application/json' -d '{"planner":"fixture"}' -o /tmp/live/agents-validation.json -w "HTTP %{http_code}\n"
python3 -c 'import json; d=json.load(open("/tmp/live/agents-validation.json")); print("validation run",d.get("run_id"),"| planner:",d.get("planner_label"),"| llm_used:",d.get("llm_used"),"| results:",len(d.get("results",[]))); [print("  ",r["result_id"],r["status"],r["severity"]) for r in d.get("results",[])]'
RUN=$(curl -s $A/studies/$S/workspace | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d["journey"]["run"] or {}).get("run_id",""))')
echo "pinned run: $RUN"
echo; echo "## data validation package validation.body_weight (deterministic executor recompute)"
curl -s -X POST $A/studies/$S/data-validation-packages -H 'content-type: application/json' -d "{\"actor\":\"Live Acceptance\",\"package_id\":\"validation.body_weight\",\"idempotency_key\":\"live-$S-bw-0001\"}" -o /tmp/live/agents-dv.json -w "HTTP %{http_code}\n"
python3 -c '
import json; d=json.load(open("/tmp/live/agents-dv.json")); r=d["receipt"]
print({k:r.get(k) for k in ("package_id","status","idempotent_replay","run_id")})
for c in d.get("claims",[])[:6]: print("  claim",c.get("claim_id"),c.get("value"),c.get("unit"))'
echo; echo "## section run (Codex SDK agent) — NOT called; it would bill the Codex login on this Mac"
echo; echo "## journey projection"; curl -s $A/studies/$S/workspace | python3 /tmp/live/stages.py | sed 's/ \[(.*//'
echo; echo "## SSE replay of $RUN (curl -N, 3 s)"; curl -s -N --max-time 3 "$A/studies/$S/pinned-runs/$RUN/events" | grep -E "^(id|event):" | paste - - | sed "s/$RUN\.//" | awk '{c[$4]++} END{for(k in c) print "  ",k,c[k]}'
curl -s -N --max-time 3 "$A/studies/$S/pinned-runs/$RUN/events" | grep -E "^(id|event):" | paste - - | tail -4
echo; echo "## DB rows"
$Q -c "select study_id, count(*) validation_runs from validation_runs group by 1" -c "select study_id, run_id, package_id from data_validation_runs" -c "select study_id, run_id from pinned_runs" -c "select run_id, count(*) events, min(sequence), max(sequence) from run_events group by 1" -c "select study_id, run_id, last_sequence from run_journey_states" -c "select type, count(*) from run_events group by 1 order by 2 desc" 2>&1
