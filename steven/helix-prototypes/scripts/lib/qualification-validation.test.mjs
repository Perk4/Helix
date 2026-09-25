import assert from "node:assert/strict";
import test from "node:test";

import { validateObservedProviderIds, validateOutcomeBindings } from "./qualification-validation.mjs";

const expected = "azureopenai:chat:gpt-5.5";

test("recorder rejects missing observed provider IDs", () => {
  assert.deepEqual(validateObservedProviderIds([undefined, null, "", "   "], expected), [
    "qualification report must contain exactly one distinct non-empty provider ID; observed none",
  ]);
});

test("recorder rejects multiple observed provider IDs", () => {
  assert.deepEqual(validateObservedProviderIds([expected, "openai:gpt-4.1", expected], expected), [
    `qualification report must contain exactly one distinct non-empty provider ID; observed ${expected}, openai:gpt-4.1`,
  ]);
});

test("recorder rejects a mismatched observed provider ID", () => {
  assert.deepEqual(validateObservedProviderIds(["openai:gpt-4.1"], expected), [
    `qualification report provider openai:gpt-4.1 does not equal HELIX_PROMPTFOO_PROVIDER ${expected}`,
  ]);
});

test("recorder accepts exactly one matching observed provider ID", () => {
  assert.deepEqual(validateObservedProviderIds([expected, expected], expected), []);
});

test("verifier rejects a missing drafter binding", () => {
  assert.deepEqual(validateOutcomeBindings({ judge: "anthropic:messages:claude-sonnet-4-6" }), [
    "qualification outcome.drafter must be a non-empty string",
  ]);
});

test("verifier rejects a missing judge binding", () => {
  assert.deepEqual(validateOutcomeBindings({ drafter: expected }), [
    "qualification outcome.judge must be a non-empty string",
  ]);
});

test("verifier accepts complete model bindings", () => {
  assert.deepEqual(
    validateOutcomeBindings({
      drafter: expected,
      judge: "anthropic:messages:claude-sonnet-4-6",
    }),
    [],
  );
});
