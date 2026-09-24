// Validates the draft against the real Section Draft Candidate contract.
//
// SKILL.md line 14 requires the candidate match this schema, and nothing
// checked it. `additionalProperties: false` is the part that earns its keep:
// without it the agent can invent a field and bury a banned word there, which
// is how `not-contains "approved"` came to fail on a draft that had obeyed the
// rule and said so in a field of its own.
//
// Handed to promptfoo as `type: javascript` rather than `is-json` because the
// contract declares draft 2020-12 and carries an `$id`. promptfoo's `is-json`
// validator rejects the first and collides on the second when two cases load
// the same file. Compiling once here fixes both and keeps the contract as the
// single source of truth rather than a copy pasted into the suite.

import Ajv2020 from "ajv/dist/2020.js";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const contract = resolve(
  import.meta.dirname,
  "../../../../skills/helix-evidence-pipeline/contracts/section-draft-candidate.schema.json",
);

const validate = new Ajv2020({ strict: false, allErrors: true }).compile(
  JSON.parse(readFileSync(contract, "utf8")),
);

export default function (output) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }
  if (validate(candidate)) {
    return { pass: true, score: 1, reason: "matches section-draft-candidate/v1" };
  }
  const detail = validate.errors
    .map((error) => `${error.instancePath || "/"} ${error.message}`)
    .join("; ");
  return { pass: false, score: 0, reason: `contract violation: ${detail}` };
}
