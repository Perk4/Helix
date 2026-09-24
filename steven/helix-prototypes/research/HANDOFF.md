# HELIX v1 UI: implementation handoff

**For:** coding agents who implement the new HELIX report workspace UI.
**Replaces:** `helix-e2e-workbench-v0.html` (the three-tab workbench).
**Reference build:** `helix-e2e-workbench-v1.html` in this folder. Open it in a browser. It is the source of truth for layout, copy, states and behavior. If this document and the reference build disagree, the reference build wins. Report each difference that you find.

---

## 1. Goal

Change the HELIX workspace from three separate tabs to **one page**. The progress of the study controls this page.

- The user does not select views. The **progress bar** is the only navigation.
- The journey has **9 stages**. **3 stages are human gates.** The other 6 stages are agent steps.
- Between the gates, the agent **runs by itself**. The page shows each action live.
- The agent **stops** at each human gate. Only a person can pass a gate.

## 2. What changes from v0

| Area | v0 | v1 |
|---|---|---|
| Navigation | 3 mode tabs (Study journey, Evidence chain, Report assembly) | No tabs, no side menu. The progress bar selects the view. |
| Stages | 10 stages, with different owners (human, agent, hybrid) | 9 stages: 3 human gates, 6 agent steps |
| Stage 1 | Text card | File upload page with an authorization form (gate 1) |
| Agent stages | Static card. A "Run next stage" button moves one stage. | The agent runs automatically. A live activity list and Pause/Resume. |
| Evidence chain | Separate tab. A static 5-card chain above a table. | Gate 2 view. The table is the main part. Each row opens to show its 5-step traceability flow. |
| Report assembly | Separate tab | Gate 3 view. Includes sign-offs and export. |
| Progress | Grid of stage buttons | Connected track: circles for agent steps, rounded squares with a person icon for gates |
| Theme | Blue/navy, Inter | Clinical teal, IBM Plex Sans/Mono, `light-dark()` tokens |

## 3. Information architecture

```
Header (brand · study · "Synthetic data" badge · release pill · user)
Progress bar (9 stages)                       <- only navigation
Stage view (one of 4 views, selected by the progress bar)
  ├─ Upload view      stage 1          (Human gate 1)
  ├─ Agent view       stages 2–7       (agent runs)
  ├─ Traceability     stage 8 "Gates"  (Human gate 2)
  └─ Review & export  stage 9          (Human gate 3)
```

### Stage table

| # | Short label | Name | Type | View |
|---|---|---|---|---|
| 1 | Upload | Upload and authorize inputs | **Human gate 1** | Upload |
| 2 | Parse | Parse protocol, template and source data | Agent | Agent |
| 3 | Resolve | Resolve study type and pattern | Agent | Agent |
| 4 | Extract | Deterministic extraction | Agent | Agent |
| 5 | Validate | Deterministic validation | Agent | Agent |
| 6 | Draft | Structured section drafting | Agent | Agent |
| 7 | Provenance | Compile provenance | Agent | Agent |
| 8 | Gates | Traceability review | **Human gate 2** | Traceability |
| 9 | Review & export | Review, sign and export | **Human gate 3** | Review |

The content for each agent stage (summary, input, output, control boundary, 4 actions) is in `STAGES` in the reference build. Use this content as it is.

## 4. State model

```ts
type State = {
  current: number;      // furthest stage reached, 0–8 (index). 9 = journey complete (after export)
  sel: number;          // stage whose view is shown, 0–8. Always <= current (or any stage after completion)
  running: boolean;     // agent auto-run is active
  tick: number;         // actions finished in the current agent stage
  authChecked: boolean; // gate 1 consent checkbox
  disposed: boolean;    // gate 2: blocker has a recorded disposition
  approved: boolean;    // gate 3: sign-offs recorded
  exported: boolean;    // gate 3: package exported
  openRule: number;     // gate 2: open accordion row (-1 = none). Default = index of the blocked rule
};
```

### Transitions

| Event | Precondition | Effect |
|---|---|---|
| `authorize` | `current === 0 && authChecked` | `current=1, sel=1, tick=0, running=true`. Start the runner. |
| runner tick (every 700 ms) | `running` | If `tick < acts.length`, then `tick++`. Else, go to the next stage. If the next stage is a gate, set `running=false` and `sel=next` (auto-show the gate). |
| `pause` / `resume` | agent stage | Stop or start the runner. On resume, `sel=current`. |
| `dispose` | `current === 7` | `disposed=true` |
| `passTrace` | `current === 7 && disposed` | `current=8, sel=8` |
| `approve` | `current === 8` | `approved=true` |
| `export` | `current === 8 && approved && !exported` | `exported=true, current=9` |
| `pick(i)` (progress bar) | `i <= current` | `sel=i` (review only, no change to progress) |

### Invariants (governance: do not break)

1. The agent **never** passes a gate. Only a user action passes a gate.
2. The agent does not start before gate 1 authorization.
3. You cannot continue at gate 2 while a blocker has no disposition.
4. Export is always a **separate, explicit** action after the sign-offs. Other actions do not export.
5. A validation blocker cannot become "Pass". It can only become "Disposition", with the reason recorded.
6. The user cannot jump to a stage in the future.

## 5. Components

### 5.1 Header
Brand mark, study ID with its descriptor line, the dashed "Synthetic data · Not for submission" badge, the release pill, and the user avatar.
Release pill: `Release blocked` (block tone) → `Ready for export` (pass tone, after the sign-offs) → `Package exported` (info tone).

### 5.2 Progress bar
- A card with the header text "Journey progress · N of 9 stages complete · P%", a legend (Human gate / Agent step) and a hint.
- 9 equal columns. Each column is a `<button>`: a track line, a node, a short label and a status line.
- **Node shape:** gate = rounded square (radius 8) with a person icon. Agent = circle with the stage number.
- **Node state:** done = filled green with a check mark. Current agent = filled teal with a 4px halo (with a spinner while it runs). Current gate = amber-soft fill with an amber border and halo. Pending = outline only (gates stay amber).
- **Track:** the line is green up to the current stage, and grey after it.
- **Status text:** Done / Approved (gate) / Agent running / Paused / Awaiting you (gate) / Agent / Human gate.
- Future stages are `disabled`. The selected stage has an accent-soft background. The current stage has `aria-current="step"`.

### 5.3 Gate banner (used by all 3 gates)
Person icon, kicker "Human gate N of 3 · Awaiting you | Approved", a title, and on the right a hint and the gate action. Tone: amber = awaiting, green = approved.

### 5.4 Upload view (gate 1)
- Left card: title, drop zone (the drag state changes the border to teal; there is a real `<input type=file>` behind "Browse files"), and a file table (File, Type, Role, Status). Status = `Uploaded` → `Frozen` after authorization. The drop zone is hidden after authorization.
- Right card, "Freeze the manifest": 3 pre-checks, a consent checkbox with a label, and the primary button "Authorize and start agent" (disabled until the box is checked). After authorization, the button label is "Manifest frozen · MANIFEST-HLX-028" and the button is disabled.

### 5.5 Agent view (stages 2–7)
- **Run banner:** running (teal, spinner, "Agent working · Stage N of 9", "<stage> — <current action>", Pause) / paused (neutral, Resume agent) / complete (green, "Agent run complete … Waiting at human gate: X").
- **Left card:** "Stage N of 9 · Agent step", name, state chip (Running / Paused / Completed), summary, Input → Output boxes, control boundary callout (amber, shield icon).
- **Right card, "Agent activity"** ("n of 4 actions"): one row for each action. States: queued (hollow circle, faint text) → active (spinner, bold text, "Working…") → done (green check). A done action with a flag shows a red warning icon and the tag "Blocker".
- When the user opens a past agent stage, it shows all its actions as done.

### 5.6 Traceability view (gate 2)
- Gate banner with the hint and the button "Approve and continue to review" (disabled until `disposed`).
- Claim header: "Claim C-BW-HIGH · Terminal body weight, high-dose group", with summary chips (3 passed / 1 blocked, or 1 disposition).
- **Accordion table:** columns = chevron, Validation rule, Evidence, Result. Each row header is a `<button aria-expanded aria-controls>`. Only one row is open at a time.
- **Open row:** a 5-step flow (Frozen source → Normalized facts → Transform → Validated claim → Report field). The steps that the rule checks are highlighted in the rule's tone (pass = green, blocked = red, disposition = amber). Under the flow is a note line ("Checked: / Blocker: / Disposition:").
- The blocked row has the button "Record disposition". It shows only while gate 2 is active. After the user records the disposition, the badge changes to "Disposition" and the note shows the disposition text.

### 5.7 Review & export view (gate 3)
- Gate banner with the status hint.
- Three columns: section list with status chips (section 7 is active) | draft document (serif body, "Needs review" flag, "Inspect 4 provenance edges" with a live mono readout) | sign-offs card.
- Sign-offs: "Traceability gate passed" (approved), then Pathologist peer review, QAU statement, Study director approval (Pending with a clock icon → Signed with a check).
- "Record demo approvals" (only in the demo; see §8), then "Export final package" (primary, enabled only after the sign-offs), then the disclaimer "A prepared package is not FDA acceptance."

## 6. Design tokens

All colors are CSS custom properties on `#helix-e2e`, with `light-dark()` pairs. Do not hard-code hex values in components.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--hx-bg` | #F5F7F8 | #0D141B | page |
| `--hx-surface` | #FFFFFF | #141E28 | cards |
| `--hx-surface-2` | #F5F7F8 | #1B2936 | table heads, input boxes |
| `--hx-line` / `--hx-line-soft` | #DCE3E8 / #EEF1F3 | #34485B / #24374A | borders, row dividers |
| `--hx-ink` / `--hx-ink-2` | #111C24 / #33434F | #E7EEF6 / #C4D1DC | text |
| `--hx-muted` / `--hx-faint` | #5A6B78 / #8FA0AC | #9EB0C1 / #6F8395 | secondary / queued |
| `--hx-accent` (+ `-soft`, `-ring`) | #0A5F66 | #5CC3CB | primary actions, current step, running |
| `--hx-pass` (+ `-soft`) | #17663F | #5DD5A7 | done, pass |
| `--hx-warn`, `--hx-gate` (+ `-soft`) | #8A4B00, #B26A00 | #F5BD67 | human gates, review flags |
| `--hx-block` (+ `-soft`) | #A61B1B | #FF8D89 | blockers |
| `--hx-info` (+ `-soft`) | #1D4F7A | #69B6F4 | exported state |

**Type:** IBM Plex Sans (UI), IBM Plex Mono (IDs, record pointers, file types), Georgia (draft report body only). Sizes: 22 (page h1), 18 (card h2), 16 (h3), 15 (banner titles, lead text), 14 (body), 13 (rows), 12 (kickers, chips, meta), 11 (step status).
**Kicker style:** 12px, weight 600, uppercase, letter-spacing .06em, muted color.
**Shape:** card radius 12, control radius 8, chips 999. Page gutter 40px (16px under 1100px). Gap 20px between blocks.
**Icons:** inline stroke SVG, 2px stroke, `currentColor`. No emoji.

## 7. Accessibility requirements

- Every interactive element is a real `<button>`, `<input>` or `<label>`. Do not put click handlers on a `div`.
- Touch targets are at least 44px high (compact 40px buttons only in banners).
- Visible `:focus-visible` outline (2px accent).
- An `aria-live="polite"` region announces: agent start or stop at each gate, pause and resume, gate approvals, export.
- Accordion: `aria-expanded` + `aria-controls`. Progress bar: `aria-current="step"`. Each step's `aria-label` includes its status.
- Status is never shown by color alone. Each state also has an icon or text (check, warning, clock, "Blocked", "Awaiting you").
- Respect `prefers-reduced-motion` (slow the spinners; do not animate other elements).
- Contrast: text 4.5:1 or more in both themes (the reference tokens meet this).

## 8. Demo-only behavior vs production wiring

The reference build uses fixed synthetic data and a timer. When you port it, replace these parts:

| Demo | Production |
|---|---|
| `setTimeout` runner, 700 ms per action | Subscribe to the real agent run events (for example SSE/WebSocket): `stage_started`, `action_started`, `action_finished {flag?}`, `stage_finished`, `run_paused`. Render from the events. Do not simulate. |
| Pause/Resume change local state | Call the agent run control API. The UI state follows the server acknowledgement. |
| Fixed `FILES` list; the drop zone only announces | Real upload with a progress bar for each file, checksum, type check against the required-input manifest, and a missing-input state |
| "Record disposition" sets a flag | Open a disposition form (reason, action, signer). Persist it to the audit log. |
| "Record demo approvals" | Remove it. Each sign-off comes from the e-signature flow of that role. |
| "Export final package" sets a flag | Call the export API. Show the checksums of the 4 artifacts when it finishes. |
| `?stage=N` query parameter | Keep it for tests and storybook only. Production reads the stage from the run record. |

## 9. Suggested task breakdown

Do the tasks in this order. Each task has acceptance criteria (AC).

1. **Tokens and shell.** Add the tokens (§6), the fonts, the header and the page layout. Remove the v0 mode tabs.
   *AC:* the header matches the reference in light and dark themes. There are no tabs or side menu.
2. **State and transitions.** Implement the state (§4) and the transitions as a reducer, with unit tests for each row in the transition table and for each invariant.
   *AC:* all transitions and invariants 1–6 have tests, and the tests pass.
3. **Progress bar** (§5.2).
   *AC:* the 9 nodes have the correct shape and state for each value of `current` from 0 to 9. Future stages are not clickable. Clicking a past stage changes only `sel`.
4. **Upload view** (§5.4).
   *AC:* authorize is disabled until the consent box is checked. After authorization the manifest is frozen, the drop zone is hidden and the agent starts.
5. **Agent view and runner** (§5.5).
   *AC:* the activity rows move from queued to active to done. Blocker actions show the warning icon. The run stops at gate 2 and the page shows the traceability view automatically. Pause/Resume work.
6. **Traceability view** (§5.6).
   *AC:* one row opens at a time. The highlighted flow steps match `focus`. Continue is disabled until the disposition is recorded.
7. **Review & export view** (§5.7).
   *AC:* export is disabled until the sign-offs are recorded. After export: the progress bar shows 9/9 (100%) and the pill says "Package exported".
8. **Accessibility and responsive pass** (§7).
   *AC:* axe shows no serious or critical issues. Keyboard-only users can complete the full journey. At 390px width the page has no horizontal page scroll (the progress bar scrolls inside itself).
9. **Production wiring** (§8). Do this task after tasks 1–8 are merged.

## 10. End-to-end test script

1. Load the page. Progress shows 0/9. Upload is "Awaiting you". "Authorize and start agent" is disabled.
2. Check the consent box, then select Authorize. Stage 2 shows "Agent running". The activity list moves forward.
3. Select Pause. The runner stops. Select Resume. The runner continues.
4. Wait. Stage 5 shows 2 blocker rows. The run stops at stage 8, and the Traceability view opens. Progress shows 7/9.
5. "Approve and continue" is disabled. Open "Expected grain": transform, claim and report field are red. Select Record disposition: the badge changes to "Disposition" and the button is enabled. Continue.
6. Review view. Export is disabled. Record the approvals. The pill changes to "Ready for export". Export: 9/9, "Package exported".
7. Select stage 5 in the progress bar. It shows the completed actions and the 2 blockers.
8. Do steps 1–7 again in dark mode, at 1100px and 390px widths, and with the keyboard only.

## 11. Out of scope / open questions

- Several claims in gate 2 (the reference shows one claim, C-BW-HIGH, with 4 rules). Should the production view group the rules by claim and by section?
- Should section review in gate 3 have per-section approve/return actions, or only the global sign-offs?
- Should the user be able to cancel an agent run, or send it back to an earlier stage, from the UI?
- Session persistence and several users at the same gate (locking, and who sees "Awaiting you").
