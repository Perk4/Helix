import { ChatInterface } from "@/components/chat-interface"
import { PriceTicker } from "@/components/price-ticker"

export default function Page() {
  return (
    <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background p-0 sm:p-6">
      {/* Ambient gold/blue glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-accent/20 blur-3xl"
      />

      <div className="relative z-10 flex h-svh w-full flex-col overflow-hidden border-primary/15 bg-card/40 backdrop-blur sm:h-[85vh] sm:max-w-3xl sm:rounded-2xl sm:border sm:shadow-2xl">
        <PriceTicker />
        <ChatInterface />
      </div>
    </main>
  )
}
