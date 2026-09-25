import type { JourneyAction, JourneyStage } from "@/lib/types";

import { CheckIcon, WarnIcon } from "../icons";
import { Spinner } from "../ui";

// Lane B (#21). Activity comes from the server projection (stage.actions, fed by #25's
// run events). The only client-side row is the HTTP request that is in flight right now,
// labelled "Request in progress"; it never marks anything recorded.

const STATUS_TEXT: Record<JourneyAction["status"], string> = {
  done: "Recorded",
  blocked: "Blocked",
  pending: "Queued",
};

export function ActivityList({ stage, inFlightLabel }: { stage: JourneyStage; inFlightLabel: string | null }) {
  return (
    <div role="list" aria-label={`${stage.name} activity`} data-testid="agent-activity">
      {stage.actions.map((action) => (
        <div
          key={action.action_id}
          role="listitem"
          className={`hx-act ${action.status === "pending" ? "queued" : ""}`}
          data-testid="agent-action"
          data-status={action.status}
        >
          <span className="ic" aria-hidden="true">
            {action.status === "done" ? (
              <CheckIcon size={14} />
            ) : action.status === "blocked" ? (
              <WarnIcon size={14} />
            ) : (
              <span className="hx-hollow" />
            )}
          </span>
          <span className="txt">
            {action.label}
            {action.detail && <span className="hx-sub"> · {action.detail}</span>}
          </span>
          <span className="tag">
            {STATUS_TEXT[action.status]}
            {action.outcome ? ` · ${action.outcome}` : ""}
          </span>
        </div>
      ))}
      {inFlightLabel && (
        <div role="listitem" className="hx-act active" data-testid="agent-request-in-flight">
          <span className="ic" aria-hidden="true">
            <Spinner />
          </span>
          <span className="txt">{inFlightLabel}</span>
          <span className="tag">Request in progress</span>
        </div>
      )}
      {stage.actions.length === 0 && !inFlightLabel && (
        <p className="hx-sub" data-testid="agent-activity-empty">
          No recorded activity for this stage yet.
        </p>
      )}
    </div>
  );
}
