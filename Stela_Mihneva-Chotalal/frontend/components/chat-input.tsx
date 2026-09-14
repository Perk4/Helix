'use client'

import { useState, type FormEvent, type KeyboardEvent } from 'react'

type ChatInputProps = {
  onSend: (message: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('')

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.nativeEvent.isComposing && e.keyCode !== 229) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-center gap-2 border-t-4 border-[#ffd700] bg-[#4c1d95] p-3 sm:gap-3 sm:p-4"
    >
      <label htmlFor="chat-input" className="sr-only">
        Ask Coach Coin a question
      </label>
      <input
        id="chat-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Ask me about coins and money!"
        autoComplete="off"
        className="min-w-0 flex-1 rounded-full border-2 border-[#4d7cff]/60 bg-white px-5 py-3 font-sans text-lg text-[#0a1a3f] shadow-inner outline-none transition placeholder:text-[#0a1a3f]/40 focus:border-[#ffd700] focus:ring-4 focus:ring-[#ffd700]/40 disabled:opacity-60 sm:text-xl"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="flex shrink-0 items-center gap-2 rounded-full border-2 border-[#e6a700] bg-[#ffd700] px-5 py-3 font-display text-lg font-bold text-[#0a1a3f] shadow-[0_4px_0_#b58600] transition-all hover:brightness-105 active:translate-y-1 active:shadow-[0_1px_0_#b58600] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-[0_4px_0_#b58600] sm:text-xl"
      >
        Send
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M3 11L21 3L13 21L11 13L3 11Z"
            stroke="#0a1a3f"
            strokeWidth="2.5"
            strokeLinejoin="round"
            fill="#0a1a3f"
          />
        </svg>
      </button>
    </form>
  )
}
