import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="page">
      <section className="page-banner">
        <div className="container">
          <p className="eyebrow">Our story</p>
          <h1>About Campus Customs</h1>
          <p>A New Haven shop built around one idea: Yale pride should be easy to wear.</p>
        </div>
      </section>

      <section className="container section about-layout">
        <div className="about-copy">
          <p className="lead">
            We run Yale Bulldog Blue, a store dedicated to officially licensed Yale apparel and gifts.
          </p>
          <p>
            Whether you are a first-year moving into Old Campus, a parent visiting for the weekend, or
            an alum cheering on the Bulldogs from far away, we want to help you find something you will
            reach for again and again.
          </p>
          <p>
            Our collection covers everyday basics like tees, hoodies, and crewnecks, plus quarter-zips
            and jackets for colder New Haven days. You will also find designs for Yale's residential
            colleges and varsity teams, so you can show off exactly where your loyalties lie.
          </p>
          <blockquote className="pull-quote">“Yale pride should be easy to wear.”</blockquote>
          <Link to="/products" className="button primary large">Explore the collection</Link>
        </div>
        <aside className="about-cards">
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">⌂</span>
            <h3>Visit the shop</h3>
            <p>57 Broadway<br />New Haven, CT 06511</p>
          </div>
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">✓</span>
            <h3>What we carry</h3>
            <p>Officially licensed Yale clothing for students, alumni, families, and fans.</p>
          </div>
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">💬</span>
            <h3>Need a hand?</h3>
            <p>Our shopping assistant can find styles, check sizes, and suggest gifts. Just open the chat.</p>
          </div>
        </aside>
      </section>
    </div>
  )
}
