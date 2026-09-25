"use client";

import { useState } from "react";

import { ApiError, exportPackage, recordApproval, recordFinalStudyApproval } from "@/lib/api";
import { APPROVAL_POLICY } from "@/lib/api/release";
import type { ApprovalRole, Workspace } from "@/lib/types";

import { DemoBanner } from "../DemoLabel";
import { Card, GateBanner } from "../ui";
import { DraftCanvas } from "./DraftCanvas";
import { Downloads } from "./Downloads";
import { ExportPanel, type ExportState } from "./ExportPanel";
import { SectionList } from "./SectionList";
import { SignOffs } from "./SignOffs";
import { stageStatus } from "./reviewState";

// Lane D (#23): Human Gate 3, Review and export. Three columns (section list | document canvas |
// sign-offs), then downloads. Every state shown comes from WorkspaceResponse; the view never
// passes a gate, derives release readiness, or advances progress locally.

export function ReviewStageView({
  workspace,
  onWorkspace,
  onRefresh,
}: {
  workspace: Workspace;
  /** Render a workspace returned by a command. */
  onWorkspace: (workspace: Workspace) => void;
  onRefresh: () => Promise<void>;
}) {
  const studyId = workspace.study.study_id;
  const sections = workspace.report.sections;
  const [selectedId, setSelectedId] = useState<string>(
    sections.find((item) => item.blocks.some((block) => block.kind === "review_marker"))?.section_id ??
      sections[0]?.section_id ??
      "",
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "info" | "block"; text: string } | null>(null);
  const [exportState, setExportState] = useState<ExportState>({ kind: "idle" });

  const section = sections.find((item) => item.section_id === selectedId) ?? sections[0];
  const gateStatus = stageStatus(workspace, "review-export");
  const passed = gateStatus === "complete";
  const hint = passed
    ? "Export recorded. Journey complete."
    : gateStatus === "pending"
      ? "Opens after the traceability gate."
      : "Record sign-offs, then export.";

  async function approve(role: ApprovalRole) {
    setBusy(role);
    setMessage(null);
    try {
      // Records exactly one role. Never exports.
      onWorkspace(await recordApproval(studyId, role));
      setMessage({ tone: "info", text: `${APPROVAL_POLICY[role].label} recorded in the synthetic audit trail.` });
    } catch (cause) {
      setMessage({ tone: "block", text: messageFrom(cause) });
    } finally {
      setBusy(null);
    }
  }

  async function approveFinalStudy() {
    setBusy("final-study-approval");
    setMessage(null);
    try {
      const key = `workbench-${studyId}-fsa-${workspace.release_candidate?.content_hash?.slice(-12) ?? "pending"}`;
      onWorkspace(await recordFinalStudyApproval(studyId, key));
      setMessage({ tone: "info", text: "Final Study Approval recorded for the exact release-candidate hashes." });
    } catch (cause) {
      setMessage({ tone: "block", text: messageFrom(cause) });
    } finally {
      setBusy(null);
    }
  }

  async function performExport() {
    setExportState({ kind: "loading" });
    setMessage(null);
    try {
      const receipt = await exportPackage(studyId);
      setExportState({ kind: "success", receipt });
      await onRefresh();
    } catch (cause) {
      setExportState({ kind: "error", message: messageFrom(cause) });
    }
  }

  return (
    <div className="stack" data-testid="review-stage" data-gate-status={gateStatus ?? undefined}>
      <GateBanner gateNumber={3} passed={passed} title="Review sections, sign and export" right={hint} data-testid="review-gate-banner" />
      <DemoBanner workspace={workspace} />
      {message && (
        <div className={`hx-notice t-${message.tone}`} role="status" data-testid="review-message">
          <span>{message.text}</span>
        </div>
      )}
      {section ? (
        <div className="g-review">
          <SectionList workspace={workspace} selectedId={section.section_id} onSelect={setSelectedId} />
          <DraftCanvas workspace={workspace} section={section} />
          <Card as="aside" className="stack" aria-labelledby="hx-so-h">
            <SignOffs
              workspace={workspace}
              busy={busy ?? (exportState.kind === "loading" ? "export" : null)}
              onApprove={(role) => void approve(role)}
              onFinalStudyApproval={() => void approveFinalStudy()}
            />
            <ExportPanel workspace={workspace} state={exportState} onExport={() => void performExport()} />
          </Card>
        </div>
      ) : (
        <Card>
          <p className="hx-sub">The server returned no report sections.</p>
        </Card>
      )}
      <Downloads workspace={workspace} />
      <p className="hx-sub hx-fine hx-review-disclaimer">
        Synthetic data · Not for submission. The report follows an FDA-like layout for demonstration only and
        HELIX makes no regulatory claim. A prepared package is not FDA acceptance.
      </p>
    </div>
  );
}

function messageFrom(cause: unknown): string {
  if (cause instanceof ApiError || cause instanceof Error) return cause.message;
  return "An unexpected review error occurred.";
}
