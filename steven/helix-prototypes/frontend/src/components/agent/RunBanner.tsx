import type { JourneyStage, WorkbenchJourney } from "@/lib/types";

import { Banner, Button, Spinner } from "../ui";
import { ClockIcon } from "../icons";

// Lane B (#21). Run banner for an Agent Step. Tone and text come from the server stage
// status plus whether an HTTP request is in flight. Pause and Resume stay disabled:
// no server command exists for them until #26.

const STATUS_TEXT: Record<JourneyStage["status"], string> = {
  complete: "Done",
  current: "Agent step",
  blocked: "Blocked",
  paused: "Paused",
  pending: "Not started",
};

export function RunBanner({
  journey,
  stage,
  requestInFlight,
}: {
  journey: WorkbenchJourney;
  stage: JourneyStage;
  requestInFlight: boolean;
}) {
  const tone = requestInFlight
    ? "running"
    : stage.status === "complete"
      ? "passed"
      : stage.status === "paused"
        ? "paused"
        : "awaiting";
  const status = requestInFlight ? "Request in progress" : STATUS_TEXT[stage.status];
  return (
    <Banner
      tone={tone}
      data-testid="agent-run-banner"
      leading={requestInFlight ? <Spinner /> : <ClockIcon size={20} />}
      kicker={`Stage ${stage.sequence} of ${journey.stages.length} · ${status}`}
      title={stage.name}
      right={
        <span className="hx-agent-banner-meta">
          {journey.run && (
            <span className="hx-mono" data-testid="agent-run-id">
              {journey.run.run_id}
            </span>
          )}
          <Button size="sm" disabled aria-describedby="agent-pause-note" data-testid="agent-pause">
            Pause
          </Button>
          <span id="agent-pause-note" className="hx-sr">
            Pause and resume are unavailable: the server has no pause or resume command yet.
          </span>
        </span>
      }
    />
  );
}
