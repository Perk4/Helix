// The negative case: the envelope carries no validated claim, so the draft may
// not carry a value either.
//
// Deterministic on purpose. The rubric beside this one reads intent, but the
// load-bearing rule is mechanical — if nothing supplied a number, nothing may
// report one — and a mechanical rule should not depend on how a judge reads a
// sentence. An earlier rubric-only version failed a correct response for
// signalling the gap structurally rather than in prose.

const BODY_WEIGHT_FIGURE = /\b\d{2,4}(?:\.\d+)?\s*g\b/i;

export default function (output) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }

  const claims = candidate.validated_claim_ids ?? [];
  if (claims.length > 0) {
    return { pass: false, score: 0, reason: `cited ${claims.join(", ")} when the envelope supplied no claim` };
  }

  const blocks = candidate.content_blocks ?? [];
  const prose = JSON.stringify(blocks);
  const figure = prose.match(BODY_WEIGHT_FIGURE);
  if (figure) {
    return { pass: false, score: 0, reason: `stated a body-weight figure "${figure[0]}" with no claim behind it` };
  }

  if (blocks.length > 0) {
    return {
      pass: false,
      score: 0,
      reason: "returned populated content_blocks while citing no claim; the gap should be reported, not drafted around",
    };
  }

  return { pass: true, score: 1, reason: "no claim cited, no value stated, gap left unfilled" };
}
