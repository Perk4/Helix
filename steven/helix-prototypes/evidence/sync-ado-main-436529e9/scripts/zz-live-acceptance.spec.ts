// Live acceptance for PR #19 (Perk bar). Not part of the suite: copied into
// frontend/tests only while it runs. Drives the demo path in the real UI against
// a running backend, screenshots each journey stage, records the server journey
// projection after each step, and captures the run-event SSE stream live.
import { expect, test, type Page } from "@playwright/test";
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const apiRoot = process.env.HELIX_API_URL ?? "http://127.0.0.1:8010/api/v1";
const out = process.env.LIVE_OUT ?? "/tmp/live/out";
const studyId = "STUDY-HLX-028";
test.setTimeout(240_000);

async function journey(page: Page, step: string) {
  const res = await page.request.get(`${apiRoot}/studies/${studyId}/workspace`);
  const ws = await res.json();
  const j = ws.journey;
  const line = {
    step,
    at: new Date().toISOString(),
    workflow_state: ws.workflow_state,
    release_gate: ws.release_gate.status,
    current_stage_id: j.current_stage_id,
    stages: j.stages.map((s: { stage_id: string; status: string }) => `${s.stage_id}:${s.status}`).join(" "),
    run_id: j.run?.run_id ?? null,
    latest_event_id: j.run?.latest_event_id ?? null,
  };
  appendFileSync(join(out, "journey-projection.jsonl"), `${JSON.stringify(line)}\n`);
  return ws;
}

async function shot(page: Page, name: string) {
  await page.screenshot({ path: join(out, `${name}.png`), fullPage: false });
}

test("live demo journey on the migrated database", async ({ page }) => {
  mkdirSync(out, { recursive: true });
  const result: Record<string, unknown> = { steps: [] as string[] };
  const steps = result.steps as string[];
  const browserErrors: string[] = [];
  page.on("pageerror", (e) => browserErrors.push(e.message));
  page.on("console", (m) => m.type() === "error" && browserErrors.push(m.text()));
  let sse: AbortController | null = null;
  let sseDone: Promise<void> | null = null;

  const startSse = (runId: string) => {
    sse = new AbortController();
    const url = `${apiRoot}/studies/${studyId}/pinned-runs/${runId}/events`;
    const file = join(out, "sse-frames.txt");
    writeFileSync(file, `# GET ${url}\n# opened ${new Date().toISOString()}\n`);
    sseDone = (async () => {
      try {
        const res = await fetch(url, { signal: sse!.signal, headers: { Accept: "text/event-stream" } });
        appendFileSync(file, `# HTTP ${res.status} ${res.headers.get("content-type")}\n`);
        const reader = res.body!.getReader();
        const dec = new TextDecoder();
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          const text = dec.decode(value);
          for (const frame of text.split("\n\n").filter((f) => f.trim())) {
            appendFileSync(file, `[${new Date().toISOString()}]\n${frame}\n\n`);
          }
        }
      } catch (e) {
        appendFileSync(file, `# closed: ${(e as Error).name}\n`);
      }
    })();
  };

  const step = async (name: string, fn: () => Promise<void>) => {
    try {
      await fn();
      steps.push(`PASS ${name}`);
      await journey(page, name);
      return true;
    } catch (e) {
      const notice = await page.locator(".hx-notice").allInnerTexts().catch(() => []);
      steps.push(`STOP ${name}`);
      result.stop = { step: name, error: String(e).split("\n").slice(0, 6).join(" | "), ui_notice: notice };
      await page.screenshot({ path: join(out, `STOP-${name}.png`), fullPage: false });
      await journey(page, `STOP ${name}`);
      return false;
    }
  };

  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await journey(page, "loaded");
  await shot(page, "00-shell-initial");

  const ok =
    (await step("01-upload-frozen-manifest", async () => {
      await page.getByRole("button", { name: /Authorized upload and frozen manifest/ }).click();
      await expect(page.getByTestId("source-manifest").locator(".source-manifest-row")).toHaveCount(10);
      await shot(page, "01-upload-frozen-manifest");
    })) &&
    (await step("02-parse-resolve-validate", async () => {
      await page.getByTestId("run-validation").click();
      await expect(page.getByRole("status")).toContainText("13 checks completed");
      const ws = await journey(page, "after-validation");
      const runId = ws.journey.run?.run_id ?? ws.pinned_run?.run_id;
      result.run_id = runId;
      if (runId) startSse(runId);
      await page.getByTestId("run-plan").scrollIntoViewIfNeeded();
      await shot(page, "02-parse-resolve-validate");
    })) &&
    (await step("03-extract-data-validation", async () => {
      await page.getByTestId("run-body-weight-validation").click();
      await expect(page.getByRole("status")).toContainText("persisted claims");
      await page.getByTestId("data-validation-package").scrollIntoViewIfNeeded();
      await shot(page, "03-extract-data-validation");
    })) &&
    (await step("04-draft-eligibility", async () => {
      // Drafting calls the Codex SDK (billed); the demo path does not click it.
      await expect(page.getByTestId("draft-body-weight")).toBeEnabled();
      await expect(page.getByTestId("eligibility-section.5_2_3_body_weight")).toHaveText("ready");
      await page.getByTestId("draft-body-weight").scrollIntoViewIfNeeded();
      await shot(page, "04-draft-eligibility");
    })) &&
    (await step("05-provenance-evidence-chain", async () => {
      await expect(page.getByText("Exact reconciliation passed", { exact: true })).toBeVisible();
      await page.getByTestId("evidence-chain").scrollIntoViewIfNeeded();
      await shot(page, "05-provenance-evidence-chain");
    })) &&
    (await step("06-gates-dispositions", async () => {
      for (let remaining = 3; remaining > 0; remaining -= 1) {
        const buttons = page.getByRole("button", { name: "Record synthetic disposition" });
        await expect(buttons).toHaveCount(remaining);
        await buttons.first().click();
        await expect(buttons).toHaveCount(remaining - 1);
      }
      await shot(page, "06-gates-dispositions");
    })) &&
    (await step("07-review-approvals", async () => {
      for (const label of ["Pathologist review", "Independent peer review", "Quality Assurance Unit statement", "Study director approval"]) {
        const row = page.locator(".approval-row").filter({ hasText: label });
        await row.getByRole("button", { name: "Record" }).click();
        await expect(row.locator(".approval-check")).toBeVisible();
      }
      await expect(page.getByTestId("release-status")).toHaveText("Ready for signature");
      await page.locator(".approval-row").first().scrollIntoViewIfNeeded();
      await shot(page, "07-review-approvals");
    })) &&
    (await step("08-final-study-approval", async () => {
      await page.getByTestId("record-final-study-approval").click();
      await expect(page.getByTestId("approval-current")).toHaveText("current");
      await expect(page.getByTestId("release-status")).toHaveText("Ready for export");
      await page.getByTestId("final-study-approval-scope").scrollIntoViewIfNeeded();
      await shot(page, "08-final-study-approval");
    })) &&
    (await step("09-export", async () => {
      await page.getByTestId("export-package").click();
      await expect(page.getByTestId("release-status")).toHaveText("Package exported", { timeout: 15_000 });
      await shot(page, "09-export");
    }));

  result.completed = ok;
  await page.waitForTimeout(2500); // let the SSE poller deliver the last frames
  if (sse) (sse as AbortController).abort();
  if (sseDone) await sseDone;
  result.browser_errors = browserErrors;
  writeFileSync(join(out, "result.json"), `${JSON.stringify(result, null, 2)}\n`);
});
