"use client";

import { useState, useRef, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STARTERS = [
  "We want to build an AI that reads legal contracts and flags risky clauses for our procurement team.",
  "Our client wants a chatbot to handle 80% of tier-1 IT helpdesk tickets automatically.",
  "We're thinking of fine-tuning a model on our company's historical project data to predict delivery risks.",
  "Can we use AI to auto-generate quarterly board reports from raw financial data?",
];

type Message = { role: "user" | "assistant"; content: string };

function formatResponse(text: string) {
  // Split on section headers (lines starting with emoji or **)
  const lines = text.split("\n");
  return lines.map((line, i) => {
    // Section headers: lines starting with emoji
    if (/^[🎯📊⚠️💼⚡]/.test(line)) {
      return (
        <div key={i} style={{ marginTop: i === 0 ? 0 : "1.2rem", marginBottom: "0.3rem" }}>
          <span style={{ color: "#A100FF", fontWeight: 700, fontSize: "0.85rem", letterSpacing: "0.05em" }}>
            {line}
          </span>
        </div>
      );
    }
    // Numbered risk lines
    if (/^[1-3]\. /.test(line)) {
      return (
        <div key={i} style={{ marginBottom: "0.4rem", paddingLeft: "0.5rem", borderLeft: "2px solid #2a2a3a" }}>
          {line}
        </div>
      );
    }
    // Blank lines
    if (line.trim() === "") return <div key={i} style={{ height: "0.3rem" }} />;
    // Regular lines
    return <div key={i}>{line}</div>;
  });
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(text?: string) {
    const userMessage = (text ?? input).trim();
    if (!userMessage || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Could not reach the backend. Make sure VPN is connected and uvicorn is running." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--bg)" }}>
      {/* Header */}
      <header style={{
        padding: "1rem 1.5rem",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        display: "flex",
        alignItems: "center",
        gap: "1rem",
        flexShrink: 0,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: "linear-gradient(135deg, #A100FF, #6600cc)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.1rem",
        }}>🧭</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text)" }}>AI Project Co-Pilot</div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            Powered by GPT-5.5 · Accenture LLM COE
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <span style={{
            fontSize: "0.7rem", padding: "0.2rem 0.6rem",
            borderRadius: 20, border: "1px solid #A100FF",
            color: "#A100FF", fontWeight: 600,
          }}>LIVE</span>
        </div>
      </header>

      {/* Chat area */}
      <main style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
        {messages.length === 0 && (
          <div style={{ maxWidth: 680, margin: "2rem auto", textAlign: "center" }}>
            <div style={{ fontSize: "2rem", marginBottom: "0.75rem" }}>🧭</div>
            <h2 style={{ fontSize: "1.4rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Should we build this AI?
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "2rem", lineHeight: 1.6 }}>
              Describe your AI project idea or business problem. Get an instant analysis:
              approach, feasibility, risks, exec pitch, and a 2-week prototype plan.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", textAlign: "left" }}>
              {STARTERS.map((s, i) => (
                <button key={i} onClick={() => sendMessage(s)} style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  padding: "0.85rem 1rem",
                  color: "var(--text-muted)",
                  fontSize: "0.8rem",
                  lineHeight: 1.5,
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "border-color 0.15s, color 0.15s",
                }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "#A100FF";
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
                    (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
                  }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {messages.map((m, i) => (
            <div key={i} style={{
              display: "flex",
              flexDirection: m.role === "user" ? "row-reverse" : "row",
              gap: "0.75rem",
              alignItems: "flex-start",
            }}>
              {/* Avatar */}
              <div style={{
                width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                background: m.role === "user"
                  ? "linear-gradient(135deg, #A100FF, #6600cc)"
                  : "var(--surface-2)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "0.85rem", border: "1px solid var(--border)",
              }}>
                {m.role === "user" ? "G" : "🧭"}
              </div>

              {/* Bubble */}
              <div style={{
                maxWidth: "80%",
                background: m.role === "user" ? "linear-gradient(135deg, #A100FF22, #6600cc22)" : "var(--surface)",
                border: `1px solid ${m.role === "user" ? "#A100FF44" : "var(--border)"}`,
                borderRadius: m.role === "user" ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                padding: "0.85rem 1.1rem",
                fontSize: "0.875rem",
                lineHeight: 1.65,
                color: "var(--text)",
              }}>
                {m.role === "assistant" ? formatResponse(m.content) : m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
              <div style={{
                width: 32, height: 32, borderRadius: 8,
                background: "var(--surface-2)", border: "1px solid var(--border)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.85rem",
              }}>🧭</div>
              <div style={{
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: "4px 16px 16px 16px", padding: "0.85rem 1.1rem",
              }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {[0, 1, 2].map(d => (
                    <div key={d} style={{
                      width: 6, height: 6, borderRadius: "50%", background: "#A100FF",
                      animation: `pulse 1.2s ease-in-out ${d * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
                <style>{`@keyframes pulse { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }`}</style>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {/* Input */}
      <footer style={{
        padding: "1rem 1.5rem",
        borderTop: "1px solid var(--border)",
        background: "var(--surface)",
        flexShrink: 0,
      }}>
        <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", gap: "0.75rem" }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Describe your AI project idea… (Enter to send, Shift+Enter for new line)"
            rows={2}
            style={{
              flex: 1,
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "0.75rem 1rem",
              color: "var(--text)",
              fontSize: "0.875rem",
              resize: "none",
              outline: "none",
              lineHeight: 1.5,
              fontFamily: "inherit",
              transition: "border-color 0.15s",
            }}
            onFocus={e => (e.target.style.borderColor = "#A100FF")}
            onBlur={e => (e.target.style.borderColor = "var(--border)")}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || loading}
            style={{
              padding: "0 1.25rem",
              borderRadius: 10,
              border: "none",
              background: input.trim() && !loading
                ? "linear-gradient(135deg, #A100FF, #6600cc)"
                : "var(--surface-2)",
              color: input.trim() && !loading ? "#fff" : "var(--text-muted)",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: input.trim() && !loading ? "pointer" : "default",
              transition: "all 0.15s",
              flexShrink: 0,
            }}>
            {loading ? "..." : "Analyze →"}
          </button>
        </div>
        <p style={{ textAlign: "center", fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
          VPN must be connected · IDE Challenge — Titanium Engineer Cohort 4
        </p>
      </footer>
    </div>
  );
}
