# Skill: Section 5.2.3 — Body Weight
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: body_weights.csv

## Purpose
Reports group mean body weights across the dosing period using tables, then interprets the data in 1–2 narrative sentences. Content is deterministic from body_weights.csv — the LLM does not calculate, it receives pre-calculated group means from the Section Agent's CSV extraction step.

## Structure (always in this order)
1. One sentence: recording frequency and timepoints
2. Bold label: "Male Mean Body Weights (g):"
3. Male body weight table
4. Bold label: "Female Mean Body Weights (g):"
5. Female body weight table
6. Interpretation paragraph: what was significant vs. what was comparable

## Recording Frequency Statement
"Body weights were recorded on Day 1 (pre-dose) and [weekly thereafter through Day 28 / at Weeks 4, 8, and 13]."

Use ProtocolContext for the exact schedule.

## Table Format
| Group | Day 1 | Day 7 | Day 14 | Day 21 | Day 28 |
Columns are timepoints from body_weights.csv — use the actual recorded days, not assumed.
Values are group means rounded to nearest whole gram.
Mark statistically significant values with asterisk: 326* and footnote: *p < 0.01 vs. control (Dunnett's test)

## Interpretation Paragraph — Required Elements
- State which groups showed statistically significant differences and at what timepoint
- State the magnitude of the difference as percentage vs. control: "−15.0% relative to controls at Week 13"
- State which groups showed no differences: "No statistically significant differences in body weight were observed in Groups 2 or 3 at any timepoint"
- If no differences at any group: single sentence: "Body weight gain was comparable across all dose groups throughout the dosing period. No statistically significant or biologically meaningful differences were observed at any timepoint."

## Statistical Note Format
"*p < 0.01 vs. control (Dunnett's test)" — always name the test

## What Must Not Be Missing
- Both sexes must have their own table — never combine males and females
- All timepoints must appear in the table — do not abbreviate
- Interpretation paragraph must state both what was significant AND what was not

## Example — Interpretation, Findings at G4 (from approved_report_2)
"At Week 13, Group 4 males were −15.0% and Group 4 females were −9.8% relative to controls. No statistically significant differences in body weight were observed in Groups 2 or 3 at any timepoint."

## Example — Interpretation, Clean Study (from approved_report_3)
"Body weight gain was comparable across all dose groups throughout the 28-day dosing period. No statistically significant or biologically meaningful differences in body weight were observed in any treatment group relative to controls at any timepoint. The body weight data indicate no treatment-related effect on body weight at any dose level tested."
