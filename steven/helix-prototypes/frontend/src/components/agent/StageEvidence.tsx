import type { ReactNode } from "react";

import { BODY_WEIGHT_PACKAGE, BODY_WEIGHT_SECTION, hybridValidationCount } from "@/lib/api/agentSteps";
import type { JourneyStageId, Workspace } from "@/lib/types";

// Lane B (#21). Package-understanding evidence per Agent Step, read only from the
// persisted Workspace. Nothing here is derived progress; empty means "not recorded".

function Hash({ value }: { value: string | null | undefined }) {
  if (!value) {
    return <span className="hx-sub">not recorded</span>;
  }
  return (
    <code className="hx-mono" title={value}>
      {value.length > 16 ? `${value.slice(0, 16)}…` : value}
    </code>
  );
}

function Row({ label, children, testId }: { label: string; children: ReactNode; testId?: string }) {
  return (
    <div className="hx-agent-fact" data-testid={testId}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Missing({ children }: { children: ReactNode }) {
  return <p className="hx-sub" data-testid="agent-evidence-missing">{children}</p>;
}

export function StageEvidence({ stageId, workspace }: { stageId: JourneyStageId; workspace: Workspace }) {
  const pinned = workspace.pinned_run;
  const run = workspace.section_runs.filter((item) => item.receipt.section_package_id === BODY_WEIGHT_SECTION).at(-1)?.receipt;
  const body = (() => {
    switch (stageId) {
      case "parse":
        if (!pinned) return <Missing>No Pinned Run yet. A person freezes the manifest at Human gate 1.</Missing>;
        return (
          <>
            <Row label="Pinned Run" testId="evidence-pinned-run">
              <code className="hx-mono">{pinned.run_id}</code>
            </Row>
            <Row label="Manifest hash">
              <Hash value={pinned.manifest_hash} />
            </Row>
            <Row label="Run-plan nodes" testId="evidence-run-plan-nodes">
              {pinned.run_plan.nodes.map((node) => node.node_id).join(", ")}
            </Row>
            <Row label="Governed inputs" testId="evidence-governed-inputs">
              {pinned.governed_inputs.length}
              <ul className="hx-agent-list">
                {pinned.governed_inputs.map((item) => (
                  <li key={item.artifact_id}>
                    {item.artifact_id} <Hash value={item.content_hash} />
                  </li>
                ))}
              </ul>
            </Row>
          </>
        );
      case "resolve": {
        const resolution = pinned?.study_type_resolution;
        if (!resolution) return <Missing>Study type is resolved when the manifest is frozen.</Missing>;
        return (
          <>
            <Row label="Resolution" testId="evidence-study-type">
              {resolution.study_type_id} ({resolution.status})
            </Row>
            <Row label="Mapping">
              {resolution.mapping_version} <Hash value={resolution.mapping_hash} />
            </Row>
            <Row label="Protocol fields">{Object.keys(resolution.protocol_fields ?? {}).length}</Row>
            <p className="hx-sub">Prior report patterns supply structure only, never values.</p>
          </>
        );
      }
      case "extract": {
        const execution = workspace.data_validation_executions.find(
          (item) => item.receipt.run_id === pinned?.run_id && item.receipt.package_id === BODY_WEIGHT_PACKAGE,
        );
        if (!execution) return <Missing>The Data Validation Package has not run for this Pinned Run.</Missing>;
        const receipt = execution.receipt;
        return (
          <>
            <Row label="Receipt" testId="evidence-dvp-receipt">
              <code className="hx-mono">{receipt.receipt_id}</code>
              {receipt.idempotent_replay ? " · idempotent replay" : ""}
            </Row>
            <Row label="Package">
              {receipt.package_id}@{receipt.package_version} <Hash value={receipt.package_hash} />
            </Row>
            <Row label="Executor">
              {receipt.executor_id}@{receipt.executor_version} <Hash value={receipt.executor_hash} />
            </Row>
            <Row label="Source artifact">
              {receipt.source_artifact_id} <Hash value={receipt.source_hash} />
            </Row>
            <Row label="Rules" testId="evidence-dvp-rules">{receipt.rule_ids.join(", ")}</Row>
            <Row label="Validated claims">{receipt.claim_ids.join(", ")}</Row>
            <Row label="Provenance edges">{execution.provenance_edges.length}</Row>
            <Row label="Section references">{execution.section_references.length}</Row>
          </>
        );
      }
      case "validate": {
        const eligibility = workspace.section_run_eligibility.find((item) => item.section_package_id === BODY_WEIGHT_SECTION);
        return (
          <>
            <Row label="Hybrid validation results" testId="evidence-validation-count">
              {hybridValidationCount(workspace) === 0 ? "not run" : hybridValidationCount(workspace)}
            </Row>
            <Row label="All validation results">{workspace.validations.length}</Row>
            <Row label="Open blockers">{workspace.summary.blocker_count}</Row>
            <Row label="Body-weight section" testId="evidence-eligibility">
              {eligibility ? (eligibility.eligible ? "Eligible to draft" : `Blocked: ${eligibility.reasons.join("; ")}`) : "not recorded"}
            </Row>
          </>
        );
      }
      case "draft": {
        if (!run) return <Missing>The Section Agent has not run for the body-weight section.</Missing>;
        const query = (workspace.cross_section_queries ?? []).find((item) => item.run_id === run.run_id);
        const evaluation = (workspace.candidate_evaluations ?? []).find((item) => item.run_id === run.run_id);
        const promotion = [...(workspace.promotion_decisions ?? [])].reverse().find((item) => item.run_id === run.run_id);
        const draft = [...(workspace.section_drafts ?? [])].reverse().find((item) => item.run_id === run.run_id);
        return (
          <>
            <Row label="Section Agent run" testId="evidence-section-run">
              <code className="hx-mono">{run.run_id}</code> · {run.status}
            </Row>
            <Row label="Candidate">
              {run.candidate_id} <Hash value={run.candidate_hash} />
            </Row>
            <Row label="Envelope / skill">
              <Hash value={run.envelope_hash} /> <Hash value={run.skill_hash} />
            </Row>
            <Row label="Dependency query" testId="evidence-query">
              {query ? `${query.status} · ${query.requested_artifact_ids.join(", ")}` : "not run"}
            </Row>
            <Row label="Candidate evaluation" testId="evidence-evaluation">
              {evaluation
                ? `${evaluation.template_conformance_receipt.status} template conformance · next: ${evaluation.next_attempt_decision.action}`
                : "not run"}
            </Row>
            <Row label="Promotion decision" testId="evidence-promotion">
              {promotion
                ? promotion.eligible
                  ? "Eligible"
                  : `Rejected: ${promotion.failed_condition_ids.join(", ")}`
                : "not run"}
            </Row>
            <Row label="Section Draft" testId="evidence-draft">
              {draft ? `${draft.draft_id} · ${draft.status}` : "none"}
            </Row>
          </>
        );
      }
      case "provenance":
        return (
          <>
            <Row label="Evidence edges" testId="evidence-provenance-count">
              {workspace.summary.provenance_count}
            </Row>
            <Row label="Claims">{workspace.claims.length}</Row>
            <p className="hx-sub">
              <a href="#hx-evidence">Inspect exact source rows, recomputation, and lineage</a>
            </p>
          </>
        );
      default:
        return null;
    }
  })();
  if (!body) return null;
  return (
    <dl className="hx-agent-facts" data-testid="agent-stage-evidence">
      {body}
    </dl>
  );
}
