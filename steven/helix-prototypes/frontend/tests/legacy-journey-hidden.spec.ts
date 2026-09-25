import { expect, test, type Page, type Route } from "@playwright/test";

import {
  freezeFixture,
  frozenWorkspace,
  journeyAt,
  liveWorkspace,
  stageButtons,
  studyId,
  trackCommands,
  type Json,
  type Journey,
} from "./lane-a-helpers";
import { legacyJourney, openLegacyJourney } from "./legacy-journey";

// DH-2 (#66): the legacy StudyJourney is off the default stage path. Every governed command it
// offered is on a stage view; the Draft-stage human decisions it alone offered (retry, revise,
// first attempt in a new cycle) are on the Draft stage view. Every command response is mocked.

const BW = "section.5_2_3_body_weight";
const REVISED = "CYCLE-REV0000001";
const hash = (seed: string) => `sha256:${seed.repeat(16)}`;
const stageIds = freezeFixture.after.journey.stages.map((stage) => stage.stage_id);
const LEGACY_CONTROLS = [
  "run-validation",
  "run-body-weight-validation",
  "draft-body-weight",
  "retry-body-weight",
  "revise-body-weight",
  "evaluate-candidate",
  "query-cross-section",
  "promote-section-draft",
];

type DraftState = {
  cycles: string[];
  attempts: Array<{ cycle: string; attempt: number; action: "retry" | "stop_for_review"; maxAttempts?: number }>;
  canRevise: boolean;
};

/** liveWorkspace, also tolerating a refetch still in flight when the test ends (teardown race). */
async function serverWorkspace(route: Route): Promise<Json | null> {
  try {
    return await liveWorkspace(route);
  } catch (error) {
    if (/Test ended/i.test(String(error))) return null;
    throw error;
  }
}

function runId(cycle: string, attempt: number) {
  return `SRUN-${cycle.replace("CYCLE-", "")}-${attempt}`;
}

function storedAttempt(cycle: string, attempt: number): Json {
  const id = runId(cycle, attempt);
  const receipt = {
    run_id: id,
    section_id: "5_2_3_body_weight",
    section_package_id: BW,
    status: "candidate_recorded",
    candidate_id: `SDC-${id}`,
    candidate_hash: hash("cafe"),
    envelope_hash: hash("a11e"),
    agent_runtime: "codex_sdk",
    codex_thread_id: `thread-${id}`,
    skill_name: "helix-section-agent",
    skill_hash: hash("b0b0"),
    skill_references_hash: hash("b0b0"),
    review_scaffold_revision: attempt + 1,
    idempotent_replay: false,
  };
  return {
    receipt,
    candidate: {
      schema_version: "helix.section-draft-candidate/v1",
      status: "section_draft_candidate",
      candidate_id: receipt.candidate_id,
      run_id: id,
      section_id: "5_2_3_body_weight",
      section_package_id: BW,
      section_package_version: "0.1.0",
      drafting_cycle_id: cycle,
      attempt,
      validated_claim_ids: ["C-BW-HIGH"],
      content_blocks: [],
      executor_receipt_ids: [],
      agent_receipt: { runtime: "codex_sdk", thread_id: receipt.codex_thread_id, skill_name: "helix-section-agent" },
    },
    envelope: {},
    review_scaffold: {},
  };
}

function evaluation(cycle: string, attempt: number, action: "retry" | "stop_for_review", maxAttempts = 3): Json {
  const id = runId(cycle, attempt);
  return {
    evaluation_id: `CEV-${id}`,
    run_id: id,
    candidate_id: `SDC-${id}`,
    candidate_hash: hash("cafe"),
    provenance_receipt: { receipt_id: `PRV-${id}`, status: "failed", bindings: [] },
    study_output_evaluation_receipt: { status: "passed", enforcement_class: "review_required" },
    template_conformance_receipt: { status: "passed", results: [] },
    hashes: { evaluation: hash("eeee") },
    next_attempt_decision: {
      action,
      attempt,
      max_attempts: maxAttempts,
      reasons: ["Provenance compilation failed"],
      blocking_receipt_ids: [`PRV-${id}`],
    },
  };
}

function cycle(cycleId: string, predecessor: string | null): Json {
  return {
    schema_version: "helix.drafting-cycle/v1",
    cycle_id: cycleId,
    run_id: "RUN-CYCLE000001",
    section_package_id: BW,
    predecessor_cycle_id: predecessor,
    max_attempts: 3,
    impact_set: { origin_section_package_id: BW, direct: [BW], transitive: [] },
    opened_at: "2026-09-24T12:00:00Z",
    opened_by: predecessor ? "Dr. Ada Path" : "HELIX Codex section runtime",
    triggering_event_id: `EV-${cycleId}`,
  };
}

/** The server reports Draft complete once validation passes; Traceability is then current. */
function draftComplete(): Journey {
  return journeyAt("traceability");
}

function draftWorkspace(live: Json, state: DraftState): Json {
  return frozenWorkspace(live, {
    section_run_eligibility: (live.section_run_eligibility as Json[]).map((entry) =>
      entry.section_package_id === BW ? { ...entry, eligible: true, reasons: [] } : entry,
    ),
    section_runs: state.attempts.map((item) => storedAttempt(item.cycle, item.attempt)),
    cross_section_queries: state.attempts.map((item) => ({
      query_id: `CSQ-${runId(item.cycle, item.attempt)}`,
      run_id: runId(item.cycle, item.attempt),
      status: "returned",
      requested_artifact_ids: [],
      returned: [],
      rejected_artifact_ids: [],
    })),
    candidate_evaluations: state.attempts.map((item) => evaluation(item.cycle, item.attempt, item.action, item.maxAttempts)),
    promotion_decisions: [],
    section_drafts: [],
    drafting_cycles: state.cycles.map((id, index) => cycle(id, index === 0 ? null : state.cycles[index - 1])),
    can_open_revision: state.canRevise,
    journey: draftComplete(),
  });
}

type Bodies = { sectionRuns: Json[]; revisions: Json[] };

async function serveDraft(page: Page, state: DraftState): Promise<Bodies> {
  const bodies: Bodies = { sectionRuns: [], revisions: [] };
  await page.route("**/api/v1/studies/*/workspace", async (route) => {
    const live = await serverWorkspace(route);
    if (live) await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(draftWorkspace(live, state)) });
  });
  await page.route("**/api/v1/studies/*/pinned-runs/*/events", (route) =>
    route.fulfill({ status: 200, contentType: "text/event-stream", body: "" }),
  );
  await page.route("**/api/v1/studies/*/section-runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    const body = (route.request().postDataJSON() ?? {}) as Json;
    bodies.sectionRuns.push(body);
    const key = String(body.idempotency_key);
    const match = /-body-weight-(CYCLE-[A-Z0-9-]+)-attempt-(\d+)$/.exec(key);
    const cycleId = match?.[1] ?? "CYCLE-BW-001";
    const attempt = Number(match?.[2] ?? 1);
    state.attempts.push({ cycle: cycleId, attempt, action: "retry" });
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify(storedAttempt(cycleId, attempt).receipt),
    });
  });
  await page.route("**/api/v1/studies/*/section-revisions", async (route) => {
    bodies.revisions.push((route.request().postDataJSON() ?? {}) as Json);
    state.cycles.push(REVISED);
    state.canRevise = false;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        cycle: cycle(REVISED, "CYCLE-BW-001"),
        stale_disposition_ids: [],
        stale_approval_ids: [],
        review_scaffold_revision: 4,
        idempotent_replay: false,
      }),
    });
  });
  return bodies;
}

async function openDraftStage(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await stageButtons(page).nth(stageIds.indexOf("draft")).click();
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "draft");
}

async function expectNoLegacyJourney(page: Page) {
  await expect(legacyJourney(page)).toHaveCount(0);
  for (const id of LEGACY_CONTROLS) await expect(page.getByTestId(id)).toHaveCount(0);
}

const live = (page: Page) => page.getByTestId("agent-live");

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.sessionStorage.clear());
});

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("no stage on the default path renders StudyJourney, and each agent stage has one set of agent controls", async ({ page }) => {
  await page.route("**/api/v1/studies/*/workspace", async (route) => {
    const body = await serverWorkspace(route);
    if (!body) return;
    const journey = journeyAt("validate");
    journey.stages = journey.stages.map((stage) => ({ ...stage, selectable: true }));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(frozenWorkspace(body, { journey })) });
  });
  const commands = trackCommands(page);
  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await expect(page.getByTestId("legacy-journey-toggle")).toHaveAttribute("aria-expanded", "false");
  for (const [index, stageId] of stageIds.entries()) {
    await stageButtons(page).nth(index).click();
    await expect(page.getByTestId("stage-view")).toHaveAttribute("data-selected-stage", stageId);
    await expectNoLegacyJourney(page);
    await expect(page.getByTestId("agent-commands")).toHaveCount(stageId === "validate" ? 1 : 0);
  }
  // Viewing stages sends no governed command (Gate 3 drafts its section content on open, lane D).
  expect(commands.filter((item) => !item.includes("/sections/"))).toEqual([]);
});

test("the Draft stage offers the retry StudyJourney offered, with the same governed key", async ({ page }) => {
  const state: DraftState = { cycles: ["CYCLE-BW-001"], attempts: [{ cycle: "CYCLE-BW-001", attempt: 1, action: "retry" }], canRevise: false };
  const bodies = await serveDraft(page, state);
  await openDraftStage(page);
  await expectNoLegacyJourney(page);
  // The server reports Draft complete, so the agent's stop is read from the evidence here.
  await expect(page.getByTestId("evidence-next-attempt")).toContainText("retry · attempt 1 of 3");
  const retry = page.getByTestId("agent-human-retry");
  await expect(retry).toHaveText("Retry candidate (attempt 2 of 3)");
  await expect(page.getByTestId("agent-human-revise")).toHaveCount(0);
  await retry.click();
  await expect(live(page)).toContainText("recorded by the server");
  // A person's decision keeps the Draft view; it does not follow the server stage (DH-1).
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "draft");
  expect(bodies.sectionRuns).toEqual([
    expect.objectContaining({ section_package_id: BW, idempotency_key: `workbench-${studyId}-body-weight-CYCLE-BW-001-attempt-2` }),
  ]);
  await expect(page.getByTestId("agent-human-retry")).toHaveText("Retry candidate (attempt 3 of 3)");
});

test("after stop_for_review there is no fourth attempt; revise and the new cycle's first attempt are on the Draft stage", async ({ page }) => {
  const state: DraftState = {
    cycles: ["CYCLE-BW-001"],
    attempts: [1, 2, 3].map((attempt) => ({ cycle: "CYCLE-BW-001", attempt, action: attempt === 3 ? "stop_for_review" : "retry" })),
    canRevise: true,
  };
  const bodies = await serveDraft(page, state);
  const commands = trackCommands(page);
  await openDraftStage(page);
  await expectNoLegacyJourney(page);
  await expect(page.getByTestId("agent-human-retry")).toHaveCount(0);
  await page.getByTestId("agent-human-revise").click();
  await expect(live(page)).toContainText(`${REVISED} opened from CYCLE-BW-001`);
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "draft");
  expect(bodies.revisions).toEqual([
    expect.objectContaining({ section_package_id: BW, idempotency_key: `workbench-${studyId}-revise-CYCLE-BW-001` }),
  ]);
  await expect(page.getByTestId("agent-human-revise")).toHaveCount(0);
  // The agent still reads the previous cycle's stop; the first attempt in the new cycle is a person's command.
  const draftCycle = page.getByTestId("agent-human-draft-cycle");
  await expect(draftCycle).toHaveText(`Draft attempt 1 in ${REVISED}`);
  await draftCycle.click();
  await expect(live(page)).toContainText("recorded by the server");
  expect(bodies.sectionRuns).toEqual([
    expect.objectContaining({ idempotency_key: `workbench-${studyId}-body-weight-${REVISED}-attempt-1` }),
  ]);
  await expect(page.getByTestId("agent-human-draft-cycle")).toHaveCount(0);
  expect(commands.filter((item) => !item.endsWith("/workspace"))).toEqual([
    `POST /api/v1/studies/${studyId}/section-revisions`,
    `POST /api/v1/studies/${studyId}/section-runs`,
  ]);
});

test("a stopped cycle with no revision offered shows the agent stop and no human commands", async ({ page }) => {
  const state: DraftState = {
    cycles: ["CYCLE-BW-001"],
    attempts: [1, 2, 3].map((attempt) => ({ cycle: "CYCLE-BW-001", attempt, action: attempt === 3 ? "stop_for_review" : "retry" })),
    canRevise: false,
  };
  const commands = trackCommands(page);
  await serveDraft(page, state);
  await openDraftStage(page);
  await expect(page.getByTestId("evidence-next-attempt")).toContainText("stop_for_review · attempt 3 of 3");
  await expect(page.getByTestId("agent-human-decisions")).toHaveCount(0);
  expect(commands).toEqual([]);
});

test("retry is hidden on the Draft stage exactly when StudyJourney hid it (legacy cap of 3 attempts)", async ({ page }) => {
  // The server asks for a retry at attempt 3 of 4; StudyJourney never offered a fourth attempt.
  const state: DraftState = {
    cycles: ["CYCLE-BW-001"],
    attempts: [1, 2, 3].map((attempt) => ({ cycle: "CYCLE-BW-001", attempt, action: "retry", maxAttempts: 4 })),
    canRevise: false,
  };
  const commands = trackCommands(page);
  await serveDraft(page, state);
  await openDraftStage(page);
  await expect(page.getByTestId("evidence-next-attempt")).toContainText("retry · attempt 3 of 4");
  await expect(page.getByTestId("agent-human-retry")).toHaveCount(0);
  await expect(page.getByTestId("agent-human-decisions")).toHaveCount(0);
  // Same shared predicate: the legacy panel hides its retry control too.
  await openLegacyJourney(page);
  await expect(page.getByTestId("candidate-attempt-CYCLE-BW-001-3")).toBeVisible();
  await expect(page.getByTestId("retry-body-weight")).toHaveCount(0);
  expect(commands).toEqual([]);
});

test("the legacy records stay reachable behind one toggle and hide again", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await openLegacyJourney(page);
  await expect(page.getByTestId("template-contract-gates")).toBeVisible();
  await page.getByTestId("legacy-journey-toggle").click();
  await expect(page.getByTestId("legacy-journey-toggle")).toHaveAttribute("aria-expanded", "false");
  await expect(legacyJourney(page)).toHaveCount(0);
});
