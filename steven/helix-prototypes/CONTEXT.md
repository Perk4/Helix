# HELIX Evidence Pipeline

This context defines the language for HELIX's traceable nonclinical-report prototype. Its purpose is to keep evidence retrieval, deterministic evidence processing, and report drafting distinct.

## Evidence and drafting

**Embedding**:
A retrieval-only representation of validated, normalized evidence. Embedding is outside the current pipeline scope; if restored later, unvalidated material cannot enter the index, and retrieval cannot supply, calculate, or override a report value.
_Avoid_: source of truth, calculated evidence, unvalidated discovery index

## Validation and gates

**Rule Bundle**:
A versioned collection of executable deterministic rules whose recorded results may affect section and release gates.
_Avoid_: validation skill, prompt suite

**Prompt Evaluation**:
Regression evidence that a prompt or drafting skill behaves as intended. It may qualify a prompt version but cannot satisfy a deterministic rule or change a gate decision.
_Avoid_: release gate, validation authority

**Skill Qualification**:
The recorded result of running an agentic skill version's complete paired Promptfoo suite before that version is eligible for use in a pinned run. Deterministic executors use ordinary code and fixture tests instead.
_Avoid_: study validation, runtime gate

**Study Output Evaluation**:
An advisory Promptfoo evaluation of content produced within a pinned run. A failure creates `[NEEDS REVIEW]`, while a pass cannot satisfy a deterministic gate.
_Avoid_: deterministic validation, gate approval

**Pinned Run**:
A study-processing execution bound to exact manifest, schema, ontology, rule-bundle, drafting-skill, and prompt-evaluation-suite versions for its entire lifetime.
_Avoid_: latest-version run, mutable run

**Run Request**:
The idempotent event emitted when an authorized manifest is frozen. Replaying it resumes or returns the existing Pinned Run for that manifest rather than creating a duplicate.
_Avoid_: duplicate trigger, mutable job request

**Superseding Run**:
A new pinned run that names an immutable predecessor and records why replacement inputs or governed versions were required. The predecessor's results, artifacts, decisions, and audit history remain preserved.
_Avoid_: amended run, overwritten run

**Dependency Fingerprint**:
A content-derived identity covering every source and governed version that can affect an artifact, including schema, ontology, rules, drafting skill, template, and prompt-evaluation qualification.
_Avoid_: file timestamp, partial version list

**Carried-Forward Artifact**:
An unchanged artifact reused by a superseding run only when its dependency fingerprint is identical, with explicit lineage to the predecessor artifact. The new run still records fresh validation results and gate decisions.
_Avoid_: copied result, assumed-valid output

**Mapping Proposal**:
A quarantined suggestion for representing source data that the pinned schema or ontology does not recognize. It has no evidentiary or gate authority until an authorized person approves a new governed version and the study is rerun.
_Avoid_: automatic schema update, inferred mapping

**Study Type Resolution**:
The deterministic classification of a study from pinned protocol fields through a versioned mapping table.
_Avoid_: inferred study pattern, free-form classification

## Report assembly

**Study Context Snapshot**:
An immutable, run-scoped view of validated claims, terminology, gate states, and evidence references across the entire study. It supports cross-section consistency but cannot lend evidence or validation authority from one section to another.
_Avoid_: mutable study context, shared section evidence

**Review Scaffold**:
A non-exportable, versioned study-wide artifact showing the current state of every report section, cross-section context, blocking results, and explicit `[NEEDS REVIEW]` placeholders. A deterministic shared assembler is its sole producer.
_Avoid_: section result, draft report, incomplete final report

**Review Scaffold Revision**:
An immutable member of a pinned run's append-only Review Scaffold history, created only when scaffold-visible state changes. It carries a monotonic sequence, content hash, timestamp, triggering event, predecessor, and the section artifacts from which it was assembled.
_Avoid_: overwritten scaffold, mutable review document

**Section Draft Candidate**:
A schema-conforming proposal emitted by a Section Agent for one eligible section after that section's blocking deterministic and Template Contract Gates pass. It carries claim, provenance, executor, and prompt-evaluation references but has no gate or approval authority.
_Avoid_: review scaffold, approved section, passed section

**Candidate Attempt**:
One immutable Section Draft Candidate and its executor receipts within a bounded drafting cycle. A section may have at most three attempts, and retries may change only wording, structure, and claim placement while all evidence and governed versions remain fixed.
_Avoid_: overwritten candidate, unlimited retry

**Human-Directed Revision**:
A request to redraft a selected section or change its components or tone without rerunning unaffected sections. It starts a new, separately audited drafting cycle of at most three Candidate Attempts, each subject to provenance, study-output evaluation, and template conformance checks.
_Avoid_: direct draft edit, export-time rewrite

**Section Draft**:
A section artifact promoted from a Section Draft Candidate after its Template Conformance Gates pass. It remains subject to human review before final export.
_Avoid_: review scaffold, section draft candidate, approved section

**Section Promotion**:
The deterministic conversion of a Section Draft Candidate into a Section Draft when no Hard Blocker exists, every Review Required result has a current disposition, and provenance and template conformance pass. Warnings remain visible but do not prevent promotion.
_Avoid_: agent approval, implicit draft status

**Template Contract Gate**:
A pre-draft check that the pinned template defines a section's required fields, locations, table shapes, controlled labels, units, and style constraints in a parseable contract.
_Avoid_: output inspection, post-draft template gate

**Template Conformance Gate**:
A post-draft check that a Section Draft Candidate satisfies the pinned template contract, including completeness, table coverage, terminology, units, rounding, and approved-language constraints.
_Avoid_: template readiness check, drafting instruction

**Section Package**:
A governed reference contract declaring a report section's required inputs, dependencies, rule IDs, output schema, Template Contract Gates, Template Conformance Gates, drafting constraints, and paired prompt evaluations. An autonomous agent uses the package, while shared executors perform parsing, validation, drafting, and gating.
_Avoid_: autonomous validator, duplicated executor

**Section Agent**:
A versioned autonomous runtime instantiated independently for one report section and configured by that section's package. Instances share one orchestration protocol and executor set and may run concurrently when their declared dependencies permit.
_Avoid_: bespoke section agent, section-specific runtime

**Run Orchestrator**:
The coordinator that instantiates eligible Section Agents from the dependency graph and collects their structured results. It has no authority to calculate or override section or study release gates.
_Avoid_: release authority, gate evaluator

**Run Plan**:
The immutable, versioned dependency graph materialized for one Pinned Run from the applicable package declarations. It is stored with the Study Evidence Package and executed by the Run Orchestrator.
_Avoid_: agent prompt, transient SDK state

**Section Execution Envelope**:
The section-scoped context delivered to one Section Agent through governed tools, containing only its package, direct dependency states and hashes, required Validated Claims, relevant study context, and current structured failures.
_Avoid_: full Run Plan, full Study Evidence Package

**Cross-Section Query**:
An audited, on-demand request by a Section Agent for canonical study facts, Validated Claims, or Section Drafts from dependencies declared in its Section Package. The response records exact artifact hashes and excludes unrelated raw study data.
_Avoid_: unrestricted study browsing, raw-data lookup

**Section Impact Set**:
The directly affected sections and every transitive dependent identified when evidence is missing, invalid, or requires a source change outside the frozen manifest. Sections outside this set may continue processing, but the study remains blocked from release.
_Avoid_: whole-report invalidation, informal affected list

**Study Release Blocker**:
A recorded condition that prevents final study release without necessarily halting valid work on independent sections.
_Avoid_: pipeline stop, section failure

**Hard Blocker**:
A validation failure that cannot be waived and must be corrected before the affected artifact can progress.
_Avoid_: review item, warning

**Review Required**:
A validation outcome that blocks progression until an Artifact-Bound Disposition resolves it.
_Avoid_: hard failure, optional warning

**Warning**:
A visible validation outcome that does not block progression.
_Avoid_: blocker, required disposition

## Workspace UI

**Workspace Journey**:
The one-page study workspace organized as nine ordered stages. The Progress Bar selects which reached stage the user reviews, while progress itself changes only through authorized gate actions or recorded agent events.
_Avoid_: tab set, side navigation, view mode

**Human Gate**:
A Workspace Journey stage that waits for an explicit qualified-person action before the study can progress. An agent may stop at a Human Gate and expose evidence, but it cannot pass the gate.
_Avoid_: agent approval, automatic gate pass

**Agent Step**:
A Workspace Journey stage that runs between Human Gates from recorded run events. The UI may show live activity and pause or resume controls, but the backend remains the authority for run state.
_Avoid_: simulated production progress, client-owned workflow state

**Traceability Review**:
The Human Gate where validation results, evidence lineage, and blocker dispositions are reviewed before report review starts.
_Avoid_: evidence tab, optional evidence inspection

**Review and Export Gate**:
The final Human Gate where role sign-offs and the separate export action are completed for the exact approved package.
_Avoid_: combined approval export, FDA approval

## Workflow trace

**Workflow Trace**:
An ordered, run-scoped view of Human Gates, deterministic executors, Skill Invocations, evaluations, and artifact transitions. It is derived from immutable Step Receipts and has no gate authority.
_Avoid_: activity animation, client progress, audit authority

**Step Receipt**:
An immutable, content-addressed record of one workflow-step attempt and its exact inputs, outputs, executor or skill identity, authority class, status, and parent receipt.
_Avoid_: mutable step state, log line

**Skill Invocation**:
One agent turn explicitly bound to a reviewed skill version and a scoped input envelope. A Skill Invocation may propose an artifact but cannot create evidence or decide a deterministic gate.
_Avoid_: arbitrary prompt, user-selected plugin

**Evaluation Artifact**:
An immutable result from Skill Qualification or Study Output Evaluation, bound to the exact evaluated artifact, suite, rubric, and evaluator versions. It is advisory and cannot satisfy a deterministic rule.
_Avoid_: gate result, unversioned score

## Review and approval

**Artifact-Bound Disposition**:
A human review decision bound to an exact Section Draft hash and Review Scaffold Revision. It becomes stale when the section or any declared dependency changes.
_Avoid_: floating approval, latest-version approval

**Final Study Approval**:
A human approval bound to the exact release-candidate manifest and every included artifact hash. It becomes stale when any included artifact changes.
_Avoid_: study-wide standing approval, mutable approval

## Provenance

**Validated Claim**:
A normalized factual or numeric assertion that passed its deterministic rules and carries upstream provenance to frozen source records and transforms.
_Avoid_: retrieved statement, drafted fact

**Data Validation Package**:
A governed, versioned contract for one canonical evidence domain, such as protocol, animal roster, formulation, body weight, organ weight, or pathology. It produces reusable Validated Claims that Section Packages reference rather than recalculate.
_Avoid_: section validator, duplicated report calculation

**Provenance Compiler**:
A shared deterministic service that binds every factual statement and table cell in a Section Draft Candidate to existing Validated Claims and rejects unsupported content. It cannot create evidence or accept agent-authored provenance.
_Avoid_: provenance generator, evidence inference

**Provenance Blocker**:
A non-waivable failure caused by a factual statement or table cell without complete lineage to a Validated Claim. Resolution requires removal, an existing supported claim, or authorized data in a superseding run.
_Avoid_: reviewable provenance gap, inferred citation
