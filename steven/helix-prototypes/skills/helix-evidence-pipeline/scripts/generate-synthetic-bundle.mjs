import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const target = resolve(process.argv[2] ?? "helix-synthetic-e2e");
mkdirSync(target, { recursive: true });

let state = 0x28da2026;
const random = () => ((state = (state * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const round = (value, places = 1) => Number(value.toFixed(places));
const doseGroups = [
  { group_id: "G1", label: "Control", dose: 0 },
  { group_id: "G2", label: "Low", dose: 10 },
  { group_id: "G3", label: "Mid", dose: 30 },
  { group_id: "G4", label: "High", dose: 100 },
];

const manifest = [
  ["A-PROTOCOL", "protocol", "protocol-v3.pdf", "3.0", 2],
  ["A-TEMPLATE", "report_template", "repeat-dose-template-v5.docx", "5.0", 2],
  ["A-DM", "source_dataset", "dm.csv", "LOCK-2026-09-18", 1],
  ["A-BW", "source_dataset", "body-weights.csv", "LOCK-2026-09-18", 1],
  ["A-CL", "source_dataset", "clinical-observations.csv", "LOCK-2026-09-18", 1],
  ["A-OM", "source_dataset", "organ-weights.xlsx", "LOCK-2026-09-18", 1],
  ["A-MI", "source_dataset", "histopathology.csv", "LOCK-2026-09-18", 1],
  ["A-PC", "source_dataset", "formulation-results.pdf", "SIGNED-2026-09-19", 1],
  ["A-STATS", "statistical_output", "analysis-output.pdf", "FINAL-2026-09-20", 1],
  ["A-PATTERN", "approved_report", "approved-study-pattern.pdf", "FINAL", 3],
].map(([artifact_id, kind, name, version, authority_tier]) => ({ artifact_id, kind, name, version, authority_tier, checksum: `sha256:synthetic-${artifact_id.toLowerCase()}-${version}`, locked: true, authorized_by: "Synthetic Demo Owner" }));

const animals = doseGroups.flatMap((group, groupIndex) => ["M", "F"].flatMap((sex) => Array.from({ length: 5 }, (_, index) => ({
  animal_id: `HXL-${sex}${groupIndex + 1}${String(index + 1).padStart(2, "0")}`,
  study_id: "STUDY-HLX-028",
  group_id: group.group_id,
  sex,
  randomization_id: `RAND-${groupIndex + 1}-${sex}-${index + 1}`,
}))));

const bodyWeights = animals.flatMap((animal) => {
  const groupIndex = doseGroups.findIndex((group) => group.group_id === animal.group_id);
  const baseline = 242 + (animal.sex === "M" ? 48 : 0) + random() * 12;
  const effect = groupIndex === 3 ? -0.055 : -groupIndex * 0.008;
  return [1, 7, 14, 21, 28].map((day) => ({
    record_id: `BW-${animal.animal_id}-${day}`,
    domain: "BW",
    animal_id: animal.animal_id,
    timepoint: `DAY ${day}`,
    test_code: "BW",
    value: round(baseline * (1 + (0.098 + effect) * ((day - 1) / 27)) + random() * 2),
    unit: "g",
    grain: "animal_x_day",
    source_pointer: `A-BW#${animal.animal_id}:DAY${day}`,
  }));
});

const clinicalObservations = animals.flatMap((animal) => Array.from({ length: 28 }, (_, dayIndex) => {
  const affected = animal.group_id === "G4" && dayIndex >= 17 && Number(animal.animal_id.slice(-2)) <= 2;
  return { record_id: `CL-${animal.animal_id}-${dayIndex + 1}`, domain: "CL", animal_id: animal.animal_id, timepoint: `DAY ${dayIndex + 1}`, test_code: "CLOBS", value: affected ? "Decreased activity" : "No abnormality detected", unit: null, grain: "animal_x_day", source_pointer: `A-CL#${animal.animal_id}:DAY${dayIndex + 1}` };
}));

const organWeights = animals.flatMap((animal) => ["LIVER", "KIDNEY"].map((organ) => ({
  record_id: `OM-${animal.animal_id}-${organ}`,
  domain: "OM",
  animal_id: animal.animal_id,
  timepoint: "TERMINAL",
  test_code: organ,
  value: round((organ === "LIVER" ? 9.2 : 1.85) * (animal.group_id === "G4" && organ === "LIVER" ? 1.16 : 1) + random() * 0.25, 2),
  unit: "g",
  grain: "animal",
  source_pointer: `A-OM#${animal.animal_id}:${organ}`,
})));

const microscopicFindings = animals.flatMap((animal) => ["Liver", "Kidney", "Heart", "Lung", "Spleen"].map((tissue) => {
  const affected = animal.group_id === "G4" && tissue === "Liver" && Number(animal.animal_id.slice(-2)) <= 2;
  return { finding_id: `MI-${animal.animal_id}-${tissue.toUpperCase()}`, domain: "MI", animal_id: animal.animal_id, tissue, finding: affected ? "Hepatocellular hypertrophy" : "No abnormality detected", severity: affected ? "minimal" : "none", controlled_term: affected ? "HEPATOCELLULAR HYPERTROPHY" : "NORMAL", source_pointer: `A-MI#${animal.animal_id}:${tissue}` };
}));

const foodConsumption = doseGroups.flatMap((group) => [1, 2, 3, 4].map((week) => ({ record_id: `FW-${group.group_id}-W${week}`, domain: "FW", group_id: group.group_id, timepoint: `WEEK ${week}`, test_code: "FOOD", value: round(21.5 - doseGroups.indexOf(group) * 0.6 + random()), unit: "g/animal/day", grain: "group_x_week", source_pointer: `A-CL#${group.group_id}:WEEK${week}` })));
const formulation = doseGroups.slice(1).flatMap((group) => [1, 28].map((day) => ({ record_id: `PC-${group.group_id}-D${day}`, domain: "PC", group_id: group.group_id, timepoint: `DAY ${day}`, test_code: "CONC", value: round(group.dose * (0.97 + random() * 0.06), 2), unit: "mg/mL", grain: "concentration_x_timepoint", source_pointer: `A-PC#${group.group_id}:DAY${day}` })));

const reportSections = [
  ["S1", "Study identity and compliance", 6], ["S2", "Objectives", 2], ["S3", "Materials and methods", 12], ["S4", "Dose formulation", 5], ["S5", "In-life observations", 8], ["S6", "Clinical pathology", 7], ["S7", "Anatomic pathology", 9], ["S8", "Discussion and conclusion", 6],
].map(([section_id, title, required_fields], index) => ({ section_id, template_id: "TPL-28D-RAT-V5", title, required_fields, status: index < 5 ? "validated" : "needs_review" }));

const highDoseTerminal = bodyWeights.filter((record) => record.timepoint === "DAY 28" && animals.find((animal) => animal.animal_id === record.animal_id).group_id === "G4");
const liverFindings = microscopicFindings.filter((finding) => finding.finding === "Hepatocellular hypertrophy");
const claims = [
  { claim_id: "C-BW-HIGH", section_id: "S5", field_id: "terminal-body-weight-high", value: round(highDoseTerminal.reduce((sum, record) => sum + record.value, 0) / highDoseTerminal.length), unit: "g", grain: "dose_group", status: "validated" },
  { claim_id: "C-MI-LIVER", section_id: "S7", field_id: "liver-hypertrophy-incidence", value: liverFindings.length, unit: "animals", grain: "dose_group", status: "needs_review" },
  { claim_id: "C-NOAEL", section_id: "S8", field_id: "noael", value: null, unit: "mg/kg/day", grain: "study", status: "needs_review" },
];

const provenanceEdges = [
  ...highDoseTerminal.map((record, index) => ({ edge_id: `PE-BW-${index + 1}`, claim_id: "C-BW-HIGH", source_record_id: record.record_id, transform_id: "mean-v1", source_pointer: record.source_pointer, authority_tier: 1 })),
  ...liverFindings.map((finding, index) => ({ edge_id: `PE-MI-${index + 1}`, claim_id: "C-MI-LIVER", source_record_id: finding.finding_id, transform_id: "incidence-count-v1", source_pointer: finding.source_pointer, authority_tier: 1 })),
];

const validationResults = [
  { result_id: "VR-001", rule_id: "manifest-locked", scope_id: "MANIFEST-HLX-028", severity: "blocker", status: "pass", evidence_ids: manifest.map((entry) => entry.artifact_id), message: "All 10 inputs are authorized, checksummed, and frozen.", rule_version: "1.0" },
  { result_id: "VR-002", rule_id: "bw-key-unique", scope_id: "BW", severity: "blocker", status: "pass", evidence_ids: ["A-BW"], message: "200 body-weight records have unique animal and day keys.", rule_version: "1.0" },
  { result_id: "VR-003", rule_id: "claim-provenance", scope_id: "C-BW-HIGH", severity: "blocker", status: "pass", evidence_ids: provenanceEdges.filter((edge) => edge.claim_id === "C-BW-HIGH").map((edge) => edge.edge_id), message: "High-dose body-weight mean traces to 10 terminal records.", rule_version: "1.0" },
  { result_id: "VR-004", rule_id: "grain-sex-stratified", scope_id: "S5", severity: "blocker", status: "fail", evidence_ids: ["C-BW-HIGH"], message: "Draft table groups n=10. Template requires sex-stratified n=5.", rule_version: "1.0" },
  { result_id: "VR-005", rule_id: "mi-severity-reconcile", scope_id: "C-MI-LIVER", severity: "blocker", status: "fail", evidence_ids: ["C-MI-LIVER"], message: "Draft severity says moderate. Source findings say minimal.", rule_version: "1.0" },
  { result_id: "VR-006", rule_id: "noael-human-judgment", scope_id: "C-NOAEL", severity: "blocker", status: "fail", evidence_ids: [], message: "NOAEL requires study director interpretation and peer review.", rule_version: "1.0" },
];

const retrievalIndex = reportSections.flatMap((section) => manifest.filter((entry) => ["source_dataset", "protocol", "report_template", "approved_report", "statistical_output"].includes(entry.kind)).map((entry) => ({ chunk_id: `IDX-${section.section_id}-${entry.artifact_id}`, study_id: "STUDY-HLX-028", study_type_id: "REPEAT_DOSE_28D_RODENT", artifact_id: entry.artifact_id, artifact_version: entry.version, source_kind: entry.kind, authority_tier: entry.authority_tier, report_section_id: section.section_id, grain: entry.kind === "approved_report" ? "pattern_only" : "mixed", lock_manifest_id: "MANIFEST-HLX-028" })));

const bundle = {
  package_id: "PKG-HLX-028",
  label: "SYNTHETIC / NOT FOR SUBMISSION",
  workflow_state: "gated",
  manifest,
  study: { study_id: "STUDY-HLX-028", study_type_id: "REPEAT_DOSE_28D_RODENT", species: "Sprague-Dawley rat", route: "oral gavage", duration_days: 28, study_start: "2026-08-03", protocol_version: "3.0", dose_groups: doseGroups.map((group) => ({ ...group, study_id: "STUDY-HLX-028", dose_unit: "mg/kg/day", sexes: ["M", "F"], planned_n_per_sex: 5 })) },
  records: { animals, body_weights: bodyWeights, clinical_observations: clinicalObservations, food_consumption: foodConsumption, organ_weights: organWeights, microscopic_findings: microscopicFindings, formulation },
  report_sections: reportSections,
  claims,
  provenance_edges: provenanceEdges,
  validation_results: validationResults,
  review_dispositions: validationResults.filter((result) => result.status === "fail").map((result, index) => ({ disposition_id: `RD-${index + 1}`, result_id: result.result_id, decision: "open", reason: null, reviewer: null, timestamp: null })),
  gate_decisions: [{ gate_id: "GATE-SECTION-S5", gate_type: "section", status: "blocked", blocking_result_ids: ["VR-004"], decided_at: "2026-09-21T14:18:00Z" }, { gate_id: "GATE-RELEASE", gate_type: "release", status: "blocked", blocking_result_ids: ["VR-004", "VR-005", "VR-006"], decided_at: "2026-09-21T14:18:02Z" }],
  export_artifacts: [{ artifact_id: "OUT-REPORT", kind: "study_report_pdf", path: "m4/4.2.3.2/repeat-dose-study-report.pdf", checksum: null, status: "pending" }, { artifact_id: "OUT-SEND", kind: "send_dataset_package", path: "m4/4.2.3.2/datasets", checksum: null, status: "pending" }, { artifact_id: "OUT-DEFINE", kind: "define_xml", path: "m4/4.2.3.2/datasets/define.xml", checksum: null, status: "pending" }, { artifact_id: "OUT-NSDRG", kind: "nsdrg", path: "m4/4.2.3.2/datasets/nsdrg.pdf", checksum: null, status: "pending" }],
  retrieval_index: retrievalIndex,
  events: ["authorized_upload", "parsed", "study_resolved", "extracted", "validated", "drafted", "provenance_compiled", "gated"].map((event, index) => ({ event_id: `EV-${index + 1}`, event, actor: index < 1 ? "Synthetic Demo Owner" : "HELIX agent", timestamp: `2026-09-21T14:${String(index * 2).padStart(2, "0")}:00Z`, outcome: "complete" })),
};

writeFileSync(resolve(target, "helix-synthetic-bundle.json"), `${JSON.stringify(bundle, null, 2)}\n`);
writeFileSync(resolve(target, "retrieval-index.json"), `${JSON.stringify(retrievalIndex, null, 2)}\n`);
writeFileSync(resolve(target, "validation-results.json"), `${JSON.stringify(validationResults, null, 2)}\n`);
writeFileSync(resolve(target, "report-claims.json"), `${JSON.stringify({ report_sections: reportSections, claims, provenance_edges: provenanceEdges }, null, 2)}\n`);
console.log(JSON.stringify({ target, animals: animals.length, body_weights: bodyWeights.length, clinical_observations: clinicalObservations.length, organ_weights: organWeights.length, microscopic_findings: microscopicFindings.length, retrieval_chunks: retrievalIndex.length, blockers: validationResults.filter((result) => result.status === "fail").length }));
