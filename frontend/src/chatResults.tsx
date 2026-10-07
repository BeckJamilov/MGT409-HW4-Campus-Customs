import { createContext, useContext, useState, type ReactNode } from 'react'
import type { ChatProductCard } from './api'

// Product matches from the latest chat search, shown on the Products page.
export interface ChatResults {
  query: string
  products: ChatProductCard[]
}

interface ChatResultsContextValue {
  results: ChatResults | null
  setResults: (results: ChatResults | null) => void
}

const ChatResultsContext = createContext<ChatResultsContextValue | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)
  return <ChatResultsContext.Provider value={{ results, setResults }}>{children}</ChatResultsContext.Provider>
}

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
