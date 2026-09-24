# Skill: Section 5.3.1 — Organ Weights
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: organ_weights.csv

## Purpose
Reports terminal organ weights as tables (absolute values) then summarises notable differences in a narrative paragraph. All values come from organ_weights.csv — the LLM receives pre-calculated group means. The narrative interprets which changes are notable and their biological context.

## Structure (always in this order)
1. One sentence: when organ weights were recorded
2. Bold label: "Male Absolute Organ Weights (g) — Group Means:"
3. Male organ weight table
4. Bold label: "Female Absolute Organ Weights (g) — Group Means:"
5. Female organ weight table
6. Interpretation paragraph

## Recording Statement
"Terminal organ weights were recorded at scheduled necropsy on Day [X]."

## Table Format
| Organ | G1 Control | G2 Low | G3 Mid | G4 High |
Rows = organs. Values = group means to 2 decimal places.
Mark significant values with asterisk (*).
Footnote: *p < 0.01 vs. control (Dunnett's test)

## Organ Row Order (standard, omit if not weighed)
Liver | Kidneys (paired) | Heart | Brain | Spleen | Thymus | Adrenal glands | Lungs

## Interpretation Paragraph — Required Elements
For each organ with a notable difference (>10% or statistically significant):
  "The [organ] showed a [direction] in Group [N] ([magnitude]% vs. [value] g control; [direction][pct]%). [These differences / This difference] [did not reach / reached] statistical significance (p [>/=] 0.05, Dunnett's test)."

If no changes:
  "All organ weights were comparable across all dose groups for both sexes. No statistically significant or biologically meaningful differences were observed."

## Significance + Biology Rule
- State significance result for all organs with ≥10% difference
- Note absence of macroscopic or clinical correlate for non-significant increases ("not associated with adverse macroscopic or clinical correlates")
- Note correlates for adverse organ weight changes ("in the context of associated microscopic findings")

## What Must Not Be Missing
- Both sexes must have their own table
- Must state significance result (not just the magnitude)
- Must note correlate status for any organ weight increase at affected doses

## Example — Notable Finding (from approved_report_2)
"Lung weight increases at G4: +24.9% males, +28.1% females. Liver weight increases at G4: +22.6% males, +23.2% females. Thymus weight decreases at G4: −35.0% males, −37.2% females. Kidney weights were unaffected at all dose levels."

## Example — Clean/Minor Finding (from approved_report_3)
"Kidney weights showed a slight increase in Group 4 males (2.33 g vs. 2.20 g control; +5.8%) and females (1.62 g vs. 1.54 g control; +5.2%). These differences did not reach statistical significance (p > 0.05, Dunnett's test) and were not associated with adverse macroscopic or clinical correlates. All other organ weights were comparable across all dose groups for both sexes."
