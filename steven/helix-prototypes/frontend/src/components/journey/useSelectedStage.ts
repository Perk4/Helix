"use client";

import { useCallback, useEffect, useState } from "react";

import type { JourneyStageId, WorkbenchJourney } from "@/lib/types";

// Lane A (#19). The ONLY local journey state is which reached stage the user is viewing.
// Selecting never calls a command and never changes the server stage. A selection that
// is not (or no longer) selectable falls back to the server's current stage.
//
// DH-1: while the agent works (`follow.active`), the view follows the server: the stage of
// the governed command in flight, else `current_stage_id`. When the agent stops, the stage
// it was showing stays the manual pick, so a later server move never yanks the view away
// from a human who is inspecting. `followServer()` drops the manual pick (after a freeze).

export type StageFollow = { active: boolean; stageId: JourneyStageId | null };

export function defaultStageId(journey: WorkbenchJourney): JourneyStageId {
  return journey.current_stage_id ?? journey.stages[journey.stages.length - 1].stage_id;
}

export function useSelectedStage(journey: WorkbenchJourney | null | undefined, follow?: StageFollow) {
  const [picked, setPicked] = useState<JourneyStageId | null>(null);

  const selectable = (id: JourneyStageId | null) =>
    Boolean(id && journey?.stages.some((stage) => stage.stage_id === id && stage.selectable));

  const following = Boolean(journey && follow?.active);
  const selectedStageId: JourneyStageId | null = !journey
    ? null
    : following
      ? selectable(follow?.stageId ?? null)
        ? (follow?.stageId as JourneyStageId)
        : defaultStageId(journey)
      : selectable(picked)
        ? picked
        : defaultStageId(journey);

  // Keep the manual pick equal to the followed stage while following, so the stage the
  // agent stopped on is already the pick on the first idle render (no flash, no remount).
  useEffect(() => {
    if (following && selectedStageId) setPicked(selectedStageId);
  }, [following, selectedStageId]);

  const select = useCallback(
    (id: string) => {
      if (journey?.stages.some((stage) => stage.stage_id === id && stage.selectable)) {
        setPicked(id as JourneyStageId);
      }
    },
    [journey],
  );

  const followServer = useCallback(() => setPicked(null), []);

  return { selectedStageId, select, followServer };
}
