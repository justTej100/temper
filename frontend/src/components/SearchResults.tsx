"use client";

import type { SearchResult } from "@/lib/types";
import Link from "next/link";

const STATUS_LABELS: Record<string, string> = {
  ready: "Ready",
  processing: "Processing...",
  failed: "Failed",
  timeout: "Timed out",
};

export function SearchResults({ results }: { results: SearchResult[] }) {
  if (!results.length) return null;

  return (
    <section className="py-8">
      <h2 className="mb-4 text-xl font-semibold">Results</h2>
      <div className="flex flex-col gap-3">
        {results.map((result) => {
          const isReady = result.status === "ready";
          const Wrapper = isReady ? Link : "div";

          return (
            <Wrapper
              key={result.product_id}
              href={isReady ? `/product/${result.product_id}` : "#"}
              className={`flex items-center justify-between rounded-lg border border-border bg-surface p-4 transition-colors ${
                isReady
                  ? "cursor-pointer hover:border-accent hover:bg-surface-2 no-underline"
                  : "opacity-80"
              }`}
            >
              <span className="text-text">{result.name}</span>
              <StatusBadge status={result.status} />
            </Wrapper>
          );
        })}
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ready: "bg-success/15 text-success",
    processing: "bg-accent/15 text-accent",
    failed: "bg-error/15 text-error",
    timeout: "bg-error/15 text-error",
  };

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${
        styles[status] || "bg-surface-2 text-muted"
      }`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}
