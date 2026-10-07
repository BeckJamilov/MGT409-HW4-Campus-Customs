import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { fetchCurrentUser, login as loginRequest, TOKEN_KEY, type User } from './api'

interface AuthContextValue {
  user: User | null
  login: (email: string, password: string) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  // Restore the session after a page refresh if a saved token is still valid.
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return
    fetchCurrentUser(token)
      .then((u) => (u ? setUser(u) : localStorage.removeItem(TOKEN_KEY)))
      .catch(() => {})
  }, [])

  const login = async (email: string, password: string) => {
    const { user: loggedIn, token } = await loginRequest(email, password)
    localStorage.setItem(TOKEN_KEY, token)
    setUser(loggedIn)
    return loggedIn
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
