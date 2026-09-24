// PKG-005 gate. A pinned run may reference only a passing qualification, and a
// qualification is only worth what a reviewer can recompute.
//
// Deliberately makes no provider call. The suite costs money and needs a key;
// this check needs neither, so CI can run it first and fail before spending
// anything. It answers three questions from what is on disk:
//
//   1. Does the package claim to be qualified at all?
//   2. Do the files still hash to what was certified?
//   3. Is the recorded digest the one those inputs and that outcome produce?
//
// Question 2 is the one that catches the real mistake: editing prompt.txt, or
// the skill, or a fixture, and pushing without re-running the qualification.
//
//   node scripts/verify-qualification.mjs

import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { canonicalHash, fileHash } from "./lib/hash.mjs";

const root = resolve(import.meta.dirname, "..");
const packagePath = resolve(root, "skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json");
const artifactPath = resolve(
  root,
  ".agents/skills/helix-section-agent/evals/qualifications/helix-section-agent-qualification.json",
);

const problems = [];
const fail = (message) => problems.push(message);

const pkg = JSON.parse(readFileSync(packagePath, "utf8"));
const { qualification_status: status, qualification_hash: recorded } = pkg.skill;

if (status !== "passed") {
  fail(
    `PKG-005: qualification_status is "${status}". A pinned run may reference only a passing qualification.\n` +
      `     5.2.3 is pending because it cannot be drafted reliably under its own rules. The presentation\n` +
      `     contract asks for male and female tables at every timepoint, roughly forty cells; SKILL.md\n` +
      `     rule 3 requires a claim id on every table cell; the envelope supplies one validated claim.\n` +
      `     The agent resolves that about half the time by drafting and half by returning a structured\n` +
      `     failure. Widen required_claims, or let rule 3 accept executor provenance for a table cell.\n` +
      `     Re-run scripts/record-qualification.mjs once the suite is reliably green.`,
  );
} else {
  console.log(`status ok        qualification_status is "passed"`);
}

if (!existsSync(artifactPath)) {
  fail(`no qualification artifact at ${artifactPath}; run scripts/record-qualification.mjs`);
} else {
  const artifact = JSON.parse(readFileSync(artifactPath, "utf8"));

  if (artifact.qualification_hash !== recorded) {
    fail(`package records ${recorded} but the artifact records ${artifact.qualification_hash}`);
  } else {
    console.log(`record ok        package and artifact agree on the digest`);
  }

  for (const [relative, certified] of Object.entries(artifact.inputs)) {
    const path = resolve(root, relative);
    if (!existsSync(path)) {
      fail(`${relative} was certified but is missing`);
      continue;
    }
    const actual = fileHash(path);
    actual === certified
      ? console.log(`input ok         ${relative}`)
      : fail(`${relative} changed since qualification. Certified ${certified}, found ${actual}. Re-run scripts/record-qualification.mjs.`);
  }

  const recomputed = canonicalHash({ inputs: artifact.inputs, outcome: artifact.outcome });
  recomputed === artifact.qualification_hash
    ? console.log(`digest ok        recomputes to ${recomputed}`)
    : fail(`artifact digest does not recompute. Recorded ${artifact.qualification_hash}, recomputed ${recomputed}.`);
}

if (problems.length > 0) {
  for (const problem of problems) console.error(`FAIL ${problem}`);
  process.exit(1);
}

console.log(JSON.stringify({ verified: true, qualification_status: status, qualification_hash: recorded }));
