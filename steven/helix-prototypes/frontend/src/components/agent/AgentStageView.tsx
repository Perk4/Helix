"use client";

import { isAgentStep, nextAgentStep, type AgentStep } from "@/lib/api/agentSteps";
import type { JourneyStage, PlannerMode, Workspace } from "@/lib/types";

import { PersonIcon, ShieldIcon } from "../icons";
import { Button, Card, Kicker } from "../ui";
import { ActivityList } from "./ActivityList";
import { RunBanner } from "./RunBanner";
import { StageEvidence } from "./StageEvidence";
import { StageIO } from "./StageIO";

// Lane B (#21). One Agent Step view for stages 2-7 (Parse through Provenance).
// Everything shown comes from the server Workspace and its journey projection.
// Commands appear only on the stage the server says is current or blocked; a
// completed stage is read-only review and selecting it never changes progress.

export const AGENT_STAGE_IDS = ["parse", "resolve", "extract", "validate", "draft", "provenance"] as const;

export function isAgentStageId(value: string | null | undefined): boolean {
  return Boolean(value && (AGENT_STAGE_IDS as readonly string[]).includes(value));
}

type Props = {
  workspace: Workspace;
  stage: JourneyStage;
  planner: PlannerMode;
  onPlannerChange: (planner: PlannerMode) => void;
  /** The governed command whose HTTP request is in flight, if any. */
  inFlight: AgentStep | null;
  /** Another workbench command is running; commands here wait. */
  otherBusy: boolean;
  onRunStep: () => void;
  onRunSequence: () => void;
};

export function AgentStageView({
  workspace,
  stage,
  planner,
  onPlannerChange,
  inFlight,
  otherBusy,
  onRunStep,
  onRunSequence,
}: Props) {
  const next = nextAgentStep(workspace);
  const actionable = stage.status === "current" || stage.status === "blocked";
  const busy = Boolean(inFlight) || otherBusy;
  const llm = workspace.planner_capabilities.find((item) => item.mode === "openai_compatible");

  return (
    <Card stack className="hx-agent-stage" data-testid="agent-stage-view" data-stage={stage.stage_id} aria-labelledby="agent-stage-heading">
      <RunBanner journey={workspace.journey} stage={stage} requestInFlight={inFlight?.stageId === stage.stage_id} />
      <div>
        <Kicker size="sm">Agent step</Kicker>
        <h2 id="agent-stage-heading">{stage.name}</h2>
        <p className="hx-sub" data-testid="agent-stage-summary">
          {stage.summary}
        </p>
      </div>
      <StageIO stage={stage} />
      <div className="hx-boundary" data-testid="agent-control-boundary">
        <ShieldIcon size={18} />
        <span>
          <strong>Control boundary. </strong>
          {stage.control_boundary}
        </span>
      </div>

      <StageEvidence stageId={stage.stage_id} workspace={workspace} />

      {actionable && (
        <div className="hx-agent-commands" data-testid="agent-commands">
          {stage.stage_id === "validate" && (
            <fieldset className="hx-agent-planner">
              <legend>Planner</legend>
              <label>
                <input
                  type="radio"
                  name="agent-planner"
                  checked={planner === "fixture"}
                  onChange={() => onPlannerChange("fixture")}
                />{" "}
                Fixture planner (no LLM)
              </label>
              <label>
                <input
                  type="radio"
                  name="agent-planner"
                  checked={planner === "openai_compatible"}
                  disabled={!llm?.available}
                  onChange={() => onPlannerChange("openai_compatible")}
                />{" "}
                LLM planner {llm?.available ? "" : "(not configured)"}
              </label>
            </fieldset>
          )}
          {isAgentStep(next) ? (
            <>
              <Button
                variant="primary"
                disabled={busy || next.stageId !== stage.stage_id}
                onClick={onRunStep}
                data-testid="agent-run-step"
              >
                {inFlight ? `${inFlight.label}…` : next.label}
              </Button>
              <Button disabled={busy} onClick={onRunSequence} data-testid="agent-run-sequence">
                Run agent steps to the next stop
              </Button>
              {next.stageId !== stage.stage_id && (
                <p className="hx-sub" data-testid="agent-next-elsewhere">
                  The next governed command belongs to another stage: {next.label}.
                </p>
              )}
            </>
          ) : (
            <p className="hx-stage-note" data-testid="agent-stop" data-stop={next.kind}>
              {next.kind === "gate" ? <PersonIcon size={16} /> : null} {next.message}
            </p>
          )}
        </div>
      )}
      {!actionable && stage.status === "complete" && (
        <p className="hx-sub" data-testid="agent-stage-review">
          Completed stage. Showing its recorded actions; nothing here changes progress.
        </p>
      )}

      <ActivityList stage={stage} inFlightLabel={inFlight?.stageId === stage.stage_id ? inFlight.label : null} />
    </Card>
  );
}
