# Skill: Section 5.3.3 — Microscopic Findings
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: histopathology.csv
# Note: This file covers ALL organs and ALL finding types.
#       The Section Agent looks up the finding_type from the CSV, matches it to a BLOCK,
#       and uses only that block's structure and patterns.

---

## Section-Level Structure (always applies, regardless of organ or finding type)

1. One sentence: examination scope (which groups received full panel vs. target tissues)
2. For each organ with findings OR that was examined: one paragraph block per group, lowest to highest
3. Recovery organ findings (if recovery groups exist): separate subsection per organ

### Examination Scope Statement
"Microscopic examination was performed on all tissues from Group 1 and Group 4 animals, and on target tissues ([organ list]) from Groups 2 and 3."

### Organ Order (describe in this order when multiple organs present)
Kidneys → Liver → Lungs → Bone Marrow → Thymus → Spleen → Heart → Other

### Per-Organ Block Structure (always)
1. Bold organ heading: "**Kidneys:**" or "**Liver:**"
2. Group 1 — baseline (always one sentence)
3. Group 2 — findings or explicit "no findings"
4. Group 3 — findings or explicit "no findings"
5. Group 4 — most detailed; all findings with full description
6. Recovery (if present)

### Group 1 Baseline (always this pattern)
"Group 1: No treatment-related microscopic findings. [Organ] [parenchyma / sections] was/were within normal limits in all animals examined."

### Clean Group Template (Groups 2, 3, or 4 with no findings)
"Group [N] ([dose] mg/kg/day): No treatment-related [organ] microscopic findings. All [organ] sections appeared within normal limits."

---

## Finding Type Mapping

Look up the finding_type column from histopathology.csv.
Match to the block name below. Use ONLY that block.
If multiple finding types present in same organ-group, use the block for the most severe finding,
and describe additional findings within that block's paragraph.

| finding_type (CSV)                    | Block to use              |
|---------------------------------------|---------------------------|
| tubular_basophilia                    | ADAPTIVE_CELLULAR_CHANGE  |
| hepatocyte_hypertrophy                | ADAPTIVE_CELLULAR_CHANGE  |
| erythroid_hyperplasia                 | ADAPTIVE_CELLULAR_CHANGE  |
| goblet_cell_hyperplasia               | ADAPTIVE_CELLULAR_CHANGE  |
| hepatocyte_vacuolisation              | ADVERSE_DEGENERATIVE      |
| tubular_necrosis                      | ADVERSE_DEGENERATIVE      |
| hepatocyte_necrosis                   | ADVERSE_DEGENERATIVE      |
| tubular_dilation                      | ADVERSE_DEGENERATIVE      |
| myocardial_degeneration               | ADVERSE_DEGENERATIVE      |
| alveolar_macrophage_accumulation      | INFLAMMATORY              |
| interstitial_pneumonia                | INFLAMMATORY              |
| hepatic_inflammation                  | INFLAMMATORY              |
| renal_interstitial_nephritis          | INFLAMMATORY              |
| thymic_lymphoid_depletion             | LYMPHOID_DEPLETION        |
| splenic_lymphoid_depletion            | LYMPHOID_DEPLETION        |
| lymph_node_depletion                  | LYMPHOID_DEPLETION        |
| bone_marrow_hypocellularity           | LYMPHOID_DEPLETION        |
| no_findings / normal                  | CLEAN_ORGAN               |

---

## [BLOCK: ADAPTIVE_CELLULAR_CHANGE]
Use for: tubular basophilia, hepatocyte hypertrophy, erythroid hyperplasia, and similar
         findings representing a cellular response without injury

### Structure
1. Finding name (Grade) — incidence
2. Morphological description — one sentence, what the cells look like
3. Mechanism — one sentence, what biological process this represents
4. Explicit absence statement — what was NOT seen
5. Adversity determination with numbered criteria

### Pattern
"[Finding name (Grade N)] was observed in [X of Y males / all N females]. The finding was
characterised by [morphology description], consistent with [mechanism]. No [absence 1],
[absence 2], or [absence 3] was observed. This change is considered adaptive and not
adverse based on: (1) [criterion]; (2) [criterion]; (3) [criterion if available]."

### Standard Absence Statements by Organ
Kidney: "No tubular degeneration, necrosis, cast formation, or inflammatory infiltrate"
Liver: "No hepatocellular necrosis, inflammatory infiltrate, biliary changes, or fibrosis"
Bone marrow: "No reduction in overall marrow cellularity"

### Standard Adversity Criteria for Adaptive Findings
Choose ≥2:
  - absence of [degeneration / necrosis]
  - no macroscopic correlate
  - no statistically significant organ weight change
  - low incidence / low grade
  - consistency with a known pharmacological mechanism (name the mechanism)
  - maintained [organ / tissue] architecture

### Example (from approved_report_3 — kidney tubular basophilia)
"Minimal renal tubular basophilia (Grade 1) was observed in 3 of 5 males (M301, M303, M304).
The finding was characterised by increased cytoplasmic basophilia of proximal tubular epithelial
cells in the cortex, consistent with increased ribosomal content and protein synthetic activity
associated with enzyme induction. No tubular degeneration, necrosis, cast formation, or
inflammatory infiltrate was observed. This change is considered adaptive and not adverse based on:
(1) absence of tubular degeneration or necrosis; (2) no macroscopic renal correlate; (3)
consistency with a well-characterised adaptive response to transporter inhibition in this species."

---

## [BLOCK: ADVERSE_DEGENERATIVE]
Use for: tubular necrosis, hepatocyte necrosis, vacuolisation, tubular dilation,
         myocardial degeneration — findings representing tissue injury

### Structure
1. Finding name (Grade range) — incidence
2. Morphological description — one sentence, what the injured cells look like
3. Associated correlates — organ weight or macroscopic findings linked to this
4. Adversity conclusion — stated, not hedged

### Pattern
"[Finding name (Grade N–N)] was observed in [incidence]. The finding was characterised by
[morphology and distribution]. [Associated correlate — organ weight or macroscopic, if present].
This finding is considered treatment-related and adverse at [dose] mg/kg/day."

### Correlate Linking Template
"[Organ] weights were increased at this dose ([magnitude]% males, [magnitude]% females)."
"[Organ] appeared [gross appearance] at macroscopic examination."

### When No Correlate
Omit the correlate sentence. Do not say "no correlate was noted" — simply state the finding and adversity conclusion.

### Example (from approved_report_2 — liver vacuolisation)
"Minimal to mild centrilobular hepatocyte vacuolisation (Grade 1 to 2) was observed in 9 of 10
males and 8 of 10 females, consistent with lipid accumulation. No hepatocellular necrosis,
inflammatory infiltrate, biliary changes, or fibrosis was observed. The finding is considered
treatment-related and adverse at 150 mg/kg/day in the context of associated organ weight
increases and body weight reduction."

---

## [BLOCK: INFLAMMATORY]
Use for: alveolar macrophage accumulation, interstitial pneumonia, hepatic inflammation,
         renal interstitial nephritis — findings involving cellular infiltrate or immune response

### Structure
1. Infiltrate type (Grade) — distribution — incidence
2. Cellular composition — what cell types are present
3. Associated epithelial or structural changes (if present)
4. Adversity conclusion
5. Reversibility statement (only if recovery data exists)

### Pattern
"[Cellular infiltrate (Grade N)] was observed [distribution] in [incidence]. The infiltrate was
composed of [cell types]. [Epithelial or structural change if present]. This finding is considered
[adverse / non-adverse] at [dose] mg/kg/day.
[Reversibility: At Day [X], [finding status], indicating [full / partial] reversibility.]"

### Non-Adverse Inflammatory (low grade, low incidence, no correlates)
"[Finding (Grade 1)] was observed in [low incidence, one sex]. [Absence statement]. This finding
was observed at low incidence without [sex] involvement and in the absence of any clinical,
macroscopic, or organ weight correlate; it is considered non-adverse and possibly incidental."

### Example — Adverse (from approved_report_2 — lung macrophages)
"Moderate to marked alveolar macrophage accumulation with associated inflammatory infiltrate
(Grade 3) was observed throughout the pulmonary parenchyma in 6 of 10 males and 5 of 10 females.
Foamy macrophage cytoplasm was prominent. Mild type II pneumocyte hypertrophy and hyperplasia
(Grade 1 to 2) was present in affected areas. This finding is considered adverse at 150 mg/kg/day.
At Day 120, the infiltrate was substantially reduced (Grade 1, 2 of 5 males), indicating partial
reversibility."

---

## [BLOCK: LYMPHOID_DEPLETION]
Use for: thymic lymphoid depletion, splenic white pulp depletion,
         lymph node depletion, bone marrow hypocellularity

### Structure
1. Compartment + finding (Grade) — incidence
2. Which compartment was affected and what was maintained
3. Adversity conclusion — lymphoid depletion Grade ≥2 is always adverse
4. Reversibility statement (if recovery data exists)

### Pattern
"[Lymphoid depletion (Grade N)] was observed in the [compartment] of [organ] in [incidence].
[Maintained structure statement]. This finding is considered treatment-related and adverse at
[dose] mg/kg/day, consistent with [secondary immune suppression / haematopoietic suppression].
[Reversibility statement if recovery present.]"

### Standard Maintained Structure Statements
Thymus: "Cortical cellularity was markedly reduced; medullary architecture was maintained."
Spleen: "White pulp follicles were reduced; red pulp architecture was maintained."
Bone marrow: "Overall marrow cellularity was reduced."

### Example (from approved_report_2 — thymus)
"Moderate lymphoid depletion (Grade 2 to 3) was observed in the thymic cortex of 8 of 10 males
and 7 of 10 females. Cortical cellularity was markedly reduced; medullary architecture was
maintained. This finding is considered treatment-related and adverse at 150 mg/kg/day, consistent
with secondary immune suppression.
At Day 120, no lymphoid depletion was observed in any recovery animal. Thymic cortical
cellularity appeared within normal limits. Full reversal was confirmed."

---

## [BLOCK: CLEAN_ORGAN]
Use for: any organ with no findings across all dose groups that were examined

### Pattern — Single organ, all groups clean
"No treatment-related microscopic findings were identified in the [organ] in any dose group.
[Organ] sections appeared within normal limits in all Group 1 and Group 4 animals examined."

### Pattern — Multiple clean organs (list them)
"No treatment-related microscopic findings were identified in the [organ 1], [organ 2], or
[organ 3] in any dose group."

### Note
Always include Group 1 baseline statement even for clean organs.
Do not say "no significant changes" — say "within normal limits."

---

## Recovery Group Findings (append after main group blocks per organ)

### Template
"Group [N]R (Recovery): At Day [X], [finding status at recovery necropsy].
[Full reversal confirmed / The [finding] was substantially reduced / [Finding] persisted at Grade N in X of Y animals], indicating [full / partial / no] reversibility."

If completely reversed:
"Group [N]R (Recovery): No [finding] was observed in any recovery animal. [Organ] appeared within normal limits. Full reversal was confirmed."
