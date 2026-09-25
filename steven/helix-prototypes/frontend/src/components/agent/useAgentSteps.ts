"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getWorkspace } from "@/lib/api";
import {
  BODY_WEIGHT_SECTION,
  executeAgentStep,
  isAgentStep,
  nextAgentStep,
  runAgentSequence,
  type AgentStep,
  type AgentStepReceipt,
  type NextStepOptions,
} from "@/lib/api/agentSteps";
import { streamRunEvents } from "@/lib/runEvents";
import type { PlannerMode, Workspace } from "@/lib/types";

// Lane B (#21). The Agent Step command handlers, kept out of the shared workbench.
// The server is the authority: every decision reads a freshly fetched Workspace, one
// command runs at a time, and a failure stops the sequence. While a command is in
// flight the hook follows #25's run-event stream for the Pinned Run and refreshes the
// Workspace on each server event, so activity rows come from the projection, never
// from local progress. Nothing here runs on a timer.

export type AgentMessage = { tone: "info" | "block"; text: string };

type Eligibility = Workspace["section_run_eligibility"][number];

export type EligibilityChange = { before: Eligibility | null; after: Eligibility | null };

export type AgentReceipts = Partial<{ [K in AgentStepReceipt["action"]]: Extract<AgentStepReceipt, { action: K }>["value"] }>;

type Options = {
  studyId: string;
  workspace: Workspace;
  onWorkspace: (workspace: Workspace) => void;
};

const CONFIRMED_KEY = "helix.agent-dv-confirmed.v1";

function readConfirmed(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const value: unknown = JSON.parse(window.sessionStorage.getItem(CONFIRMED_KEY) ?? "[]");
    return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

function eligibilityOf(workspace: Workspace): Eligibility | null {
  return workspace.section_run_eligibility.find((item) => item.section_package_id === BODY_WEIGHT_SECTION) ?? null;
}

export function messageFrom(cause: unknown): string {
  if (cause instanceof ApiError) return cause.message;
  if (cause instanceof Error) return cause.message;
  return "The request failed.";
}

export function useAgentSteps({ studyId, workspace, onWorkspace }: Options) {
  const [planner, setPlanner] = useState<PlannerMode>("fixture");
  const [inFlight, setInFlight] = useState<AgentStep | null>(null);
  const [message, setMessage] = useState<AgentMessage | null>(null);
  const [receipts, setReceipts] = useState<AgentReceipts>({});
  const [eligibilityChange, setEligibilityChange] = useState<EligibilityChange | null>(null);
  const [confirmed, setConfirmed] = useState<Set<string>>(() => new Set());
  const confirmedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const stored = readConfirmed();
    confirmedRef.current = stored;
    setConfirmed(stored);
  }, []);

  const options = useCallback((): NextStepOptions => ({ confirmedDataValidationRuns: confirmedRef.current }), []);

  const record = useCallback((agentStep: AgentStep, receipt: AgentStepReceipt, before: Workspace, after: Workspace) => {
    setReceipts((current) => ({ ...current, [receipt.action]: receipt.value }));
    if (receipt.action === "validation") {
      setEligibilityChange({ before: eligibilityOf(before), after: eligibilityOf(after) });
    }
    if (receipt.action === "data-validation") {
      const runId = receipt.value.receipt.run_id;
      const next = new Set(confirmedRef.current).add(runId);
      confirmedRef.current = next;
      setConfirmed(next);
      window.sessionStorage.setItem(CONFIRMED_KEY, JSON.stringify([...next]));
    }
    void agentStep;
  }, []);

  // #25: follow the server's run events while a command is in flight; each event refreshes
  // the projection. The stream closes when the command settles (abort), never on a timer.
  const runId = workspace.pinned_run?.run_id ?? null;
  const cursor = workspace.journey.run?.latest_event_id ?? null;
  const cursorRef = useRef(cursor);
  cursorRef.current = cursor;
  const following = Boolean(inFlight);
  useEffect(() => {
    if (!following || !runId) return;
    const controller = new AbortController();
    void streamRunEvents({
      studyId,
      runId,
      lastEventId: cursorRef.current,
      signal: controller.signal,
      onEvent: () => {
        void getWorkspace(studyId).then(onWorkspace, () => undefined);
      },
      onWorkspaceRefresh: onWorkspace,
    }).catch(() => undefined); // The command's own refresh stays the fallback authority.
    return () => controller.abort();
  }, [following, runId, studyId, onWorkspace]);

  const runStep = useCallback(async () => {
    const next = nextAgentStep(workspace, options());
    if (!isAgentStep(next)) return;
    setMessage(null);
    setInFlight(next);
    try {
      const receipt = await executeAgentStep(studyId, workspace, next, planner);
      const after = await getWorkspace(studyId);
      onWorkspace(after);
      record(next, receipt, workspace, after);
      setMessage({
        tone: "info",
        text:
          receipt.action === "data-validation" && receipt.value.receipt.idempotent_replay
            ? `${next.label}: the server returned the recorded execution ${receipt.value.receipt.receipt_id} as an idempotent replay.`
            : `${next.label}: recorded by the server.`,
      });
    } catch (cause) {
      try {
        onWorkspace(await getWorkspace(studyId));
      } catch {
        // Keep the last server state; the error below explains what failed.
      }
      setMessage({ tone: "block", text: `${next.label} failed. ${messageFrom(cause)}` });
    } finally {
      setInFlight(null);
    }
  }, [workspace, options, studyId, planner, onWorkspace, record]);

  const runSequence = useCallback(async () => {
    setMessage(null);
    let current: AgentStep | null = null;
    try {
      const stop = await runAgentSequence(studyId, planner, {
        fetchWorkspace: () => getWorkspace(studyId),
        onWorkspace,
        onStep: (value) => {
          if (value) current = value;
          setInFlight(value);
        },
        onReceipt: record,
        options,
      });
      if (stop) setMessage({ tone: "info", text: stop.message });
    } catch (cause) {
      const label = (current as AgentStep | null)?.label;
      try {
        onWorkspace(await getWorkspace(studyId));
      } catch {
        // Keep the last server state.
      }
      setMessage({
        tone: "block",
        text: `${label ? `${label} failed. ` : ""}${messageFrom(cause)} The agent stopped; later steps did not run.`,
      });
    }
  }, [studyId, planner, onWorkspace, record, options]);

  return {
    planner,
    setPlanner,
    inFlight,
    message,
    dismissMessage: () => setMessage(null),
    receipts,
    eligibilityChange,
    next: nextAgentStep(workspace, { confirmedDataValidationRuns: confirmed }),
    runStep: () => void runStep(),
    runSequence: () => void runSequence(),
  };
}
