"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  ApiError,
  applySection,
  discardSection,
  getChat,
  reviseSection,
  sendChat,
} from "@/lib/api";
import type { ChatMessage, SectionDraft } from "@/lib/types";

type Props = {
  studyId: string;
  sectionId: string;
  sectionTitle: string;
  onApplied?: () => void;
};

export function ChatDock({ studyId, sectionId, sectionTitle, onApplied }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [proposed, setProposed] = useState<SectionDraft | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState<null | "ask" | "revise" | "apply">(null);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    getChat(studyId)
      .then((value) => active && setMessages(value))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [studyId]);

  useEffect(() => {
    if (open && listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, proposed, open]);

  function pushLocal(role: "user" | "assistant", content: string) {
    setMessages((prev) => [
      ...prev,
      {
        message_id: -Date.now() - Math.random(),
        role,
        content,
        scope: "section",
        section_id: sectionId,
        intent: "revise",
        created_at: new Date().toISOString(),
      },
    ]);
  }

  async function ask() {
    const text = input.trim();
    if (!text || busy) return;
    setBusy("ask");
    setError(null);
    setOpen(true);
    setInput("");
    const optimistic: ChatMessage = {
      message_id: -Date.now(),
      role: "user",
      content: text,
      scope: "section",
      section_id: sectionId,
      intent: "ask",
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    try {
      // The backend grounds every answer in the study summary + this section,
      // so one Ask handles study-wide or section questions.
      await sendChat(studyId, text, "section", sectionId);
      setMessages(await getChat(studyId));
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setBusy(null);
    }
  }

  async function revise() {
    const text = input.trim();
    if (!text || busy) return;
    setBusy("revise");
    setError(null);
    setOpen(true);
    setInput("");
    pushLocal("user", `Revise: ${text}`);
    try {
      const draft = await reviseSection(studyId, sectionId, text);
      setProposed(draft);
      pushLocal("assistant", `Proposed v${draft.version} — review and approve or discard below.`);
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setBusy(null);
    }
  }

  async function apply() {
    if (!proposed || busy) return;
    setBusy("apply");
    setError(null);
    try {
      await applySection(studyId, sectionId, proposed.version);
      pushLocal("assistant", `Applied v${proposed.version} to “${sectionTitle}”.`);
      setProposed(null);
      onApplied?.();
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setBusy(null);
    }
  }

  async function discard() {
    if (!proposed || busy) return;
    setBusy("apply");
    setError(null);
    try {
      await discardSection(studyId, sectionId, proposed.version);
      pushLocal("assistant", `Discarded v${proposed.version}. Describe another change to try again.`);
      setProposed(null);
    } catch (cause) {
      setError(toMessage(cause));
    } finally {
      setBusy(null);
    }
  }

  const proposedProse = proposed?.blocks
    .filter((block) => block.kind === "prose")
    .map((block) => (block.kind === "prose" ? block.markdown : ""))
    .join("\n\n");

  return (
    <div className={open ? "chat-dock open" : "chat-dock"} data-testid="chat-dock">
      <div className="chat-header">
        <button
          type="button"
          className="chat-title-button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
        >
          <span className="chat-glyph" aria-hidden="true">
            💬
          </span>
          <span className="chat-title">
            Assistant
            <strong>{sectionTitle}</strong>
          </span>
          <span className="chat-chevron" aria-hidden="true">
            {open ? "⌄" : "⌃"}
          </span>
        </button>
      </div>

      {open && (
        <div className="chat-body">
          <div className="chat-messages" ref={listRef}>
            {messages.length === 0 && !proposed && (
              <p className="chat-empty">
                <strong>Ask</strong> a question about the study or this section, or describe a change
                and click <strong>Revise</strong> to rewrite it — you approve with 👍 / 👎.
              </p>
            )}
            {messages.map((message) => (
              <div key={message.message_id} className={`chat-msg ${message.role}`}>
                <div className="chat-bubble">
                  {message.role === "assistant" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                  ) : (
                    message.content
                  )}
                </div>
              </div>
            ))}
            {busy && busy !== "apply" && (
              <div className="chat-msg assistant">
                <div className="chat-bubble typing">{busy === "revise" ? "Rewriting…" : "Thinking…"}</div>
              </div>
            )}
            {proposed && (
              <div className="proposed-card" data-testid="proposed-card">
                <div className="proposed-head">
                  <strong>Proposed rewrite · v{proposed.version}</strong>
                  <span>{sectionTitle}</span>
                </div>
                <div className="proposed-body draft-prose">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {proposedProse || "(no narrative change)"}
                  </ReactMarkdown>
                </div>
                <div className="proposed-actions">
                  <button
                    className="button small thumbs-up"
                    type="button"
                    onClick={() => void apply()}
                    disabled={busy !== null}
                    data-testid="apply-proposed"
                  >
                    👍 Apply
                  </button>
                  <button
                    className="button small thumbs-down"
                    type="button"
                    onClick={() => void discard()}
                    disabled={busy !== null}
                    data-testid="discard-proposed"
                  >
                    👎 Discard
                  </button>
                </div>
              </div>
            )}
          </div>
          {error && <div className="chat-error">{error}</div>}
        </div>
      )}

      <form
        className="chat-input-row"
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <input
          className="chat-input"
          value={input}
          placeholder={`Ask about the study, or describe a change to “${sectionTitle}”…`}
          onChange={(event) => setInput(event.target.value)}
          onFocus={() => setOpen(true)}
          data-testid="chat-input"
        />
        <button className="button secondary small" type="submit" disabled={busy !== null || !input.trim()}>
          {busy === "ask" ? "…" : "Ask"}
        </button>
        <button
          className="button primary small"
          type="button"
          onClick={() => void revise()}
          disabled={busy !== null || !input.trim()}
          title="Rewrite this section with your feedback"
        >
          {busy === "revise" ? "…" : "Revise"}
        </button>
      </form>
    </div>
  );
}

function toMessage(cause: unknown): string {
  if (cause instanceof ApiError || cause instanceof Error) {
    return cause.message;
  }
  return "Request failed.";
}
