import { useEffect, useRef, useState, type FormEvent } from 'react'
import { matchPath, useLocation, useNavigate } from 'react-router-dom'
import { fetchChatHistory, sendChat, type GuestHistoryMessage } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'

interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  text: string
  productCount?: number
  productIds?: string[] // structured product_ids from the API response (used for guest context)
}

const GUEST_HISTORY_LIMIT = 12
const GENERAL_SUGGESTIONS = ['Show me hoodies', 'Gift ideas under $50', 'Cheapest fleece']

// Tell the agent which products an earlier reply showed (ids from the API, not parsed text).
const withProductNote = (m: ChatMessage) =>
  m.productIds && m.productIds.length > 0
    ? `${m.text}\n[Products shown on the page: ${m.productIds.slice(0, 15).join(', ')}]`
    : m.text

const greeting = (firstName?: string | null): ChatMessage => ({
  role: 'assistant',
  text: `Hi${firstName ? ` ${firstName}` : ''}! I am the Campus Customs assistant. How can I help you find Yale gear today?`,
})

export default function ChatWidget() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()
  const { setResults } = useChatResults()
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([greeting()])
  const endRef = useRef<HTMLDivElement>(null)

  // Real page context: the product_id comes straight from the current /products/:productId URL.
  const currentProductId = matchPath('/products/:productId', location.pathname)?.params.productId ?? null
  // Quick suggestions; on a product page, offer a stock check for that product.
  const suggestions = currentProductId
    ? ['Is this in stock in M?', ...GENERAL_SUGGESTIONS.slice(0, 2)]
    : GENERAL_SUGGESTIONS

  // Logged-in customers get their saved conversation back; guests (or after logout) start fresh.
  const userId = user?.id
  const firstName = user?.first_name
  useEffect(() => {
    let cancelled = false
    if (!userId) {
      setMessages([greeting()])
      return
    }
    fetchChatHistory().then((history) => {
      if (cancelled) return
      const saved: ChatMessage[] = history.map((m) => ({
        role: m.role,
        text: m.content,
        productCount: m.products.length,
      }))
      setMessages(saved.length > 0 ? saved : [greeting(firstName)])
    })
    return () => {
      cancelled = true
    }
  }, [userId, firstName])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending, open])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await sendMessage(input)
  }

  const sendMessage = async (rawText: string) => {
    const text = rawText.trim()
    if (!text || sending) return
    // Guests: send the current chat (kept only in this tab) so follow-ups make sense.
    // Logged-in customers don't need this; the backend loads their saved history.
    const guestHistory: GuestHistoryMessage[] = user
      ? []
      : messages
          .filter((m): m is ChatMessage & { role: 'user' | 'assistant' } => m.role !== 'error')
          .slice(-GUEST_HISTORY_LIMIT)
          .map((m) => ({ role: m.role, content: withProductNote(m).slice(0, 2000) }))
    setMessages((prev) => [...prev, { role: 'user', text }])
    setInput('')
    setSending(true)
    try {
      const { reply, products } = await sendChat(
        text,
        { path: location.pathname, product_id: currentProductId },
        guestHistory,
      )
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: reply, productCount: products.length, productIds: products.map((p) => p.product_id) },
      ])
      // Structured matches from the backend update the page as product cards
      // (unless the only match is the product already on screen).
      const onlyCurrentProduct = products.length === 1 && products[0].product_id === currentProductId
      if (products.length > 0 && !onlyCurrentProduct) {
        setResults({ query: text, products })
        navigate('/products')
      }
    } catch (e) {
      const detail = e instanceof Error ? e.message : 'Something went wrong.'
      setMessages((prev) => [...prev, { role: 'error', text: detail }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <div className="chat-header">
            <span className="chat-avatar" aria-hidden="true">CC</span>
            <div className="chat-title">
              <strong>Campus Customs Assistant</strong>
              <div className="chat-status">
                {user ? 'Your chat is saved to your account' : 'Guest chat · not saved'} · AI may make mistakes
              </div>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </div>
          <div className="chat-messages" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`chat-bubble ${m.role}`}>
                {m.text}
                {!!m.productCount && (
                  <div className="chat-products-note">
                    🛍️ Showing {m.productCount} {m.productCount === 1 ? 'product' : 'products'} on the page
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-bubble assistant typing" aria-label="Assistant is typing">
                <span className="dot" /><span className="dot" /><span className="dot" />
              </div>
            )}
            <div ref={endRef} />
          </div>
          <div className="chat-suggestions" aria-label="Suggested questions">
            {suggestions.map((s) => (
              <button key={s} type="button" onClick={() => sendMessage(s)} disabled={sending}>
                {s}
              </button>
            ))}
          </div>
          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about Yale gear…"
              aria-label="Chat message"
              maxLength={2000}
            />
            <button type="submit" disabled={sending || !input.trim()} aria-label="Send message">Send ➤</button>
          </form>
        </section>
      )}
      <button
        className={`chat-toggle ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat with our shopping assistant'}
      >
        {open ? (
          <span className="chat-toggle-icon" aria-hidden="true">✕</span>
        ) : (
          <>
            <span className="chat-toggle-icon" aria-hidden="true">💬</span>
            <span className="chat-toggle-label">Ask our assistant</span>
          </>
        )}
      </button>
    </div>
  )
}
