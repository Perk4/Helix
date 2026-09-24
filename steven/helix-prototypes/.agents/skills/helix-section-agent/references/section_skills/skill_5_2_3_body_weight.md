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
6. Interpretation paragraph: how the treated groups compare to controls

## Recording Frequency Statement
"Body weights were recorded on Day 1 (pre-dose) and [weekly thereafter through Day 28 / at Weeks 4, 8, and 13]."

Use ProtocolContext for the exact schedule.

## Table Format
| Group | Day 1 | Day 7 | Day 14 | Day 21 | Day 28 |
Columns are timepoints from body_weights.csv — use the actual recorded days, not assumed.
Values are group means rounded to nearest whole gram.
Do not mark values with significance asterisks. No layer of this pipeline runs a
statistical test, so an asterisk would assert a result nothing computed.

## Interpretation Paragraph — Required Elements
- State the magnitude of each difference as percentage vs. control, computed from
  the supplied group means: "-15.0% relative to controls at Week 13"
- State which groups were comparable to controls
- Describe differences as observed, never as statistically significant, treatment
  related, or adverse. The section package lists all three as forbidden claims

## Statistical Claims
Do not state, imply, or name a statistical test. The executor supplies group means
only; it computes no variance, no group n, and no test, so the data required to
support a significance claim is not present. A statistics step belongs in
deterministic code before this skill can report its result.

## What Must Not Be Missing
- Both sexes must have their own table — never combine males and females
- All timepoints must appear in the table — do not abbreviate
- Interpretation paragraph must cover both the groups that differed and the groups
  that were comparable

## Example — Interpretation, Findings at G4 (from approved_report_2)
"At Week 13, Group 4 males were -15.0% and Group 4 females were -9.8% relative to controls. Body weights in Groups 2 and 3 were comparable to controls at all timepoints."

## Example — Interpretation, Clean Study (from approved_report_3)
"Body weight gain was comparable across all dose groups throughout the 28-day dosing period. No differences in body weight were observed in any treatment group relative to controls at any timepoint."
