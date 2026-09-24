# Skill: Section 1 — Objective
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: ProtocolContext (protocol .md frontmatter + body)

## Purpose
States the scientific and regulatory purpose of the study. The content comes almost entirely from the protocol — not from the CSV study data. The Section Agent extracts language from the protocol's Objective section and adapts it into the approved report format.

## Structure (always in this order)
1. Four-part numbered objective statement (standard across all GLP studies)
2. Compound description sentence: what it is, what it targets, why those organs were chosen
3. Dose selection rationale: reference to prior range-finding study and dose selection logic

## Required Elements
- All four standard GLP objectives (evaluate toxicity / characterise findings / identify target organs / establish NOAEL)
- Compound class or mechanism of action (from protocol)
- Primary and secondary target organs (from protocol target_organs field)
- Dose selection basis (from protocol Objective section)
- GLP compliance statement

## Standard Four-Part Objective (use this template, fill in compound name and duration)
"The objectives of this study were to: (1) evaluate the potential toxicity of Compound [NAME] following repeated oral gavage administration to Sprague-Dawley rats for [DURATION]; (2) characterise the nature, severity, and dose-response relationship of any treatment-related effects; (3) identify any target organs of toxicity; and (4) establish a no-observed-adverse-effect level (NOAEL) to support further development. The study was conducted in compliance with Good Laboratory Practice (GLP) regulations."

## Length
2 paragraphs. Paragraph 1: the four objectives + GLP statement. Paragraph 2: compound background + dose selection rationale.

## Example (from approved_report_3)
"The objectives of this study were to: (1) evaluate the potential toxicity of Compound BM-341 following repeated oral gavage administration to Sprague-Dawley rats for 28 consecutive days; (2) characterise the nature, severity, and dose-response relationship of any treatment-related effects; (3) identify any target organs of toxicity; and (4) establish a no-observed-adverse-effect level (NOAEL) to support further development. The study was conducted in compliance with Good Laboratory Practice (GLP) regulations.

Compound BM-341 is a novel small-molecule inhibitor of a renal proximal tubular transporter under development for the treatment of metabolic syndrome. Based on the mechanism of action and the renal tubular target, the kidney was designated as the organ of primary interest. Bone marrow was identified as a secondary organ of interest based on in vitro haematopoietic assay data. The doses of 15, 75, and 300 mg/kg/day were selected based on the no-effect level and supratherapeutic multiples established in a 7-day dose range-finding study, in which no adverse findings were observed up to 300 mg/kg/day."
