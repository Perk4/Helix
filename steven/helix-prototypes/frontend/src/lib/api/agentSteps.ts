// Lane B (#21). Governed Agent Step sequence for stages 2-7.
//
// The server is the only authority: every decision below reads a freshly fetched
// Workspace, one command runs at a time, and the sequence stops on the first error,
// blocker, or human decision. Nothing here advances on a timer, and the agent never
// passes Traceability review (Human gate 2).

import {
  ApiError,
  evaluateCandidate,
  promoteSectionDraft,
  queryCrossSection,
  runDataValidation,
  runSectionAgent,
  runValidation,
} from "@/lib/api";
import type { JourneyStageId, PlannerMode, Workspace } from "@/lib/types";

export const BODY_WEIGHT_PACKAGE = "validation.body_weight";
export const BODY_WEIGHT_SECTION = "section.5_2_3_body_weight";

export type AgentAction =
  | "data-validation"
  | "validation"
  | "section-run"
  | "cross-section-query"
  | "candidate-evaluation"
  | "section-promotion";

export type AgentStep = {
  action: AgentAction;
  stageId: JourneyStageId;
  label: string;
  /** Section Agent run the command targets (draft-stage commands only). */
  runId?: string;
};

export type AgentStop =
  | { kind: "needs-freeze"; stageId: JourneyStageId; message: string }
  | { kind: "blocker"; stageId: JourneyStageId; message: string }
  | { kind: "human-decision"; stageId: JourneyStageId; message: string }
  | { kind: "gate"; stageId: JourneyStageId; message: string };

export const ACTION_LABELS: Record<AgentAction, string> = {
  "data-validation": "Execute Data Validation Package",
  validation: "Run deterministic and hybrid validation",
  "section-run": "Run governed Section Agent",
  "cross-section-query": "Query declared dependencies",
  "candidate-evaluation": "Evaluate candidate",
  "section-promotion": "Promote governed draft",
};

const ACTION_STAGE: Record<AgentAction, JourneyStageId> = {
  "data-validation": "extract",
  validation: "validate",
  "section-run": "draft",
  "cross-section-query": "draft",
  "candidate-evaluation": "draft",
  "section-promotion": "draft",
};

function step(action: AgentAction, runId?: string): AgentStep {
  return { action, stageId: ACTION_STAGE[action], label: ACTION_LABELS[action], runId };
}

/** The next governed command, or why the agent must stop, from server state only. */
// Workspace validations also carry the Data Validation Package results, so hybrid
// validation counts as run only when a result exists that no package execution made.
export function hybridValidationCount(workspace: Workspace): number {
  const packageResultIds = new Set(
    workspace.data_validation_executions.flatMap((execution) => execution.results.map((item) => item.result_id)),
  );
  return workspace.validations.filter((item) => !packageResultIds.has(item.result_id)).length;
}

export function nextAgentStep(workspace: Workspace): AgentStep | AgentStop {
  const pinned = workspace.pinned_run;
  if (!pinned) {
    return {
      kind: "needs-freeze",
      stageId: "upload",
      message: "The agent starts after a person freezes the authorized manifest at Human gate 1.",
    };
  }
  const execution = workspace.data_validation_executions.find(
    (item) => item.receipt.run_id === pinned.run_id && item.receipt.package_id === BODY_WEIGHT_PACKAGE,
  );
  if (!execution) {
    return step("data-validation");
  }
  const eligibility = workspace.section_run_eligibility.find(
    (item) => item.section_package_id === BODY_WEIGHT_SECTION,
  );
  const runs = workspace.section_runs.filter(
    (item) => item.receipt.section_package_id === BODY_WEIGHT_SECTION,
  );
  const run = runs.at(-1)?.receipt;
  if (!run && !eligibility?.eligible && hybridValidationCount(workspace) === 0) {
    return step("validation");
  }
  if (!run) {
    if (!eligibility?.eligible) {
      return {
        kind: "blocker",
        stageId: "validate",
        message: `The Section Agent is not eligible: ${(eligibility?.reasons ?? ["no eligibility recorded"]).join("; ")}.`,
      };
    }
    return step("section-run");
  }
  if (!(workspace.cross_section_queries ?? []).some((item) => item.run_id === run.run_id)) {
    return step("cross-section-query", run.run_id);
  }
  const evaluation = (workspace.candidate_evaluations ?? []).find((item) => item.run_id === run.run_id);
  if (!evaluation) {
    return step("candidate-evaluation", run.run_id);
  }
  const decision = evaluation.next_attempt_decision;
  if (decision.action === "retry" || decision.action === "hold") {
    return {
      kind: "human-decision",
      stageId: "draft",
      message:
        decision.action === "retry"
          ? `Candidate evaluation asks for another attempt (attempt ${decision.attempt}). A person chooses whether to retry.`
          : "Candidate evaluation put the draft on hold for a person.",
    };
  }
  if (!(workspace.promotion_decisions ?? []).some((item) => item.run_id === run.run_id)) {
    return step("section-promotion", run.run_id);
  }
  return {
    kind: "gate",
    stageId: "traceability",
    message: "The agent stops at Traceability review. Only a person can pass Human gate 2.",
  };
}

export function isAgentStep(value: AgentStep | AgentStop): value is AgentStep {
  return "action" in value;
}

// #17 run-scoped durable action IDs. A key names the study, Pinned Run, action,
// subject, and attempt. A retry after an unknown result (network failure, 5xx)
// reuses the pending key so the server can replay it; a definite answer (a receipt
// or a 4xx rejection) settles it, and the next attempt gets a new key. A superseding
// run has a new run ID, so its keys are new too.
const STORE_KEY = "helix.agent-action-keys.v1";

type KeyRecord = { attempt: number; pending: string | null };

function readStore(): Record<string, KeyRecord> {
  if (typeof window === "undefined") {
    return {};
  }
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(STORE_KEY) ?? "{}");
    return value && typeof value === "object" ? (value as Record<string, KeyRecord>) : {};
  } catch {
    return {};
  }
}

function writeStore(store: Record<string, KeyRecord>) {
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(STORE_KEY, JSON.stringify(store));
  }
}

function slot(studyId: string, runId: string, action: AgentAction, subject: string) {
  return `${studyId}:${runId}:${action}:${subject}`;
}

export function actionKey(studyId: string, runId: string, action: AgentAction, subject: string): string {
  const store = readStore();
  const id = slot(studyId, runId, action, subject);
  const record = store[id] ?? { attempt: 0, pending: null };
  if (record.pending) {
    return record.pending;
  }
  const attempt = record.attempt + 1;
  const key = `workbench:${id}:a${attempt}`;
  store[id] = { attempt, pending: key };
  writeStore(store);
  return key;
}

export function settleActionKey(
  studyId: string,
  runId: string,
  action: AgentAction,
  subject: string,
  outcome: "recorded" | "rejected" | "unknown",
) {
  if (outcome === "unknown") {
    return; // keep the pending key: the retry must reuse it
  }
  const store = readStore();
  const id = slot(studyId, runId, action, subject);
  if (store[id]) {
    store[id] = { ...store[id], pending: null };
    writeStore(store);
  }
}

export function outcomeOf(cause: unknown): "rejected" | "unknown" {
  return cause instanceof ApiError && cause.status >= 400 && cause.status < 500 ? "rejected" : "unknown";
}

/** Run one governed command with its run-scoped key. Returns nothing: callers refresh. */
export async function executeAgentStep(
  studyId: string,
  workspace: Workspace,
  agentStep: AgentStep,
  planner: PlannerMode,
): Promise<void> {
  const runId = workspace.pinned_run?.run_id;
  if (!runId) {
    throw new Error("No Pinned Run: freeze the manifest first.");
  }
  const subject = agentStep.runId ?? BODY_WEIGHT_SECTION;
  const key = actionKey(studyId, runId, agentStep.action, subject);
  try {
    switch (agentStep.action) {
      case "data-validation":
        await runDataValidation(studyId, key);
        break;
      case "validation":
        await runValidation(studyId, planner);
        break;
      case "section-run":
        await runSectionAgent(studyId, key);
        break;
      case "cross-section-query":
        await queryCrossSection(studyId, subject, key);
        break;
      case "candidate-evaluation":
        await evaluateCandidate(studyId, subject, key);
        break;
      case "section-promotion":
        await promoteSectionDraft(studyId, subject, key);
        break;
    }
  } catch (cause) {
    settleActionKey(studyId, runId, agentStep.action, subject, outcomeOf(cause));
    throw cause;
  }
  settleActionKey(studyId, runId, agentStep.action, subject, "recorded");
}

export type SequenceHooks = {
  fetchWorkspace: () => Promise<Workspace>;
  onWorkspace: (workspace: Workspace) => void;
  onStep: (agentStep: AgentStep | null) => void;
};

/**
 * Run governed commands in order until the agent must stop. Each command waits for
 * a refreshed Workspace (the server precondition) before the next one is chosen.
 * A failed command throws and nothing after it runs.
 */
export async function runAgentSequence(
  studyId: string,
  planner: PlannerMode,
  hooks: SequenceHooks,
  maxSteps = 8,
): Promise<AgentStop | null> {
  let workspace = await hooks.fetchWorkspace();
  hooks.onWorkspace(workspace);
  try {
    for (let index = 0; index < maxSteps; index += 1) {
      const next = nextAgentStep(workspace);
      if (!isAgentStep(next)) {
        return next;
      }
      hooks.onStep(next);
      await executeAgentStep(studyId, workspace, next, planner);
      workspace = await hooks.fetchWorkspace();
      hooks.onWorkspace(workspace);
    }
    return null;
  } finally {
    hooks.onStep(null);
  }
}
