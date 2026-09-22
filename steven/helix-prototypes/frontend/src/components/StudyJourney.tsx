"use client";

import { useEffect, useMemo, useState } from "react";

import type { PlannerMode, Workspace } from "@/lib/types";

type Props = {
  workspace: Workspace;
  planner: PlannerMode;
  busy: boolean;
  onPlannerChange: (planner: PlannerMode) => void;
  onValidate: () => void;
};

export function StudyJourney({
  workspace,
  planner,
  busy,
  onPlannerChange,
  onValidate,
}: Props) {
  const defaultStage = useMemo(
    () =>
      workspace.stages.find((stage) => stage.status === "current" || stage.status === "blocked") ??
      workspace.stages.at(-1),
    [workspace.stages],
  );
  const [selectedStageId, setSelectedStageId] = useState(defaultStage?.stage_id ?? "gate");

  useEffect(() => {
    if (!workspace.stages.some((stage) => stage.stage_id === selectedStageId)) {
      setSelectedStageId(defaultStage?.stage_id ?? "gate");
    }
  }, [defaultStage, selectedStageId, workspace.stages]);

  const stage =
    workspace.stages.find((candidate) => candidate.stage_id === selectedStageId) ?? defaultStage;
  const fixture = workspace.planner_capabilities.find((item) => item.mode === "fixture");
  const llm = workspace.planner_capabilities.find((item) => item.mode === "openai_compatible");

  if (!stage) {
    return null;
  }

  return (
    <section className="view-content" aria-labelledby="journey-heading">
      <div className="view-intro">
        <div>
          <p className="eyebrow">Evidence-to-report control plane</p>
          <h2 id="journey-heading">A ten-stage journey with visible boundaries.</h2>
          <p>
            HELIX can locate, extract, check, and draft. Qualified people retain scientific
            interpretation, quality assurance, signatures, and export authorization.
          </p>
        </div>
        <div className="summary-strip" aria-label="Study summary">
          <Metric value={workspace.summary.source_count} label="Frozen sources" />
          <Metric value={workspace.summary.record_count.toLocaleString()} label="Study records" />
          <Metric value={workspace.summary.provenance_count} label="Evidence edges" />
          <Metric
            value={workspace.summary.blocker_count}
            label="Open blockers"
            tone={workspace.summary.blocker_count > 0 ? "danger" : "success"}
          />
        </div>
      </div>

      <div className="stage-rail" aria-label="Study workflow stages">
        {workspace.stages.map((item, index) => (
          <button
            key={item.stage_id}
            type="button"
            className={`stage-step ${item.status} ${item.stage_id === stage.stage_id ? "selected" : ""}`}
            onClick={() => setSelectedStageId(item.stage_id)}
            aria-current={item.stage_id === stage.stage_id ? "step" : undefined}
          >
            <span className="stage-index">{String(index + 1).padStart(2, "0")}</span>
            <span className="stage-dot" aria-hidden="true" />
            <span className="stage-name">{item.name}</span>
          </button>
        ))}
      </div>

      <div className="journey-grid">
        <article className="panel stage-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Selected stage</p>
              <h3>{stage.name}</h3>
            </div>
            <span className={`owner-chip ${stage.owner}`}>{ownerLabel(stage.owner)}</span>
          </div>
          <p className="lead-copy">{stage.summary}</p>
          <div className="check-list">
            {stage.checks.map((check) => (
              <div className="check-row" key={check}>
                <span className="check-icon">✓</span>
                <span>{check}</span>
              </div>
            ))}
          </div>
          {stage.stage_id === "authorized-upload" && (
            <div className="source-manifest" data-testid="source-manifest">
              <div className="source-manifest-heading">
                <strong>Frozen source manifest</strong>
                <span>{workspace.manifest.length} authorized</span>
              </div>
              {workspace.manifest.map((entry) => (
                <div className="source-manifest-row" key={entry.artifact_id}>
                  <span className="manifest-lock">✓</span>
                  <div>
                    <strong>{entry.name}</strong>
                    <span>
                      Tier {entry.authority_tier} · {entry.version} · {entry.authorized_by}
                    </span>
                  </div>
                  <code>{entry.checksum.slice(0, 15)}…</code>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="panel transformation-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Evidence transformation</p>
              <h3>Input stays distinct from output.</h3>
            </div>
            <span className={`status-dot-label ${stage.status}`}>
              <span /> {stage.status}
            </span>
          </div>
          <div className="flow-pair">
            <div className="flow-node">
              <span>Input</span>
              <strong>{stage.input_title}</strong>
              <code>{stage.input_detail}</code>
            </div>
            <div className="flow-arrow" aria-hidden="true">
              →
            </div>
            <div className="flow-node output">
              <span>Output</span>
              <strong>{stage.output_title}</strong>
              <code>{stage.output_detail}</code>
            </div>
          </div>
          <div className="boundary-callout">
            <span>Control boundary</span>
            <p>{stage.boundary}</p>
          </div>
        </article>

        <aside className="panel validation-console">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Hybrid validation</p>
              <h3>Plan with a model. Decide with code.</h3>
            </div>
          </div>
          <div className="planner-options" role="radiogroup" aria-label="Check planner">
            <button
              type="button"
              role="radio"
              aria-checked={planner === "fixture"}
              className={planner === "fixture" ? "planner-option active" : "planner-option"}
              onClick={() => onPlannerChange("fixture")}
            >
              <span className="planner-title">
                Fixture planner <small>Offline</small>
              </span>
              <span>{fixture?.detail}</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={planner === "openai_compatible"}
              disabled={!llm?.available}
              className={planner === "openai_compatible" ? "planner-option active" : "planner-option"}
              onClick={() => onPlannerChange("openai_compatible")}
            >
              <span className="planner-title">
                LLM planner <small>{llm?.available ? "Configured" : "Needs API key"}</small>
              </span>
              <span>{llm?.detail}</span>
            </button>
          </div>
          <button
            className="button primary wide"
            type="button"
            onClick={onValidate}
            disabled={busy}
            data-testid="run-validation"
          >
            {busy ? "Running checks…" : "Run hybrid validation"}
          </button>
          <p className="fine-print">
            The planner can only select registered tools. Python calculates every result and gate state.
          </p>
        </aside>
      </div>

      <div className="journey-lower-grid">
        <article className="panel source-map-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Package map</p>
              <h3>One frozen study package, four controlled outputs.</h3>
            </div>
          </div>
          <div className="package-map">
            <PackageNode label="Authorized research inputs" value="10" detail="Frozen and checksummed" />
            <MapArrow />
            <PackageNode label="Normalized evidence" value="1,662" detail="Typed and source-linked" />
            <MapArrow />
            <PackageNode label="Structured report" value="8" detail="Sections with field rules" />
            <MapArrow />
            <PackageNode
              label="Export package"
              value="4"
              detail="Report and synthetic data support files"
            />
          </div>
        </article>

        <aside className="panel activity-card">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Append-only activity</p>
              <h3>Latest decisions</h3>
            </div>
            <span className="count-chip">{workspace.events.length}</span>
          </div>
          <div className="activity-list">
            {[...workspace.events]
              .reverse()
              .slice(0, 5)
              .map((event) => (
                <div className="activity-row" key={event.event_id}>
                  <span className="activity-marker" />
                  <div>
                    <strong>{humanize(event.event)}</strong>
                    <span>
                      {event.actor} · {formatTime(event.timestamp)}
                    </span>
                  </div>
                  <em>{event.outcome}</em>
                </div>
              ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function Metric({
  value,
  label,
  tone = "default",
}: {
  value: string | number;
  label: string;
  tone?: "default" | "danger" | "success";
}) {
  return (
    <div className={`metric ${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function PackageNode({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="package-node">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function MapArrow() {
  return (
    <div className="map-arrow" aria-hidden="true">
      →
    </div>
  );
}

function ownerLabel(owner: "agent" | "human" | "hybrid"): string {
  return {
    agent: "Agent executed",
    human: "Human controlled",
    hybrid: "Hybrid control",
  }[owner];
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}
