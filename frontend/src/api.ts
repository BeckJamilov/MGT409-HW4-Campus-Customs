export interface StockLevel {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock: number
  category: string
  sizes_in_stock?: string[] // only in the /api/products list
  inventory?: StockLevel[]
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(response.status === 404 ? 'Not found' : `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export interface User {
  id: number
  first_name: string | null
  last_name: string | null
  name: string
  email: string
}

export const TOKEN_KEY = 'campus_customs_token'

// Sends JSON and turns FastAPI error responses ({"detail": "..."}) into readable messages.
async function sendJson<T>(url: string, body: unknown): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error('Could not reach the server. Is the backend running?')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`
    throw new Error(detail)
  }
  return data as T
}

export interface SignupData {
  first_name: string
  last_name: string
  email: string
  password: string
}

export const signup = (data: SignupData) => sendJson<{ user: User }>('/api/auth/signup', data)

export const login = (email: string, password: string) =>
  sendJson<{ user: User; token: string }>('/api/auth/login', { email, password })

// Matches backend ProductCard; used by both the Products page and chat search results.
export interface ChatProductCard {
  product_id: string
  name: string
  price: number
  image_url: string
  garment_type: string | null
  short_description: string | null
}

export interface ChatResponse {
  reply: string
  products: ChatProductCard[]
}

// The page the customer is on when chatting; product_id comes from the /products/:id URL.
export interface PageContext {
  path: string
  product_id: string | null
}

// Guests only: earlier messages of the current chat, so follow-ups make sense (never saved).
export interface GuestHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export const sendChat = (message: string, pageContext: PageContext, guestHistory: GuestHistoryMessage[] = []) =>
  sendJson<ChatResponse>('/api/chat', { message, page_context: pageContext, guest_history: guestHistory })

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

export async function fetchChatHistory(): Promise<ChatHistoryMessage[]> {
  const token = localStorage.getItem(TOKEN_KEY)
  if (!token) return []
  const response = await fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) return []
  return ((await response.json()) as { messages: ChatHistoryMessage[] }).messages
}

export async function fetchCurrentUser(token: string): Promise<User | null> {
  const response = await fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
  if (!response.ok) return null
  return ((await response.json()) as { user: User }).user
}

export const formatPrice =(price: number) => `$${price.toFixed(2)}`

// Three catalogue rows hold an auto-generated stub instead of a real description.
export const displayDescription = (product: Product) =>
  product.description.startsWith('Campus Customs product photo')
    ? `${product.name} from the Campus Customs Yale collection.`
    : product.description

export const shortDescription = (product: Product, maxLength = 110) => {
  const text = displayDescription(product)
  return text.length > maxLength ? `${text.slice(0, maxLength).trimEnd()}…` : text
}

export const toCard = (product: Product): ChatProductCard => ({
  product_id: product.product_id,
  name: product.name,
  price: product.price,
  image_url: product.image_url,
  garment_type: product.garment_type,
  short_description: shortDescription(product),
})
