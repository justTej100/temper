export function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center py-16 text-center">
      <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-border border-t-accent" />
      {message && <p className="mt-4 text-muted">{message}</p>}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border border-border bg-surface p-5">
      <div className="h-4 w-3/4 rounded bg-surface-2" />
      <div className="mt-3 h-3 w-1/4 rounded bg-surface-2" />
    </div>
  );
}

export function SkeletonChart() {
  return (
    <div className="animate-pulse rounded-lg border border-border bg-surface p-6">
      <div className="h-64 rounded bg-surface-2" />
    </div>
  );
}
