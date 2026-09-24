import json,sys
d=json.load(sys.stdin)
for s in d["journey"]["stages"]:
    print(s["sequence"], s["stage_id"], s["short_label"], s["kind"], s["status"], [(a["action_id"], a.get("command")) for a in s["actions"] if a.get("command")])
print("run:", d["journey"]["run"])
