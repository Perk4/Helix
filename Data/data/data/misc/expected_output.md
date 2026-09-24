# FINAL STUDY REPORT — HELIX DRAFT OUTPUT
# Test Article: Compound YZ-389
# Sources:
#   study_protocol_YZ389.md  — study design, test article details, dose rationale
#   study_data_new.csv       — all individual animal measurements
#   approved_report_1.md     — section patterns (RAG)
# Provenance format: [value | source: <file> | field/col: <field> | rows: <ids>]

**Study Title:** A 28-Day Repeat-Dose Oral Gavage Toxicity Study with Compound YZ-389 in Sprague-Dawley Rats
**Study Number:** TOX-2025-0118
**Test Article:** Compound YZ-389
**Species/Strain:** Rat / Sprague-Dawley (Crl:CD(SD))
**Report Date:** [NEEDS REVIEW — insert report date]
**Status:** DRAFT — Pending Pathologist Review

---

## 1. Introduction

This study was conducted to evaluate the potential toxicity of Compound YZ-389 following repeated oral gavage administration to Sprague-Dawley rats for 28 consecutive days. The study was designed to characterize the nature and severity of any treatment-related effects, identify target organs, and establish a no-observed-adverse-effect level (NOAEL). The study was conducted in compliance with Good Laboratory Practice (GLP) regulations.

Compound YZ-389 ([2-(4-fluorophenyl)-N-(pyridin-3-yl)acetamide | source: study_protocol_YZ389.md | field: Chemical Name], molecular formula [C13H11FN2O | source: study_protocol_YZ389.md | field: Molecular Formula], MW [230.24 g/mol | source: study_protocol_YZ389.md | field: Molecular Weight]) is a small-molecule candidate under development. Based on pharmacological activity and a 7-day range-finding study (Protocol TOX-2024-DRF-004), the liver was identified as a potential target organ.

The doses selected for this study ([25 | source: study_protocol_YZ389.md | field: Group 2 Dose], [100 | source: study_protocol_YZ389.md | field: Group 3 Dose], and [400 | source: study_protocol_YZ389.md | field: Group 4 Dose] mg/kg/day) were based on [the MTD established in the 7-day range-finding study | source: study_protocol_YZ389.md | field: Dose Rationale]. The high dose of 400 mg/kg/day is intended to produce discernible toxicity; the low dose of 25 mg/kg/day is anticipated to represent a NOAEL candidate.

---

## 2. Experimental Design

| Parameter | Detail |
|---|---|
| Species | [Sprague-Dawley rat (Crl:CD(SD)) | source: study_protocol_YZ389.md | field: Species/Strain] |
| Source | [Charles River Laboratories | source: study_protocol_YZ389.md | field: Source] |
| Age at study start | [7 to 8 weeks | source: study_protocol_YZ389.md | field: Age at study initiation] |
| Route of administration | [Oral gavage | source: study_protocol_YZ389.md | field: Route of administration] |
| Dosing frequency | [Once daily, 7 days per week | source: study_protocol_YZ389.md | field: Dosing frequency] |
| Study duration | [28 days | source: study_protocol_YZ389.md | field: Study duration] |
| Vehicle | [0.5% methylcellulose in purified water | source: study_protocol_YZ389.md | field: Vehicle] |
| Dose volume | [10 mL/kg body weight | source: study_protocol_YZ389.md | field: Dose volume] |

**Animal Allocation:**

| Group | Dose (mg/kg/day) | Males | Females | Total |
|---|---|---|---|---|
| 1 - Vehicle Control | [0 | source: study_data_new.csv | col: dose_mgkg_day | rows: M101-M105,F101-F105] | [5 | source: study_data_new.csv | col: sex | rows: M101-M105] | [5 | source: study_data_new.csv | col: sex | rows: F101-F105] | 10 |
| 2 - Low Dose | [25 | source: study_data_new.csv | col: dose_mgkg_day | rows: M201-M205] | 5 | 5 | 10 |
| 3 - Mid Dose | [100 | source: study_data_new.csv | col: dose_mgkg_day | rows: M301-M305] | 5 | 5 | 10 |
| 4 - High Dose | [400 | source: study_data_new.csv | col: dose_mgkg_day | rows: M401-M405] | 5 | 5 | 10 |
| **Total** | | 20 | 20 | 40 |

Animals were housed [2 per cage | source: study_protocol_YZ389.md | field: Housing] under standard conditions ([22 ± 2°C | source: study_protocol_YZ389.md | field: Room temperature], [12-hour light/dark cycle | source: study_protocol_YZ389.md | field: Light cycle]) with free access to certified rodent diet and water. Animals were assigned to groups by stratified randomisation based on body weight on Day 1.

---

## 3. Body Weight

Body weights were recorded on Day 1 (pre-dose) and weekly thereafter through Day 28. All animals survived to scheduled necropsy. No unscheduled deaths occurred.

**Male Mean Body Weights (g):**

| Group | Day 1 | Day 7 | Day 14 | Day 21 | Day 28 |
|---|---|---|---|---|---|
| G1 - Control (0 mg/kg) | [231.5 | source: study_data_new.csv | col: bw_day1_g | rows: M101-M105 | agg: mean] | [261.3 | source: study_data_new.csv | col: bw_day7_g | rows: M101-M105 | agg: mean] | [289.5 | source: study_data_new.csv | col: bw_day14_g | rows: M101-M105 | agg: mean] | [313.7 | source: study_data_new.csv | col: bw_day21_g | rows: M101-M105 | agg: mean] | [339.4 | source: study_data_new.csv | col: bw_day28_g | rows: M101-M105 | agg: mean] |
| G2 - Low (25 mg/kg) | [230.6 | source: study_data_new.csv | col: bw_day1_g | rows: M201-M205 | agg: mean] | [260.4 | source: study_data_new.csv | col: bw_day7_g | rows: M201-M205 | agg: mean] | [288.7 | source: study_data_new.csv | col: bw_day14_g | rows: M201-M205 | agg: mean] | [312.7 | source: study_data_new.csv | col: bw_day21_g | rows: M201-M205 | agg: mean] | [338.2 | source: study_data_new.csv | col: bw_day28_g | rows: M201-M205 | agg: mean] |
| G3 - Mid (100 mg/kg) | [231.1 | source: study_data_new.csv | col: bw_day1_g | rows: M301-M305 | agg: mean] | [258.5 | source: study_data_new.csv | col: bw_day7_g | rows: M301-M305 | agg: mean] | [283.6 | source: study_data_new.csv | col: bw_day14_g | rows: M301-M305 | agg: mean] | [304.6 | source: study_data_new.csv | col: bw_day21_g | rows: M301-M305 | agg: mean] | [318.5 | source: study_data_new.csv | col: bw_day28_g | rows: M301-M305 | agg: mean] |
| G4 - High (400 mg/kg) | [230.4 | source: study_data_new.csv | col: bw_day1_g | rows: M401-M405 | agg: mean] | [247.5 | source: study_data_new.csv | col: bw_day7_g | rows: M401-M405 | agg: mean] | [262.4 | source: study_data_new.csv | col: bw_day14_g | rows: M401-M405 | agg: mean] | [275.6 | source: study_data_new.csv | col: bw_day21_g | rows: M401-M405 | agg: mean] | [287.2 | source: study_data_new.csv | col: bw_day28_g | rows: M401-M405 | agg: mean] |

**Female Mean Body Weights (g):**

| Group | Day 1 | Day 7 | Day 14 | Day 21 | Day 28 |
|---|---|---|---|---|---|
| G1 - Control (0 mg/kg) | [183.6 | source: study_data_new.csv | col: bw_day1_g | rows: F101-F105 | agg: mean] | [204.2 | source: study_data_new.csv | col: bw_day7_g | rows: F101-F105 | agg: mean] | [220.4 | source: study_data_new.csv | col: bw_day14_g | rows: F101-F105 | agg: mean] | [233.1 | source: study_data_new.csv | col: bw_day21_g | rows: F101-F105 | agg: mean] | [245.5 | source: study_data_new.csv | col: bw_day28_g | rows: F101-F105 | agg: mean] |
| G2 - Low (25 mg/kg) | [184.2 | source: study_data_new.csv | col: bw_day1_g | rows: F201-F205 | agg: mean] | [205.0 | source: study_data_new.csv | col: bw_day7_g | rows: F201-F205 | agg: mean] | [221.2 | source: study_data_new.csv | col: bw_day14_g | rows: F201-F205 | agg: mean] | [233.9 | source: study_data_new.csv | col: bw_day21_g | rows: F201-F205 | agg: mean] | [246.5 | source: study_data_new.csv | col: bw_day28_g | rows: F201-F205 | agg: mean] |
| G3 - Mid (100 mg/kg) | [183.6 | source: study_data_new.csv | col: bw_day1_g | rows: F301-F305 | agg: mean] | [202.3 | source: study_data_new.csv | col: bw_day7_g | rows: F301-F305 | agg: mean] | [216.7 | source: study_data_new.csv | col: bw_day14_g | rows: F301-F305 | agg: mean] | [227.3 | source: study_data_new.csv | col: bw_day21_g | rows: F301-F305 | agg: mean] | [234.7 | source: study_data_new.csv | col: bw_day28_g | rows: F301-F305 | agg: mean] |
| G4 - High (400 mg/kg) | [183.9 | source: study_data_new.csv | col: bw_day1_g | rows: F401-F405 | agg: mean] | [196.7 | source: study_data_new.csv | col: bw_day7_g | rows: F401-F405 | agg: mean] | [207.1 | source: study_data_new.csv | col: bw_day14_g | rows: F401-F405 | agg: mean] | [213.8 | source: study_data_new.csv | col: bw_day21_g | rows: F401-F405 | agg: mean] | [219.1 | source: study_data_new.csv | col: bw_day28_g | rows: F401-F405 | agg: mean] |

Body weight gain in Group 4 males was reduced by [15.3% | source: study_data_new.csv | computed: (339.4-287.2)/339.4*100] relative to controls by Day 28 ([287.2 | source: study_data_new.csv | col: bw_day28_g | rows: M401-M405 | agg: mean] g vs. [339.4 | source: study_data_new.csv | col: bw_day28_g | rows: M101-M105 | agg: mean] g). Group 4 females showed a similar reduction of [10.8% | source: study_data_new.csv | computed: (245.5-219.1)/245.5*100] ([219.1 | source: study_data_new.csv | col: bw_day28_g | rows: F401-F405 | agg: mean] g vs. [245.5 | source: study_data_new.csv | col: bw_day28_g | rows: F101-F105 | agg: mean] g). Group 3 showed reductions of [6.2% | source: study_data_new.csv | computed: (339.4-318.5)/339.4*100] in males and [4.4% | source: study_data_new.csv | computed: (245.5-234.7)/245.5*100] in females relative to controls at Day 28. Groups 1 and 2 showed comparable body weight trajectories throughout the study.

---

## 4. Clinical Observations

Cage-side observations were recorded twice daily throughout the study. Detailed clinical examinations were performed weekly.

**Group 1 (0 mg/kg/day - Vehicle Control):** No treatment-related clinical signs were observed in any male or female animal during the study.

**Group 2 (25 mg/kg/day - Low Dose):** No treatment-related clinical signs were observed. All animals appeared healthy throughout the dosing period.

**Group 3 (100 mg/kg/day - Mid Dose):** Soft stool was observed in [2 | source: study_data_new.csv | col: clin_obs_d8_14 | rows: M301,M303 | agg: count(soft stool)] of 5 males (M301, M303) during Days 8 to 14. The finding was transient and resolved by Day 15. No clinical signs were noted in females at this dose level.

**Group 4 (400 mg/kg/day - High Dose):** Multiple clinical signs consistent with systemic toxicity were observed throughout the study. Reduced activity was observed in [4 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: M401-M405 | agg: count(Reduced activity)] of 5 males and [3 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: F401-F405 | agg: count(Reduced activity)] of 5 females from Day 1 through Day 28. Hunched posture was recorded in [3 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: M401-M405 | agg: count(hunched posture)] males (M401, M402, M403) and [2 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: F401-F405 | agg: count(hunched posture)] females (F401, F402). Soft stool was observed in [5 | source: study_data_new.csv | col: clin_obs_d8_14 | rows: M401-M405 | agg: count(soft stool)] of 5 males and [5 | source: study_data_new.csv | col: clin_obs_d8_14 | rows: F401-F405 | agg: count(soft stool)] of 5 females from Day 8 onward. Partially closed eyes were noted in [2 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: M401-M405 | agg: count(partially closed eyes)] males (M401, M402) and [1 | source: study_data_new.csv | col: clin_obs_d1_7 | rows: F401-F405 | agg: count(partially closed eyes)] female (F401) during Days 1 to 14. All findings are considered treatment-related.

---

## 5. Organ Weights

Terminal organ weights were recorded at scheduled necropsy on Day 29. Absolute organ weights are presented below.

**Male Absolute Organ Weights (g) - Group Means:**

| Organ | G1 Control | G2 Low | G3 Mid | G4 High |
|---|---|---|---|---|
| Liver | [11.48 | source: study_data_new.csv | col: liver_wt_g | rows: M101-M105 | agg: mean] | [11.47 | source: study_data_new.csv | col: liver_wt_g | rows: M201-M205 | agg: mean] | [12.82 | source: study_data_new.csv | col: liver_wt_g | rows: M301-M305 | agg: mean] | [15.33 | source: study_data_new.csv | col: liver_wt_g | rows: M401-M405 | agg: mean] |
| Kidneys (paired) | [2.18 | source: study_data_new.csv | col: kidney_wt_g | rows: M101-M105 | agg: mean] | [2.18 | source: study_data_new.csv | col: kidney_wt_g | rows: M201-M205 | agg: mean] | [2.31 | source: study_data_new.csv | col: kidney_wt_g | rows: M301-M305 | agg: mean] | [2.64 | source: study_data_new.csv | col: kidney_wt_g | rows: M401-M405 | agg: mean] |
| Heart | [1.12 | source: study_data_new.csv | col: heart_wt_g | rows: M101-M105 | agg: mean] | [1.12 | source: study_data_new.csv | col: heart_wt_g | rows: M201-M205 | agg: mean] | [1.13 | source: study_data_new.csv | col: heart_wt_g | rows: M301-M305 | agg: mean] | [1.17 | source: study_data_new.csv | col: heart_wt_g | rows: M401-M405 | agg: mean] |
| Brain | [1.89 | source: study_data_new.csv | col: brain_wt_g | rows: M101-M105 | agg: mean] | [1.89 | source: study_data_new.csv | col: brain_wt_g | rows: M201-M205 | agg: mean] | [1.87 | source: study_data_new.csv | col: brain_wt_g | rows: M301-M305 | agg: mean] | [1.86 | source: study_data_new.csv | col: brain_wt_g | rows: M401-M405 | agg: mean] |
| Spleen | [0.74 | source: study_data_new.csv | col: spleen_wt_g | rows: M101-M105 | agg: mean] | [0.74 | source: study_data_new.csv | col: spleen_wt_g | rows: M201-M205 | agg: mean] | [0.77 | source: study_data_new.csv | col: spleen_wt_g | rows: M301-M305 | agg: mean] | [0.81 | source: study_data_new.csv | col: spleen_wt_g | rows: M401-M405 | agg: mean] |
| Thymus | [0.38 | source: study_data_new.csv | col: thymus_wt_g | rows: M101-M105 | agg: mean] | [0.38 | source: study_data_new.csv | col: thymus_wt_g | rows: M201-M205 | agg: mean] | [0.34 | source: study_data_new.csv | col: thymus_wt_g | rows: M301-M305 | agg: mean] | [0.28 | source: study_data_new.csv | col: thymus_wt_g | rows: M401-M405 | agg: mean] |

**Female Absolute Organ Weights (g) - Group Means:**

| Organ | G1 Control | G2 Low | G3 Mid | G4 High |
|---|---|---|---|---|
| Liver | [8.65 | source: study_data_new.csv | col: liver_wt_g | rows: F101-F105 | agg: mean] | [8.73 | source: study_data_new.csv | col: liver_wt_g | rows: F201-F205 | agg: mean] | [9.66 | source: study_data_new.csv | col: liver_wt_g | rows: F301-F305 | agg: mean] | [11.79 | source: study_data_new.csv | col: liver_wt_g | rows: F401-F405 | agg: mean] |
| Kidneys (paired) | [1.53 | source: study_data_new.csv | col: kidney_wt_g | rows: F101-F105 | agg: mean] | [1.54 | source: study_data_new.csv | col: kidney_wt_g | rows: F201-F205 | agg: mean] | [1.64 | source: study_data_new.csv | col: kidney_wt_g | rows: F301-F305 | agg: mean] | [1.87 | source: study_data_new.csv | col: kidney_wt_g | rows: F401-F405 | agg: mean] |
| Heart | [0.87 | source: study_data_new.csv | col: heart_wt_g | rows: F101-F105 | agg: mean] | [0.87 | source: study_data_new.csv | col: heart_wt_g | rows: F201-F205 | agg: mean] | [0.87 | source: study_data_new.csv | col: heart_wt_g | rows: F301-F305 | agg: mean] | [0.90 | source: study_data_new.csv | col: heart_wt_g | rows: F401-F405 | agg: mean] |
| Brain | [1.86 | source: study_data_new.csv | col: brain_wt_g | rows: F101-F105 | agg: mean] | [1.86 | source: study_data_new.csv | col: brain_wt_g | rows: F201-F205 | agg: mean] | [1.84 | source: study_data_new.csv | col: brain_wt_g | rows: F301-F305 | agg: mean] | [1.83 | source: study_data_new.csv | col: brain_wt_g | rows: F401-F405 | agg: mean] |
| Spleen | [0.61 | source: study_data_new.csv | col: spleen_wt_g | rows: F101-F105 | agg: mean] | [0.62 | source: study_data_new.csv | col: spleen_wt_g | rows: F201-F205 | agg: mean] | [0.63 | source: study_data_new.csv | col: spleen_wt_g | rows: F301-F305 | agg: mean] | [0.67 | source: study_data_new.csv | col: spleen_wt_g | rows: F401-F405 | agg: mean] |
| Thymus | [0.42 | source: study_data_new.csv | col: thymus_wt_g | rows: F101-F105 | agg: mean] | [0.41 | source: study_data_new.csv | col: thymus_wt_g | rows: F201-F205 | agg: mean] | [0.37 | source: study_data_new.csv | col: thymus_wt_g | rows: F301-F305 | agg: mean] | [0.30 | source: study_data_new.csv | col: thymus_wt_g | rows: F401-F405 | agg: mean] |

Liver weights were increased in Group 3 ([12.82 | source: study_data_new.csv | col: liver_wt_g | rows: M301-M305 | agg: mean] g males, [9.66 | source: study_data_new.csv | col: liver_wt_g | rows: F301-F305 | agg: mean] g females) and Group 4 ([15.33 | source: study_data_new.csv | col: liver_wt_g | rows: M401-M405 | agg: mean] g males, [11.79 | source: study_data_new.csv | col: liver_wt_g | rows: F401-F405 | agg: mean] g females) relative to controls. The increase in Group 4 males represents a [33.5% | source: study_data_new.csv | computed: (15.33-11.48)/11.48*100] elevation over control mean. Thymus weights were reduced in Group 4 ([0.28 | source: study_data_new.csv | col: thymus_wt_g | rows: M401-M405 | agg: mean] g males, [0.30 | source: study_data_new.csv | col: thymus_wt_g | rows: F401-F405 | agg: mean] g females). [NEEDS REVIEW — pathologist to confirm adverse vs. adaptive classification for organ weight changes]

---

## 6. Histopathology Findings

Microscopic examination was performed on tissues from all animals in Groups 1 and 4 and selected tissues from Groups 2 and 3.

**Liver:**

Group 1 and Group 2: No treatment-related microscopic findings were observed. Hepatic parenchyma appeared within normal limits in all animals examined.

Group 3: Minimal hepatocellular hypertrophy (Grade 1) was observed in [3 | source: study_data_new.csv | col: histo_liver_finding | rows: M301-M305 | agg: count(Hepatocellular hypertrophy)] of 5 males (M301, M303, M304) and [2 | source: study_data_new.csv | col: histo_liver_finding | rows: F301-F305 | agg: count(Hepatocellular hypertrophy)] of 5 females (F301, F303). [NEEDS REVIEW — pathologist to characterise distribution and classify as adaptive or adverse]

Group 4: [2 | source: study_data_new.csv | col: histo_liver_finding | rows: M401-M405 | agg: count(centrilobular necrosis)] of 5 males (M401, M402) and [1 | source: study_data_new.csv | col: histo_liver_finding | rows: F401-F405 | agg: count(centrilobular necrosis)] of 5 females (F401) showed centrilobular necrosis alongside hepatocellular hypertrophy in all Group 4 animals ([5 | source: study_data_new.csv | col: histo_liver_finding | rows: M401-M405 | agg: count(Hepatocellular hypertrophy)] of 5 males, [5 | source: study_data_new.csv | col: histo_liver_finding | rows: F401-F405 | agg: count(Hepatocellular hypertrophy)] of 5 females). [NEEDS REVIEW — pathologist to assign severity grades and confirm adverse classification]

**Kidney:**

Group 1 and Group 2: No treatment-related findings.

Group 3: No treatment-related renal findings.

Group 4: Renal tubular basophilia (Grade 1) was observed in [3 | source: study_data_new.csv | col: histo_kidney_finding | rows: M401-M405 | agg: count(Renal tubular basophilia)] of 5 males (M401, M402, M403) and [3 | source: study_data_new.csv | col: histo_kidney_finding | rows: F401-F405 | agg: count(Renal tubular basophilia)] of 5 females (F401, F402, F403). [NEEDS REVIEW — pathologist to confirm morphological characterisation]

**Other Organs (Heart, Brain, Spleen, Thymus):**

No treatment-related microscopic findings were identified in the heart, brain, or spleen in any dose group. [NEEDS REVIEW — pathologist to confirm thymic findings and characterise lymphoid changes if present]

**Conclusion:**

[NEEDS REVIEW — pathologist to determine NOAEL and LOAEL based on full microscopic review and integrated assessment of all endpoints]
