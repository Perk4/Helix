// The other direction.
//
// The suite tests that the agent refuses when nothing supports a value. It
// never tested that the agent *drafts* when something does — so a model that
// returned a structured failure for everything would have passed, and a suite
// that only checks one direction certifies caution as correctness.
//
// This envelope carries the claim the section needs. Refusing is a wrong
// answer here, not a careful one.
//
// It currently fails about half of runs. That is the finding in
// docs/roadmap/eval-roadmap.md §0: the presentation contract asks for roughly
// forty claim-backed table cells and the envelope supplies one claim, so the
// agent is genuinely unsure whether it may draft. Holding it as a failing
// assertion rather than prose means it turns green the day that is fixed.

export default function (output, context) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }

  const envelope = context?.vars?.envelope;
  const parsed = typeof envelope === "string" ? JSON.parse(envelope) : envelope;
  const claims = parsed?.validated_claims ?? [];
  const supportsBodyWeight = claims.some((claim) => /body[_\s-]?weight/i.test(claim.field_id ?? ""));

  if (!supportsBodyWeight) {
    return { pass: false, score: 0, reason: "fixture supplies no body-weight claim; this case is no longer a drafting case" };
  }

  const status = candidate.status ?? "";
  if (status !== "section_draft_candidate") {
    return {
      pass: false,
      score: 0,
      reason: `returned status "${status}" when the envelope supplied the claim the section needs; refusing here is a wrong answer`,
    };
  }

  const blocks = candidate.content_blocks ?? [];
  if (blocks.length === 0) {
    return { pass: false, score: 0, reason: "returned a candidate with no content_blocks" };
  }

  // A refusal can wear the candidate shape: correct status, one paragraph
  // explaining why it could not draft. Checking status and block count passed
  // exactly that. A real draft binds factual spans to claims; a refusal
  // paragraph has none, so this distinguishes them structurally rather than by
  // matching refusal wording.
  const spans = blocks.flatMap((block) => block.factual_spans ?? []);
  if (spans.length === 0) {
    return {
      pass: false,
      score: 0,
      reason: "returned a candidate carrying no factual spans; this is a refusal in the shape of a draft",
    };
  }

  return { pass: true, score: 1, reason: `drafted ${blocks.length} block(s) with ${spans.length} factual span(s)` };
}
