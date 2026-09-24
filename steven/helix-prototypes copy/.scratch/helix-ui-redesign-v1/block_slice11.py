from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

repo = "Steven-Espaillat/Helix"
blocker = "#12"
issues = list(range(18, 28))
out_path = Path(".scratch/helix-ui-redesign-v1/block-slice11-verification.json")
summary: dict[str, object] = {"repo": repo, "blocker": {}, "excluded": {}, "updated": []}

blocker_view = subprocess.run(
    ["gh", "issue", "view", "12", "--repo", repo, "--json", "number,title,state,url,body,labels"],
    check=True,
    text=True,
    capture_output=True,
).stdout
blocker_obj = json.loads(blocker_view)
summary["blocker"] = {
    "number": blocker_obj["number"],
    "title": blocker_obj["title"],
    "state": blocker_obj["state"],
    "url": blocker_obj["url"],
}

spec_view = subprocess.run(
    ["gh", "issue", "view", "17", "--repo", repo, "--json", "number,title,state,url,body,labels"],
    check=True,
    text=True,
    capture_output=True,
).stdout
spec_obj = json.loads(spec_view)
summary["excluded"] = {
    "number": spec_obj["number"],
    "title": spec_obj["title"],
    "url": spec_obj["url"],
    "reason": "spec issue, not an implementation ticket",
    "has_process_section": "## Process" in spec_obj["body"],
}

for number in issues:
    raw = subprocess.run(
        ["gh", "issue", "view", str(number), "--repo", repo, "--json", "number,title,state,url,body,labels"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    obj = json.loads(raw)
    body = obj["body"]
    if "## Process" not in body:
        raise SystemExit(f"issue #{number} has no Process section")
    before_process, process = body.split("## Process", 1)
    match = re.search(r"Blocked by ([^.]+)\.", process)
    if not match:
        raise SystemExit(f"issue #{number} has no Blocked by sentence")
    old_sentence = match.group(0)
    old_blockers = match.group(1).strip()
    if blocker in old_blockers.split(", "):
        new_sentence = old_sentence
        new_body = body
        changed = False
    elif old_blockers == "none":
        new_sentence = f"Blocked by {blocker}."
        new_body = before_process + "## Process" + process.replace(old_sentence, new_sentence, 1)
        changed = True
    else:
        new_sentence = f"Blocked by {blocker}, {old_blockers}."
        new_body = before_process + "## Process" + process.replace(old_sentence, new_sentence, 1)
        changed = True
    if changed:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write(new_body)
            body_file = handle.name
        subprocess.run(
            ["gh", "issue", "edit", str(number), "--repo", repo, "--body-file", body_file],
            check=True,
            text=True,
            capture_output=True,
        )
    verified_raw = subprocess.run(
        ["gh", "issue", "view", str(number), "--repo", repo, "--json", "number,title,state,url,body,labels"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    verified = json.loads(verified_raw)
    verified_process = verified["body"].split("## Process", 1)[1]
    if f"Blocked by {blocker}" not in verified_process:
        raise SystemExit(f"issue #{number} does not verify blocker {blocker}")
    summary["updated"].append(
        {
            "number": number,
            "title": obj["title"],
            "url": obj["url"],
            "changed": changed,
            "old": old_sentence,
            "new": new_sentence,
            "verified": True,
        }
    )

out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
