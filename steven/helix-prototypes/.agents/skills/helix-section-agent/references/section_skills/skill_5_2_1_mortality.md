# Skill: Section 5.2.1 — Mortality
# Sources: approved_report_1, approved_report_2, approved_report_3
# Primary data source: animal_roster.csv (necropsy_type, death_date fields)

## Purpose
States survival outcome for all animals. If all animals survived, this is one sentence. If unscheduled deaths occurred, each is individually documented with animal ID, day, and attribution. This section directly feeds R-4 eval rule.

## Two Possible States

### State A — All Animals Survived
"No unscheduled deaths or moribund euthanasias occurred during the study. All [N] animals ([M] males, [F] females) survived to scheduled necropsy on Day [X]."

Fill N, M, F, X from animal_roster.csv counts and ProtocolContext.necropsy_date.

### State B — Unscheduled Death(s) Occurred
One paragraph per death, then a closing survival statement for remaining animals.

Per-death paragraph structure:
1. Animal ID + group + finding date + disposition (found dead / euthanised moribund)
2. Post-mortem or preliminary cause if available
3. Treatment relationship determination

Then closing:
"All remaining animals ([N] males, [F] females) survived to scheduled necropsy on Day [X]."

## Per-Death Template
"[Sex] [Animal ID] (Group [N], [dose] mg/kg/day) was found [dead on Day X / moribund on Day X and humanely euthanised in extremis]. Post-mortem examination revealed [cause]. This death is considered [incidental to treatment and not compound-related / treatment-related]."

## Treatment Relationship Rules
Non-treatment-related indicators (use "incidental to treatment"):
  - Gavage error (oesophageal perforation, haemothorax)
  - Accidental trauma
  - Fight wound
  - Intercurrent disease unrelated to dosing

Treatment-related indicators (use "treatment-related"):
  - Death in high-dose group with systemic toxicity signs
  - Pathological findings consistent with compound mechanism
  - Moribund state with organ-weight correlates

## What Must Not Be Missing
- Animal ID must be named — never "one animal in Group 4"
- Day must be stated — never "early in the study"
- Treatment relationship must be stated — never left open

## Example — State A (from approved_report_3)
"No unscheduled deaths or moribund euthanasias occurred during the study. All 40 animals (20 males, 20 females) survived to scheduled necropsy on Day 29."

## Example — State B (from approved_report_2)
"One unscheduled death occurred during the study. Male M101 (Group 1, Vehicle Control) was found moribund on Day 35 and humanely euthanised in extremis. Post-mortem examination revealed an oesophageal perforation with associated haemothorax, consistent with a gavage error. No microscopic findings attributable to compound administration were identified. This death is considered incidental to treatment.

All remaining animals (39 males, 40 females main cohort; 10 males, 10 females recovery) survived to scheduled necropsy."
