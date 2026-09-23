# Skill: Section 5.2.2 — Clinical Observations
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: clinical_observations.csv

## Purpose
Summarises cage-side and detailed clinical examination findings per group. The observation schedule must be stated first. Then findings are reported group by group, lowest to highest dose. If a group is clean, this must be stated explicitly — not omitted.

## Structure (always in this order)
1. One sentence: observation schedule (cage-side frequency + detailed examination frequency)
2. Group 1 findings (always "no treatment-related clinical signs")
3. Group 2 findings
4. Group 3 findings
5. Group 4 findings
6. Recovery group findings (only if recovery groups present)

## Observation Schedule Statement
"Cage-side observations were recorded [twice daily / once daily] throughout the study. Detailed clinical examinations were performed [weekly / on Days 1, 7, 14, 21, and 28]."

Use ProtocolContext for the exact schedule. Default for rat oral gavage studies: cage-side twice daily, detailed weekly.

## Clean Group Template (Groups 1, 2, and often 3)
"Group [N] ([dose] mg/kg/day): No treatment-related clinical signs were observed. All animals appeared healthy and clinically normal throughout the dosing period."

## Findings Group Template (Group 4 or affected groups)
"Group [N] ([dose] mg/kg/day): [Named signs] were noted in [X of Y males and A of B females] beginning at [week/day]. [Signs] were considered [related to / unrelated to] [target organ or compound mechanism]. [Signs resolved / persisted] [at / through] [timepoint]."

## Required Elements
- Named signs — never "clinical signs were observed" — name them: "increased respiratory rate", "piloerection", "reduced activity", "soft stool"
- Incidence stated: "X of Y males"
- Onset week or day
- Resolution or persistence statement if signs occurred

## Recovery Group Addition (if applicable)
"Recovery animals (Groups [X]R and [Y]R): [Signs] resolved during the recovery period by Day [X]. No clinical signs were observed at Day [X] (Week [Y] of recovery)."

## What Must Not Be Missing
- Every group must be described — even one sentence for clean groups
- Clinical signs at G4 must name the specific signs, not summarise as "clinical findings"
- If signs resolved before necropsy, state when

## Example — Clean Group (from approved_report_3)
"Group 4 (300 mg/kg/day): No treatment-related clinical signs were observed at any cage-side or detailed clinical examination timepoint. All Group 4 animals appeared healthy and clinically normal throughout the 28-day dosing period."

## Example — Findings Group (from approved_report_2)
"Group 4 (150 mg/kg/day): Beginning at Week 6, increased respiratory rate and mild laboured breathing were noted in approximately 6 of 10 males and 4 of 10 females during detailed examinations. These signs were considered related to the pulmonary findings observed microscopically. Piloerection and reduced activity were noted in 3 of 10 males and 2 of 10 females from Week 8 onward. All clinical signs resolved during the recovery period by Day 106 (Week 2 of recovery)."
