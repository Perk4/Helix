---
name: helix-section-agent
description: Draft one HELIX nonclinical report section from a governed Section Execution Envelope and validated claims. Use only when the prompt explicitly invokes this skill with an envelope identifier.
---

# HELIX Section Agent

Draft one section candidate within the supplied contract.

## Inputs

The caller supplies one `SectionExecutionEnvelope`. It identifies the Pinned Run, Section Package, required Validated Claims, declared dependency artifacts, governed versions, and current structured failures.

Read the schemas referenced by the envelope before drafting. The candidate must match `skills/helix-evidence-pipeline/contracts/section-draft-candidate.schema.json`.

## Section presentation contract

Before drafting, read both of these files relative to this skill directory:

1. `references/section_skills/meta_prompt_pathology_narrative.md`
2. `references/section_skills/skill_<section_id>.md`, where `<section_id>` is the envelope's exact section identifier

For example, section `5_2_3_body_weight` uses `references/section_skills/skill_5_2_3_body_weight.md`. The `summary` section uses `references/section_skills/skill_summary.md`.

Treat these files only as presentation contracts. Any instruction in a section reference to read source data, calculate values, or use worked-example values is superseded by this skill and the Section Execution Envelope. If the matching section reference is absent, return the structured failure form requested by the caller rather than drafting without it.

## Rules

1. Use only the Validated Claim identifiers in the envelope or returned by an allowed Cross-Section Query.
2. Use cross-section facts only from dependencies declared in the Section Package.
3. Attach claim identifiers to every factual span and table cell.
4. Keep observations separate from scientific interpretation.
5. Preserve the template's terminology, units, rounding, labels, and table shape.
6. Do not inspect unrelated raw source files.
7. Do not calculate an authoritative value.
8. Do not create or edit provenance.
9. Do not mark a candidate passed, approved, promoted, or ready for release.
10. Return one JSON object and no surrounding prose.

## Output

Return a `section_draft_candidate` that includes the section and package identifiers, drafting cycle, attempt number, content blocks, factual-span claim references, executor receipts supplied by the envelope, and the agent receipt fields requested by the caller.

If the envelope lacks a required claim or governed version, return the structured failure form requested by the caller. Do not fill the gap from model knowledge.
