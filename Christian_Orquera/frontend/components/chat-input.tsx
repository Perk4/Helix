"use client"

import type React from "react"
import { useRef, useState } from "react"
import { ArrowUp } from "lucide-react"
import { cn } from "@/lib/utils"

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void
  disabled?: boolean
}) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
    requestAnimationFrame(() => {
      if (textareaRef.current) textareaRef.current.style.height = "auto"
    })
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Respect IME composition (CJK) and Safari's unreliable final event.
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value)
    const el = e.target
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
      className="flex items-end gap-2 rounded-2xl border border-primary/25 bg-card/80 p-2 shadow-lg backdrop-blur focus-within:border-primary/60 focus-within:ring-1 focus-within:ring-primary/40"
    >
      <label htmlFor="chat-message" className="sr-only">
        Ask about cryptocurrency
      </label>
      <textarea
        id="chat-message"
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Ask about Bitcoin, market trends, portfolio strategy…"
        className="max-h-40 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground transition",
          "hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40",
        )}
      >
        <ArrowUp className="h-5 w-5" />
      </button>
    </form>
  )
}
