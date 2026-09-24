# Skill: Section 4 — Deviations
# Sources: approved_report_1, approved_report_2
# Primary data source: animal_roster.csv (necropsy_type field), clinical_observations.csv

## Purpose
Documents any departure from the study protocol. This section is triggered by data — if animal_roster.csv contains rows with necropsy_type = Unscheduled, or if clinical_observations.csv contains entries flagged as deviations, Section 4 must document them. If no deviations occurred, the section states that explicitly.

## Two Possible States

### State A — No Deviations (most common)
Single sentence only:
"No protocol deviations were noted during the conduct of this study."

### State B — One or More Deviations
A table with one row per deviation, followed by a brief narrative assessment.

## Deviation Table — Required Columns
Deviation ID | Date | Description | Assessment

## Deviation ID Format
DEV-[study_id]-[sequential number]: e.g., DEV-TOX-2023-0856-001

## Description — Required Elements
- Animal ID (if animal-specific)
- Day of occurrence
- What happened (factual, not interpretive)

## Assessment — Required Elements
- Treatment-related or not
- Impact on study integrity: "No impact on study integrity or interpretation"
  or "Impact assessed; findings in affected animal excluded from group statistics"

## Tone Rules
✅ Factual and neutral — describe what happened, not who was at fault
✅ Assessment is always one of: non-treatment-related / treatment-related / no impact / impact noted
❌ Never use language implying negligence or error attribution to individuals
❌ Never omit impact assessment — every deviation must have one

## Trigger Logic (for Section Agent)
Query animal_roster.csv:
  IF any row has necropsy_type IN ('Unscheduled', 'Moribund') → State B, document each animal
  IF any row has death_date populated → State B, document each death

Query clinical_observations.csv:
  IF any row has observation_type = 'deviation' or similar flag → State B

IF no triggers → State A

## Example — State B (from approved_report_2)
| Deviation ID | Date | Description | Assessment |
|---|---|---|---|
| DEV-2023-0856-001 | Day 35 | Male M101: found moribund and euthanised. Post-mortem findings included oesophageal perforation with haemothorax, consistent with a gavage technique error. No microscopic findings attributable to compound administration were observed. | Non-treatment-related. Gavage error. No impact on study integrity or interpretation. |
