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
import type { ChatMessage, ChatScope, SectionDraft } from "@/lib/types";

type Props = {
  studyId: string;
  sectionId: string;
  sectionTitle: string;
  onApplied?: () => void;
};

type Mode = "ask" | "revise";

export function ChatDock({ studyId, sectionId, sectionTitle, onApplied }: Props) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<Mode>("ask");
  const [scope, setScope] = useState<ChatScope>("section");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [proposed, setProposed] = useState<SectionDraft | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
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

  async function submit() {
    const text = input.trim();
    if (!text || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setOpen(true);
    setInput("");
    try {
      if (mode === "revise") {
        pushLocal("user", `Revise: ${text}`);
        const draft = await reviseSection(studyId, sectionId, text);
        setProposed(draft);
        pushLocal("assistant", `Proposed v${draft.version} — review and apply or discard below.`);
      } else {
        const optimistic: ChatMessage = {
          message_id: -Date.now(),
          role: "user",
          content: text,
          scope,
          section_id: scope === "section" ? sectionId : null,
          intent: "ask",
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, optimistic]);
        await sendChat(studyId, text, scope, scope === "section" ? sectionId : null);
        setMessages(await getChat(studyId));
      }
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error ? cause.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  }

  async function apply() {
    if (!proposed || busy) return;
    setBusy(true);
    setError(null);
    try {
      await applySection(studyId, sectionId, proposed.version);
      pushLocal("assistant", `Applied v${proposed.version} to “${sectionTitle}”.`);
      setProposed(null);
      onApplied?.();
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error ? cause.message : "Apply failed.");
    } finally {
      setBusy(false);
    }
  }

  async function discard() {
    if (!proposed || busy) return;
    setBusy(true);
    setError(null);
    try {
      await discardSection(studyId, sectionId, proposed.version);
      pushLocal("assistant", `Discarded v${proposed.version}. Give more feedback to try again.`);
      setProposed(null);
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error ? cause.message : "Discard failed.");
    } finally {
      setBusy(false);
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
            {mode === "revise" ? "Revise" : "Ask about"}
            <strong>{mode === "revise" || scope === "section" ? sectionTitle : "the whole study"}</strong>
          </span>
          <span className="chat-chevron" aria-hidden="true">
            {open ? "⌄" : "⌃"}
          </span>
        </button>
        <div className="chat-controls">
          <div className="chat-scope" role="radiogroup" aria-label="Chat mode">
            <button
              type="button"
              role="radio"
              aria-checked={mode === "ask"}
              className={mode === "ask" ? "chat-scope-option active" : "chat-scope-option"}
              onClick={() => setMode("ask")}
            >
              Ask
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={mode === "revise"}
              className={mode === "revise" ? "chat-scope-option active" : "chat-scope-option"}
              onClick={() => setMode("revise")}
            >
              Revise
            </button>
          </div>
          {mode === "ask" && (
            <div className="chat-scope" role="radiogroup" aria-label="Chat scope">
              <button
                type="button"
                role="radio"
                aria-checked={scope === "section"}
                className={scope === "section" ? "chat-scope-option active" : "chat-scope-option"}
                onClick={() => setScope("section")}
              >
                This section
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={scope === "study"}
                className={scope === "study" ? "chat-scope-option active" : "chat-scope-option"}
                onClick={() => setScope("study")}
              >
                Whole study
              </button>
            </div>
          )}
        </div>
      </div>

      {open && (
        <div className="chat-body">
          <div className="chat-messages" ref={listRef}>
            {messages.length === 0 && !proposed && (
              <p className="chat-empty">
                <strong>Ask</strong> a question (grounded in verified data), or switch to{" "}
                <strong>Revise</strong> to rewrite “{sectionTitle}” with your feedback.
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
            {busy && (
              <div className="chat-msg assistant">
                <div className="chat-bubble typing">{mode === "revise" ? "Rewriting…" : "Thinking…"}</div>
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
                  <button className="button primary small" type="button" onClick={() => void apply()} disabled={busy}>
                    👍 Apply
                  </button>
                  <button className="button secondary small" type="button" onClick={() => void discard()} disabled={busy}>
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
          void submit();
        }}
      >
        <input
          className="chat-input"
          value={input}
          placeholder={
            mode === "revise"
              ? `Describe the change to “${sectionTitle}”…`
              : `Ask about “${scope === "section" ? sectionTitle : "the study"}”…`
          }
          onChange={(event) => setInput(event.target.value)}
          onFocus={() => setOpen(true)}
          data-testid="chat-input"
        />
        <button className="button primary small" type="submit" disabled={busy || !input.trim()}>
          {busy ? "…" : mode === "revise" ? "Rewrite" : "Send"}
        </button>
      </form>
    </div>
  );
}
