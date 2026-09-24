# Skill: Section 5.3.4 — Conclusion
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: derived from 5.3.3 adversity classifications

## Purpose
The most consequential section in the report. States the NOAEL and LOAEL and links them explicitly to the findings described in 5.3.3. The NOAEL/LOAEL values are derived by logic from the adversity classifications made in the microscopic findings section — not re-determined here. This section must be internally consistent with 5.3.3 (G-1 guardrail).

## Structure (always in this order)
1. Overall adverse/non-adverse statement ("No adverse findings" OR "Adverse findings at [dose]")
2. NOAEL statement — bold, with units
3. LOAEL statement (or "No LOAEL established") — bold
4. For each finding classified as adaptive: one sentence explaining why it is not adverse
5. For each finding classified as adverse: one sentence referencing it

## NOAEL Derivation Logic
NOAEL = highest dose group where ALL findings are classified as non-adverse or absent
LOAEL = lowest dose group where ANY finding is classified as adverse
If no adverse findings at any dose: NOAEL = highest dose tested, no LOAEL

## NOAEL Statement Templates

All doses clean:
"The no-observed-adverse-effect level (NOAEL) for Compound [NAME] under the conditions of this study is **[dose] mg/kg/day**, the highest dose tested. No lowest-observed-adverse-effect level (LOAEL) was established."

Findings at high dose:
"The NOAEL for Compound [NAME] is **[dose] mg/kg/day**. The LOAEL is **[next dose] mg/kg/day**, based on [named finding(s)] observed at that dose."

## Adaptive Finding Rationale (one sentence per finding)
"The [finding] observed at [dose] and [dose] is considered an adaptive cellular response based on: (1) [criterion]; (2) [criterion]; (3) [criterion if available]."

Minimum 2 criteria required (G-2 guardrail). Common criteria:
  - absence of [necrosis / degeneration / cast formation]
  - no macroscopic correlate
  - no statistically significant organ weight change
  - low incidence / low grade
  - consistency with a known pharmacological mechanism

## Adverse Finding Reference (one sentence per finding)
"The [finding] observed in Group [N] animals is considered treatment-related and adverse, as described in Section 5.3.3."

## What Must Not Be Missing
- NOAEL must be stated as a number with units — never "a NOAEL was established"
- NOAEL must be linked to which dose had no adverse findings
- Every adaptive finding must have explicit criteria (not just "considered adaptive")
- LOAEL must name the finding that triggered it

## Example — NOAEL = Highest Dose (from approved_report_3)
"No adverse treatment-related findings were identified at any dose level tested in this study. The no-observed-adverse-effect level (NOAEL) for Compound BM-341 under the conditions of this study is **300 mg/kg/day**, the highest dose tested. No lowest-observed-adverse-effect level (LOAEL) was established.

The minimal to mild renal tubular basophilia observed at 75 and 300 mg/kg/day is considered an adaptive cellular response to the pharmacological activity of BM-341 at the proximal tubular transporter target. This finding is not considered adverse based on: (1) absence of tubular degeneration or necrosis; (2) absence of cast formation or inflammatory infiltrate; (3) no adverse macroscopic renal correlate; (4) no statistically significant organ weight change; and (5) consistency with a well-characterised adaptive response to transporter inhibition in this species."

## Example — NOAEL = Low Dose, LOAEL = Mid Dose (from approved_report_2)
"The NOAEL for Compound LF-892 is **10 mg/kg/day**. The LOAEL is **50 mg/kg/day**, based on minimal pulmonary macrophage accumulation observed in 2 of 10 males at that dose.

Compound LF-892 caused treatment-related adverse effects at 150 mg/kg/day, characterised by pulmonary macrophage accumulation with inflammation, hepatic centrilobular vacuolisation, and thymic lymphoid depletion. All findings showed partial to complete reversal following a 4-week recovery period."
