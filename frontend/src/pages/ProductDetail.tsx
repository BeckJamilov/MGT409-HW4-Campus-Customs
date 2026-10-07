import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { displayDescription, fetchProduct, formatPrice, type Product } from '../api'

const LOW_STOCK = 5

function stockLabel(quantity: number) {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

function sizeClass(quantity: number) {
  if (quantity === 0) return 'size out'
  if (quantity <= LOW_STOCK) return 'size low'
  return 'size'
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setProduct(null)
    setError('')
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message === 'Not found' ? 'Product not found.' : 'Could not load this product.'))
  }, [productId])

  if (error) {
    return (
      <section className="container section page">
        <div className="empty-state">
          <p className="error">{error}</p>
          <Link to="/products" className="button primary">Back to products</Link>
        </div>
      </section>
    )
  }
  if (!product) {
    return (
      <section className="container section" aria-busy="true">
        <div className="detail">
          <div className="detail-image skeleton-block" />
          <div className="detail-info">
            <div className="skeleton-line short" />
            <div className="skeleton-line title" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
          </div>
        </div>
      </section>
    )
  }

  const sizesInStock = product.inventory?.filter((s) => s.quantity > 0).length ?? 0
  const totalSizes = product.inventory?.length ?? 0

  return (
    <section className="container section page">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span aria-hidden="true">/</span>
        <Link to="/products" className="back-link">Products</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{product.name}</span>
      </nav>
      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <div className="product-card-type">{product.garment_type}</div>
          <h1>{product.name}</h1>
          <div className="detail-price-row">
            <span className="detail-price">{formatPrice(product.price)}</span>
            <span className={`availability ${product.total_stock > 0 ? 'in' : 'out'}`}>
              {product.total_stock > 0 ? `In stock · ${sizesInStock} of ${totalSizes} sizes` : 'Sold out'}
            </span>
          </div>
          <p className="detail-description">{displayDescription(product)}</p>

          {product.colors.length > 0 && (
            <div className="detail-block">
              <h4>Colors</h4>
              <div className="chips">
                {product.colors.map((c) => <span key={c} className="chip">{c}</span>)}
              </div>
            </div>
          )}

          <div className="detail-block">
            <h4>Sizes &amp; availability</h4>
            {product.inventory && product.inventory.length > 0 ? (
              <div className="sizes">
                {product.inventory.map((s) => (
                  <div key={s.size} className={sizeClass(s.quantity)}>
                    <strong>{s.size}</strong>
                    <span>{stockLabel(s.quantity)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">Size information is not available.</p>
            )}
            <p className="muted small">{product.total_stock} units in stock across all sizes</p>
          </div>

          <ul className="assurances">
            <li><span aria-hidden="true">✓</span> Officially licensed Yale merchandise</li>
            <li><span aria-hidden="true">⌂</span> Campus Customs, 57 Broadway, New Haven</li>
            <li><span aria-hidden="true">💬</span> Questions about fit or stock? Ask our assistant in the chat</li>
          </ul>

          {product.search_tags.length > 0 && (
            <div className="detail-block">
              <h4>Tags</h4>
              <div className="chips">
                {product.search_tags.map((t) => <span key={t} className="chip subtle">{t}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
