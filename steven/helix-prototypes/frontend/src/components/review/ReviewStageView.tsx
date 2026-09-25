"use client";

import type { ReactNode } from "react";

import type { Workspace } from "@/lib/types";

import { Chip, GateBanner } from "../ui";
import { demoFrozenPackages, stageStatus } from "./reviewState";

export function ReviewStageView({ workspace, children }: { workspace: Workspace; children: ReactNode }) {
  const gateStatus = stageStatus(workspace, "review-export");
  const passed = gateStatus === "complete";
  const hint = passed
    ? "Export recorded. Journey complete."
    : gateStatus === "pending"
      ? "Opens after the traceability gate."
      : "Review section drafts, record approvals, then export.";
  const notQualified = demoFrozenPackages(workspace).length > 0;

  return (
    <div className="stack" data-testid="review-stage" data-gate-status={gateStatus ?? undefined}>
      <GateBanner
        gateNumber={3}
        passed={passed}
        title="Review sections, sign and export"
        right={
          notQualified ? (
            <>
              <Chip
                tone="warn"
                size="xs"
                data-testid="run-not-qualified"
                title="This run was frozen without a passing qualification for some section packages. Export is refused."
              >
                Not qualified
              </Chip>
              {hint}
            </>
          ) : (
            hint
          )
        }
        data-testid="review-gate-banner"
      />
      {children}
      <p className="hx-sub hx-fine hx-review-disclaimer">
        Synthetic data · Not for submission. The report follows an FDA-like layout for demonstration only.
        HELIX makes no regulatory claim.
      </p>
    </div>
  );
}
