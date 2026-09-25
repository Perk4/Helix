import type { JourneyStage, ValidationResult, Workspace } from "@/lib/types";

// Lane C (#22). Presentation helpers over server state ONLY. Nothing here passes the
// gate or derives release readiness: every answer reads the refreshed workspace
// (journey projection, dispositions, validations) the server returned.

export type Disposition = Workspace["dispositions"][number];

/** The decisions the backend treats as resolving a blocker (schemas.RESOLVED_DISPOSITIONS). */
const RECORDED_DECISIONS = new Set<Disposition["decision"]>([
  "corrected",
  "explained_in_nsdrg",
  "approved_exception",
]);

export function latestDispositions(workspace: Workspace): Map<string, Disposition> {
  const latest = new Map<string, Disposition>();
  for (const disposition of workspace.dispositions) {
    latest.set(disposition.result_id, disposition);
  }
  return latest;
}

export function isRecorded(disposition: Disposition | undefined): disposition is Disposition {
  return Boolean(disposition && RECORDED_DECISIONS.has(disposition.decision) && disposition.reviewer);
}

/** A blocker with a disposition stays a blocker; it displays as Disposition, never Pass. */
export type RuleDisplay = "pass" | "disposition" | "blocked" | "warning" | "skipped";

export function ruleDisplay(result: ValidationResult, disposition: Disposition | undefined): RuleDisplay {
  if (result.status === "pass") return "pass";
  if (result.status === "skipped") return "skipped";
  if (isRecorded(disposition)) return "disposition";
  if (result.status === "fail" && result.severity === "blocker") return "blocked";
  return "warning";
}

export function stageById(workspace: Workspace, id: JourneyStage["stage_id"]): JourneyStage | undefined {
  return workspace.journey.stages.find((stage) => stage.stage_id === id);
}

/** Result IDs the server's traceability stage lists as required dispositions. */
export function requiredBlockerIds(workspace: Workspace): string[] {
  const ids = new Set<string>(workspace.release_gate.blocking_result_ids);
  for (const action of stageById(workspace, "traceability")?.actions ?? []) {
    if (action.action_id.startsWith("disposition:")) ids.add(action.action_id.slice("disposition:".length));
  }
  return [...ids];
}

export type ContinueEligibility = { eligible: boolean; hint: string };

/**
 * Continue may only change the selected view. It is enabled when the refreshed server
 * state reports (a) the Review stage reached and (b) every required blocker carrying a
 * recorded disposition. There is no local `disposed` or `gatePassed` flag.
 */
export function continueEligibility(workspace: Workspace): ContinueEligibility {
  const trace = stageById(workspace, "traceability");
  const review = stageById(workspace, "review-export");
  const latest = latestDispositions(workspace);
  const pendingTraceActions = (trace?.actions ?? []).filter((action) => action.status !== "done");
  const undisposed = requiredBlockerIds(workspace).filter((id) => !isRecorded(latest.get(id)));
  const reviewReached = Boolean(review && review.selectable && review.status !== "pending");

  if (!trace || trace.status === "pending") {
    return { eligible: false, hint: "The server has not reached the traceability gate yet." };
  }
  if (undisposed.length > 0 || pendingTraceActions.length > 0) {
    const count = Math.max(undisposed.length, pendingTraceActions.length);
    return {
      eligible: false,
      hint: `Record a disposition for ${count === 1 ? "the blocked rule" : `${count} blocked rules`} to continue.`,
    };
  }
  if (!reviewReached) {
    return { eligible: false, hint: "Waiting for the server to open Review." };
  }
  return { eligible: true, hint: "All blockers have a disposition." };
}

/** The claim a validation result belongs to, from its scope or evidence IDs (server data). */
export function claimForResult(workspace: Workspace, result: ValidationResult | undefined): string | undefined {
  if (!result) return undefined;
  const claimIds = new Set(workspace.claims.map((claim) => claim.claim_id));
  if (claimIds.has(result.scope_id)) return result.scope_id;
  return result.evidence_ids.find((id) => claimIds.has(id));
}
