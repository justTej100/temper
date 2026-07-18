"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { LoadingSpinner } from "@/components/Loading";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";
import { pollJobs, searchProducts } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

export default function HomePage() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("Searching...");
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch(query: string) {
    setLoading(true);
    setError(null);
    setLoadingMessage("Searching...");
    setHasSearched(true);

    try {
      const data = await searchProducts(query);
      let searchResults = data.results;

      const pending = searchResults.filter((r) => r.status === "processing" && r.job_id);

      if (pending.length > 0) {
        setLoadingMessage(`Training models for ${pending.length} product(s)...`);
        await pollJobs(
          pending.map((r) => ({ job_id: r.job_id! })),
          setLoadingMessage
        );
        searchResults = searchResults.map((r) =>
          r.status === "processing" ? { ...r, status: "ready" as const } : r
        );
      }

      setResults(searchResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Header tagline="On-demand price dip prediction" />

      <main className="mx-auto w-full max-w-5xl flex-1 px-6">
        <section className="py-16 text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            When will the price drop?
          </h1>
          <p className="mx-auto mt-4 max-w-lg text-muted">
            Search any product to see its price history and get a forecast of the
            next likely dip — models are trained on demand, not pre-computed.
          </p>
          <div className="mt-8">
            <SearchBar onSearch={handleSearch} disabled={loading} />
          </div>
        </section>

        {error && (
          <div className="mb-6 rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-error">
            {error}
          </div>
        )}

        {loading && <LoadingSpinner message={loadingMessage} />}

        {!loading && hasSearched && results.length === 0 && !error && (
          <p className="py-8 text-center text-muted">No products found.</p>
        )}

        {!loading && results.length > 0 && <SearchResults results={results} />}
      </main>
    </>
  );
}
