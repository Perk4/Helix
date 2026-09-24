// Records a Tier-1 skill qualification on a section package (PKG-005).
//
// Recording by hand is forbidden: the digest has to be reproducible by a
// reviewer who checks out the tree and re-runs this. So the script owns the
// whole path — run the suite, refuse on red, hash the inputs, write the fields.
//
//   node scripts/record-qualification.mjs [--dry-run]

import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { relative, resolve } from "node:path";

import { canonicalHash, fileHash } from "./lib/hash.mjs";

const root = resolve(import.meta.dirname, "..");
const evalsDir = resolve(root, ".agents/skills/helix-section-agent/evals");
const skillPath = resolve(root, ".agents/skills/helix-section-agent/SKILL.md");
const packagePath = resolve(root, "skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json");
const qualificationsDir = resolve(evalsDir, "qualifications");
const artifactPath = resolve(qualificationsDir, "helix-section-agent-qualification.json");
const dryRun = process.argv.includes("--dry-run");

const walk = (dir) =>
  readdirSync(dir).flatMap((name) => {
    const path = resolve(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });

// Everything that decides the outcome. The config pulls the skill, the prompt,
// the fixtures, the candidate contract, and the assertion scripts in by
// `file://`, so any of them can change behaviour while promptfooconfig.yaml
// stays byte-identical. A config-only digest would certify a skill that no
// longer behaves the way it was qualified.
//
// Derived from the config's own references rather than a hand-kept list, so a
// reference added later is covered without anyone remembering to add it here.
const configPath = resolve(evalsDir, "promptfooconfig.yaml");
const configSource = readFileSync(configPath, "utf8");
const referenced = [...configSource.matchAll(/file:\/\/(\S+)/g)]
  .map(([, reference]) => resolve(evalsDir, reference))
  .flatMap((path) => (statSync(path).isDirectory() ? walk(path) : [path]));

// References only. Walking `fixtures/` wholesale looks safer but is not: the
// tier-2 guardrails keep their fixtures in the same directory, so a blanket
// walk would invalidate a tier-1 qualification whenever a tier-2 fixture
// changed. A digest that moves for reasons outside the thing it certifies
// teaches reviewers to re-record without reading why.
const inputPaths = [...new Set([skillPath, configPath, ...referenced])].sort();

const inputs = Object.fromEntries(
  inputPaths.map((path) => [relative(root, path).split("\\").join("/"), fileHash(path)]),
);

const runSuite = () => {
  const outPath = resolve(root, ".promptfoo-qualification.json");
  try {
    execFileSync("npx", ["promptfoo", "eval", "-c", resolve(evalsDir, "promptfooconfig.yaml"), "-o", outPath, "--no-cache"], {
      cwd: root,
      stdio: "inherit",
      shell: process.platform === "win32",
    });
  } catch {
    // promptfoo exits non-zero when a test fails; read the report and report why.
  }
  const report = JSON.parse(readFileSync(outPath, "utf8"));
  rmSync(outPath, { force: true });
  return report;
};

const report = runSuite();
const stats = report.results?.stats ?? {};
const cases = (report.results?.results ?? []).map((entry) => ({
  description: entry.testCase?.description ?? "",
  assertions: (entry.gradingResult?.componentResults ?? []).map((component) => ({
    type: component.assertion?.type,
    value: component.assertion?.value,
    pass: component.pass === true,
  })),
}));

const assertions = cases.flatMap((entry) => entry.assertions);
const failures = assertions.filter((assertion) => !assertion.pass);

if (stats.failures > 0 || stats.errors > 0 || failures.length > 0 || cases.length === 0) {
  console.error(`FAIL suite is not green: ${stats.failures ?? "?"} failing cases, ${failures.length} failing assertions`);
  for (const assertion of failures) {
    console.error(`  - ${assertion.type}${assertion.value ? ` ${JSON.stringify(assertion.value)}` : ""}`);
  }
  console.error("No qualification recorded.");
  process.exit(1);
}

const suite = JSON.parse(readFileSync(packagePath, "utf8")).skill.promptfoo_suite;

// The outcome, not the transcript. promptfoo's report carries an eval id,
// timestamps, latency, token counts, and the model's prose — all of which move
// between runs. Hashing those would produce a digest nobody could reproduce.
// Token cost belongs in the certificate. It went from 8.5k to 68k across one
// week of making the suite faithful, and nothing noticed, because the perf
// rule only ever watched wall-clock. A qualification that silently costs eight
// times what it used to is a qualification nobody runs before pushing.
const tokens = stats.tokenUsage?.total ?? 0;

const outcome = {
  suite_id: suite.id,
  suite_version: suite.version,
  tokens,
  cases: cases.length,
  assertions: assertions.length,
  assertion_shape: cases.map((entry) => ({
    description: entry.description,
    assertions: entry.assertions.map((assertion) => ({ type: assertion.type, value: assertion.value ?? null })),
  })),
};

// Compare against the last certificate before writing a new one. Growth is
// expected as coverage grows; doubling without anyone deciding to is not.
const previous = existsSync(artifactPath) ? JSON.parse(readFileSync(artifactPath, "utf8")) : null;
const before = previous?.outcome?.tokens ?? 0;
if (before > 0 && tokens > before * 2) {
  console.error(`FAIL cost doubled: ${before} tokens at the last qualification, ${tokens} now.`);
  console.error("     Re-run to rule out variance. If the growth is intended, record it in the");
  console.error("     roadmap and delete the previous artifact to accept the new baseline.");
  process.exit(1);
}
if (before > 0) {
  console.log(`cost ok          ${tokens} tokens against ${before} at the last qualification`);
}

const qualificationHash = canonicalHash({ inputs, outcome });
const pkg = JSON.parse(readFileSync(packagePath, "utf8"));
const recorded = pkg.skill.qualification_hash;

if (recorded === qualificationHash && pkg.skill.qualification_status === "passed") {
  console.log(`unchanged ${qualificationHash}`);
  console.log("Tree matches the recorded qualification. Nothing rewritten.");
  process.exit(0);
}

const qualificationId = `${suite.id}@${suite.version}/${new Date().toISOString().replace(/\.\d{3}Z$/, "Z")}`;

if (dryRun) {
  console.log(`would record ${qualificationHash}`);
  console.log(`would set    qualification_id ${qualificationId}`);
  for (const [path, hash] of Object.entries(inputs)) console.log(`  input ${hash}  ${path}`);
  process.exit(0);
}

pkg.skill.qualification_status = "passed";
pkg.skill.qualification_id = qualificationId;
pkg.skill.qualification_hash = qualificationHash;
writeFileSync(packagePath, `${JSON.stringify(pkg, null, 2)}\n`, "utf8");

mkdirSync(qualificationsDir, { recursive: true });
writeFileSync(
  artifactPath,
  `${JSON.stringify({ qualification_id: qualificationId, qualification_hash: qualificationHash, inputs, outcome }, null, 2)}\n`,
  "utf8",
);

console.log(`recorded ${qualificationHash}`);
for (const [path, hash] of Object.entries(inputs)) console.log(`  input ${hash}  ${path}`);
