"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { LoadingSpinner } from "@/components/Loading";
import { listEdges, listMarkets, triggerSync } from "@/lib/api";
import type { EdgeOut, MarketListItem, TempType } from "@/lib/types";

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

export default function HomePage() {
  const [tempType, setTempType] = useState<TempType | "all">("high");
  const [sort, setSort] = useState("edge");
  const [markets, setMarkets] = useState<MarketListItem[]>([]);
  const [edges, setEdges] = useState<EdgeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, e] = await Promise.all([
        listMarkets({
          temp_type: tempType === "all" ? undefined : tempType,
          sort,
        }),
        listEdges(),
      ]);
      setMarkets(m);
      setEdges(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load markets");
    } finally {
      setLoading(false);
    }
  }, [tempType, sort]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSync() {
    setSyncing(true);
    try {
      await triggerSync();
      await new Promise((r) => setTimeout(r, 3000));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <>
      <Header tagline="Model bakeoff vs Polymarket high/low temp odds" />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-12">
        <section className="py-12">
          <h1 className="text-4xl font-bold tracking-tight">Daily temperature edges</h1>
          <p className="mt-3 max-w-2xl text-muted">
            Discover Polymarket weather markets, train ARIMA-family + Prophet models on
            free station history, and highlight where our probabilities disagree with the crowd.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <div className="flex rounded-lg border border-border overflow-hidden">
              {(["high", "low", "all"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTempType(t)}
                  className={`px-4 py-2 text-sm capitalize ${
                    tempType === t ? "bg-accent text-black font-semibold" : "bg-surface text-muted"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-sm"
            >
              <option value="edge">Sort by edge</option>
              <option value="volume">Sort by volume</option>
              <option value="date">Sort by date</option>
            </select>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm hover:bg-border disabled:opacity-50"
            >
              {syncing ? "Syncing…" : "Sync Polymarket"}
            </button>
            <Link
              href="/example"
              className="rounded-lg border border-accent/40 bg-accent/10 px-4 py-2 text-sm text-accent no-underline"
            >
              View example UI
            </Link>
          </div>
        </section>

        {error && (
          <div className="mb-6 rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-error">
            {error}
          </div>
        )}

        {edges.length > 0 && (
          <section className="mb-10">
            <h2 className="mb-3 text-lg font-semibold">Top edges right now</h2>
            <div className="flex flex-col gap-2">
              {edges.slice(0, 5).map((e) => (
                <Link
                  key={`${e.market_id}-${e.bucket_label}`}
                  href={`/market/${e.market_id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-4 py-3 no-underline text-text hover:border-accent"
                >
                  <span>
                    <span className="font-medium">{e.city_name}</span>
                    <span className="text-muted"> · {e.bucket_label}</span>
                  </span>
                  <span className="text-accent font-semibold">
                    {e.edge >= 0 ? "+" : ""}
                    {pct(e.edge)} edge
                  </span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {loading ? (
          <LoadingSpinner message="Loading markets…" />
        ) : markets.length === 0 ? (
          <p className="text-muted">
            No markets yet. Hit <strong>Sync Polymarket</strong> (requires worker + network).
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {markets.map((m) => (
              <Link
                key={m.id}
                href={`/market/${m.id}`}
                className="rounded-lg border border-border bg-surface p-4 no-underline text-text transition-colors hover:border-accent hover:bg-surface-2"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{m.question}</p>
                    <p className="mt-1 text-sm text-muted">
                      {m.city_name} · {m.temp_type} · {m.target_date}
                      {m.best_model ? ` · best: ${m.best_model}` : ""}
                    </p>
                  </div>
                  <div className="text-right text-sm">
                    {m.top_bucket_label && (
                      <p>
                        Crowd: {m.top_bucket_label}{" "}
                        {m.top_bucket_price != null ? pct(m.top_bucket_price) : ""}
                      </p>
                    )}
                    {m.max_edge != null && (
                      <p className="text-accent">max |edge| {pct(m.max_edge)}</p>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
