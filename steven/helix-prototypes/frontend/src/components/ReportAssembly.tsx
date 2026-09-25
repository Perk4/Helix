"use client";

import type { ApprovalRole, Workspace } from "@/lib/types";

// LEGACY fallback (Lane D slimmed it for #23). The report canvas, role approvals, Final Study
// Approval, export, and downloads moved to components/review/ReviewStageView. What remains is
// the blocker disposition list that Lane C (#22) replaces with its Traceability view; its
// onResolve call is left exactly as it was so C's sequenced edit still applies.

type Props = {
  workspace: Workspace;
  busy: string | null;
  onResolve: (resultId: string, message: string) => void;
  /**
   * Legacy props HelixWorkbench still passes. Unused here: the review view owns these actions
   * through its own handlers (components/review). They stay so lane D's HelixWorkbench edit is
   * limited to its stage case block; drop them when the workbench's legacy handlers go.
   */
  onInspectClaim?: (claimId: string) => void;
  onApprove?: (role: ApprovalRole) => void;
  onFinalStudyApproval?: () => void;
  onExport?: () => void;
};

export function ReportAssembly({ workspace, busy, onResolve }: Props) {
  const latestDispositions = latestDispositionMap(workspace);
  const blockingResults = workspace.validations.filter(
    (result) => result.status === "fail" && result.severity === "blocker",
  );
  const openBlockers = blockingResults.filter(
    (result) => !isResolved(latestDispositions.get(result.result_id)?.decision),
  );

  return (
    <section className="view-content report-view" aria-label="Blocker dispositions (legacy)">
      <aside className="release-column">
          <section className="panel release-card">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Release controls</p>
                <h3>Human gate</h3>
              </div>
              <span className={`gate-badge ${workspace.release_gate.status}`}>
                {workspace.release_gate.status.replaceAll("_", " ")}
              </span>
            </div>
            <div className="gate-progress">
              <div>
                <span>Blocking checks</span>
                <strong>
                  {blockingResults.length - openBlockers.length}/{blockingResults.length}
                </strong>
              </div>
              <div className="progress-track">
                <span
                  style={{
                    width: `${blockingResults.length ? ((blockingResults.length - openBlockers.length) / blockingResults.length) * 100 : 100}%`,
                  }}
                />
              </div>
            </div>
            <div className="blocker-list" data-testid="blocker-list">
              {blockingResults.map((result) => {
                const disposition = latestDispositions.get(result.result_id);
                const resolved = isResolved(disposition?.decision);
                return (
                  <div className={resolved ? "blocker resolved" : "blocker"} key={result.result_id}>
                    <div className="blocker-top">
                      <span>{resolved ? "Resolved" : "Open"}</span>
                      <code>{result.result_id}</code>
                    </div>
                    <strong>{humanize(result.rule_id)}</strong>
                    <p>{result.message}</p>
                    {resolved ? (
                      <small>
                        {disposition?.decision.replaceAll("_", " ")} by {disposition?.reviewer}
                      </small>
                    ) : (
                      <button
                        className="button secondary small"
                        type="button"
                        disabled={busy !== null}
                        onClick={() => onResolve(result.result_id, result.message)}
                      >
                        {busy === result.result_id ? "Recording…" : "Record Gate 2 disposition"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {blockingResults.length === 0 && (
              <p className="empty-copy">Run hybrid validation to create the current gate record.</p>
            )}
          </section>
        </aside>
    </section>
  );
}

function latestDispositionMap(workspace: Workspace) {
  const map = new Map<string, Workspace["dispositions"][number]>();
  for (const disposition of workspace.dispositions) {
    map.set(disposition.result_id, disposition);
  }
  return map;
}

function isResolved(decision: string | undefined): boolean {
  return ["corrected", "explained_in_nsdrg", "approved_exception"].includes(decision ?? "");
}

function humanize(value: string): string {
  return value.replaceAll("-", " ");
}

