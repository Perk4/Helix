# Section Drafting + Human-in-the-Loop Chat — Requirements, Design & Plan

- **Branch:** `feat/draft-section-hitl`
- **Status:** Phase 0 + A + B done → Phase C (chat) next
- **Created:** 2026-09-24
- **Approach:** B (lighter first) — build the UI + chat now on already-verified numbers; mark the rest `needs_review`; expand verified coverage over time.

This is a living document. Each task has a checkbox; update it as work completes and record the change in the **Progress log** at the bottom (date + commit) for tracing.

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked

---

## 1. Requirements

### R1 — Show each section's drafted content in the UI
- The website must render each report section's content when the user navigates to it (today the draft pipeline is CLI-only and writes one combined `draft_output.md`; the UI shows only templated stubs).
- Content must be **generated and stored per section** (not one combined file) so a single section can be shown and reran independently.
- Content must be **richly viewable** — tables render as real tables, never broken raw markdown.

### R2 — Human-in-the-Loop chat per section
- A chat where a research scientist / pathologist can ask questions and say "redo this section with my feedback," and the system re-writes the section.
- Questions may be **section-specific**, **whole-study**, or **general domain** — the chat handles all three but defaults to the current section.
- A revised draft is shown as a **proposal with 👍 / 👎**; on 👍 the reran content is **applied** to the section; on 👎 it is discarded and can be refined.
- The chat is **part of the report page** (not a separate screen), **docked to the bottom**, minimal by default and **expanding upward** when engaged; it must not block the section content.
- The chat behaves like a **production-grade agent**: it remembers the conversation and stays grounded in study-specific data.

### R3 — `needs_review` is the HITL trigger
- `needs_review` flags a section so the scientist verifies it and provides feedback.
- Regeneration is driven by **(a) the scientist's feedback + (b) the existing section content + (c) study-specific verified data** (the section executor).
- Reruns must be **consistent** — refine the section, not produce a different-looking draft each run.

---

## 2. Decisions

| Decision | Choice | Why |
|---|---|---|
| Rollout | **Lighter first (B)** | See UI + chat working early; grow rigor per section |
| Model access | **Azure / APIM**, OpenAI SDK **server-side only** | APIM is what the environment can reach; keeps keys off the client. Codex SDK is installed but targets OpenAI (likely blocked here) |
| Section scheme | **14 docx sections** (`5_2_3_body_weight`, …) | Matches executor, skills, approved-report few-shot, docx target |
| Numbers vs prose | **Tables from verified data (UI draws them) + AI writes prose only** | Kills broken-markdown tables; numbers never drift |
| Chat placement | **Bottom-docked, minimize/expand**, scoped to current section, study/domain aware | Requested; non-blocking; good usability |
| Apply model | **Revise → proposed → 👍 apply / 👎 discard** | Nothing overwrites a section until the human approves |
| Governance depth | Lightweight now; `needs_review → verified` human gate; expand later | Consistent with B |

---

## 3. Design

### 3.1 Section lifecycle (status model)
```
generated ──────────────▶ needs_review        (default: awaiting the scientist)
   scientist reviews + gives feedback in chat
        ▼
   rerun (grounded + anchored) ─▶ proposed     (shown in chat with 👍 / 👎)
        │ 👍 apply                    │ 👎 discard
        ▼                             ▼
   current (still needs_review)       keep current, refine again
        │ scientist "Mark verified"
        ▼
      verified                        (human-approved; HITL gate satisfied)
```
- Every fresh/reran draft starts `needs_review`; nothing is final until a human verifies it.
- Sections with no verified numbers are a stronger `needs_review` (explicit gap shown) — no invented prose.

### 3.2 Draft generation (anchored + grounded + consistent)
```
generate(study_id, section_id, feedback_history, existing_content, apply=False)
  COMPUTE   run_section()                    → verified facts + provenance (the numbers)
  GROUND    build_draft_messages() + facts + skill + meta-prompt
  ANCHOR    inject existing_content + feedback: "revise, don't rewrite"
  RENDER    APIM, temperature 0 (+ seed if supported)  → prose ONLY
  ASSEMBLE  verified tables (unchanged) + refined prose
  PERSIST   new version (diff-able against previous)
```

### 3.3 Consistency contract (reruns don't drift)
1. Numbers come only from the section executor (verified data) — identical every run.
2. Deterministic model call: `temperature = 0` (+ `seed` where APIM supports it).
3. Anchored minimal-change edit: rerun gets the current draft + feedback with "change only what the feedback requires; keep other wording/structure identical; never alter a number."
4. Accumulated feedback: each rerun builds on prior feedback, not from scratch.
5. Fixed grounding: same skill + meta-prompt + facts each time.
6. Versioned + diff-able: the scientist can see exactly what changed between runs.

### 3.4 Chat: scope, memory, UX
- **Scope:** defaults to the current section; toggle **This section | Whole study**. Backend sends current-section data (primary) + study summary (background); domain questions use general knowledge, clearly separated, never inventing study numbers. **Revise is always section-locked.**
- **Memory (prod-grade, pragmatic):** the model is stateless; memory is built by (a) persisting the transcript (one thread per study, append-only), (b) rebuilding context each turn = system rules + grounding + **windowed** recent history + new message, (c) tracking **actions** (revise/apply/discard as events). Rolling-summary and retrieval added later only if chats grow.
- **UX:** bottom-pinned bar, minimized by default, expands upward on focus/message; streaming replies; a `needs_review` section shows a "Needs your review" banner with a "Review & give feedback" button that opens the chat scoped to that section.

### 3.5 Data model (new, append-only)
- `section_drafts` — `(study_id, section_id, version, status[proposed|needs_review|verified], blocks, narrative_md, provenance, note, model, feedback, created_at)`. Current = latest non-discarded version.
- `chat_messages` — `(study_id, message_id, role, content, scope[section|study], section_id, intent[ask|revise], draft_version, created_at)`.

### 3.6 API endpoints (new)
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/studies/{id}/sections` | 14 sections + status |
| `GET` | `/api/v1/studies/{id}/sections/{sid}/draft` | current draft + versions |
| `POST` | `/api/v1/studies/{id}/sections/{sid}/draft` | generate/regenerate (auto) |
| `POST` | `/api/v1/studies/{id}/sections/{sid}/revise` | feedback → **proposed** draft |
| `POST` | `/api/v1/studies/{id}/sections/{sid}/apply` | 👍 apply a proposed version |
| `POST` | `/api/v1/studies/{id}/sections/{sid}/discard` | 👎 discard a proposed version |
| `POST` | `/api/v1/studies/{id}/sections/{sid}/verify` | Mark verified (human gate) |
| `GET` | `/api/v1/studies/{id}/chat` | conversation history |
| `POST` | `/api/v1/studies/{id}/chat` | ask (streamed reply) |

---

## 4. Phased plan (tasks)

### Phase 0 — Foundations · Status: done
- [x] `backend/app/llm.py` — APIM client (detect `azure-api.net`, `subscription-key`, `/deployments/{model}`); lazy OpenAI import so the app loads without the SDK
- [x] APIM settings — read `APIM_API_KEY` / `APIM_BASE_URL` / `APIM_MODEL` from env in `llm.py` (matches `draft_pipeline.py`; no `config.py` change needed); `openai` added to `backend/pyproject.toml`
- [x] `backend/app/section_catalog.py` — 14 sections → `{id, title, order, template_section, has_verified_claims}`
- [x] Smoke test: executor → assembly runs without credentials (prose degrades gracefully)

### Phase A — Per-section drafts: generate, store, read (R1 backend, R3) · Status: done
- [x] `section_drafts` table (append-only versions) in `models.py` + repository methods
- [x] `backend/app/draft_service.py` — `generate(...)` anchored to current draft + feedback; `temperature=0` via `llm.chat`
- [x] Assemble draft = **verified tables (structured, from executor facts) + AI prose**; sections without data → `needs_review` + note (no invented prose)
- [x] `get_current(...)`, `list_sections(...)`
- [x] Endpoints: `GET /sections`, `GET/POST /sections/{sid}/draft`
- [x] Schemas: `SectionDraft`, `SectionBlock (prose|table|note)`, `SectionListItem`, `DraftRequest`
- [x] Tests: `tests/test_section_drafts.py` — deterministic tables/provenance, feedback-anchoring, no-data note, endpoints (6 tests)

### Phase B — Show section content richly (R1 frontend) · Status: done (pending browser check)
- [x] Regenerated OpenAPI + TS types (`api-schema.d.ts`) for the new endpoints
- [x] `lib/api.ts` + `lib/types.ts` — `getSections`, `getSectionDraft`, `generateSectionDraft` + types
- [x] `ReportAssembly.tsx` — navigator uses 14 sections + status chips
- [x] Center paper renders current draft: **table blocks as real tables**, **prose via `react-markdown` + `remark-gfm`**; version badge; needs-review banner; Generate/Regenerate; provenance count
- [x] Add deps `react-markdown`, `remark-gfm`; styles in `globals.css`
- [x] typecheck + production build pass
- [~] Manual browser check: verify tables render richly and "needs review" shows (user to confirm visually)

### Phase C — Bottom chat + memory (R2 Ask) · Status: not started
- [ ] `chat_messages` table (append-only, one thread per study)
- [ ] `backend/app/chat_service.py` — `ask(...)`: windowed history + grounding (section/study/domain) + APIM streaming + persist turns
- [ ] Endpoints: `GET /chat`, `POST /chat` (SSE stream)
- [ ] Frontend `ChatDock.tsx` — bottom-pinned, minimize/expand, scope toggle, streaming list + input
- [ ] Grounding guardrails: never invent numbers; unverified → "needs review"
- [ ] Tests: context assembly with mocked LLM

### Phase D — Revise → proposed → 👍/👎 apply (R2 revise, R3) · Status: not started
- [ ] `DraftService` revise path returns **proposed** version (anchored to existing + feedback history), not applied
- [ ] Endpoints: `POST /sections/{sid}/revise`, `/apply`, `/discard`, `/verify`
- [ ] Record revise/apply/discard/verify as events (audit + agent action memory)
- [ ] Bound to ≤3 attempts per cycle
- [ ] Frontend: "Revise this section" (section-locked) → proposed rewrite card with 👍 / 👎; 👍 updates section above; 👎 refine; "Mark verified" action
- [ ] Manual UI check: feedback → consistent proposed rewrite → 👍 applies → 👎 discards

---

## 5. Cross-cutting
- [ ] Security: API key server-side only; page calls our endpoints, never the model
- [ ] Streaming: SSE from FastAPI for chat
- [ ] Consistency verified: reruns stable (numbers fixed, temp 0, anchored)
- [ ] Versioned drafts are diff-able for the reviewer

## 6. Out of scope now / future
- Full governed integration (every value promoted to a Validated Claim via Data Validation Packages; SectionDraftCandidate + Review Scaffold + promotion gates for all 14 sections).
- Rolling conversation summary + retrieval/embeddings for very long chats.
- Codex SDK agent track (kept behind the `SectionAgent` Protocol for when OpenAI access is available).
- Final export wiring of applied section drafts.

## 7. Progress log
| Date | Phase / task | Change | Commit |
|---|---|---|---|
| 2026-09-24 | — | Plan captured | (local) |
| 2026-09-24 | Phase 0 + A | Backend: `llm.py`, `section_catalog.py`, `section_drafts` table, `draft_service.py`, 3 section endpoints, schemas, 6 tests (all pass, ruff clean) | ea8be03 |
| 2026-09-24 | Phase 0 | `llm.py`: accept OPENAI_*/LLM_*/APIM_* env names + best-effort `.env` load (key lives in repo-root `.env`, git-ignored); `openai` dep added; APIM smoke test OK (gpt-5.5 wrote grounded prose, refused to invent %) | (pending) |
| 2026-09-24 | Phase B | Frontend: regenerated types, `api.ts`/`types.ts` section calls, `ReportAssembly` renders 14-section drafts (native tables + markdown prose + needs-review banner + generate), CSS; typecheck + build pass; 7 backend tests | (pending) |
