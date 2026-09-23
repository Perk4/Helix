# HELIX evals — build state, roadmap, and GLP check catalog

Single reference for the HELIX evaluation workstream. Reflects team repo state `04ca1f8` (2026-09-23). Synthesizes: the current Promptfoo build, the assurance-gap eval items raised with the team, and the GLP domain checks from `HELIX_GLP_RULES.md` v1.0 — consolidated here so no separate rules doc is needed.

## 1. The eval model

Two Promptfoo tiers plus the deterministic gate layer they sit beside. **Core invariant (ADR-0001): Promptfoo can never turn a gate green** — deterministic rule bundles own all gate authority.

| Layer | What it is | Authority |
|---|---|---|
| **Deterministic gate layer** | Rule Bundles / Data Validation Packages — code checks, `hard_blocker` (ADR-0001/0014). Tested with code + fixtures, **never Promptfoo** (ADR-0021). The 5 GLP **Rules** below live here. | Owns gates |
| **Tier 1 — Skill Qualification** | Promptfoo suite run at skill-promotion time; a pinned run may reference only a *passing* qualification (PKG-005) | Gates skill-version eligibility (recorded on the package), not study gates |
| **Tier 2 — Study Output Evaluation** | Per-run Promptfoo LLM-judge on drafted output; advisory (GATE-006). The 2 GLP **Guardrails** + the assurance-gap judges below live here. | None — fail → `[NEEDS REVIEW]`; a pass is inert |

## 2. GLP domain checks (synthesized from `HELIX_GLP_RULES.md` v1.0, 21 CFR Part 58)

Seven checks placed only where AI failure is consequential and a busy human reviewer might miss it. They divide exactly along the eval boundary: **Rules = deterministic gates; Guardrails = LLM-judge evals.**

### 2a. Deterministic rules — hard-block, validation layer (NOT Promptfoo)

Implement as Data Validation Package / Rule-Bundle **code** (`hard_blocker`); prove each with deterministic **fixture tests** (ADR-0021). These are *not* the Promptfoo workstream — they are the gate layer the evals sit beside.

| ID | Rule | Checks (code vs source CSV) | Reg | When |
|---|---|---|---|---|
| **R-1** | Dose levels match source | Section 2 doses == unique `dose_mgkgday` in `dosing_formulation.csv` | §58.130/.120 | After §2 assembled |
| **R-2** | Animal counts match roster | §2 group×sex counts == row counts in `animal_roster.csv` | §58.185 | After §2 assembled |
| **R-3** | 7 mandatory sections non-empty | Summary, 1, 2 (≥1 table), 3 (≥3.1+3.7), 4, 5 (5.1/5.2/5.3), 7 present + non-placeholder | §58.185 | After full report |
| **R-4** | Unscheduled deaths named in 5.2.1 | If roster `necropsy_type=Unscheduled`/`death_date` set → §5.2.1 names ≥1 animal ID (not "all survived") | §58.81 | After §5.2.1 |
| **R-5** | Numeric claims carry provenance | Every number in §5.2.3/5.3.1/5.3.3 has a resolvable `[value \| source \| col \| rows \| agg]` tag (file/col/rows exist, recompute matches) | §58.185/.190 | After each section |

> **Alignment flag for the colleague:** the shared doc labels rules "Enforced by: Eval assertion checker." In this architecture rules must be **deterministic rule-bundle code**, not Promptfoo assertions — ADR-0001 keeps gate authority in rules and forbids Promptfoo from satisfying a gate. R-5 is effectively the Provenance Compiler (GATE-004); R-1/R-2 are data-validation rules; R-3 is the template/coverage gate.

### 2b. LLM-judge guardrails — flag-and-continue, Tier-2 evals (YOUR lane)

Advisory Promptfoo `llm-rubric` study-output evals; score `0/1` (doc's ≥6/10 → pass), **never hard-block** — fail flags for the human with the judge's reasoning. Host in Promptfoo (not a bespoke `judge.py`) to stay on the team's Tier-2 path (ADR-0007).

| ID | Guardrail | Judge question (verbatim from source) | Reg |
|---|---|---|---|
| **G-1** | NOAEL/LOAEL consistent with findings | "Read §5.3.3 and §5.3.4 together. Is the NOAEL the highest dose group with no adverse findings in 5.3.3? Is the LOAEL the lowest dose with an adverse finding? Score 1 if consistent, 0 if contradictory/unsupported." | §58.185 |
| **G-2** | Adaptive/non-adverse rationale present | "When a finding is called adaptive/non-adverse, does the text give ≥2 specific scientific reasons (no necrosis, no macro correlate, low grade, low incidence, known pharmacological mechanism)? Score 1 if present+specific, 0 if asserted without criteria." | §58.185 |

**G-1 is the highest-value eval in the system** — a wrong NOAEL sets the human starting dose in clinical trials.

### 2c. Deliberately out of scope for MVP (human-gate responsibility)

Terminology consistency (Study Director vs. PI), formulation-stability language, statistical-significance claims, recovery/reversibility completeness, personnel accountability, QA audit tone. The Human Gate covers these — do not build evals for them in the PoC.

## 3. Current eval build state

- **Authored:** Tier-1 suite (`.agents/skills/helix-section-agent/evals/promptfooconfig.yaml`, 2 cases / 8 string-JSON assertions), Tier-2 fragment (`study-output.yaml`), `prompt.txt`, one fixture (`fixtures/body-weight-envelope.json`); contracts require qualification metadata.
- **Not wired:** no runner (`make evals`/CI — no `.github/`), provider unbound (`${HELIX_PROMPTFOO_PROVIDER}` absent from `.env.example`), `qualification_status: pending`, `study-output.yaml` headless, single-section coverage only.

## 4. Roadmap — eval work mapped to the 10-phase build

Overall build phases live in `docs/specifications/agentic-report-pipeline.md` (status: *proposed for implementation review*; current = Phase 1, not yet built).

### Infra & first qualification
| # | Item | Phase | Unblocked now? |
|---|---|---|---|
| S0.1 | Add a runner (`make evals` → `promptfoo eval -c .../promptfooconfig.yaml`) | Stage 0 | **Yes** |
| S0.2 | Bind provider — `HELIX_PROMPTFOO_PROVIDER` in `.env.example` + document key | Stage 0 | **Yes** |
| S0.3 | Add CI (none today) — run qualification on skill/suite change | Stage 0 | **Yes** |
| S0.4 | Harden Tier-1 — semantic (`llm-rubric`) assertions + negative/failure-path fixture (missing-claim envelope) | Stage 0 | **Yes** |
| T1.1 | Run the body-weight Tier-1 suite green against a real provider | Stage 0 → Phase 2 | Yes (after S0.1–S0.2) |
| T1.2 | Record `qualification_status: passed` + `qualification_id` + `qualification_hash` (PKG-005) | Stage 0 → Phase 2 | Yes (after T1.1) |

### Enforcement & pinning
| # | Item | Phase |
|---|---|---|
| T1.3 | Enforce qualification in the Package Loader (PKG-005) | Phase 2 |
| P.1 | Pin eval artifacts into the Pinned Run — qualification suite + result + study-output suite (RUN-004) | Phase 2 |
| P.2 | Fold qualification + study-output suite into the Section Draft dependency fingerprint (PKG-008) | Phase 2 / 5 |

### Tier-2 study-output harness
| # | Item | Phase |
|---|---|---|
| T2.1 | Make `study-output.yaml` executable — harness that applies advisory assertions to a Section Draft Candidate in a run | Phase 5 |
| T2.2 | Implement GATE-006 — study-output fail → `review_required`; a pass changes no deterministic gate | Phase 5 |
| T2.3 | Add the "Study Output Evaluation result" contract/receipt (§11 Phase-5 contract) | Phase 5 |
| T2.4 | Rerun study-output eval for every candidate in a human redraft cycle (REVIEW-004) | Phase 8 |
| T2.5 | Eval-suite version change → new fingerprint → forces fresh qualification / superseding run | Phase 9 |

### Judge catalog — the concrete Tier-2 / behavior evals to author
Each is a specific judge or fixture set that rides the Tier-2 harness (or Tier-1 for agent-behavior). Provenance and status noted.

| ID | Judge / eval | Type | Phase | Source · status |
|---|---|---|---|---|
| **G-1** | NOAEL/LOAEL consistency (§2b) | Tier-2 `llm-rubric` | Author now (fixtures) → live Phase 5 | Colleague GLP doc v1.0 · **in scope, top priority** |
| **G-2** | Adaptive/non-adverse rationale (§2b) | Tier-2 `llm-rubric` | Author now (fixtures) → live Phase 5 | Colleague GLP doc v1.0 · in scope |
| **A-1** | Faithfulness judge — prose grounded in Validated Claims only, zero invented numbers | Tier-2 `llm-rubric` | Seed Stage 0 → live Phase 5 | Teams assurance-gap · **pending team agreement** |
| **A-2** | Bounded-path trajectory eval — cites only envelope claim IDs, registered tools only, ≤3 attempts, no unrelated-data access, no self-promotion | Tier-1 agent-behavior | Author now → validated once Phase 1 yields trajectories | Teams assurance-gap · pending |
| **A-3** | Framing/interpretation injection — adversarial fixtures inducing adversity/"treatment related"/"significant"; assert refusal | Tier-1 harden (S0.4) + Tier-2 | Stage 0 + Phase 5 | Teams assurance-gap · pending |

### Deterministic rules (tracked for completeness — validation workstream, not Promptfoo)
| # | Item | Phase |
|---|---|---|
| R-1…R-5 | Author the 5 rules as rule-bundle code + deterministic fixture tests (§2a) | Phase 3 (Data Validation Packages); R-5 overlaps today's slice |

### Ongoing
| # | Item | Phase |
|---|---|---|
| X.1 | Each new agentic section skill gets its own paired qualification suite (ADR-0021); extend coverage beyond body weight | Ongoing |
| X.2 | Keep deterministic executor/gate fixture tests as gate authority; extend per validation package | Ongoing |

## 5. Sequenced view & critical path

- **Stage 0 (now, no phase dependency):** S0.1 → S0.2 → T1.1 → T1.2, then S0.3 + S0.4. Promptfoo runs, the body-weight skill is genuinely qualified, change is enforced. Author A-1/A-3 seeds and the G-1/G-2 judges against fixtures here (Tier-1 qualification of the judges), even before Phase 5.
- **Phase 1 (Codex SDK path):** no new eval item, but it's the dependency that produces real candidates + trajectories (unblocks A-2, and live G-1/G-2/A-1).
- **Phase 2:** T1.3 + P.1 (enforce + pin).
- **Phase 3:** R-1…R-5 as deterministic rules (validation workstream).
- **Phase 5 (center of gravity):** T2.1–T2.3, P.2, and the judges go live (G-1, G-2, A-1, A-3).
- **Phase 8 / 9:** T2.4 rerun; T2.5 eval-version fingerprinting.

**Critical path:** two fronts — (a) Stage-0 qualification infra, fully unblocked, build now; (b) Tier-2 judge integration, gated on Phase 1 (a Section Agent must produce candidates before study-output evals grade anything), landing mainly in Phase 5. **Scope note:** G-1/G-2 target §5.3.3–5.3.4 and most rules span sections beyond the current body-weight PoC slice (§5.2.3); author the judges now against fixtures, but they operate once those sections exist. The A-* items stay **proposed until the team agrees**.

## 6. Verification (when built)
- `make evals` runs Tier-1 green with a bound provider; `qualification_status: passed` + id/hash recorded.
- CI fails a PR that changes the skill/suite without a passing qualification.
- (Phase 5) a planted unfaithful candidate makes the study-output eval emit `review_required` while leaving deterministic gates unchanged (GATE-006).
- (G-1) a fixture pairing Grade-3 necrosis in §5.3.3 with a NOAEL at that same group scores 0 and flags for human review without hard-blocking.
