// Guards the Promptfoo eval configs against the two ways they fail silently:
// a `${...}` placeholder nobody documented, and a `file://` reference that no
// longer resolves. Either one turns a green suite into a suite that proved
// nothing. Run before every push.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const evalsDir = resolve(root, ".agents/skills/helix-section-agent/evals");
// `study-output.yaml` is deliberately absent: it is a flat assert list the
// backend parses, not a promptfoo config, so it has no placeholders or
// `file://` references to check and the checks below would misread it.
const configs = ["promptfooconfig.yaml", "glp-guardrails.yaml"].map((name) => resolve(evalsDir, name));
const envExample = resolve(root, ".env.example");

const problems = [];
const fail = (message) => problems.push(message);

const documented = new Set(
  readFileSync(envExample, "utf8")
    .split("\n")
    .map((line) => line.match(/^([A-Z_][A-Z0-9_]*)=/)?.[1])
    .filter(Boolean),
);

for (const configPath of configs) {
  if (!existsSync(configPath)) { fail(`config is missing: ${configPath}`); continue; }
  const source = readFileSync(configPath, "utf8");

  // Promptfoo renders config through nunjucks with `env` in scope, so the
  // binding is `{{ env.NAME }}`. A bare `${NAME}` is passed through verbatim
  // and reaches the provider loader as a literal, which is how an unbound
  // provider used to fail. Reject that shape outright.
  for (const [, stray] of source.matchAll(/\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g)) {
    fail(`${configPath} uses \${${stray}}, which promptfoo does not substitute. Use {{ env.${stray} }}`);
  }

  for (const [, name] of source.matchAll(/\{\{\s*env\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/g)) {
    documented.has(name)
      ? console.log(`placeholder ok   ${name} -> documented in .env.example`)
      : fail(`placeholder ${name} in ${configPath} has no entry in .env.example`);
  }

  for (const [, reference] of source.matchAll(/file:\/\/(\S+)/g)) {
    const target = resolve(dirname(configPath), reference);
    existsSync(target)
      ? console.log(`reference ok     ${reference} -> ${target}`)
      : fail(`file:// reference ${reference} in ${configPath} does not resolve to ${target}`);
  }
}

// The skill is the artifact under qualification. A suite that never loads it
// measures the base model instead, and every assertion below becomes noise.
const qualificationConfig = readFileSync(configs[0], "utf8");
qualificationConfig.includes("file://../SKILL.md") || fail("promptfooconfig.yaml does not load SKILL.md into the judged prompt");
readFileSync(resolve(evalsDir, "prompt.txt"), "utf8").includes("{{skill}}") || fail("prompt.txt does not render {{skill}}");

// Every envelope fixture must be a real Section Execution Envelope, and must
// exercise every property the contract defines — not merely the required ones.
//
// Both halves earned their place. The fixtures were missing `pinned_run_id`,
// which the contract requires, so they were never valid envelopes at all. And
// when the executor receipt gained `facts` and `provenance`, the fixtures kept
// the old shape: the suite handed the agent no computed numbers while
// production handed it group means and forty provenance entries. The
// qualification certified behaviour against an envelope that no longer existed.
//
// Checking optional properties too is the point. `facts` is optional in the
// contract, so a required-only check would have passed the drift.
const envelopeSchemaPath = resolve(root, "skills/helix-evidence-pipeline/contracts/section-execution-envelope.schema.json");
const envelopeSchema = JSON.parse(readFileSync(envelopeSchemaPath, "utf8"));

const missingProperties = (value, schema, trail = "") =>
  Object.entries(schema.properties ?? {}).flatMap(([name, property]) => {
    if (value?.[name] === undefined) return [`${trail}${name}`];
    const item = Array.isArray(value[name]) ? value[name][0] : value[name];
    const itemSchema = property.items ?? property;
    const resolved = itemSchema.$ref
      ? envelopeSchema.$defs?.[itemSchema.$ref.replace("#/$defs/", "")]
      : itemSchema;
    return resolved?.properties && item ? missingProperties(item, resolved, `${trail}${name}.`) : [];
  });

for (const fixture of ["body-weight-envelope.json", "body-weight-missing-claim.json"]) {
  const path = resolve(evalsDir, "fixtures", fixture);
  if (!existsSync(path)) { fail(`envelope fixture is missing: ${fixture}`); continue; }
  const gaps = missingProperties(JSON.parse(readFileSync(path, "utf8")), envelopeSchema);
  gaps.length === 0
    ? console.log(`envelope ok      ${fixture} exercises every contract property`)
    : fail(`${fixture} does not exercise ${gaps.join(", ")}. The contract moved and the fixture did not; regenerate it from a real envelope.`);
}

// Judge fixtures must read as ordinary study sections.
//
// The eval playbook bars meta words from anything the judged model sees: a
// fixture that announces it is a test invites the model to perform rather
// than behave. This was checked by hand when G-1 and G-2 were authored, which
// is not a mechanism — the next fixture gets written by someone who never
// read the playbook.
//
// Matches the meta senses only. "the highest dose tested" is ordinary
// toxicology and tripped a naive substring version of this check.
const META = /\b(eval|evaluation|judge|judging|rubric|scored?|scoring|candidate|test case|testing|benchmark|arena|fixture|ground truth|expected)\b/gi;

for (const name of readdirSync(resolve(evalsDir, "fixtures")).filter((file) => file.startsWith("study-"))) {
  const body = readFileSync(resolve(evalsDir, "fixtures", name), "utf8");
  const leaks = [...new Set([...body.matchAll(META)].map((match) => match[0].toLowerCase()))];
  leaks.length === 0
    ? console.log(`blinding ok      ${name}`)
    : fail(`${name} leaks ${leaks.join(", ")} into content the judge reads; fixtures must read as ordinary sections`);
}

if (problems.length > 0) {
  for (const problem of problems) { console.error(`FAIL ${problem}`); }
  process.exit(1);
}

console.log(JSON.stringify({ verified: true, configs: configs.length, placeholders_documented: true, references_resolved: true, skill_in_prompt: true }));
