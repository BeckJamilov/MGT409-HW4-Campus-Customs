import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, toCard, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const FEATURED_COUNT = 4

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])

  const inStock = products.filter((p) => p.total_stock > 0)
  const featured = inStock.slice(0, FEATURED_COUNT)
  // Hero collage: three real hoodies from the catalogue.
  const collage = inStock.filter((p) => p.category === 'Hoodies').slice(0, 3)
  const categoryCount = new Set(products.map((p) => p.category)).size

  return (
    <div className="page">
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">New Haven's Yale outfitter · 57 Broadway</p>
            <h1>
              Wear your <em>Bulldog</em> blue.
            </h1>
            <p className="hero-text">
              From game-day tees to cozy crewnecks, Campus Customs makes it easy to rep Yale on
              campus, at the Bowl, or a thousand miles from Old Campus.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="button light large">Shop the collection</Link>
              <Link to="/about" className="button ghost large">Our story</Link>
            </div>
            <p className="hero-hint">Need help choosing? Ask our assistant in the chat ↘</p>
          </div>
          <div className="hero-collage" aria-hidden={collage.length === 0}>
            {collage.map((p, i) => (
              <Link key={p.product_id} to={`/products/${p.product_id}`} className={`collage-item collage-${i + 1}`}>
                <img src={p.image_url} alt={p.name} />
                {i === 0 && <span className="collage-tag">${p.price.toFixed(0)}</span>}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {products.length > 0 && (
        <section className="stats-strip">
          <div className="container stats-inner">
            <div><strong>{products.length}</strong><span>Yale styles</span></div>
            <div><strong>{categoryCount}</strong><span>Categories</span></div>
            <div><strong>XS–XXL</strong><span>Sizes</span></div>
            <div><strong>100%</strong><span>Officially licensed</span></div>
          </div>
        </section>
      )}

      <section className="container section">
        <div className="feature-grid">
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">✓</span>
            <h3>Officially licensed</h3>
            <p>Every piece carries authentic Yale marks, so you know your gear is the real deal.</p>
          </div>
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">★</span>
            <h3>Something for every Eli</h3>
            <p>Residential college pride, varsity sports logos, and classic YALE wordmarks in one place.</p>
          </div>
          <div className="feature">
            <span className="feature-icon" aria-hidden="true">⌂</span>
            <h3>Right on Broadway</h3>
            <p>Stop by our shop at 57 Broadway, steps from campus, or browse the full lineup online.</p>
          </div>
        </div>
      </section>

      {featured.length > 0 && (
        <section className="container section">
          <div className="section-heading">
            <div>
              <p className="eyebrow dark">Shop now</p>
              <h2>Fan favorites</h2>
            </div>
            <Link to="/products" className="text-link">View all {products.length} products →</Link>
          </div>
          <div className="product-grid">
            {featured.map((p) => <ProductCard key={p.product_id} product={toCard(p)} />)}
          </div>
        </section>
      )}

      <section className="container section">
        <div className="promo-band">
          <div>
            <p className="eyebrow">Gift season, every season</p>
            <h2>Shopping for a Yale parent, grad, or fan?</h2>
            <p>Find hoodies for Mom, Dad, Grandma, and the whole family, plus residential college and team gear.</p>
          </div>
          <Link to="/products" className="button light large">Browse gifts</Link>
        </div>
      </section>
    </div>
  )
}
