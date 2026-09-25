"use client";

import type { ExportReceipt, Workspace } from "@/lib/types";

import { RetryIcon } from "../icons";
import { Button, Spinner } from "../ui";
import { exportedAtFromJourney } from "./reviewState";

// Lane D (#23): the explicit export. Enabled only when the SERVER release gate reports
// ready_for_export. It is its own button press with loading, success, error, and replay states.

export type ExportState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; receipt: ExportReceipt }
  | { kind: "error"; message: string };

export function ExportPanel({
  workspace,
  state,
  onExport,
}: {
  workspace: Workspace;
  state: ExportState;
  onExport: () => void;
}) {
  const status = workspace.release_gate.status;
  const exported = status === "exported";
  const ready = status === "ready_for_export";
  const exportedAt = state.kind === "success" ? state.receipt.exported_at : exportedAtFromJourney(workspace);
  return (
    <div className="stack hx-export" data-testid="export-panel" data-state={state.kind}>
      <Button
        variant="primary"
        disabled={!ready || state.kind === "loading"}
        onClick={onExport}
        data-testid="export-final-package"
      >
        {state.kind === "loading" ? (
          <>
            <Spinner onFill /> Exporting…
          </>
        ) : exported ? (
          "Package exported"
        ) : state.kind === "error" ? (
          <>
            <RetryIcon size={16} /> Retry export
          </>
        ) : (
          "Export final package"
        )}
      </Button>
      {!ready && !exported && (
        <p className="hx-sub hx-fine" data-testid="export-disabled-reason">
          Export stays disabled until the server release gate is ready for export (now:{" "}
          {status.replaceAll("_", " ")}).
        </p>
      )}
      {state.kind === "error" && (
        <p className="hx-notice t-block" role="alert" data-testid="export-error">
          {state.message}
        </p>
      )}
      {(state.kind === "success" || exported) && (
        <dl className="hx-export-receipt" data-testid="export-receipt">
          <dt>Exported at</dt>
          <dd className="hx-mono" data-testid="export-exported-at">
            {exportedAt ?? "recorded by the server"}
          </dd>
          <dt>Idempotent replay</dt>
          <dd className="hx-mono" data-testid="export-idempotent-replay">
            {state.kind === "success" ? (state.receipt.idempotent_replay ? "yes" : "no") : "not in this session"}
          </dd>
        </dl>
      )}
      <p className="hx-sub hx-fine">
        Export is a separate action after approval. A prepared package is not FDA acceptance.
      </p>
    </div>
  );
}
