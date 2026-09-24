// Run-event stream client (Steven-Espaillat/Helix#25).
// Reads the backend SSE stream for one Pinned Run. On HTTP 409 `event_cursor_expired`
// it refreshes the workspace projection and reconnects from the server's latest event,
// deduplicating by event_id so a completion is never delivered twice.
import { API_ROOT, getWorkspace } from "./api";
import type { EventCursorExpired, RunEvent, Workspace } from "./types";

export type RunEventStreamOptions = {
  studyId: string;
  runId: string;
  lastEventId?: string | null;
  onEvent: (event: RunEvent) => void;
  onWorkspaceRefresh?: (workspace: Workspace) => void;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  refreshWorkspace?: (studyId: string) => Promise<Workspace>;
  maxReconnects?: number;
};

export type RunEventStreamResult = {
  lastEventId: string | null;
  delivered: number;
  refreshed: number;
};

export function isEventCursorExpired(value: unknown): value is EventCursorExpired {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { code?: unknown }).code === "event_cursor_expired" &&
    typeof (value as { run_id?: unknown }).run_id === "string"
  );
}

export function parseRunEventFrames(text: string): RunEvent[] {
  const events: RunEvent[] = [];
  for (const block of text.split(/\n\n/)) {
    const data = block
      .split("\n")
      .filter((line) => line.startsWith("data: "))
      .map((line) => line.slice(6))
      .join("\n");
    if (data) {
      events.push(JSON.parse(data) as RunEvent);
    }
  }
  return events;
}

export async function streamRunEvents(options: RunEventStreamOptions): Promise<RunEventStreamResult> {
  const fetcher = options.fetchImpl ?? fetch;
  const refresh = options.refreshWorkspace ?? getWorkspace;
  const seen = new Set<string>();
  let cursor = options.lastEventId ?? null;
  let delivered = 0;
  let refreshed = 0;
  const maxReconnects = options.maxReconnects ?? 1;

  for (let attempt = 0; attempt <= maxReconnects; attempt += 1) {
    const url = `${API_ROOT}/studies/${encodeURIComponent(options.studyId)}/pinned-runs/${encodeURIComponent(options.runId)}/events`;
    const response = await fetcher(url, {
      headers: cursor ? { Accept: "text/event-stream", "Last-Event-ID": cursor } : { Accept: "text/event-stream" },
      cache: "no-store",
      signal: options.signal,
    });
    if (response.status === 409) {
      const body: unknown = await response.json();
      if (!isEventCursorExpired(body)) {
        throw new Error("The run-event stream returned an untyped conflict.");
      }
      const workspace = await refresh(options.studyId);
      refreshed += 1;
      options.onWorkspaceRefresh?.(workspace);
      cursor = workspace.journey.run?.latest_event_id ?? body.latest_event_id ?? null;
      continue;
    }
    if (!response.ok || !response.body) {
      throw new Error(`The run-event stream failed with HTTP ${response.status}.`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      const boundary = buffer.lastIndexOf("\n\n");
      if (boundary >= 0) {
        for (const event of parseRunEventFrames(buffer.slice(0, boundary + 2))) {
          if (seen.has(event.event_id)) continue;
          seen.add(event.event_id);
          cursor = event.event_id;
          delivered += 1;
          options.onEvent(event);
        }
        buffer = buffer.slice(boundary + 2);
      }
      if (done) break;
    }
    return { lastEventId: cursor, delivered, refreshed };
  }
  throw new Error("The run-event cursor expired repeatedly; reload the workspace.");
}
