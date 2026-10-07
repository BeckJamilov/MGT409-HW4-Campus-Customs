import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { signup } from '../api'
import AuthAside from '../components/AuthAside'

const MIN_PASSWORD_LENGTH = 8

export default function CreateAccount() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      const { user } = await signup({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
      })
      navigate('/login', { state: { email: user.email, justSignedUp: true } })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Account creation failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-page page">
      <div className="auth-shell">
        <AuthAside />
        <div className="auth-card">
          <h1>Create account</h1>
          <p className="muted">Join the Campus Customs community.</p>
          {error && <div className="alert error" role="alert"><strong>Account not created.</strong> {error}</div>}
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <label>
                First name
                <input type="text" required maxLength={50} autoComplete="given-name"
                  value={form.first_name} onChange={update('first_name')} />
              </label>
              <label>
                Last name
                <input type="text" required maxLength={50} autoComplete="family-name"
                  value={form.last_name} onChange={update('last_name')} />
              </label>
            </div>
            <label>
              Email
              <input type="email" required placeholder="you@yale.edu" autoComplete="email"
                value={form.email} onChange={update('email')} />
            </label>
            <label>
              Password
              <input type="password" required minLength={MIN_PASSWORD_LENGTH} autoComplete="new-password"
                value={form.password} onChange={update('password')} />
              <span className="hint">At least {MIN_PASSWORD_LENGTH} characters</span>
            </label>
            <label>
              Confirm password
              <input type="password" required autoComplete="new-password"
                value={form.confirm} onChange={update('confirm')} />
            </label>
            <button type="submit" className="button primary" disabled={submitting}>
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>
          <p className="muted small">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    </section>
  )
}
