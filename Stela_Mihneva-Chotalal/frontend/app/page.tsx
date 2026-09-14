import { ChatInterface } from '@/components/chat-interface'

export default function Page() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center bg-[#7c3aed] sm:bg-gradient-to-br sm:from-[#7c3aed] sm:via-[#db2777] sm:to-[#2563eb] sm:p-4">
      <ChatInterface />
    </main>
  )
}
