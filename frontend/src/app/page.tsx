"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Header } from "@/components/Header";
import { SkeletonCard } from "@/components/Loading";
import { listEdges, listMarkets, pollJob, triggerSync } from "@/lib/api";
import type { EdgeOut, MarketListItem } from "@/lib/types";

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

export default function HomePage() {
  const [sort, setSort] = useState("date");
  const [query, setQuery] = useState("");
  const [markets, setMarkets] = useState<MarketListItem[]>([]);
  const [edges, setEdges] = useState<EdgeOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState("");
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, e] = await Promise.all([
        listMarkets({ sort }),
        listEdges(),
      ]);
      setMarkets(m);
      setEdges(e);
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load markets");
    } finally {
      setLoading(false);
    }
  }, [sort]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSync() {
    setSyncing(true);
    setSyncStatus("Queueing catalog refresh");
    setError(null);
    try {
      const { job_id } = await triggerSync();
      await pollJob(job_id, (status) => setSyncStatus(`Catalog refresh: ${status}`));
      await load();
      setSyncStatus("Catalog refresh complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  const visibleMarkets = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return markets;
    return markets.filter(
      (market) =>
        market.city_name.toLowerCase().includes(normalized) ||
        market.question.toLowerCase().includes(normalized) ||
        market.target_date.includes(normalized)
    );
  }, [markets, query]);

  return (
    <>
      <Header tagline="Daily high-temperature forecasts and market comparisons" />
      <main className="shell page">
        <section className="hero">
          <p className="eyebrow">High-temperature outlook</p>
          <h1>See what the models expect, and how uncertain they are.</h1>
          <p className="lede">
            Time-series forecasts use Open-Meteo historical observations and compare calibrated
            bucket probabilities with active Polymarket odds. Differences are not guaranteed value.
          </p>
          <div className="toolbar" aria-label="Market filters">
            <label className="field search-field">
              <span>Search city or date</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="New York or 2026-08-08"
              />
            </label>
            <label className="field">
              <span>Sort markets</span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
                <option value="date">Soonest target</option>
                <option value="edge">Largest disagreement</option>
                <option value="volume">Highest volume</option>
            </select>
            </label>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="button secondary"
            >
              {syncing ? "Refreshing…" : "Refresh markets"}
            </button>
          </div>
          <p className="update-note" aria-live="polite">
            {syncStatus ||
              (updatedAt ? `Page updated ${updatedAt.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : "")}
          </p>
        </section>

        {error && (
          <div className="notice error" role="alert">
            <strong>Couldn&apos;t load predictions.</strong>
            <span>{error}</span>
            <button className="text-button" onClick={load}>Try again</button>
          </div>
        )}

        {edges.length > 0 && (
          <section className="section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Largest model–market gaps</p>
                <h2>Notable disagreements</h2>
              </div>
              <p>Absolute probability difference; not a recommendation.</p>
            </div>
            <div className="disagreement-grid">
              {edges.slice(0, 5).map((e) => (
                <Link
                  key={`${e.market_id}-${e.bucket_label}`}
                  href={`/market/${e.market_id}`}
                  className="mini-card"
                >
                  <span className="mini-card-title">{e.city_name}</span>
                  <span>{e.bucket_label}</span>
                  <strong>
                    {e.edge >= 0 ? "+" : ""}
                    {pct(e.edge)} model difference
                  </strong>
                </Link>
              ))}
            </div>
          </section>
        )}

        <section className="section" aria-labelledby="markets-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Active high-temperature markets</p>
              <h2 id="markets-heading">Forecasts</h2>
            </div>
            {!loading && <p>{visibleMarkets.length} result{visibleMarkets.length === 1 ? "" : "s"}</p>}
          </div>
        {loading ? (
          <div className="market-grid" role="status" aria-label="Loading market forecasts">
            {[0, 1, 2].map((item) => <SkeletonCard key={item} />)}
          </div>
        ) : markets.length === 0 ? (
          <div className="empty-state">
            <h3>No active markets yet</h3>
            <p>Refresh the catalog to discover supported daily high-temperature markets.</p>
            <button className="button primary" onClick={handleSync} disabled={syncing}>Refresh markets</button>
          </div>
        ) : visibleMarkets.length === 0 ? (
          <div className="empty-state">
            <h3>No matching forecasts</h3>
            <p>Try another city name or target date.</p>
            <button className="text-button" onClick={() => setQuery("")}>Clear search</button>
          </div>
        ) : (
          <div className="market-grid">
            {visibleMarkets.map((m) => (
              <Link
                key={m.id}
                href={`/market/${m.id}`}
                className="market-card"
              >
                <div className="market-card-head">
                  <div>
                    <span className={`status ${m.best_model ? "ready" : "pending"}`}>
                      <span aria-hidden="true">{m.best_model ? "✓" : "…"}</span>
                      {m.best_model ? "Forecast ready" : "Awaiting forecast"}
                    </span>
                    <h3>{m.city_name}</h3>
                    <p>{new Date(`${m.target_date}T12:00:00`).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</p>
                  </div>
                  <span className="chevron" aria-hidden="true">›</span>
                </div>
                <dl className="metric-row">
                  <div>
                    <dt>Predicted high</dt>
                    <dd>{m.point_forecast_c != null ? `${m.point_forecast_c.toFixed(1)}°C` : "View details"}</dd>
                  </div>
                  <div>
                    <dt>Top market bucket</dt>
                    <dd>{m.top_bucket_label || "Not available"}</dd>
                    {m.top_bucket_price != null && <span>{pct(m.top_bucket_price)} market probability</span>}
                  </div>
                  <div>
                    <dt>Largest difference</dt>
                    <dd>{m.max_edge != null ? pct(m.max_edge) : "Not available"}</dd>
                  </div>
                </dl>
                <p className="model-note">{m.best_model ? `Selected model: ${m.best_model.replaceAll("_", " ")}` : "Open to generate or inspect this forecast."}</p>
              </Link>
            ))}
          </div>
        )}
        </section>

        <aside className="transparency">
          <h2>How to read these results</h2>
          <p>
            Forecasts are estimates from historical daily highs, not weather-service forecasts.
            Uncertainty grows with horizon and unusual conditions may not appear in past data.
            Market comparisons can change after the model run and are not financial advice.
          </p>
        </aside>
      </main>
    </>
  );
}
