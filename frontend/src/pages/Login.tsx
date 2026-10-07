import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import AuthAside from '../components/AuthAside'

interface LoginState {
  email?: string
  justSignedUp?: boolean
  loggedOut?: boolean
}

export default function Login() {
  const { user, login } = useAuth()
  const state = (useLocation().state ?? {}) as LoginState
  const [email, setEmail] = useState(state.email ?? '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      setPassword('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed.')
    } finally {
      setSubmitting(false)
    }
  }

  if (user) {
    return (
      <section className="auth-page page">
        <div className="auth-shell">
          <AuthAside />
          <div className="auth-card">
            <div className="alert success" role="status">
              <strong>Login successful.</strong> Welcome back, {user.first_name || user.name}!
            </div>
            <p className="muted">You are logged in as {user.email}.</p>
            <Link to="/products" className="button primary">Continue shopping</Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="auth-page page">
      <div className="auth-shell">
        <AuthAside />
        <div className="auth-card">
          <h1>Log in</h1>
          <p className="muted">Welcome back, Bulldog.</p>
          {state.justSignedUp && !error && (
            <div className="alert success" role="status">Account created! Log in with your new password.</div>
          )}
          {state.loggedOut && !error && <div className="alert info" role="status">You have been logged out.</div>}
          {error && <div className="alert error" role="alert"><strong>Login failed.</strong> {error}</div>}
          <form onSubmit={handleSubmit}>
            <label>
              Email
              <input type="email" required placeholder="you@yale.edu" autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label>
              Password
              <input type="password" required autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <button type="submit" className="button primary" disabled={submitting}>
              {submitting ? 'Logging in…' : 'Log in'}
            </button>
          </form>
          <p className="muted small">
            New here? <Link to="/create-account">Create an account</Link>
          </p>
        </div>
      </div>
    </section>
  )
}
