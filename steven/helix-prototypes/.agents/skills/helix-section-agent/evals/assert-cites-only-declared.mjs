// SKILL.md rule 2: use cross-section facts only from dependencies declared in
// the Section Package.
//
// Rule 2 has two halves and only one is visible in output.
//
// The attempt is enforced, not evaluated. `cross_section_queries.py` builds
// its allowed set from the envelope's `direct_dependencies` and records
// anything else in `rejected_artifact_ids` with "Cross-Section Queries cannot
// read undeclared data." A draft cannot obtain undeclared data at runtime.
//
// The citation is what this checks. A draft can still *claim* to rest on a
// claim or artifact the envelope never declared, which reads as provenance to
// anyone downstream and resolves to nothing. That is visible in the candidate,
// so it belongs in the suite.
//
// Rule 6, do not inspect unrelated raw source files, stays uncovered. The run
// receipt records skill and candidate hashes and a Codex thread id, and no
// file-access trail, so there is nothing to assert against. Recorded as a gap
// rather than papered over with a check that cannot fail.

export default function (output, context) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }

  const envelope = context?.vars?.envelope;
  const parsed = typeof envelope === "string" ? JSON.parse(envelope) : envelope;

  const declared = new Set([
    ...(parsed?.validated_claims ?? []).map((claim) => claim.claim_id),
    ...(parsed?.direct_dependencies ?? []).map((dependency) => dependency.artifact_id),
    ...(parsed?.executor_receipts ?? []).map((receipt) => receipt.artifact_id),
  ]);

  const cited = [
    ...(candidate.validated_claim_ids ?? []),
    ...(candidate.executor_receipt_ids ?? []),
  ];

  const undeclared = [...new Set(cited.filter((id) => !declared.has(id)))];
  if (undeclared.length > 0) {
    return {
      pass: false,
      score: 0,
      reason: `cited ${undeclared.join(", ")}, which the envelope never declared`,
    };
  }

  return { pass: true, score: 1, reason: `cited ${cited.length} identifier(s), all declared` };
}
