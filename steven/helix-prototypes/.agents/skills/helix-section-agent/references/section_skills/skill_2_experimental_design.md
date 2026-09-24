# Skill: Section 2 — Experimental Design
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: ProtocolContext YAML frontmatter (structured fields)

## Purpose
Presents the study design as two tables plus a brief housing statement. Almost entirely deterministic — pulled from ProtocolContext structured fields. No LLM inference required for content; the agent fills the template from data.

## Structure (always in this order)
1. Parameters table (study design overview)
2. Animal Allocation table (groups × dose × sex × n)
3. One sentence: housing conditions and randomisation method

## Parameters Table — Required Rows (in this order)
Species | Strain full name from protocol
Source | Animal supplier
Age at study start
Route of administration
Dosing frequency
Study duration (in days and weeks if >7 days)
Recovery period (only if recovery groups exist)
Vehicle | Full description
Dose volume | "X mL/kg body weight"

## Animal Allocation Table — Required Columns
Group number | Treatment (name) | Dose (mg/kg/day) | Males | Females | Total
If recovery groups: add Recovery Males | Recovery Females columns
Bold the Total row

## Housing Statement (1 sentence)
"Animals were housed [X] per cage under standard conditions ([temp] ± 2°C, 12-hour light/dark cycle) with free access to certified rodent diet and water. Animals were assigned to groups by stratified randomisation based on body weight on Day 1."

## What Must Not Be Missing
- Dose volume must be stated (it is required for provenance of formulation concentration calculations)
- Recovery groups must appear in the table if present in animal_roster.csv
- Species and strain must be the full formal name, not abbreviated

## Example — Parameters Table (from approved_report_1)
| Parameter | Detail |
|---|---|
| Species | Sprague-Dawley rat (Crl:CD(SD)) |
| Source | Charles River Laboratories |
| Age at study start | 7 to 8 weeks |
| Route of administration | Oral gavage |
| Dosing frequency | Once daily, 7 days per week |
| Study duration | 28 days |
| Vehicle | 0.5% methylcellulose in purified water |
| Dose volume | 10 mL/kg body weight |

## Example — Animal Allocation Table (from approved_report_1)
| Group | Dose (mg/kg/day) | Males | Females | Total |
|---|---|---|---|---|
| 1 — Vehicle Control | 0 | 5 | 5 | 10 |
| 2 — Low Dose | 10 | 5 | 5 | 10 |
| 3 — Mid Dose | 50 | 5 | 5 | 10 |
| 4 — High Dose | 150 | 5 | 5 | 10 |
| **Total** | | **20** | **20** | **40** |
