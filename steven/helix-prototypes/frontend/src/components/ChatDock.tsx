"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ApiError, getChat, sendChat } from "@/lib/api";
import type { ChatMessage, ChatScope } from "@/lib/types";

type Props = {
  studyId: string;
  sectionId: string;
  sectionTitle: string;
};

export function ChatDock({ studyId, sectionId, sectionTitle }: Props) {
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState<ChatScope>("section");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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
  }, [messages, open]);

  async function send() {
    const text = input.trim();
    if (!text || busy) {
      return;
    }
    setBusy(true);
    setError(null);
    setOpen(true);
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
    setInput("");
    try {
      await sendChat(studyId, text, scope, scope === "section" ? sectionId : null);
      setMessages(await getChat(studyId));
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error ? cause.message : "Chat failed.");
    } finally {
      setBusy(false);
    }
  }

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
            Ask or revise
            <strong>{scope === "section" ? sectionTitle : "the whole study"}</strong>
          </span>
          <span className="chat-chevron" aria-hidden="true">
            {open ? "⌄" : "⌃"}
          </span>
        </button>
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
      </div>

      {open && (
        <div className="chat-body">
          <div className="chat-messages" ref={listRef}>
            {messages.length === 0 && (
              <p className="chat-empty">
                Ask about this section, the whole study, or a general question (e.g. “what does
                Grade 2 severity mean?”). Answers use only verified study data.
              </p>
            )}
            {messages.map((message) => (
              <div key={message.message_id} className={`chat-msg ${message.role}`}>
                {message.role === "assistant" ? (
                  <div className="chat-bubble">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="chat-bubble">{message.content}</div>
                )}
                {message.section_id && message.scope === "section" && (
                  <span className="chat-scope-tag">{message.section_id}</span>
                )}
              </div>
            ))}
            {busy && <div className="chat-msg assistant"><div className="chat-bubble typing">Thinking…</div></div>}
          </div>
          {error && <div className="chat-error">{error}</div>}
        </div>
      )}

      <form
        className="chat-input-row"
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <input
          className="chat-input"
          value={input}
          placeholder={`Ask about “${scope === "section" ? sectionTitle : "the study"}”…`}
          onChange={(event) => setInput(event.target.value)}
          onFocus={() => setOpen(true)}
          data-testid="chat-input"
        />
        <button className="button primary small" type="submit" disabled={busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
