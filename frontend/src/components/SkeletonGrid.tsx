// Placeholder cards shown while products load.
export default function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="product-grid" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="product-card skeleton">
          <div className="product-card-image" />
          <div className="product-card-body">
            <div className="skeleton-line short" />
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line price" />
          </div>
        </div>
      ))}
    </div>
  )
}
