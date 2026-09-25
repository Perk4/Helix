"use client";

import { Fragment } from "react";

import { APPROVAL_ORDER, APPROVAL_POLICY } from "@/lib/api/release";
import type { ApprovalRole, Workspace } from "@/lib/types";

import { CheckIcon, ClockIcon } from "../icons";
import { Button, Kicker, ListRow, toneColor } from "../ui";
import { latestApproval, priorApprovalsRecorded, stageStatus } from "./reviewState";

// Lane D (#23): one control per role. Pathologist, peer reviewer, and QAU in any order; the
// study director stays disabled until all three exist, and the server enforces the rule too.
// Approval handlers only record approvals; they never export.

export function SignOffs({
  workspace,
  busy,
  onApprove,
  onFinalStudyApproval,
}: {
  workspace: Workspace;
  busy: string | null;
  onApprove: (role: ApprovalRole) => void;
  onFinalStudyApproval: () => void;
}) {
  const traceabilityPassed = stageStatus(workspace, "traceability") === "complete";
  const priorsDone = priorApprovalsRecorded(workspace);
  const directorRecorded = latestApproval(workspace, "study_director") !== null;
  const fsaCurrent = workspace.approval_current;
  return (
    <div className="stack" data-testid="sign-offs">
      <div>
        <Kicker>Release controls</Kicker>
        <h2 id="hx-so-h" className="hx-so-title">
          Sign-offs
        </h2>
      </div>
      <div>
        <ListRow
          icon={traceabilityPassed ? <CheckIcon /> : <ClockIcon />}
          iconColor={toneColor(traceabilityPassed ? "pass" : "warn")}
          meta={traceabilityPassed ? "Approved" : "Pending"}
          metaColor={toneColor(traceabilityPassed ? "pass" : "warn")}
        >
          Traceability gate passed
        </ListRow>
        {APPROVAL_ORDER.map((role) => {
          const policy = APPROVAL_POLICY[role];
          const approval = latestApproval(workspace, role);
          const blockedByOrder = role === "study_director" && !priorsDone;
          return (
            <div className="hx-signoff" key={role} data-testid={`signoff-${role}`} data-signed={approval ? "true" : "false"}>
              <ListRow
                icon={approval ? <CheckIcon /> : <ClockIcon />}
                iconColor={toneColor(approval ? "pass" : "warn")}
                meta={approval ? "Signed" : "Pending"}
                metaColor={toneColor(approval ? "pass" : "warn")}
              >
                {policy.label}
              </ListRow>
              <div className="hx-signoff-detail">
                <span className="hx-sub">
                  {approval
                    ? `${approval.reviewer} · “${approval.meaning}”`
                    : `Meaning: “${policy.meaning}” · synthetic demo identity ${policy.reviewer}`}
                </span>
                {!approval && (
                  <Button
                    size="sm"
                    disabled={busy !== null || blockedByOrder}
                    title={blockedByOrder ? "Needs pathologist, peer reviewer, and QAU approvals first" : undefined}
                    onClick={() => onApprove(role)}
                    data-testid={`approve-${role}`}
                  >
                    {busy === role ? "Recording…" : `Record ${policy.label.toLowerCase()}`}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
        <div className="hx-signoff" data-testid="signoff-final-study-approval" data-signed={fsaCurrent ? "true" : "false"}>
          <ListRow
            icon={fsaCurrent ? <CheckIcon /> : <ClockIcon />}
            iconColor={toneColor(fsaCurrent ? "pass" : "warn")}
            meta={fsaCurrent ? "Recorded" : workspace.final_study_approval ? "Stale" : "Pending"}
            metaColor={toneColor(fsaCurrent ? "pass" : "warn")}
          >
            Final Study Approval (hash-bound)
          </ListRow>
          <div className="hx-signoff-detail">
            <span className="hx-mono" data-testid="fsa-manifest-hash">
              {workspace.final_study_approval?.manifest_hash ?? workspace.release_candidate?.content_hash ?? "No release candidate yet"}
            </span>
            {!fsaCurrent && (
              <Button
                size="sm"
                disabled={busy !== null || !directorRecorded || !workspace.release_candidate}
                onClick={onFinalStudyApproval}
                data-testid="approve-final-study"
              >
                {busy === "final-study-approval" ? "Recording…" : "Record Final Study Approval"}
              </Button>
            )}
          </div>
          {workspace.final_study_approval && (
            <dl className="hx-fsa-scope" data-testid="final-study-approval-scope">
              <dt>Approval</dt>
              <dd className="hx-mono" data-testid="approval-current">
                {fsaCurrent ? "current" : "stale"}
              </dd>
              <dt>Manifest</dt>
              <dd className="hx-mono" data-testid="approval-manifest-hash">
                {workspace.final_study_approval.manifest_hash}
              </dd>
              {workspace.final_study_approval.included_artifact_hashes.map((item) => (
                <Fragment key={item.artifact_id}>
                  <dt className="hx-mono">{item.artifact_id}</dt>
                  <dd className="hx-mono" data-testid={`approval-artifact-${item.artifact_id}`}>
                    {item.content_hash}
                  </dd>
                </Fragment>
              ))}
            </dl>
          )}
        </div>
      </div>
      <p className="hx-sub hx-fine">
        Reviewer names are synthetic demo identities, not authenticated signers or e-signatures (#27).
      </p>
    </div>
  );
}
