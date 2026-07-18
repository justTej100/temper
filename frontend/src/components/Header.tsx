import Link from "next/link";

export function Header({ tagline }: { tagline?: string }) {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto max-w-5xl px-6 py-4">
        <Link href="/" className="text-2xl font-bold text-text no-underline">
          Price<span className="text-accent">Forecast</span>
        </Link>
        {tagline && (
          <p className="mt-1 text-sm text-muted">{tagline}</p>
        )}
      </div>
    </header>
  );
}
