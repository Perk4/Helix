from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

REPO = "Steven-Espaillat/Helix"
ROOT = Path(__file__).resolve().parent
SPEC_PATH = Path("docs/specifications/helix-v1-ui-redesign.md")
RENDERED = ROOT / "rendered-issues"
RESULTS = ROOT / "published-issues.json"
SPEC_TITLE = "SPEC: HELIX v1 stage-gated UI redesign"

TICKETS = [
    {
        "key": "ui0",
        "title": "UI SLICE 0: Adopt v1 tokens and one-page shell",
        "goal": "Replace the v0 tabbed workbench shell with the v1 clinical workspace shell, header, release pill, and page layout so the app looks and reads like the reference before stage behavior is added.",
        "locked": [
            "Remove the v0 workspace tabs and side menu affordances from the redesign path.",
            "Use the v1 `light-dark()` token set for color, surface, border, and tone values. Do not hard-code reference hex values in components.",
            "Use IBM Plex Sans for UI text, IBM Plex Mono for identifiers, and Georgia only for draft report body text.",
            "Keep the `Synthetic data · Not for submission` badge and avoid any FDA approval claim.",
        ],
        "acceptance": [
            "The workbench renders the v1 header with brand, study identity, synthetic badge, release pill, and user avatar in light and dark themes.",
            "The old Study journey, Evidence chain, and Report assembly tabs are absent from the redesigned shell.",
            "Cards, buttons, chips, focus outlines, and tone helpers read from v1 tokens.",
            "Inline stroke SVG icons replace emoji and decorative text symbols in the new shell.",
            "The existing release status still comes from the workspace response and remains visible in the pill.",
            "A screenshot or Playwright assertion covers the shell in both light and dark themes.",
        ],
        "out": "Reducer behavior, Progress Bar interactions, upload authorization, Agent Step activity, traceability review, sign-offs, and export remain out of scope.",
        "refs": "`UI-001` through `UI-006`, `UI-014` through `UI-021`; `research/HANDOFF.md` §§2, 3, 5.1, and 6; `research/helix-e2e-workbench-v1.html` header and token definitions; `docs/adr/0022-adopt-stage-gated-workspace.md`.",
        "blockers": [],
        "blocks": ["ui1", "ui2"],
    },
    {
        "key": "ui1",
        "title": "UI SLICE 1: Implement the reducer and Progress Bar governance",
        "goal": "Give the one-page workspace a tested nine-stage reducer and Progress Bar that selects reached stages without letting the user or agent skip Human Gates.",
        "locked": [
            "Encode the handoff transition table and invariants in one reducer or equivalent state boundary.",
            "The Progress Bar is the only navigation for the redesigned workspace.",
            "Clicking a reached stage changes only the selected view. It never changes progress.",
            "Future stages are disabled, and the agent never passes a Human Gate.",
            "Gate nodes are rounded squares with a person icon. Agent nodes are circles with stage numbers or running state.",
        ],
        "acceptance": [
            "Reducer tests cover every transition row from `authorize` through `export`.",
            "Reducer tests cover all six governance invariants from the handoff.",
            "Progress Bar tests cover `current` values from 0 through 9, including done, current, selected, paused, awaiting, and pending states.",
            "Future stages cannot be clicked, and clicking a past stage changes only the selected stage.",
            "The current stage uses `aria-current=\"step\"`, and each stage button has an accessible label that includes its status.",
            "The track is green through completed progress and neutral after the current stage.",
        ],
        "out": "Stage view content, file upload behavior, live agent actions, traceability accordion, approvals, export, and backend production events remain out of scope.",
        "refs": "`UI-001` through `UI-013`, `UI-014` through `UI-021`; `research/HANDOFF.md` §§3, 4, 5.2, and 7; `research/helix-e2e-workbench-v1.html` `State`, `Transitions`, and stepper rendering.",
        "blockers": ["ui0"],
        "blocks": ["ui2", "ui3", "ui4", "ui5"],
    },
    {
        "key": "ui2",
        "title": "UI SLICE 2: Build the upload authorization gate",
        "goal": "Make Stage 1 work as Human Gate 1 so a user can review the required inputs, check consent, freeze the manifest, and start the Agent Steps.",
        "locked": [
            "The agent cannot start before Gate 1 authorization.",
            "The authorize action is disabled until the consent checkbox is checked.",
            "After authorization, files show `Frozen`, the drop zone is hidden, and the primary action becomes disabled.",
            "This slice may use the seeded demo file list. Real upload, checksums, type checks, and missing-input handling belong to the production wiring ticket.",
        ],
        "acceptance": [
            "The Upload view shows the drop zone, file table, pre-checks, consent checkbox, and `Authorize and start agent` action from the reference.",
            "The authorize action is disabled until consent is checked.",
            "After authorization, the Progress Bar moves to Stage 2, selects Stage 2, resets the action tick, and starts the runner.",
            "After authorization, the manifest action reads `Manifest frozen · MANIFEST-HLX-028` and cannot be clicked again.",
            "The live region announces that the manifest is frozen and the agent started.",
            "Tests cover both the disabled and authorized paths.",
        ],
        "out": "Real upload persistence, checksum validation, server-side manifest freeze, Agent Step activity details, traceability review, approvals, and export remain out of scope.",
        "refs": "`UI-022` through `UI-027`; `research/HANDOFF.md` §§4, 5.3, 5.4, 7, and 8; `research/helix-e2e-workbench-v1.html` Upload view and `authorize` action.",
        "blockers": ["ui0", "ui1"],
        "blocks": ["ui3"],
    },
    {
        "key": "ui3",
        "title": "UI SLICE 3: Run Agent Steps with live activity and pause or resume",
        "goal": "Show stages 2 through 7 as a live agent run with a run banner, control boundary, activity rows, blocker flags, and pause or resume controls.",
        "locked": [
            "The agent runs only between Human Gates and stops at Traceability Review.",
            "Each Agent Step shows its input, output, summary, and control boundary from the reference content.",
            "Activity rows move through queued, active, done, and blocker states without using color as the only signal.",
            "Pause and Resume affect only Agent Steps. They do not pass gates or change release state.",
            "Past Agent Steps show all actions as done when selected for review.",
        ],
        "acceptance": [
            "Stages 2 through 7 share one Agent Step view that renders the correct stage content and four actions.",
            "The run banner shows running, paused, and complete states with the correct current action or next gate copy.",
            "Pause stops the runner, and Resume continues from the current Agent Step.",
            "The validation stage shows blocker actions with a warning icon and `Blocker` tag.",
            "The agent stops at Stage 8, sets running false, selects Traceability Review, and announces the stop.",
            "A test covers pause, resume, blocker rendering, automatic stop at Gate 2, and review of a past Agent Step.",
        ],
        "out": "Production run events, server-side pause and resume, Traceability Review internals, sign-offs, and export remain out of scope.",
        "refs": "`UI-028` through `UI-034`; `research/HANDOFF.md` §§4, 5.5, 7, 8, and 10; `research/helix-e2e-workbench-v1.html` `STAGES`, runner, and Agent view rendering.",
        "blockers": ["ui2"],
        "blocks": ["ui4", "ui7"],
    },
    {
        "key": "ui4",
        "title": "UI SLICE 4: Build the Traceability Review gate",
        "goal": "Make Stage 8 work as Human Gate 2 so a reviewer can inspect rule evidence, record a blocker disposition, and continue only after the disposition exists.",
        "locked": [
            "Only one validation rule row is open at a time.",
            "The Continue action is disabled until the blocked rule has a disposition.",
            "A blocker with a recorded disposition changes to `Disposition`. It never becomes `Pass`.",
            "The five-step traceability flow shows Frozen source, Normalized facts, Transform, Validated claim, and Report field.",
            "The implementation matches the reference claim first and keeps the data shape ready for more claims later.",
        ],
        "acceptance": [
            "The gate banner, claim header, summary chips, accordion table, and rule rows match the reference behavior.",
            "Each row button uses `aria-expanded` and `aria-controls`, and only one row can be open.",
            "Opening a rule shows the five-step traceability flow with highlighted checked, blocked, or disposition steps.",
            "The blocked row shows `Record disposition` only while Gate 2 is active and unresolved.",
            "After disposition, the badge reads `Disposition`, the note shows the disposition text, and Continue is enabled.",
            "Continuing moves to Stage 9, selects Review and Export, and announces Traceability Review approval.",
        ],
        "out": "Multi-claim grouping, production disposition forms, server persistence, Review and Export internals, and export remain out of scope.",
        "refs": "`UI-035` through `UI-042`; `research/HANDOFF.md` §§4, 5.3, 5.6, 7, 8, 10, and 11; `research/helix-e2e-workbench-v1.html` Traceability view and `RULES` data.",
        "blockers": ["ui3"],
        "blocks": ["ui5", "ui9"],
    },
    {
        "key": "ui5",
        "title": "UI SLICE 5: Build the Review and Export gate",
        "goal": "Make Stage 9 work as Human Gate 3 so a reviewer can inspect the draft section, record role sign-offs, and export the package through a separate explicit action.",
        "locked": [
            "Export is disabled until required sign-offs are recorded.",
            "Export remains a separate action after sign-off. Recording approvals does not export.",
            "The release pill changes only through blocked, ready for export, and package exported states.",
            "The prototype must never state or imply FDA approval.",
            "The demo approval action is allowed only in the parity milestone and must be removed during production wiring.",
        ],
        "acceptance": [
            "The Review and Export view renders the section list, active draft document, provenance readout, sign-offs card, and export card from the reference.",
            "Before sign-off, export is disabled and the release pill remains blocked.",
            "Recording demo approvals marks the sign-off rows signed and changes the release pill to ready for export.",
            "Export changes the journey to 9 of 9, changes the pill to package exported, updates the provenance readout, and announces completion.",
            "Selecting a past Agent Step after export shows completed actions and blocker flags.",
            "Tests cover approvals, export, release pill copy, 100 percent progress, and no FDA approval claim.",
        ],
        "out": "Production e-signature flows, real artifact checksums, download verification, per-section approve or return, cancel, and rewind remain out of scope.",
        "refs": "`UI-043` through `UI-050`; `research/HANDOFF.md` §§4, 5.7, 7, 8, 10, and 11; `research/helix-e2e-workbench-v1.html` Review view, release pill, and export action.",
        "blockers": ["ui4"],
        "blocks": ["ui6", "ui9"],
    },
    {
        "key": "ui6",
        "title": "UI SLICE 6: Prove accessibility, responsiveness, and full journey parity",
        "goal": "Harden the redesigned parity milestone so keyboard, screen-reader, desktop, tablet, mobile, light theme, and dark theme users can complete the full journey.",
        "locked": [
            "Every interactive element is a real button, input, or label.",
            "Status is never shown by color alone.",
            "A polite live region announces agent start, gate stops, pause, resume, gate approvals, and export.",
            "The page has no horizontal page scroll at 390 px. The Progress Bar may scroll inside itself.",
            "Reduced motion slows spinners and avoids extra animation.",
        ],
        "acceptance": [
            "Axe reports no serious or critical accessibility violations for the redesigned journey.",
            "A keyboard-only test completes authorization, pause, resume, disposition, approvals, export, and past-stage review.",
            "The full journey passes in light and dark themes.",
            "Responsive tests cover desktop, 1100 px, and 390 px widths with no horizontal page scroll at 390 px.",
            "Focus-visible outlines appear for Progress Bar stages, accordion rows, gate actions, and export controls.",
            "Playwright screenshots capture the initial, Traceability Review, Review and Export, and exported states.",
        ],
        "out": "Production run events, real upload APIs, server-side pause and resume, e-signature flows, and checksum verification remain out of scope.",
        "refs": "`UI-051` through `UI-058`; `research/HANDOFF.md` §§6, 7, and 10; `research/helix-e2e-workbench-v1.html` responsive styles and live region behavior.",
        "blockers": ["ui5"],
        "blocks": ["ui7", "ui8", "ui9"],
    },
    {
        "key": "ui7",
        "title": "UI SLICE 7: Expose backend-owned nine-stage journey and run events",
        "goal": "Replace demo-only progress authority with a backend-owned nine-stage journey contract and recorded run events that the UI can render without simulating production progress.",
        "locked": [
            "The backend is authoritative for current stage, selected allowed history, running state, gate stops, and release status.",
            "Production progress comes from recorded run events or a server-owned equivalent, not a client timer.",
            "The contract uses the v1 nine-stage model with Human Gates and Agent Steps.",
            "The client may render state and request controls. It must not derive release readiness or pass gates locally.",
            "Generated TypeScript API types must match the backend schema before frontend production wiring lands.",
        ],
        "acceptance": [
            "The workspace response or run endpoint exposes the nine v1 stages with type, short label, name, status, and selected-view eligibility.",
            "Run events represent stage started, action started, action finished with optional flag, stage finished, run paused, and gate reached, or an explicitly equivalent server-owned model.",
            "The current backend ten-stage or hybrid-owner model no longer leaks into the redesigned Progress Bar.",
            "Backend tests prove that agent progress stops at Human Gates and cannot pass them without gate commands.",
            "Type generation updates the frontend contract, and typecheck fails if the UI reads the old stage shape.",
            "A Playwright or API test proves that reloading the page restores progress from server state, not client memory.",
        ],
        "out": "Real file upload, pause or resume controls, disposition forms, sign-off commands, export download verification, and visual parity polish remain out of scope.",
        "refs": "`UI-059` through `UI-066`; `research/HANDOFF.md` §§4, 5.5, 8, and 11; `backend/app/service.py` `build_stages`; `backend/app/schemas.py` `Stage`; `frontend/src/lib/types.ts`.",
        "blockers": ["ui3", "ui6"],
        "blocks": ["ui8", "ui9"],
    },
    {
        "key": "ui8",
        "title": "UI SLICE 8: Wire upload gate and run controls to API state",
        "goal": "Replace the fixed demo file list, demo manifest freeze, local runner controls, and client-owned running state with API-backed upload, manifest authorization, pause, and resume behavior.",
        "locked": [
            "Real upload state shows progress, checksum, type check, required role, and missing-input state for each required input.",
            "Manifest authorization is idempotent and starts or resumes the same run on replay.",
            "Pause and Resume call backend run-control commands, and the UI updates only from server acknowledgement or subsequent run events.",
            "The agent still cannot start before Gate 1 authorization and cannot pass later Human Gates.",
            "Client code must remove the production use of fixed `FILES` data and timer-driven state.",
        ],
        "acceptance": [
            "Uploading or selecting required files renders per-file progress, checksum, type, role, and validation status returned by the backend.",
            "Missing or invalid required inputs keep authorization disabled and show an accessible explanation.",
            "Authorizing the manifest records the server manifest identity and starts or resumes the backend run exactly once for an idempotent replay.",
            "Pause and Resume call backend commands and render the acknowledged state without advancing progress locally.",
            "A reload after authorization shows the frozen manifest and current run state from the API.",
            "Tests cover duplicate authorization replay, conflicting replay rejection, pause, resume, missing input, invalid type, and checksum rendering.",
        ],
        "out": "Traceability disposition forms, role-specific sign-off flows, artifact download verification, multi-user locking beyond the run-control contract, cancel, and rewind remain out of scope.",
        "refs": "`UI-067` through `UI-070`; `research/HANDOFF.md` §§5.4 and 8; `docs/adr/0022-adopt-stage-gated-workspace.md`; `backend/app/main.py` command patterns; `frontend/src/lib/api.ts` command wrappers.",
        "blockers": ["ui7"],
        "blocks": ["ui9"],
    },
    {
        "key": "ui9",
        "title": "UI SLICE 9: Wire production review, sign-off, export, and checksums",
        "goal": "Replace demo Traceability Review and Review and Export actions with persisted disposition, role sign-off, export, artifact checksum, and download behavior while preserving the v1 interaction model.",
        "locked": [
            "`Record demo approvals` is removed from production wiring.",
            "A disposition requires reason, action, and signer data and persists to the audit trail.",
            "Role sign-offs come from the configured review flow and remain blocked until prerequisites pass.",
            "Export calls the backend export command and displays the checksums of the four finished artifacts.",
            "Export remains separate from approval and never claims FDA acceptance.",
            "The client renders backend release state and artifact data without recalculating readiness.",
        ],
        "acceptance": [
            "Gate 2 opens a disposition form for the blocked rule, persists the disposition through the API, and keeps the result labeled as `Disposition`.",
            "Gate 3 renders role-specific sign-off state from the backend and blocks study director approval until prerequisite roles are complete.",
            "Export calls the backend command, shows the four artifact checksums returned by the API, and enables downloads for exported artifacts.",
            "A stale or missing disposition, missing sign-off, stale approval, or backend-blocked release keeps export disabled with an accessible reason.",
            "The full browser workflow verifies API state after disposition, approvals, export, artifact checksums, and download availability.",
            "The production path contains no demo timer, fixed reference data, or demo approval shortcut.",
        ],
        "out": "Cancel, rewind, per-section return workflows, FDA submission readiness, and multi-user gate locking beyond the implemented backend review contracts remain out of scope.",
        "refs": "`UI-071` through `UI-074`; `research/HANDOFF.md` §§5.6, 5.7, 8, 10, and 11; `backend/app/main.py` review and export endpoints; `frontend/src/components/ReportAssembly.tsx`; `frontend/tests/workbench.spec.ts`.",
        "blockers": ["ui4", "ui5", "ui6", "ui7", "ui8"],
        "blocks": [],
    },
]


def run(args: list[str], input_text: str | None = None) -> str:
    result = subprocess.run(args, input=input_text, text=True, check=True, capture_output=True)
    return result.stdout.strip()


def load_issues() -> dict[str, dict[str, object]]:
    raw = run([
        "gh",
        "issue",
        "list",
        "--repo",
        REPO,
        "--state",
        "all",
        "--limit",
        "200",
        "--json",
        "number,title,url,state",
    ])
    issues = json.loads(raw)
    return {issue["title"]: issue for issue in issues}


def write_temp(text: str) -> str:
    handle = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
    with handle:
        handle.write(text)
    return handle.name


def create_or_find(title: str, body: str) -> dict[str, object]:
    issues = load_issues()
    if title in issues:
        return issues[title]
    body_file = write_temp(body)
    url = run([
        "gh",
        "issue",
        "create",
        "--repo",
        REPO,
        "--title",
        title,
        "--body-file",
        body_file,
    ])
    number = int(url.rstrip("/").split("/")[-1])
    return {"number": number, "title": title, "url": url, "state": "OPEN"}


def edit_issue(number: int, body: str) -> None:
    body_file = write_temp(body)
    run([
        "gh",
        "issue",
        "edit",
        str(number),
        "--repo",
        REPO,
        "--body-file",
        body_file,
    ])


def ref_for(key: str, numbers: dict[str, int]) -> str:
    return f"#{numbers[key]}"


def ref_list(keys: list[str], numbers: dict[str, int]) -> str:
    if not keys:
        return "none"
    return ", ".join(ref_for(key, numbers) for key in keys)


def render_ticket(ticket: dict[str, object], numbers: dict[str, int]) -> str:
    locked = "\n".join(f"- {item}" for item in ticket["locked"])
    acceptance = "\n".join(f"- [ ] {item}" for item in ticket["acceptance"])
    blocked = ref_list(ticket["blockers"], numbers)
    blocks = ref_list(ticket["blocks"], numbers)
    if blocked == "none":
        blocked_sentence = "Blocked by none."
    else:
        blocked_sentence = f"Blocked by {blocked}."
    if blocks == "none":
        blocks_sentence = "Blocks none."
    else:
        blocks_sentence = f"Blocks {blocks}."
    return f"""## Goal

{ticket["goal"]}

## Locked

{locked}

## Acceptance

{acceptance}

## Out of scope

{ticket["out"]}

## Refs

Spec #{numbers["spec"]}; `docs/specifications/helix-v1-ui-redesign.md` · {ticket["refs"]}

## Process

{blocked_sentence} {blocks_sentence} One vertical PR.
"""


def main() -> None:
    RENDERED.mkdir(parents=True, exist_ok=True)
    spec_body = SPEC_PATH.read_text(encoding="utf-8")
    spec_issue = create_or_find(SPEC_TITLE, spec_body)
    numbers: dict[str, int] = {"spec": int(spec_issue["number"])}
    issue_records: dict[str, dict[str, object]] = {"spec": spec_issue}

    for ticket in TICKETS:
        provisional = "Provisioning issue body. Re-run `.scratch/helix-ui-redesign-v1/publish_issues.py` if this text remains."
        issue = create_or_find(ticket["title"], provisional)
        numbers[ticket["key"]] = int(issue["number"])
        issue_records[ticket["key"]] = issue

    edit_issue(numbers["spec"], spec_body)

    for index, ticket in enumerate(TICKETS, start=1):
        body = render_ticket(ticket, numbers)
        slug = ticket["title"].lower().replace(":", "").replace(" ", "-").replace("/", "-")
        (RENDERED / f"{index:02d}-{slug}.md").write_text(body, encoding="utf-8")
        edit_issue(numbers[ticket["key"]], body)

    output = {
        "repo": REPO,
        "spec": {"number": numbers["spec"], "title": SPEC_TITLE, "url": f"https://github.com/{REPO}/issues/{numbers['spec']}"},
        "tickets": [
            {"key": ticket["key"], "number": numbers[ticket["key"]], "title": ticket["title"], "url": f"https://github.com/{REPO}/issues/{numbers[ticket['key']]}"}
            for ticket in TICKETS
        ],
    }
    RESULTS.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
