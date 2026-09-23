# Skill: Section 5.1 — Test Article Formulation and Analyses Verification
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: dosing_formulation.csv

## Purpose
Reports the results of analytical concentration verification of dosing formulations. This is a pass/fail section — it states what was checked, when, and whether it met acceptance criteria. Content is deterministic from dosing_formulation.csv.

## Structure (always in this order)
1. When samples were collected (days, from dosing_formulation.csv or ProtocolContext.formulation_check_days)
2. What the acceptance criteria were
3. Pass/fail outcome — all pass (typical) or flag any failure
4. Vehicle control statement (no test article detected)
5. Closing confirmation sentence

## Required Elements
- Specific days or timepoints when samples were collected
- Acceptance criterion stated explicitly: "within ±10% of nominal target concentration"
- Result: all passed or named exceptions
- Vehicle control confirmed negative for test article

## Pass Template (most common)
"Dosing formulation samples were collected and analysed on Days [X, Y, Z]. All measured concentrations were within ±10% of the nominal target concentration. No test article was detected in vehicle control formulations. All dosing formulations met the predefined acceptance criteria."

## Fail Template (rare — document specifically)
"Dosing formulation samples were collected and analysed on Days [X, Y, Z]. The formulation for Group [N] collected on Day [Z] had a measured concentration of [X] mg/mL vs. a nominal [Y] mg/mL (deviation: [Z]%). This deviation was assessed by the Study Director and determined to have [no impact / a potential impact] on study integrity. All other formulations met the predefined acceptance criteria."

## What Must Not Be Missing
- Days of collection must be stated — not just "samples were collected"
- Acceptance criterion must be stated — not just "criteria were met"
- Vehicle control result must be explicitly stated

## Data Extraction from dosing_formulation.csv
Required columns: check_day, group_number, nominal_conc_mgml, measured_conc_mgml, result (PASS/FAIL)
Agent calculates percentage deviation = ((measured - nominal) / nominal) × 100
All PASS rows → use Pass Template
Any FAIL row → use Fail Template for that row

## Example (from approved_report_3)
"Dosing formulation samples were collected and analysed on Days 1 and 28. All measured concentrations were within ±10% of the nominal target concentration. No test article was detected in vehicle control formulations. All dosing formulations met the predefined acceptance criteria."
