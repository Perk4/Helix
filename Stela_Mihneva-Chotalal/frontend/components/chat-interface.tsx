'use client'

import { useEffect, useRef, useState } from 'react'
import { ChatMessage, type Message } from './chat-message'
import { ChatInput } from './chat-input'
import { TypingIndicator } from './typing-indicator'
import { CoinMascot } from './coin-mascot'

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hi there, superstar! I'm Coach Coin, your crypto buddy. Ask me anything about coins, money, or crypto and I'll explain it in a super easy way!",
}

const SUGGESTIONS = [
  'What is Bitcoin?',
  'Why do coins go up and down?',
  'What is a wallet?',
]

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [isLoading, setIsLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, isLoading])

  async function sendMessage(text: string) {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })

      if (!res.ok) throw new Error(`Request failed: ${res.status}`)

      const data = await res.json()
      const reply =
        data.response ?? data.message ?? data.reply ?? JSON.stringify(data)

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: String(reply) },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content:
            "Oopsie! My piggy bank got stuck and I couldn't reach my brain. Please try asking me again in a moment!",
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const showSuggestions = messages.length === 1 && !isLoading

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden bg-[#2e1065] sm:h-[92vh] sm:max-h-[820px] sm:w-full sm:max-w-2xl sm:rounded-[2rem] sm:border-4 sm:border-[#ffd700] sm:shadow-2xl">
      {/* Header */}
      <header className="flex items-center gap-3 border-b-4 border-[#ffd700] bg-gradient-to-r from-[#7c3aed] via-[#db2777] to-[#2563eb] px-4 py-3 sm:px-5 sm:py-4">
        <div className="animate-float-bob rounded-full border-2 border-[#e6a700] bg-white p-1 shadow-lg">
          <CoinMascot size={44} />
        </div>
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold leading-tight text-[#ffd700] sm:text-3xl">
            Coach Coin
          </h1>
          <p className="font-sans text-sm text-[#ffe4f0] sm:text-base">
            Crypto Analyst for 1st Graders!
          </p>
        </div>
        <span className="ml-auto hidden rounded-full border-2 border-[#ffd700]/40 bg-[#ffd700]/10 px-3 py-1 font-display text-sm font-semibold text-[#ffd700] sm:inline-block">
          Super Smart
        </span>
      </header>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto bg-[radial-gradient(circle_at_15%_15%,#6d28d9_0%,#2e1065_45%,#1e1b4b_100%)] p-4 sm:p-5"
      >
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isLoading && <TypingIndicator />}

        {showSuggestions && (
          <div className="flex flex-wrap gap-2 pt-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="rounded-full border-2 border-[#f472b6] bg-[#4c1d95] px-4 py-2 font-sans text-base font-medium text-[#fbcfe8] shadow-md transition-all hover:border-[#ffd700] hover:text-[#ffd700] active:translate-y-0.5"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </div>
  )
}
