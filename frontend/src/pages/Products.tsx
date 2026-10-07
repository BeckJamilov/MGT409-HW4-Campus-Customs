import { useEffect, useMemo, useState } from 'react'
import { fetchProducts, toCard, type Product } from '../api'
import { useChatResults } from '../chatResults'
import ProductCard from '../components/ProductCard'
import SkeletonGrid from '../components/SkeletonGrid'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
type SortOption = 'name' | 'price-asc' | 'price-desc'

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [size, setSize] = useState('')
  const [sort, setSort] = useState<SortOption>('name')
  const { results: chatResults, setResults: setChatResults } = useChatResults()

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running on port 8000?'))
      .finally(() => setLoading(false))
  }, [])

  // Categories come from the backend (grouped from the database's garment_type).
  const categories = useMemo(() => [...new Set(products.map((p) => p.category))].sort(), [products])

  // Client-side search, category, in-stock size filter, and sorting.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    const filtered = products.filter(
      (p) =>
        (!q || [p.name, p.garment_type, ...p.colors, ...p.search_tags].join(' ').toLowerCase().includes(q)) &&
        (!category || p.category === category) &&
        (!size || (p.sizes_in_stock ?? []).includes(size)),
    )
    const sorted = [...filtered]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name))
    return sorted
  }, [products, query, category, size, sort])

  const filtersActive = query || category || size || sort !== 'name'
  const clearFilters = () => {
    setQuery('')
    setCategory('')
    setSize('')
    setSort('name')
  }

  // Products found by the chat assistant (structured results from /api/chat).
  if (chatResults) {
    return (
      <section className="container section page">
        <div className="chat-results-banner">
          <span className="chat-results-icon" aria-hidden="true">💬</span>
          <div className="chat-results-text">
            <div className="eyebrow dark">From your chat</div>
            <h1>“{chatResults.query}”</h1>
            <p>{chatResults.products.length} matching {chatResults.products.length === 1 ? 'product' : 'products'} · click any card for sizes and stock</p>
          </div>
          <button className="button primary" onClick={() => setChatResults(null)}>Show all products</button>
        </div>
        <div className="product-grid">
          {chatResults.products.map((p) => <ProductCard key={p.product_id} product={p} />)}
        </div>
      </section>
    )
  }

  return (
    <div className="page">
      <section className="page-banner">
        <div className="container">
          <p className="eyebrow">The collection</p>
          <h1>Shop all products</h1>
          <p>Tees, hoodies, crewnecks, quarter-zips, and jackets for every kind of Eli.</p>
        </div>
      </section>
    <section className="container section">
      <div className="filters">
        <div className="filters-row">
        <input
          className="search"
          type="search"
          placeholder="Search hoodies, crewnecks, hockey, navy…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search products"
        />
        <label>
          Category
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>
          Size in stock
          <select value={size} onChange={(e) => setSize(e.target.value)} aria-label="Filter by size in stock">
            <option value="">Any size</option>
            {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label>
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value as SortOption)} aria-label="Sort products">
            <option value="name">Name (A–Z)</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
          </select>
        </label>
        </div>
        <div className="filters-summary">
          <span className="result-count">{loading ? 'Loading…' : `${visible.length} of ${products.length} items`}</span>
          {filtersActive && (
            <button className="clear-filters" onClick={clearFilters}>Clear filters ✕</button>
          )}
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <SkeletonGrid />
      ) : (
        <div className="product-grid">
          {visible.map((p) => <ProductCard key={p.product_id} product={toCard(p)} />)}
        </div>
      )}
      {!loading && !error && visible.length === 0 && (
        <div className="empty-state">
          <p>No products match these filters.</p>
          <button className="button primary" onClick={clearFilters}>Clear filters</button>
        </div>
      )}
    </section>
    </div>
  )
}
