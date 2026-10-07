import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const navClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')

export default function Header() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Close the mobile menu after navigating.
  useEffect(() => setMenuOpen(false), [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login', { state: { loggedOut: true } })
  }

  return (
    <header className="header">
      <div className="announcement">
        <span>Officially licensed Yale apparel</span>
        <span className="announcement-dot" aria-hidden="true">•</span>
        <span>Visit us at 57 Broadway, New Haven</span>
      </div>
      <div className="header-inner container">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <span className="brand-mark">CC</span>
          <span>
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale Bulldog Blue</span>
          </span>
        </Link>
        <button
          className="menu-toggle"
          onClick={() => setMenuOpen((o) => !o)}
          aria-expanded={menuOpen}
          aria-controls="main-nav"
          aria-label="Toggle menu"
        >
          <span /><span /><span />
        </button>
        <nav id="main-nav" className={`nav ${menuOpen ? 'open' : ''}`} aria-label="Main navigation">
          <NavLink to="/" end className={navClass}>Home</NavLink>
          <NavLink to="/products" className={navClass}>Products</NavLink>
          <NavLink to="/about" className={navClass}>About Us</NavLink>
          <span className="nav-divider" aria-hidden="true" />
          {user ? (
            <>
              <span className="nav-user">
                <span className="nav-avatar" aria-hidden="true">{(user.first_name || user.name).charAt(0)}</span>
                Hi, {user.first_name || user.name}
              </span>
              <button className="nav-cta" onClick={handleLogout}>Log out</button>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navClass}>Log in</NavLink>
              <NavLink to="/create-account" className="nav-cta">Create account</NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
