import { expect, test } from "@playwright/test";

test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("rejects a workspace response from an incompatible API", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.route("**/api/v1/studies/*/workspace", async (route) => {
    const response = await route.fetch();
    const workspace: unknown = await response.json();
    if (!isObject(workspace)) throw new Error("Workspace fixture is invalid.");
    const incompatibleWorkspace = { ...workspace };
    delete incompatibleWorkspace.section_run_eligibility;
    delete incompatibleWorkspace.section_runs;
    await route.fulfill({
      status: response.status(),
      contentType: "application/json",
      body: JSON.stringify(incompatibleWorkspace),
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "The workbench API is unavailable." })).toBeVisible();
  await expect(page.getByText("The workspace response does not match the generated API contract.")).toBeVisible();
  expect(browserErrors).toEqual([]);
});

test("renders one nine-stage workspace without the old control plane", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("journey-progress")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Journey progress" }).getByRole("button")).toHaveCount(9);
  await expect(page.getByText("Evidence-to-report control plane")).toHaveCount(0);
  await expect(page.getByText("A ten-stage journey with visible boundaries.")).toHaveCount(0);
});

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
