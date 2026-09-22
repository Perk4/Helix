# HELIX — Nonclinical Safety Report Automation
### Comprehensive Spec Sheet

---

## Problem Statement

Nonclinical safety studies generate 6-8 disconnected data files across different systems and formats. The study pathologist manually reconciles every number against its source, writes prose around verified values, and cross-checks each figure against raw data — a clerical process consuming 5-6 weeks per study. One untraced value requires a formal report amendment under GLP (Good Laboratory Practice). Scientific judgment — interpreting findings, determining NOAEL, characterizing toxicity — is blocked until the clerical work is complete. The data already contains the answer; the process does not.

---

## Current Process (end to end)

```
Study ends (Day 29 necropsy)
      │
      ▼
Data lock  (~1-2 weeks post-study)
  ├── LIMS export: body weights, clinical observations, dosing records
  ├── Excel: organ weights + manually calculated ratios
  ├── Histopath system (Provantis): pathologist reads slides, enters findings
  ├── Statistician: ANOVA/Dunnett's output — SAS or JMP, separate file
  ├── HPLC lab: formulation verification results
  └── Study director: protocol deviations log finalized
      │
      ▼
Report authoring  (4-6 weeks) ← primary bottleneck
  ├── Pathologist opens 6-8 files simultaneously
  ├── Copies values into Word template section by section
  ├── Manually writes provenance cross-references
  ├── Writes prose narrative around verified values
  ├── Flags gaps informally — no systematic coverage check
  └── Peer review pathologist reads slides independently
      │
      ▼
QA audit  (1-2 weeks)
  └── GLP QAU re-traces every value in the report to raw data
      │
      ▼
Final report issued and signed
      │
      ▼
SEND dataset prepared separately  (2-4 weeks)
  └── Data manager rebuilds structured electronic dataset for FDA submission
      │
      ▼
Archive  (GLP: life of compound + 2 years post-marketing approval)
```

**Total elapsed: 3-4 months from study end to final report. Authoring alone: 5-6 weeks.**

---

## Pain Points

| Pain point | Consequence |
|---|---|
| 6-8 disconnected source files in different formats | Pathologist manually context-switches; copy-paste boundaries introduce errors |
| No automated provenance | Every value manually verified against raw data; QA unit re-derives the same provenance |
| Grain errors invisible to exact-match | Per-group N=10 written instead of sex-stratified N=5; passes a manual check, fails a GLP audit |
| Version control on Excel files | Which organ weight file is the locked version — the source of truth is ambiguous |
| Report amendment cost | One wrong value restarts the QA cycle; formal GLP amendment event required |
| SEND dataset disconnected from report | Data manager rebuilds what the report already contains — duplicate effort, additional delay |
| Histopath section complexity | 40 animals × 20+ tissues × finding + severity grade = hundreds of manual entries per study |
| NOAEL determination blocked | Scientific judgment cannot begin until all data is compiled and verified; the bottleneck is clerical |

---

## Regulatory Requirements and Guardrails

| Framework | What it governs | Impact on HELIX |
|---|---|---|
| **21 CFR Part 58** (FDA GLP) | Every data point must trace to raw data; audit trail mandatory; no inferred values | Provenance trail is a GLP artifact, not a UX feature — logged at every extraction |
| **OECD Principles of GLP** | International harmonized equivalent; mutual acceptance of data | Same traceability requirement; applies to non-US submissions |
| **OECD TG 407** | Required endpoints for 28-day oral rodent study | Defines required sections and content — feeds validation rules schema |
| **ICH S4** | Study duration and design requirements | Defines what study types require what report depth |
| **SEND (CDISC)** | FDA electronic submission standard for nonclinical data | Input schema AND output format — if data is SEND-formatted, corpus ingest is deterministic |
| **IACUC / Animal Welfare Act** | Animal care and use protocols; 3Rs (Replace, Reduce, Refine) | Does not affect report format; N per group and species choices must be defensible — HELIX reports, does not set these |

**HIPAA does not apply.** Study data is proprietary sponsor data — not protected health information. Relevant governance is GLP confidentiality (access-controlled, archived per study retention schedule).

---

## Data Sources (full taxonomy)

### Type 1 — Regulatory requirements
*Baked into validation rules schema at build time. Answer: "Is this field required, and what makes a value acceptable?"*

- 21 CFR Part 58 (FDA GLP) — traceability and audit trail requirements
- OECD TG 407 — required endpoints for 28-day oral rodent study
- ICH S4 — duration and design requirements
- FDA Guidance: Nonclinical Safety Evaluation — section content requirements
- SEND Controlled Terminology (CDISC) — standardized finding names, tissue names, severity grades

### Type 2 — Report template
*Runtime input. HELIX reads this to know which sections exist and what each must contain. The fixed workflow shell.*

- Sponsor-approved report template (docx) — section headers, required subsections, boilerplate
- Section content checklist derived from TG 407 + FDA guidance
- Statistical methods specification (which test applies to which endpoint)

Adding a study type = dropping in a new template. No new code path.

### Type 3 — Study design artifacts
*Define this specific study — planned vs. executed.*

- Study protocol — dose groups, N per group, endpoints, statistical methods, schedule
- Protocol amendments — any deviations from original; GLP-required to report
- Certificate of Analysis — compound identity, purity, batch number
- Randomization records — animal-to-group assignment documentation
- Deviations log — GLP-required record of protocol departures

### Type 4 — Study execution data
*Primary number sources. Structured by SEND domain.*

| SEND Domain | Content | Grain |
|---|---|---|
| `DM` — Demographics | Animal ID, group, sex, dose level | Per animal |
| `BW` — Body weights | Weight per timepoint (Days 1, 7, 14, 21, 28) | Per animal × timepoint |
| `EX` — Exposure | Dose administered, volume, per animal per day | Per animal × day |
| `CL` — Clinical observations | Finding, severity, timepoint | Per animal × day |
| `FW` — Food consumption | Weekly consumption | Per group × week (not individual) |
| `OM` — Organ weights | Absolute weight + body and brain ratios | Per animal (paired organs = one record) |
| `MA` — Macroscopic findings | Gross lesion, tissue, size | Per animal × finding |
| `MI` — Microscopic findings | Tissue, finding, severity grade (1-5) | Per animal × tissue |
| `PC`/`PP` — Formulation | HPLC concentration results | Per concentration × timepoint |
| `DS` — Disposition | Mortality, euthanasia, survival | Per animal |
| Statistical output | ANOVA/Dunnett's, KW/Dunn's, Fisher's exact tables | Per endpoint × group comparison |

### Type 5 — Pattern corpus (approved prior reports)
*What good looks like for this study type. Powers Pattern RAG.*

- 2-5 approved, signed reports of the same study type
- Same sponsor preferred — house style and regulatory vocabulary already accepted
- Teaches: section structure, prose conventions, NOAEL framing, severity-grade language
- The hardest input to acquire; the highest-value one

### Type 6 — External reference databases
*Authority-checking context — is this finding biologically meaningful or within normal range?*

| Database | Role |
|---|---|
| **Historical control database** (lab's own) | Baseline ranges for SD rats — required to contextualize organ weight shifts and histopath incidences |
| **ToxRefDB** (EPA) | Public repeat-dose toxicity reference — NOAEL plausibility check |
| **RepDose / eTOX** | Historical cross-compound toxicity data — cross-study comparison |
| **ChemIDplus / PubChem** | Compound identity verification against CoA |

---

## Source Authority Hierarchy

```
Tier 1 (highest)  Validated study data — locked LIMS export, signed HPLC results
Tier 2            Study protocol + CoA — sponsor-approved design documents
Tier 3            Approved prior reports — peer-reviewed, signed
Tier 4            Historical control database — lab-validated reference ranges
Tier 5            External public databases — ToxRefDB, RepDose
Tier 6 (lowest)   Draft / unvalidated outputs — interim data, in-use formulations
```

A NOAEL supported only by a Tier 6 draft source → [NEEDS REVIEW]. A body weight value from a Tier 1 locked export → fills with provenance citation.

---

## Solution: HELIX

A bounded agent. The report skeleton is fixed by regulation — HELIX follows it exactly. Agency lives inside each mandated section.

```
For each required field in each section:
  1. Decide    → which source (by type + authority tier) satisfies this field?
  2. Extract   → deterministic tool call against corpus (CSV lookup or Pattern RAG)
  3. Validate  → grain check + authority check + exact-match
  4. Reflect   → is this defensible? re-work or escalate
  5. Output    → fill with provenance citation, or flag [NEEDS REVIEW] with reason

Coverage gate → blocks assembly until every required field is filled or flagged
Human gate    → scientist reviews and signs; nothing finalizes without it
```

### Agent harness

| Component | What it does |
|---|---|
| **Orchestrator** | Manages section-by-section loop; tracks state (filled / [NEEDS REVIEW] / pending); enforces coverage gate and human gate |
| **Tool registry** | Defines which tools the agent can call: CSV lookup, Pattern RAG, validation functions. Agent selects; harness executes |
| **Observability / audit log** | Every tool call, extraction decision, validation result, timestamp logged. GLP audit trail as a byproduct of execution |
| **Eval harness** | Runs agent against labeled gold-standard study + approved report pairs; scores extraction accuracy, grain, authority, coverage, [NEEDS REVIEW] precision/recall |

### Ontology and schema

**Ontology** — the domain model shared across all report types:
`Study → DoseGroup → Animal → Endpoint → Finding → Source → Field → Section → AuthorityTier → Grain`

**Schema** — three contracts:
- Corpus schema: every number indexed with `source_id, authority_tier, table, row, column, value, grain_level`
- Report schema: `field_id, required, expected_grain, value, status, source_id, validated_at`
- Validation rules: `field_id → expected_grain, min_authority_tier, allowed_source_types`

---

## Data Outputs

| Output | Who uses it | Notes |
|---|---|---|
| **Draft nonclinical study report** | Study pathologist (review + sign) | Every section filled or [NEEDS REVIEW] flagged |
| **Provenance trail** | QAU, regulatory agencies | Per value: SEND domain + record ID + variable + authority tier |
| **Lineage coverage %** | Study director, QAU | Fraction of required fields with validated provenance |
| **[NEEDS REVIEW] log** | Study pathologist | Gaps and conflicts with reason code — replaces informal gap tracking |
| **GLP audit log** | QAU, regulatory agencies | Machine-readable; every tool call and decision timestamped |
| **SEND dataset** | FDA electronic submission | Byproduct of same extraction run — not a separate rebuild |
| **Pathology report** (sub-report) | Study director, peer reviewer | Histopath section exportable independently |

---

## Before vs. After

```
Current:    Data lock → [5-6 weeks manual authoring] → Draft → Peer review → QA → Final
                                                                     3-4 months total

With HELIX: Data lock → [<2 min agent draft + provenance trail]
                      → Scientist reviews findings, not transcription
                      → Peer review: slides only, values pre-verified
                      → QA: works from generated audit log, not re-derivation
                      → Final
                      → SEND dataset: byproduct, no separate rebuild
```

**PoC:** one study type end to end.
**North star:** fleet engine across N report types — router selects template, corpus slice, and filing adapter at runtime. Adding a study type = drop in approved examples, no new code.
