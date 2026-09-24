# Skill: Section 3 — Materials and Methods
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: ProtocolContext (frontmatter + body text)

## Purpose
Documents how the study was conducted. Content is drawn from the protocol. This section uses future-in-past tense ("formulations were prepared", not "will be prepared") because the study is complete. The Section Agent converts protocol language from future tense to past tense.

## Subsections Required (in this order)
3.1 Test Article
3.2 Vehicle
3.3 Test System
3.4 Dose Formulation Verification
3.5 Terminal Procedures
3.6 Histology and Histopathology
3.7 Statistical Analysis

## 3.1 Test Article — Required Elements
- Supplier ("supplied by the Sponsor Analytical Chemistry Group")
- Batch/lot number (from ProtocolContext.batch_number)
- Purity percentage and method: "purity of X% (HPLC)"
- Storage conditions

## 3.2 Vehicle — Required Elements
- Full vehicle description (from ProtocolContext.vehicle)
- Preparation frequency: "prepared weekly" or "prepared at weekly intervals"
- Storage conditions of formulations

## 3.3 Test System — Required Elements
- Species and strain (full name)
- Supplier
- Age at arrival
- Acclimation period ("minimum 5 days prior to Day 1")
- Randomisation statement

## 3.4 Dose Formulation Verification — Required Elements
- Which days samples were collected (from ProtocolContext.formulation_check_days)
- Analytical method (HPLC)
- Acceptance criteria ("within ±10% of nominal")

## 3.5 Terminal Procedures — Required Elements
- Euthanasia method ("carbon dioxide inhalation followed by exsanguination")
- Macroscopic examination statement
- List of organs weighed (from protocol)

## 3.6 Histology and Histopathology — Required Elements
- Which groups got full panel vs. target tissues only
- Fixative ("10% neutral buffered formalin")
- Section thickness ("4 to 6 μm")
- Stain ("haematoxylin and eosin (H&E)")
- Grading scale ("1 (Minimal) to 5 (Severe)")
- Pathology peer review statement

## 3.7 Statistical Analysis — Required Elements
- Primary test: "one-way ANOVA with Dunnett's post-hoc test"
- Variance check: "Bartlett's test; if heterogeneous, Kruskal-Wallis with Dunn's post-hoc"
- Incidence test: "Fisher's exact test"
- Significance threshold: "p < 0.05"

## Tense Conversion Rule
Protocol text uses future tense. Section 3 uses past tense. Agent converts:
  "will be administered" → "was administered" / "were administered"
  "will be collected" → "were collected"
  "will be performed" → "was performed" / "were performed"

## Example — 3.1 (from approved_report_3)
"Compound BM-341 was supplied by the Sponsor Analytical Chemistry Group. The batch used (BM341-2024-D02) had a purity of 98.3% (HPLC). The test article was stored refrigerated (2 to 8°C), protected from light."
