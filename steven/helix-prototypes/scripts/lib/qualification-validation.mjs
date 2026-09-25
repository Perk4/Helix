const isNonEmptyString = (value) => typeof value === "string" && value.trim().length > 0;

export function validateObservedProviderIds(providerIds, expectedProviderId) {
  const observed = [...new Set(providerIds.filter(isNonEmptyString))];

  if (observed.length !== 1) {
    return [
      `qualification report must contain exactly one distinct non-empty provider ID; observed ${observed.length === 0 ? "none" : observed.join(", ")}`,
    ];
  }

  if (observed[0] !== expectedProviderId) {
    return [`qualification report provider ${observed[0]} does not equal HELIX_PROMPTFOO_PROVIDER ${expectedProviderId}`];
  }

  return [];
}

export function validateOutcomeBindings(outcome) {
  const problems = [];

  if (!isNonEmptyString(outcome?.drafter)) {
    problems.push("qualification outcome.drafter must be a non-empty string");
  }
  if (!isNonEmptyString(outcome?.judge)) {
    problems.push("qualification outcome.judge must be a non-empty string");
  }

  return problems;
}
