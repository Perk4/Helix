"use client";

import { useEffect, useRef, useState } from "react";

type Message = { role: "user" | "bot"; content: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const QUICK_PROMPTS = [
  "I feel stressed about a deadline.",
  "A 60-second breathing exercise",
  "Help me reframe a rough day",
  "One small step to get unstuck",
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function ask(text: string) {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      setOnline(res.ok);
      const reply =
        data.response ?? data.error ?? "Sorry, something went wrong.";
      setMessages((m) => [...m, { role: "bot", content: reply }]);
    } catch {
      setOnline(false);
      setMessages((m) => [
        ...m,
        { role: "bot", content: "Could not reach the Mindful Coach service." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const started = messages.length > 0;

  return (
    <div className="page">
      {/* Top nav */}
      <nav className="top-nav">
        <div className="wordmark">
          <span className="dot" aria-hidden />
          Mindful Coach
        </div>
        <div className="nav-links">
          <span>Calm</span>
          <span>Focus</span>
          <span>Sleep</span>
        </div>
        <span className="status">
          <span className={`led ${online === false ? "off" : ""}`} />
          {online === false ? "Offline" : "Online"}
        </span>
        <button
          className="btn btn-secondary"
          onClick={() => {
            setMessages([]);
            setInput("");
          }}
        >
          New session
        </button>
      </nav>

      {/* Hero */}
      <header className="hero">
        <p className="eyebrow">AI wellness companion</p>
        <h1 className="display">
          Breathe.
          <br />
          Focus.
          <br />
          Reset.
        </h1>
        <p className="subhead">
          A calmer next step, one message at a time — powered by GPT-5.5.
        </p>
      </header>

      {/* Chat shell */}
      <main className="chat-shell">
        <div className="chat-head">
          <p className="eyebrow">Session</p>
          <span className="status">
            <span className={`led ${online === false ? "off" : ""}`} />
            {online === false ? "Reconnecting" : "Coach ready"}
          </span>
        </div>

        <div className="messages">
          {!started && (
            <div className="spotlight">
              <h2>How are you feeling today?</h2>
              <p>
                Ask for a breathing exercise, a way to reframe a stressful day,
                or a small step to get unstuck.
              </p>
              <div className="chips">
                {QUICK_PROMPTS.map((p, i) => (
                  <button
                    key={i}
                    className="chip"
                    onClick={() => ask(p)}
                    disabled={loading}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`row ${m.role}`}>
              <div className="bubble">
                <span className="speaker">
                  {m.role === "user" ? "You" : "Coach"}
                </span>
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="row bot">
              <div className="bubble typing">Mindful Coach is thinking…</div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="composer">
          <input
            className="text-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask(input)}
            placeholder="Type how you're feeling…"
            aria-label="Message"
          />
          <button
            className="btn btn-primary"
            onClick={() => ask(input)}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>

        {started && (
          <div className="quick-row">
            {QUICK_PROMPTS.map((p, i) => (
              <button
                key={i}
                className="chip"
                onClick={() => ask(p)}
                disabled={loading}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="wordmark">
          <span className="dot" aria-hidden />
          Mindful Coach
        </div>
        <span className="meta">
          Titanium AI Engineer · IDE Challenge · deployed by Annie Choi ·
          wellness support, not medical advice
        </span>
      </footer>
    </div>
  );
}
