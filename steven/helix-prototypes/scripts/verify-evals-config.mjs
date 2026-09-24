// Guards the Promptfoo eval configs against the two ways they fail silently:
// a `${...}` placeholder nobody documented, and a `file://` reference that no
// longer resolves. Either one turns a green suite into a suite that proved
// nothing. Run before every push.

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const evalsDir = resolve(root, ".agents/skills/helix-section-agent/evals");
const configs = ["promptfooconfig.yaml", "study-output.yaml"].map((name) => resolve(evalsDir, name));
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

if (problems.length > 0) {
  for (const problem of problems) { console.error(`FAIL ${problem}`); }
  process.exit(1);
}

console.log(JSON.stringify({ verified: true, configs: configs.length, placeholders_documented: true, references_resolved: true, skill_in_prompt: true }));
