// Can this section actually be drafted from the claims it declares?
//
// Three artifacts have to agree and nothing checked that they do:
//
//   the executor        computes N values for the section
//   the provenance
//   compiler            binds exactly one Validated Claim per factual span
//                       and per table cell, and rejects anything else
//   the section package declares `required_claims`
//
// For 5.2.3 those numbers are 40 and 1. Forty claim-backed cells cannot come
// from one claim, so the section is undraftable under its own rules and no
// amount of prompt work fixes it.
//
// That took six suite runs against a live model to notice, showing up as the
// agent drafting half the time and refusing half the time. It is a static
// mismatch between three committed files and should cost a second, not a
// provider bill. Hence this check.
//
// Deliberately reads only committed artifacts. No backend import, no Python,
// no network: the fixture already carries a real executor receipt, so the
// value count comes from there rather than from running the executor.
//
//   node scripts/verify-claim-coverage.mjs
//
// DEMO ONLY, NOT QUALIFICATION: with HELIX_DEMO_UNQUALIFIED_PACKAGES=1 (or true/yes/on) in
// the environment, or the --demo-unqualified-packages CLI flag, the check applies option 2
// of upstream 47c19c4 exactly as the backend does in demo mode: for 5.2.3 only, a table
// cell backed by the envelope's executor receipt counts as covered. Every such line is
// labelled "Demo: not qualified". Without the flag the check is unchanged.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const sectionsDir = resolve(root, "skills/helix-evidence-pipeline/packages/sections");
const fixturesDir = resolve(root, ".agents/skills/helix-section-agent/evals/fixtures");

const problems = [];

const DEMO_LABEL = "Demo: not qualified";
// Mirrors backend/app/demo_mode.py RECEIPT_BACKED_CELL_PACKAGE_IDS (5.2.3 only).
const RECEIPT_BACKED_SECTIONS = new Set(["5_2_3_body_weight"]);
const demoMode =
  process.argv.includes("--demo-unqualified-packages") ||
  /^(1|true|yes|on)$/i.test(process.env.HELIX_DEMO_UNQUALIFIED_PACKAGES ?? "");
if (demoMode) {
  console.log(`DEMO MODE (${DEMO_LABEL}): executor-receipt table cells count as covered for 5.2.3 only`);
}

/** Every leaf number the executor computed, which is one table cell each. */
const countValues = (node) => {
  if (typeof node === "number") return 1;
  if (Array.isArray(node)) return node.reduce((total, item) => total + countValues(item), 0);
  if (node && typeof node === "object") {
    return Object.values(node).reduce((total, item) => total + countValues(item), 0);
  }
  return 0;
};

// Facts that describe the run rather than the section's content. Counting them
// as cells would overstate what needs a claim behind it.
// `statistical_comparisons` holds p-values from the analysis method, not body
// weight measurements. Each p-value would otherwise count as a cell requiring
// a claim, which is not the intent — the section reports means, not test stats.
const METADATA_KEYS = new Set(["recording_days", "duration_days", "unit", "groups", "grading_scale", "statistical_comparisons"]);

const envelopeFor = (sectionId) =>
  readdirSync(fixturesDir)
    .filter((name) => name.endsWith(".json"))
    .map((name) => ({ name, body: JSON.parse(readFileSync(resolve(fixturesDir, name), "utf8")) }))
    .find(({ body }) => body.section_package?.package_id === `section.${sectionId}`);

for (const sectionId of readdirSync(sectionsDir)) {
  const packagePath = resolve(sectionsDir, sectionId, "package.json");
  if (!existsSync(packagePath)) continue;
  const pkg = JSON.parse(readFileSync(packagePath, "utf8"));
  const declared = (pkg.required_claims ?? []).length;

  const fixture = envelopeFor(sectionId);
  if (!fixture) {
    console.log(`skipped   ${sectionId}: no envelope fixture, nothing to compare against`);
    continue;
  }

  const facts = fixture.body.executor_receipts?.[0]?.facts ?? {};
  const cells = Object.entries(facts)
    .filter(([key]) => !METADATA_KEYS.has(key))
    .reduce((total, [, value]) => total + countValues(value), 0);

  const receipt = fixture.body.executor_receipts?.[0];
  if (demoMode && RECEIPT_BACKED_SECTIONS.has(sectionId) && receipt?.artifact_id && cells > declared) {
    // Every computed value is a table cell the receipt itself backs, so all cells are covered.
    console.log(
      `coverage ok   ${sectionId}: ${cells} computed value(s), ${declared} declared claim(s), ` +
        `${cells} cell(s) backed by executor receipt ${receipt.artifact_id} [${DEMO_LABEL}]`,
    );
    continue;
  }

  if (cells > declared) {
    problems.push(
      `${sectionId}: the executor computes ${cells} value(s) but the package declares ${declared} ` +
        `required claim(s). The provenance compiler binds exactly one Validated Claim per cell, so ` +
        `${cells - declared} cell(s) have nothing that can back them and the section cannot be drafted ` +
        `under its own rules. Widen required_claims, or reduce what the section reports.`,
    );
  } else {
    console.log(`coverage ok   ${sectionId}: ${cells} computed value(s), ${declared} declared claim(s)`);
  }
}

if (problems.length > 0) {
  for (const problem of problems) console.error(`FAIL ${problem}`);
  process.exit(1);
}

console.log(
  JSON.stringify({
    verified: true,
    sections: readdirSync(sectionsDir).length,
    ...(demoMode ? { demo_unqualified_packages: true, label: DEMO_LABEL } : {}),
  }),
);
