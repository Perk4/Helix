from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = "Steven-Espaillat/Helix"
PUBLISHED = json.loads((ROOT / "published-issues.json").read_text(encoding="utf-8"))
SPEC_BODY = Path("docs/specifications/helix-v1-ui-redesign.md").read_text(encoding="utf-8").rstrip()
RENDERED = sorted((ROOT / "rendered-issues").glob("*.md"))


def run(args: list[str]) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout


def issue(number: int) -> dict[str, object]:
    raw = run([
        "gh",
        "issue",
        "view",
        str(number),
        "--repo",
        REPO,
        "--json",
        "number,title,state,body,url",
    ])
    return json.loads(raw)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    spec = issue(PUBLISHED["spec"]["number"])
    require(spec["state"] == "OPEN", f"spec issue #{spec['number']} is not open")
    require(spec["title"] == PUBLISHED["spec"]["title"], "spec title mismatch")
    require(spec["body"].rstrip() == SPEC_BODY, "spec body mismatch")

    tickets = PUBLISHED["tickets"]
    require(len(tickets) == 10, f"expected 10 tickets, got {len(tickets)}")
    require(len(RENDERED) == 10, f"expected 10 rendered bodies, got {len(RENDERED)}")

    checked = []
    for ticket, body_path in zip(tickets, RENDERED, strict=True):
        remote = issue(ticket["number"])
        expected_body = body_path.read_text(encoding="utf-8").rstrip()
        body = remote["body"].rstrip()
        require(remote["state"] == "OPEN", f"issue #{ticket['number']} is not open")
        require(remote["title"] == ticket["title"], f"title mismatch for #{ticket['number']}")
        require(body == expected_body, f"body mismatch for #{ticket['number']}")
        for heading in ["## Goal", "## Locked", "## Acceptance", "## Out of scope", "## Refs", "## Process"]:
            require(heading in body, f"{heading} missing from #{ticket['number']}")
        require("- [ ]" in body, f"acceptance checklist missing from #{ticket['number']}")
        require(f"Spec #{PUBLISHED['spec']['number']}" in body, f"spec reference missing from #{ticket['number']}")
        require("Blocked by" in body and "Blocks" in body, f"process edges missing from #{ticket['number']}")
        checked.append({"number": ticket["number"], "title": ticket["title"], "url": remote["url"]})

    output = {"spec": PUBLISHED["spec"], "tickets_checked": checked}
    (ROOT / "verification.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
