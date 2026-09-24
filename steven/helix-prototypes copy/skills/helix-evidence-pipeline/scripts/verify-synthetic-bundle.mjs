import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const bundlePath = resolve(process.argv[2] ?? "helix-synthetic-e2e/helix-synthetic-bundle.json");
const bundle = JSON.parse(readFileSync(bundlePath, "utf8"));
const fail = (message) => { throw new Error(message); };

bundle.label === "SYNTHETIC / NOT FOR SUBMISSION" || fail("synthetic label is missing");
bundle.manifest.length === 10 || fail("manifest must contain 10 frozen inputs");
bundle.manifest.every((entry) => entry.locked && entry.checksum && entry.authorized_by) || fail("manifest entry is not frozen and authorized");
bundle.records.animals.length === 40 || fail("expected 40 animals");
bundle.records.body_weights.length === 200 || fail("expected 200 body-weight records");
bundle.records.clinical_observations.length === 1120 || fail("expected 1,120 clinical-observation records");
bundle.records.organ_weights.length === 80 || fail("expected 80 organ-weight records");
bundle.records.microscopic_findings.length === 200 || fail("expected 200 microscopic findings");
new Set(bundle.records.body_weights.map((record) => record.record_id)).size === bundle.records.body_weights.length || fail("body-weight keys are not unique");
bundle.claims.filter((claim) => typeof claim.value === "number").every((claim) => bundle.provenance_edges.some((edge) => edge.claim_id === claim.claim_id)) || fail("numeric claim lacks provenance");
bundle.validation_results.filter((result) => result.status === "fail").length === 3 || fail("expected three deliberate blockers");
bundle.gate_decisions.find((gate) => gate.gate_type === "release")?.status === "blocked" || fail("release gate should be blocked");
bundle.export_artifacts.every((artifact) => artifact.status === "pending" && artifact.checksum === null) || fail("prototype must not pre-export artifacts");

console.log(JSON.stringify({ verified: true, package_id: bundle.package_id, records: Object.values(bundle.records).reduce((sum, records) => sum + records.length, 0), provenance_edges: bundle.provenance_edges.length, retrieval_chunks: bundle.retrieval_index.length, blockers: 3, release: "blocked" }));
