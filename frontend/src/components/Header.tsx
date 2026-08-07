import Link from "next/link";
import { API_DOCS_URL } from "@/lib/api";

export function Header({ tagline }: { tagline?: string }) {
  return (
    <header className="app-header">
      <div className="shell header-inner">
        <div>
          <Link href="/" className="brand" aria-label="Temperature Predictor home">
            <span aria-hidden="true" className="brand-mark">°</span>
            Temperature Predictor
          </Link>
          {tagline && <p className="tagline">{tagline}</p>}
        </div>
        <nav className="header-nav" aria-label="Primary navigation">
          <a
            href={API_DOCS_URL}
            target="_blank"
            rel="noreferrer"
            className="nav-link"
          >
            API Docs
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
