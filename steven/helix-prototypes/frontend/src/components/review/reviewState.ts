import type { ApprovalRole, ValidationResult, Workspace } from "@/lib/types";

import { PRIOR_APPROVAL_ROLES } from "@/lib/api/release";

// Lane D (#23): read-only projections of server state for the review view. Nothing here
// decides a gate: release readiness is WorkspaceResponse.release_gate.status only.

const RESOLVED = new Set(["corrected", "explained_in_nsdrg", "approved_exception"]);

export function latestApproval(workspace: Workspace, role: ApprovalRole) {
  return [...workspace.approvals].reverse().find((item) => item.role === role) ?? null;
}

export function priorApprovalsRecorded(workspace: Workspace): boolean {
  return PRIOR_APPROVAL_ROLES.every((role) => latestApproval(workspace, role) !== null);
}

export function stageStatus(workspace: Workspace, stageId: string): string | null {
  return workspace.journey.stages.find((stage) => stage.stage_id === stageId)?.status ?? null;
}

function sectionOf(result: ValidationResult, workspace: Workspace): string | null {
  if (result.scope_id.startsWith("S")) return result.scope_id;
  return workspace.claims.find((claim) => claim.claim_id === result.scope_id)?.section_id ?? null;
}

/** Open (undispositioned) blockers per report section, for section chips only. */
export function openBlockersBySection(workspace: Workspace): Map<string, number> {
  const latest = new Map<string, string>();
  for (const item of workspace.dispositions) latest.set(item.result_id, item.decision);
  const counts = new Map<string, number>();
  for (const result of workspace.validations) {
    if (result.status !== "fail" || result.severity !== "blocker") continue;
    if (RESOLVED.has(latest.get(result.result_id) ?? "")) continue;
    const section = sectionOf(result, workspace);
    if (section) counts.set(section, (counts.get(section) ?? 0) + 1);
  }
  return counts;
}

/** Server-recorded export time when no receipt is in memory (e.g. after a reload). */
export function exportedAtFromJourney(workspace: Workspace): string | null {
  const stage = workspace.journey.stages.find((item) => item.stage_id === "review-export");
  return stage?.status === "complete" ? (stage.finished_at ?? null) : null;
}
