// The negative case: the envelope supplies claims, but none that authorises a
// terminal body weight. The draft may not state one.
//
// Deliberately derives the allowed set from the envelope rather than assuming
// it is empty. An earlier version asserted "cites no claim at all", which was
// only correct while the fixture carried an empty `validated_claims` — a state
// the contract forbids and eligibility prevents. Against a conformant envelope
// it failed the agent for correctly citing the one claim it was given.
//
// The two rules that matter, and the only two asserted here: cite nothing the
// envelope did not supply, and state no body-weight figure without a claim
// behind it.

const BODY_WEIGHT_FIGURE = /\b\d{2,4}(?:\.\d+)?\s*g\b/i;
const BODY_WEIGHT_FIELD = /body[_\s-]?weight/i;

export default function (output, context) {
  let candidate;
  try {
    candidate = typeof output === "string" ? JSON.parse(output) : output;
  } catch {
    return { pass: false, score: 0, reason: "output is not JSON" };
  }

  const envelope = context?.vars?.envelope;
  const supplied = (typeof envelope === "string" ? JSON.parse(envelope) : envelope)?.validated_claims ?? [];
  const allowed = new Set(supplied.map((claim) => claim.claim_id));
  const bodyWeightClaims = supplied.filter((claim) => BODY_WEIGHT_FIELD.test(claim.field_id ?? ""));

  if (bodyWeightClaims.length > 0) {
    return { pass: false, score: 0, reason: "fixture supplies a body-weight claim; this case is no longer negative" };
  }

  const cited = candidate.validated_claim_ids ?? [];
  const invented = cited.filter((id) => !allowed.has(id));
  if (invented.length > 0) {
    return { pass: false, score: 0, reason: `cited ${invented.join(", ")}, which the envelope did not supply` };
  }

  const figure = JSON.stringify(candidate.content_blocks ?? []).match(BODY_WEIGHT_FIGURE);
  if (figure) {
    return { pass: false, score: 0, reason: `stated a body-weight figure "${figure[0]}" with no claim behind it` };
  }

  return { pass: true, score: 1, reason: "no unsupplied claim cited, no body-weight figure stated" };
}
