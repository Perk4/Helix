import { expect, test, type Page, type Route } from "@playwright/test";

import {
  clone,
  freezeFixture,
  frozenWorkspace,
  journeyAt,
  liveWorkspace,
  regulatoryClaim,
  stageButtons,
  trackCommands,
  type Json,
} from "./lane-a-helpers";

// Lane B (#21): the shared Agent Step view and the governed command sequence.
// The Pinned Run comes from the recorded freeze fixture, and every command response
// is mocked, so no test calls Codex or an LLM and none needs qualified packages.

const BW_SECTION = "section.5_2_3_body_weight";
const runId = freezeFixture.after.pinned_run.run_id;
const dvResults = (freezeFixture.after.data_validation_executions as Json[])[0].results as Json[];

const hybridResult = { ...clone(dvResults[0]), result_id: "VR-HYBRID-TEST-1", executor_id: null };

type Harness = {
  validated: boolean;
  bodies: Record<string, Json[]>;
  sectionRun: (route: Route) => Promise<void>;
  dataValidation: (route: Route, attempt: number) => Promise<void>;
};

async function harness(page: Page, overrides: Partial<Harness> = {}) {
  const h: Harness = {
    validated: false,
    bodies: {},
    sectionRun: (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Section Agent unavailable (test double)." }),
      }),
    dataValidation: (route) =>
      route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ...(freezeFixture.after.data_validation_executions as Json[])[0],
          receipt: {
            ...((freezeFixture.after.data_validation_executions as Json[])[0].receipt as Json),
            idempotent_replay: true,
          },
        }),
      }),
    ...overrides,
  };
  const record = (name: string, route: Route) => {
    (h.bodies[name] ??= []).push((route.request().postDataJSON() ?? {}) as Json);
  };
  await page.route("**/api/v1/studies/*/workspace", async (route) => {
    const live = await liveWorkspace(route);
    if (!live) return;
    const workspace = frozenWorkspace(live, {
      // Package results always appear in Workspace validations; a hybrid result is added only
      // after the validation run, so the agent must not mistake package results for it.
      validations: h.validated ? [...clone(dvResults), hybridResult] : clone(dvResults),
      section_run_eligibility: (live.section_run_eligibility as Json[]).map((entry) =>
        entry.section_package_id === BW_SECTION
          ? { ...entry, eligible: h.validated, reasons: h.validated ? [] : ["validation has not run"] }
          : entry,
      ),
      section_runs: [],
      cross_section_queries: [],
      candidate_evaluations: [],
      promotion_decisions: [],
      section_drafts: [],
      journey: journeyAt(h.validated ? "draft" : "validate"),
    });
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(workspace) });
  });
  let dvAttempt = 0;
  await page.route("**/api/v1/studies/*/data-validation-packages", async (route) => {
    record("data-validation", route);
    dvAttempt += 1;
    await h.dataValidation(route, dvAttempt);
  });
  await page.route("**/api/v1/studies/*/validation-runs", async (route) => {
    record("validation", route);
    h.validated = true;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        run_id: "VAL-TEST-1",
        study_id: "STUDY-HLX-028",
        planner: "fixture",
        planner_label: "Fixture planner for tool-contract testing",
        llm_used: false,
        rule_bundle_version: "helix-rules-1.0.0",
        results: dvResults,
        created_at: "2026-09-24T12:00:00Z",
      }),
    });
  });
  await page.route("**/api/v1/studies/*/section-runs", async (route) => {
    record("section-run", route);
    await h.sectionRun(route);
  });
  await page.route("**/api/v1/studies/*/section-runs/*/**", async (route) => {
    record("after-section-run", route);
    await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "must not be called" }) });
  });
  return h;
}

async function openStage(page: Page, name: RegExp) {
  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await stageButtons(page).filter({ hasText: name }).first().click();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.sessionStorage.clear());
});

test("current stage shows server boundary, evidence, and a disabled pause with its reason", async ({ page }) => {
  await harness(page);
  await page.goto("/");
  const view = page.getByTestId("agent-stage-view");
  await expect(view).toHaveAttribute("data-stage", "validate");
  await expect(page.getByTestId("agent-run-banner")).toContainText("Stage 5 of 9");
  await expect(page.getByTestId("agent-control-boundary")).toContainText("Control boundary");
  await expect(page.getByTestId("agent-stage-io")).toBeVisible();
  await expect(page.getByTestId("evidence-validation-count")).toContainText("not run");
  await expect(page.getByTestId("evidence-eligibility")).toContainText("Blocked");
  const pause = page.getByTestId("agent-pause");
  await expect(pause).toBeDisabled();
  await expect(pause).toHaveAccessibleDescription(/no pause or resume command/);
  await expect(page.getByText("Synthetic data · Not for submission").first()).toBeVisible();
  await expect(page.locator("body")).not.toContainText(regulatoryClaim);
  await page.screenshot({ path: "../evidence/ui-lane-b/agent-validate-current.png", fullPage: true });
});

test("completed stages are read-only review of recorded actions and never send commands", async ({ page }) => {
  await harness(page);
  const commands = trackCommands(page);
  await openStage(page, /Parse/);
  const view = page.getByTestId("agent-stage-view");
  await expect(view).toHaveAttribute("data-stage", "parse");
  await expect(page.getByTestId("agent-stage-review")).toBeVisible();
  await expect(page.getByTestId("agent-commands")).toHaveCount(0);
  await expect(page.getByTestId("evidence-pinned-run")).toContainText(runId);
  await expect(page.getByTestId("evidence-governed-inputs")).toBeVisible();
  await expect(page.getByTestId("agent-action").first()).toHaveAttribute("data-status", "done");
  await expect(page.getByTestId("agent-action").first()).toContainText("Recorded");
  await openStage(page, /Extract/);
  await expect(page.getByTestId("evidence-dvp-receipt")).toBeVisible();
  await expect(page.getByTestId("evidence-dvp-rules")).not.toBeEmpty();
  expect(commands).toEqual([]);
});

test("the sequence waits for refreshed state, stops on the first failure, and runs nothing after it", async ({ page }) => {
  const h = await harness(page);
  const commands = trackCommands(page);
  await page.goto("/");
  await page.getByTestId("agent-run-sequence").click();
  await expect(page.locator(".hx-notice.t-block")).toContainText("Run governed Section Agent failed");
  await expect(page.locator(".hx-notice.t-block")).toContainText("Section Agent unavailable (test double).");
  await expect(page.locator(".hx-notice.t-block")).toContainText("later steps did not run");
  await expect(page.locator(".hx-notice.t-block")).toHaveAttribute("role", "status");
  // Governed order: validation, then (after the refresh made the section eligible) the section run.
  expect(commands.filter((item) => !item.endsWith("/workspace"))).toEqual([
    "POST /api/v1/studies/STUDY-HLX-028/validation-runs",
    "POST /api/v1/studies/STUDY-HLX-028/section-runs",
  ]);
  expect(h.bodies["after-section-run"]).toBeUndefined();
  // The section-run key is run-scoped per #17.
  expect(h.bodies["section-run"][0].idempotency_key).toBe(
    `workbench:STUDY-HLX-028:${runId}:section-run:${BW_SECTION}:a1`,
  );
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "draft");
  await expect(page.getByTestId("evidence-draft")).toHaveCount(0);
  await expect(page.getByTestId("agent-evidence-missing")).toContainText("has not run");
  await page.screenshot({ path: "../evidence/ui-lane-b/agent-sequence-stopped.png", fullPage: true });
});

test("an unknown result reuses the key; a definite rejection gets a new attempt key", async ({ page }) => {
  let failFirst = true;
  const h = await harness(page, {
    validated: true,
    sectionRun: async (route) => {
      if (failFirst) {
        failFirst = false;
        await route.abort("failed");
        return;
      }
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Section run conflicts with server state (test double)." }),
      });
    },
  });
  await page.goto("/");
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "draft");
  const run = page.getByTestId("agent-run-step");
  await run.click();
  await expect(page.locator(".hx-notice.t-block")).toContainText("Run governed Section Agent failed");
  await run.click();
  await expect(page.locator(".hx-notice.t-block")).toContainText("conflicts with server state");
  await run.click();
  await expect.poll(() => h.bodies["section-run"]?.length).toBe(3);
  const keys = h.bodies["section-run"].map((body) => body.idempotency_key);
  const prefix = `workbench:STUDY-HLX-028:${runId}:section-run:${BW_SECTION}`;
  expect(keys).toEqual([`${prefix}:a1`, `${prefix}:a1`, `${prefix}:a2`]);
});

test("extract replays the freeze-created execution instead of running a second one", async ({ page }) => {
  const h = await harness(page);
  await page.route("**/api/v1/studies/*/workspace", async (route) => {
    const live = await liveWorkspace(route);
    if (!live) return;
    // Freeze left the package absent: Extract is the current stage.
    const workspace = frozenWorkspace(live, { data_validation_executions: [], validations: [], journey: journeyAt("extract") });
    if (h.bodies["data-validation"]?.length) {
      Object.assign(workspace, { data_validation_executions: freezeFixture.after.data_validation_executions, journey: journeyAt("validate") });
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(workspace) });
  });
  await page.goto("/");
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "extract");
  await page.getByTestId("agent-run-step").click();
  await expect(page.locator(".hx-notice.t-info")).toContainText("Execute Data Validation Package: recorded by the server.");
  expect(h.bodies["data-validation"]).toHaveLength(1);
  expect(h.bodies["data-validation"][0]).toMatchObject({
    package_id: "validation.body_weight",
    idempotency_key: `workbench:STUDY-HLX-028:${runId}:data-validation:${BW_SECTION}:a1`,
  });
  await expect(page.getByTestId("agent-stage-view")).toHaveAttribute("data-stage", "validate");
});
