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

  // Deliberately not asserting that content_blocks is empty. SKILL.md asks the
  // agent to report the gap, and a paragraph naming the absent claim does that
  // as well as an empty draft does. An earlier version failed exactly such a
  // response. The two rules above are the ones that matter: cite no claim the
  // envelope did not supply, and state no figure nothing supplied.
  return { pass: true, score: 1, reason: "no claim cited, no value stated" };
}
