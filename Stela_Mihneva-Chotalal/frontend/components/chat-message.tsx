import { CoinMascot } from './coin-mascot'

export type ChatRole = 'user' | 'assistant'

export type Message = {
  id: string
  role: ChatRole
  content: string
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex animate-pop-in items-end gap-2 ${
        isUser ? 'flex-row-reverse' : 'flex-row'
      }`}
    >
      {isUser ? (
        <div
          aria-hidden="true"
          className="flex size-10 shrink-0 items-center justify-center rounded-full border-2 border-[#0a1a3f] bg-[#4d7cff] font-display text-lg font-bold text-white shadow-md"
        >
          You
        </div>
      ) : (
        <div className="flex size-10 shrink-0 items-center justify-center rounded-full border-2 border-[#e6a700] bg-white shadow-md">
          <CoinMascot size={30} />
        </div>
      )}

      <div
        className={`max-w-[78%] rounded-3xl border-2 px-4 py-3 text-lg leading-relaxed shadow-lg sm:text-xl ${
          isUser
            ? 'rounded-br-md border-[#3a63d6] bg-[#4d7cff] text-white'
            : 'rounded-bl-md border-[#e6a700] bg-[#fffbe6] text-[#0a1a3f]'
        }`}
      >
        {message.content}
      </div>
    </div>
  )
}
