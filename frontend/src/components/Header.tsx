import Link from "next/link";

export function Header({ tagline }: { tagline?: string }) {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div>
          <Link href="/" className="text-2xl font-bold text-text no-underline">
            Temperature <span className="text-accent">Predictor</span>
          </Link>
          {tagline && <p className="mt-1 text-sm text-muted">{tagline}</p>}
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/example" className="text-muted no-underline hover:text-accent">
            Example
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-muted no-underline hover:text-accent"
          >
            API Docs
          </a>
        </nav>
      </div>
    </header>
  );
}
