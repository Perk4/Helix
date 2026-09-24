## Goal

Replace the v0 tabbed workbench shell with the v1 clinical workspace shell, header, release pill, and page layout so the app looks and reads like the reference before stage behavior is added.

## Locked

- Remove the v0 workspace tabs and side menu affordances from the redesign path.
- Use the v1 `light-dark()` token set for color, surface, border, and tone values. Do not hard-code reference hex values in components.
- Use IBM Plex Sans for UI text, IBM Plex Mono for identifiers, and Georgia only for draft report body text.
- Keep the `Synthetic data · Not for submission` badge and avoid any FDA approval claim.

## Acceptance

- [ ] The workbench renders the v1 header with brand, study identity, synthetic badge, release pill, and user avatar in light and dark themes.
- [ ] The old Study journey, Evidence chain, and Report assembly tabs are absent from the redesigned shell.
- [ ] Cards, buttons, chips, focus outlines, and tone helpers read from v1 tokens.
- [ ] Inline stroke SVG icons replace emoji and decorative text symbols in the new shell.
- [ ] The existing release status still comes from the workspace response and remains visible in the pill.
- [ ] A screenshot or Playwright assertion covers the shell in both light and dark themes.

## Out of scope

Reducer behavior, Progress Bar interactions, upload authorization, Agent Step activity, traceability review, sign-offs, and export remain out of scope.

## Refs

Spec #17; `docs/specifications/helix-v1-ui-redesign.md` · `UI-001` through `UI-006`, `UI-014` through `UI-021`; `research/HANDOFF.md` §§2, 3, 5.1, and 6; `research/helix-e2e-workbench-v1.html` header and token definitions; `docs/adr/0022-adopt-stage-gated-workspace.md`.

## Process

Blocked by none. Blocks #19, #20. One vertical PR.
