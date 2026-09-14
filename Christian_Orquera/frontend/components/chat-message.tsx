import { cn } from "@/lib/utils"
import { Bitcoin, User } from "lucide-react"

export type ChatRole = "user" | "assistant"

export interface Message {
  id: string
  role: ChatRole
  content: string
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div className={cn("flex w-full gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "border-accent/40 bg-accent/30 text-foreground"
            : "border-primary/40 bg-primary/15 text-primary",
        )}
        aria-hidden="true"
      >
        {isUser ? <User className="h-4 w-4" /> : <Bitcoin className="h-4 w-4" />}
      </div>

      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser
            ? "rounded-tr-sm bg-accent/40 text-foreground"
            : "rounded-tl-sm border border-primary/20 bg-card text-card-foreground",
        )}
      >
        <p className="whitespace-pre-wrap text-pretty">{message.content}</p>
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div className="flex w-full flex-row gap-3">
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-primary/40 bg-primary/15 text-primary"
        aria-hidden="true"
      >
        <Bitcoin className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-primary/20 bg-card px-4 py-4">
        <span className="sr-only">CryptoSage is thinking</span>
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary" />
      </div>
    </div>
  )
}
