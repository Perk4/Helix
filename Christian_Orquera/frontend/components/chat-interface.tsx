"use client"

import { useEffect, useRef, useState } from "react"
import { Bitcoin, TrendingUp } from "lucide-react"
import { ChatInput } from "@/components/chat-input"
import { ChatMessage, TypingIndicator, type Message } from "@/components/chat-message"

const SUGGESTIONS = [
  "What's driving Bitcoin's price today?",
  "Explain dollar-cost averaging",
  "Is now a good time to rebalance?",
  "Compare Ethereum vs Solana",
]

function createId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, isLoading])

  async function sendMessage(text: string) {
    const userMessage: Message = { id: createId(), role: "user", content: text }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)

      const data = await res.json()
      const reply =
        typeof data === "string"
          ? data
          : (data.response ?? data.message ?? data.reply ?? JSON.stringify(data))

      setMessages((prev) => [...prev, { id: createId(), role: "assistant", content: reply }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: "assistant",
          content:
            "I couldn't reach the analysis service right now. Please check your connection and try again.",
        },
      ])
      console.log("[v0] Chat request error:", err instanceof Error ? err.message : err)
    } finally {
      setIsLoading(false)
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-primary/15 px-4 py-4 sm:px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/30">
          <Bitcoin className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-base font-semibold text-foreground">
            CryptoSage
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
              <TrendingUp className="h-3 w-3" /> Live Analyst
            </span>
          </h1>
          <p className="truncate text-xs text-muted-foreground">AI cryptocurrency market analyst</p>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
        {isEmpty ? (
          <div className="mx-auto flex max-w-md flex-col items-center gap-6 pt-8 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/15 text-primary ring-1 ring-primary/30">
              <Bitcoin className="h-8 w-8" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-lg font-semibold text-foreground text-balance">
                Your AI cryptocurrency analyst
              </h2>
              <p className="text-sm text-muted-foreground text-pretty">
                Ask about prices, market trends, tokenomics, or trading strategy. CryptoSage breaks it
                down in plain language.
              </p>
            </div>
            <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => sendMessage(s)}
                  className="rounded-xl border border-primary/20 bg-card/60 px-3 py-2.5 text-left text-sm text-foreground/90 transition hover:border-primary/50 hover:bg-card"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            {messages.map((m) => (
              <ChatMessage key={m.id} message={m} />
            ))}
            {isLoading && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-primary/15 px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-2xl">
          <ChatInput onSend={sendMessage} disabled={isLoading} />
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            CryptoSage can make mistakes. Not financial advice — always do your own research.
          </p>
        </div>
      </div>
    </div>
  )
}
