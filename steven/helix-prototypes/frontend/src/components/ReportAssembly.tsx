"use client";

import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  ApiError,
  artifactDownloadUrl,
  generateSectionDraft,
  getSectionDraft,
  getSections,
  verifySection,
} from "@/lib/api";

import { ChatDock } from "./ChatDock";
import type {
  ApprovalRole,
  SectionBlock,
  SectionContentDraft,
  SectionListItem,
  Workspace,
} from "@/lib/types";

type Props = {
  workspace: Workspace;
  busy: string | null;
  onInspectClaim: (claimId: string) => void;
  onResolve: (resultId: string, message: string) => void;
  onApprove: (role: ApprovalRole) => void;
  onFinalStudyApproval: () => void;
  onExport: () => void;
};

const approvalOrder: ApprovalRole[] = ["pathologist", "peer_reviewer", "qau", "study_director"];

export function ReportAssembly({
  workspace,
  busy,
  onResolve,
  onApprove,
  onFinalStudyApproval,
  onExport,
}: Props) {
  const studyId = workspace.study.study_id;
  const [sections, setSections] = useState<SectionListItem[]>([]);
  const [selectedSectionId, setSelectedSectionId] = useState("5_2_3_body_weight");
  const [draft, setDraft] = useState<SectionContentDraft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  const refreshSections = useCallback(async () => {
    try {
      setSections(await getSections(studyId));
    } catch {
      /* non-fatal: navigator falls back to whatever it has */
    }
  }, [studyId]);

  useEffect(() => {
    void refreshSections();
  }, [refreshSections]);

  useEffect(() => {
    let active = true;
    setDraft(null);
    setDraftError(null);
    setDraftLoading(true);
    getSectionDraft(studyId, selectedSectionId)
      .then(async (value) => {
        if (!active) return;
        if (value) {
          setDraft(value);
          return;
        }
        // No draft persisted yet — generate once so content is present, then
        // it is fetched from the database on every later visit.
        const created = await generateSectionDraft(studyId, selectedSectionId);
        if (active) {
          setDraft(created);
          void refreshSections();
        }
      })
      .catch((cause) => active && setDraftError(messageFrom(cause)))
      .finally(() => active && setDraftLoading(false));
    return () => {
      active = false;
    };
  }, [studyId, selectedSectionId, refreshSections]);

  async function generate() {
    setDraftBusy(true);
    setDraftError(null);
    try {
      setDraft(await generateSectionDraft(studyId, selectedSectionId));
      await refreshSections();
    } catch (cause) {
      setDraftError(messageFrom(cause));
    } finally {
      setDraftBusy(false);
    }
  }

  const reloadDraft = useCallback(async () => {
    try {
      setDraft(await getSectionDraft(studyId, selectedSectionId));
      setSections(await getSections(studyId));
    } catch {
      /* non-fatal */
    }
  }, [studyId, selectedSectionId]);

  async function markVerified() {
    setDraftBusy(true);
    setDraftError(null);
    try {
      setDraft(await verifySection(studyId, selectedSectionId));
      await refreshSections();
    } catch (cause) {
      setDraftError(messageFrom(cause));
    } finally {
      setDraftBusy(false);
    }
  }

  const selectedMeta = sections.find((item) => item.section_id === selectedSectionId);
  const selectedTitle = draft?.title ?? selectedMeta?.title ?? selectedSectionId;

  const latestDispositions = latestDispositionMap(workspace);
  const blockingResults = workspace.validations.filter(
    (result) => result.status === "fail" && result.severity === "blocker",
  );
  const openBlockers = blockingResults.filter(
    (result) => !isResolved(latestDispositions.get(result.result_id)?.decision),
  );
  const approvalRoles = new Set(workspace.approvals.map((approval) => approval.role));
  const priorRoles: ApprovalRole[] = ["pathologist", "peer_reviewer", "qau"];
  const priorHumanApprovalsComplete = priorRoles.every((role) => approvalRoles.has(role));

  return (
    <section className="view-content report-view" aria-labelledby="report-heading">
      <div className="view-intro report-intro">
        <div>
          <p className="eyebrow">Drafted from verified study data</p>
          <h2 id="report-heading">Read each section as it will appear in the report.</h2>
          <p>
            Tables are drawn directly from the verified numbers; the narrative is written around them.
            Sections still marked <strong>needs review</strong> await your verification.
          </p>
        </div>
        <div className="template-identity">
          <div>
            <span>Template</span>
            <strong>{workspace.report.template.template_id}</strong>
          </div>
          <div>
            <span>CTD location</span>
            <strong>{workspace.report.template.ctd_location}</strong>
          </div>
        </div>
      </div>

      <div className="report-layout">
        <aside className="panel report-sections" aria-label="Report sections">
          <div className="panel-heading compact">
            <div>
              <p className="eyebrow">Report navigator</p>
              <h3>Fourteen sections</h3>
            </div>
          </div>
          <div className="section-list">
            {(sections.length ? sections : []).map((item) => (
              <button
                key={item.section_id}
                type="button"
                className={item.section_id === selectedSectionId ? "section-button active" : "section-button"}
                onClick={() => setSelectedSectionId(item.section_id)}
              >
                <span className="section-number">{String(item.order + 1).padStart(2, "0")}</span>
                <span className="section-label">
                  <strong>{item.title}</strong>
                  <small>{item.has_verified_claims ? "verified data" : "narrative / review"}</small>
                </span>
                <span className={`section-state ${statusClass(item.status)}`}>{statusLabel(item.status)}</span>
              </button>
            ))}
            {!sections.length && <div className="empty-copy">Loading sections…</div>}
          </div>
          <div className="template-note">
            <strong>Template boundary</strong>
            <p>{workspace.report.template.disclaimer}</p>
          </div>
        </aside>

        <div className="report-center-column">
          <article className="panel report-paper">
            <header className="report-paper-header">
              <div>
                <p className="eyebrow">Draft section</p>
                <h3>{selectedTitle}</h3>
              </div>
              <div className="report-paper-actions">
                {draft && (
                  <span className={`document-status ${statusClass(draft.status)}`}>
                    {statusLabel(draft.status)} · v{draft.version}
                  </span>
                )}
                {draft && draft.status === "needs_review" && (
                  <button
                    className="button secondary small"
                    type="button"
                    onClick={() => void markVerified()}
                    disabled={draftBusy}
                    data-testid="verify-draft"
                  >
                    Mark verified
                  </button>
                )}
                <button
                  className="button secondary small"
                  type="button"
                  onClick={() => void generate()}
                  disabled={draftBusy}
                  data-testid="generate-draft"
                >
                  {draftBusy ? "Drafting…" : draft ? "Regenerate" : "Generate draft"}
                </button>
              </div>
            </header>
            <div className="report-rule" />

            {draftError && <div className="notice error inline">{draftError}</div>}

            {draft && draft.status !== "verified" && (
              <div className="review-banner" role="status">
                <strong>Needs your review.</strong> Verify the content below and use the chat to give
                feedback or rerun this section.
              </div>
            )}

            {draftLoading && !draft && <div className="empty-copy">Loading draft…</div>}

            {!draftLoading && !draft && (
              <div className="empty-copy">
                No draft yet for this section. Choose <em>Generate draft</em> to create one.
              </div>
            )}

            {draft && (
              <div className="report-blocks">
                {draft.blocks.map((block, index) => (
                  <BlockView key={index} block={block} />
                ))}
                <p className="draft-provenance">
                  {draft.provenance_count > 0
                    ? `${draft.provenance_count} values traced to source records.`
                    : "No numeric values in this section."}
                  {draft.model ? ` · narrative by ${draft.model}` : " · narrative pending (model not configured)"}
                </p>
              </div>
            )}

            <footer className="report-paper-footer">
              <span>{workspace.study.study_id}</span>
              <span>Protocol {workspace.study.protocol_version}</span>
              <span>Synthetic working draft</span>
            </footer>
          </article>
        </div>

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
                        {busy === result.result_id ? "Recording…" : "Record synthetic disposition"}
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

          <section className="panel approval-card">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">Required records</p>
                <h3>Review and approval</h3>
              </div>
              <span className="count-chip">{approvalRoles.size}/4</span>
            </div>
            <div className="approval-list">
              {approvalOrder.map((role, index) => {
                const approval = [...workspace.approvals].reverse().find((item) => item.role === role);
                const directorBlocked = role === "study_director" && !priorHumanApprovalsComplete;
                return (
                  <div className={approval ? "approval-row complete" : "approval-row"} key={role}>
                    <span className="approval-index">{index + 1}</span>
                    <div>
                      <strong>{approvalLabel(role)}</strong>
                      <span>{approval ? `${approval.reviewer} · recorded` : approvalDetail(role)}</span>
                    </div>
                    {approval ? (
                      <span className="approval-check">✓</span>
                    ) : (
                      <button
                        type="button"
                        className="text-button"
                        disabled={openBlockers.length > 0 || directorBlocked || busy !== null}
                        onClick={() => onApprove(role)}
                      >
                        {busy === role ? "Recording…" : "Record"}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
            {workspace.approval_current ? (
              <span className="approval-check">✓ Final Study Approval recorded</span>
            ) : (
              <button
                type="button"
                className="text-button"
                data-testid="record-final-study-approval"
                disabled={
                  !priorHumanApprovalsComplete ||
                  !approvalRoles.has("study_director") ||
                  openBlockers.length > 0 ||
                  busy !== null ||
                  workspace.release_candidate == null
                }
                onClick={onFinalStudyApproval}
              >
                {busy === "final-study-approval" ? "Recording…" : "Record Final Study Approval"}
              </button>
            )}
          </section>

          <section className="panel export-card">
            <p className="eyebrow">Explicit action</p>
            <h3>Submission-support package</h3>
            <div className="artifact-list">
              {workspace.export_artifacts.map((artifact) => (
                <div key={artifact.artifact_id}>
                  <span className={`artifact-icon ${artifact.status}`}>
                    {artifact.status === "exported" ? "✓" : ""}
                  </span>
                  <div>
                    {artifact.status === "exported" ? (
                      <a
                        className="artifact-download"
                        href={artifactDownloadUrl(workspace.study.study_id, artifact.artifact_id)}
                        download
                      >
                        <strong>{artifactLabel(artifact.kind)}</strong>
                        <code>Download · {artifact.path}</code>
                      </a>
                    ) : (
                      <>
                        <strong>{artifactLabel(artifact.kind)}</strong>
                        <code>{artifact.path}</code>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <button
              className="button primary wide"
              type="button"
              disabled={workspace.release_gate.status !== "ready_for_export" || busy !== null}
              onClick={onExport}
              data-testid="export-package"
            >
              {workspace.release_gate.status === "exported"
                ? "Synthetic package exported"
                : busy === "export"
                  ? "Checksumming artifacts…"
                  : "Export synthetic package"}
            </button>
            <p className="fine-print">A prepared or exported prototype package is not FDA acceptance.</p>
          </section>
        </aside>
      </div>

      <ChatDock
        studyId={studyId}
        sectionId={selectedSectionId}
        sectionTitle={selectedTitle}
        onApplied={() => void reloadDraft()}
      />
    </section>
  );
}

function BlockView({ block }: { block: SectionBlock }) {
  if (block.kind === "prose") {
    return (
      <div className="report-block prose draft-prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.markdown}</ReactMarkdown>
      </div>
    );
  }
  if (block.kind === "note") {
    return (
      <div className="report-block note draft-note">
        <span className="marker-label">Needs review</span>
        <p>{block.text}</p>
      </div>
    );
  }
  return (
    <figure className="draft-table-wrap">
      <figcaption>{block.title}</figcaption>
      <table className="draft-table">
        <thead>
          <tr>
            {block.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
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

function statusLabel(status: string): string {
  return {
    needs_review: "needs review",
    proposed: "proposed",
    verified: "verified",
    discarded: "discarded",
    empty: "not drafted",
  }[status] ?? status.replaceAll("_", " ");
}

function statusClass(status: string): string {
  return status === "verified" ? "reviewed" : status === "empty" ? "pending" : "needs_review";
}

function humanize(value: string): string {
  return value.replaceAll("-", " ");
}

function messageFrom(cause: unknown): string {
  if (cause instanceof ApiError || cause instanceof Error) {
    return cause.message;
  }
  return "An unexpected error occurred.";
}

function approvalLabel(role: ApprovalRole): string {
  return {
    pathologist: "Pathologist review",
    peer_reviewer: "Independent peer review",
    qau: "Quality Assurance Unit statement",
    study_director: "Study director approval",
  }[role];
}

function approvalDetail(role: ApprovalRole): string {
  return {
    pathologist: "Scientific findings and dispositions",
    peer_reviewer: "Independent pathology assessment",
    qau: "Inspection dates and report statement",
    study_director: "Final approval meaning and responsibility",
  }[role];
}

function artifactLabel(kind: string): string {
  return (
    {
      study_report_pdf: "Study report PDF",
      send_dataset_package: "Illustrative dataset archive",
      define_xml: "Illustrative define.xml",
      nsdrg: "Synthetic nSDRG PDF",
    }[kind] ?? kind
  );
}
