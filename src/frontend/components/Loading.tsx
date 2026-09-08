export function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      {message && <p>{message}</p>}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="skeleton card" aria-hidden="true">
      <div className="skeleton-line wide" />
      <div className="skeleton-line short" />
      <div className="skeleton-line" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="skeleton card" aria-hidden="true">
      <div className="skeleton-chart" />
    </div>
  );
}
