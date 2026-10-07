import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-band">
        <div className="container footer-band-inner">
          <p className="footer-tagline">For God, for Country, and for Yale. And for your closet.</p>
          <Link to="/products" className="button light">Shop the collection</Link>
        </div>
      </div>
      <div className="container footer-inner">
        <div className="footer-brand">
          <div className="brand">
            <span className="brand-mark">CC</span>
            <span>
              <span className="brand-name">Campus Customs</span>
              <span className="brand-sub">Yale Bulldog Blue</span>
            </span>
          </div>
          <p>Officially licensed Yale gear for students, alumni, families, and fans.</p>
        </div>
        <div>
          <div className="footer-heading">Visit</div>
          <p>57 Broadway<br />New Haven, CT 06511</p>
        </div>
        <div>
          <div className="footer-heading">Shop</div>
          <ul className="footer-links">
            <li><Link to="/products">All products</Link></li>
            <li><Link to="/about">About us</Link></li>
          </ul>
        </div>
        <div>
          <div className="footer-heading">Account</div>
          <ul className="footer-links">
            <li><Link to="/login">Log in</Link></li>
            <li><Link to="/create-account">Create account</Link></li>
          </ul>
        </div>
      </div>
      <div className="footer-note">Homework project for MGT 409 · Not the official store website</div>
    </footer>
  )
}
