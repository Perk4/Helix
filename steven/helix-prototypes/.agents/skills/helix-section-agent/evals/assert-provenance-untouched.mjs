// SKILL.md rule 8: do not create or edit provenance.
//
// Untested until now, and invisible to every other assertion. A draft that
// invents an executor receipt id, or cites one the envelope never supplied,
// still satisfies the contract schema, cites the right claim, states the right
// number, and passes both rubrics. Provenance is what lets a reviewer trace a
// figure back to a source record, so a fabricated receipt reference is a
// citation to nothing — and it looks exactly like a real one.
//
// Deterministic by nature: the envelope says which receipts exist, so this is
// set membership rather than judgement.

export default function (output, context) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }

  const envelope = context?.vars?.envelope;
  const parsed = typeof envelope === "string" ? JSON.parse(envelope) : envelope;
  const supplied = new Set((parsed?.executor_receipts ?? []).map((receipt) => receipt.artifact_id));

  // A structured failure legitimately cites no receipts. There is nothing to
  // tamper with and nothing to assert.
  const cited = candidate.executor_receipt_ids ?? [];
  if (cited.length === 0) {
    return { pass: true, score: 1, reason: "no receipts cited" };
  }

  const invented = cited.filter((id) => !supplied.has(id));
  if (invented.length > 0) {
    return {
      pass: false,
      score: 0,
      reason: `cited executor receipt ${invented.join(", ")}, which the envelope did not supply`,
    };
  }

  return { pass: true, score: 1, reason: `cited only supplied receipts (${cited.join(", ")})` };
}
