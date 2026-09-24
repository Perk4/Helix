import { expect, test } from "@playwright/test";

const apiRoot = process.env.HELIX_API_URL ?? "http://127.0.0.1:8000/api/v1";

test("runs the synthetic study from validation through explicit export", async ({ page, request }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      browserErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));

  await page.goto("/");
  await expect(page.getByTestId("helix-workbench")).toBeVisible();
  await expect(page.getByText("Synthetic / not for submission", { exact: true })).toBeVisible();
  await expect(page.getByTestId("release-status")).toHaveText("blocked");
  await expect(page.getByTestId("draft-body-weight")).toBeDisabled();
  await expect(page.getByTestId("section-run-ineligible")).toContainText("Run hybrid validation first");
  await expect(page.getByLabel("Study summary").getByText("1,662", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../evidence/helix-workbench-initial.png", fullPage: true });

  await page.getByRole("button", { name: /Authorized upload and frozen manifest/ }).click();
  await expect(page.getByTestId("source-manifest").locator(".source-manifest-row")).toHaveCount(10);
  await expect(page.getByTestId("source-manifest").getByText("body-weights.csv")).toBeVisible();
  await page.screenshot({ path: "../evidence/helix-source-manifest.png", fullPage: true });

  await page.getByTestId("run-validation").click();
  await expect(page.getByRole("status")).toContainText("13 checks completed");
  await expect(page.getByTestId("draft-body-weight")).toBeEnabled();
  await expect(page.getByText("3", { exact: true }).first()).toBeVisible();
  const runPlan = page.getByTestId("run-plan");
  await expect(runPlan.getByText(/^RUN-/)).toBeVisible();
  await expect(runPlan.getByText("REPEAT_DOSE_28D_RODENT", { exact: true })).toBeVisible();
  await runPlan.getByText(/Complete Run Plan/).click();
  await expect(runPlan.getByText("section.5_2_3_body_weight", { exact: true }).first()).toBeVisible();
  await expect(runPlan.getByText("helix-section-agent", { exact: true })).toBeVisible();
  await page.screenshot({ path: "../evidence/helix-run-plan.png", fullPage: true });

  await page.getByRole("button", { name: /Evidence chain/ }).click();
  await expect(page.getByTestId("evidence-chain")).toBeVisible();
  await expect(page.getByText("286.2 g", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("10 exact records", { exact: true })).toBeVisible();
  await expect(page.getByText("Exact reconciliation passed", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Liver Hypertrophy Incidence/ }).click();
  await expect(page.getByText("4 animals", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Source and claim agree.", { exact: true })).toBeVisible();
  await expect(page.getByText("agent source severity match", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: /Report assembly/ }).click();
  await expect(page.getByRole("heading", { name: "Anatomic pathology" })).toBeVisible();
  await expect(
    page.locator(".report-paper").getByText("The pattern draft says moderate.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "OECD TG 407, 2025" }).first()).toBeVisible();

  for (let remaining = 3; remaining > 0; remaining -= 1) {
    const buttons = page.getByRole("button", { name: "Record synthetic disposition" });
    await expect(buttons).toHaveCount(remaining);
    await buttons.first().click();
    await expect(buttons).toHaveCount(remaining - 1);
  }
  await expect(
    page.locator(".report-paper").getByText("Minimal hepatocellular hypertrophy", { exact: false }),
  ).toBeVisible();

  await recordApproval(page, "Pathologist review");
  await recordApproval(page, "Independent peer review");
  await recordApproval(page, "Quality Assurance Unit statement");
  await recordApproval(page, "Study director approval");

  await expect(page.getByTestId("release-status")).toHaveText("ready for export");
  await expect(page.getByTestId("export-package")).toBeEnabled();
  await page.getByTestId("export-package").click();
  await expect(page.getByTestId("release-status")).toHaveText("exported");
  await expect(page.getByText("4 synthetic artifacts checksummed", { exact: false })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /Study report PDF/ }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("repeat-dose-study-report.pdf");
  expect(await download.failure()).toBeNull();

  const workspaceResponse = await request.get(`${apiRoot}/studies/STUDY-HLX-028/workspace`);
  expect(workspaceResponse.ok()).toBeTruthy();
  const workspace: unknown = await workspaceResponse.json();
  expect(isExportedWorkspace(workspace)).toBeTruthy();

  await page.screenshot({ path: "../evidence/helix-workbench-exported.png", fullPage: true });
  expect(browserErrors).toEqual([]);
});

async function recordApproval(page: import("@playwright/test").Page, label: string) {
  const row = page.locator(".approval-row").filter({ hasText: label });
  await row.getByRole("button", { name: "Record" }).click();
  await expect(row.locator(".approval-check")).toBeVisible();
}

function isExportedWorkspace(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  if (!("release_gate" in value) || !("export_artifacts" in value)) {
    return false;
  }
  const gate = value.release_gate;
  const artifacts = value.export_artifacts;
  return (
    typeof gate === "object" &&
    gate !== null &&
    "status" in gate &&
    gate.status === "exported" &&
    Array.isArray(artifacts) &&
    artifacts.length === 4 &&
    artifacts.every(
      (artifact) =>
        typeof artifact === "object" &&
        artifact !== null &&
        "checksum" in artifact &&
        typeof artifact.checksum === "string" &&
        artifact.checksum.startsWith("sha256:"),
    )
  );
}
