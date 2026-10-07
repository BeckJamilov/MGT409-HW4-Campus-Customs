import { Link } from 'react-router-dom'
import { formatPrice, type ChatProductCard } from '../api'

// Shared by the Products page and chat search results, so both link to the same product page.
export default function ProductCard({ product }: { product: ChatProductCard }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="product-card-cta" aria-hidden="true">View details</span>
      </div>
      <div className="product-card-body">
        {product.garment_type && <div className="product-card-type">{product.garment_type}</div>}
        <h3>{product.name}</h3>
        <p>{product.short_description ?? `${product.name} from the Campus Customs Yale collection.`}</p>
        <div className="product-card-footer">
          <span className="product-card-price">{formatPrice(product.price)}</span>
          <span className="product-card-arrow" aria-hidden="true">→</span>
        </div>
      </div>
    </Link>
  )
}
