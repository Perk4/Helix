"use client";

import { ReviewStageView } from "@/components/review/ReviewStageView";
import type { Workspace } from "@/lib/types";

import fixture from "./fixture.json";

// Display-only: commands are no-ops so the fixture can never reach the API.
const workspace = fixture as unknown as Workspace;

export function ReviewParityFixture() {
  return (
    <div id="helix-e2e" className="hx-app">
      <main className="hx-main">
        <section className="hx-stage-view" aria-label="Stage view" data-testid="stage-view" data-selected-stage="review-export">
          <ReviewStageView workspace={workspace} onWorkspace={() => undefined} onRefresh={async () => undefined} />
        </section>
      </main>
    </div>
  );
}
