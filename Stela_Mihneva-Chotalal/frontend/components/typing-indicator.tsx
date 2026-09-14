import { CoinMascot } from './coin-mascot'

export function TypingIndicator() {
  return (
    <div className="flex animate-pop-in items-end gap-2">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-full border-2 border-[#e6a700] bg-white shadow-md">
        <CoinMascot size={30} className="animate-wiggle" />
      </div>
      <div className="flex items-center gap-1.5 rounded-3xl rounded-bl-md border-2 border-[#e6a700] bg-[#fffbe6] px-5 py-4 shadow-lg">
        <span className="sr-only">Coach Coin is thinking</span>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-3 rounded-full bg-[#e6a700]"
            style={{
              animation: 'bounce-dot 1.2s ease-in-out infinite',
              animationDelay: `${i * 0.18}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}
