import type { JourneyStage } from "@/lib/types";

import { ArrowIcon } from "../icons";
import { Kicker } from "../ui";

// Lane B (#21). Input and output cards for an Agent Step, straight from the server projection.
export function StageIO({ stage }: { stage: JourneyStage }) {
  return (
    <div className="hx-io" data-testid="agent-stage-io">
      <div>
        <Kicker size="sm">Input</Kicker>
        <strong>{stage.input.title}</strong>
        <p className="hx-sub">{stage.input.detail}</p>
      </div>
      <div className="arrow" aria-hidden="true">
        <ArrowIcon size={18} />
      </div>
      <div className="out">
        <Kicker size="sm">Output</Kicker>
        <strong>{stage.output.title}</strong>
        <p className="hx-sub">{stage.output.detail}</p>
      </div>
    </div>
  );
}
