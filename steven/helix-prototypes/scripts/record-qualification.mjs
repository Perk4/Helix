// Records a Tier-1 skill qualification on a section package (PKG-005).
//
// Recording by hand is forbidden: the digest has to be reproducible by a
// reviewer who checks out the tree and re-runs this. So the script owns the
// whole path — run the suite, refuse on red, hash the inputs, write the fields.
//
//   node scripts/record-qualification.mjs [--dry-run]

import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { relative, resolve } from "node:path";

import { canonicalHash, fileHash } from "./lib/hash.mjs";

const root = resolve(import.meta.dirname, "..");
const evalsDir = resolve(root, ".agents/skills/helix-section-agent/evals");
const skillPath = resolve(root, ".agents/skills/helix-section-agent/SKILL.md");
const packagePath = resolve(root, "skills/helix-evidence-pipeline/packages/sections/5_2_3_body_weight/package.json");
const qualificationsDir = resolve(evalsDir, "qualifications");
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

// Warn when a feature branch already changes something this digest covers.
//
// A qualification certifies the tree it was taken from, so one taken the day
// before an upstream branch lands is stale on arrival. That has happened three
// times: a section-skills move, a SKILL.md edit, and a retry cap — each found
// only after the work was done. Checking here means it surfaces at the one
// moment it matters, when you are about to certify.
//
// Informational. It does not block: the branch may never merge, and a warning
// a reviewer can weigh beats a gate that cries wolf.
const warnOnUpstreamChanges = () => {
  const ref = process.env.HELIX_UPSTREAM_REF ?? "origin/feat/steven-workspace";
  let changed;
  try {
    // The package is not a hashed input, but it is where the qualification is
    // written. An upstream branch editing it is the collision we actually hit:
    // a hand-written status and hash landing on top of a recorded one.
    changed = execFileSync("git", ["diff", "--name-only", `origin/main...${ref}`, "--", ...inputPaths, packagePath], {
      cwd: root,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    })
      .split("\n")
      .filter(Boolean);
  } catch {
    return; // ref not fetched, or not a git checkout; nothing to say
  }
  if (changed.length === 0) return;
  console.warn(`\nWARNING ${ref} already changes ${changed.length} file(s) this digest covers:`);
  for (const path of changed) console.warn(`  ${path}`);
  console.warn("Recording now certifies a tree that branch will replace. Consider waiting for it to land.\n");
};

warnOnUpstreamChanges();

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
const outcome = {
  suite_id: suite.id,
  suite_version: suite.version,
  cases: cases.length,
  assertions: assertions.length,
  assertion_shape: cases.map((entry) => ({
    description: entry.description,
    assertions: entry.assertions.map((assertion) => ({ type: assertion.type, value: assertion.value ?? null })),
  })),
};

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
  resolve(qualificationsDir, `${suite.id}.json`),
  `${JSON.stringify({ qualification_id: qualificationId, qualification_hash: qualificationHash, inputs, outcome }, null, 2)}\n`,
  "utf8",
);

console.log(`recorded ${qualificationHash}`);
for (const [path, hash] of Object.entries(inputs)) console.log(`  input ${hash}  ${path}`);
