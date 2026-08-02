"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { BucketCompare } from "@/components/BucketCompare";
import { Header } from "@/components/Header";
import { LoadingSpinner, SkeletonChart } from "@/components/Loading";
import { ModelComparisonTable } from "@/components/ModelComparisonTable";
import { TempChart } from "@/components/TempChart";
import { getMarket, pollJob, retrainMarket } from "@/lib/api";
import type { MarketDetail } from "@/lib/types";

export default function MarketPage() {
  const params = useParams();
  const marketId = Number(params.id);
  const [data, setData] = useState<MarketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("Loading market…");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let detail = await getMarket(marketId);
      if (
        detail.job_status &&
        ["pending", "fetching", "training"].includes(detail.job_status) &&
        !detail.model_comparison.length
      ) {
        setMessage(`Job ${detail.job_status}…`);
        // Poll via retrain status isn't available by id from detail — refetch
        for (let i = 0; i < 90; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          detail = await getMarket(marketId);
          setMessage(`Job ${detail.job_status ?? "running"}…`);
          if (
            !detail.job_status ||
            detail.job_status === "complete" ||
            detail.job_status === "failed" ||
            detail.model_comparison.length > 0
          ) {
            break;
          }
        }
      }
      setData(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [marketId]);

  useEffect(() => {
    if (!Number.isNaN(marketId)) load();
  }, [marketId, load]);

  async function handleRetrain() {
    setLoading(true);
    setMessage("Retraining models…");
    setData(null);
    try {
      const { job_id } = await retrainMarket(marketId);
      await pollJob(job_id, (s) => setMessage(`Job ${s}…`));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retrain failed");
      setLoading(false);
    }
  }

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-12">
        <p className="pt-6">
          <Link href="/" className="text-accent no-underline hover:underline">
            ← Markets
          </Link>
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-error">
            {error}
          </div>
        )}

        {loading && <LoadingSpinner message={message} />}
        {loading && !data && (
          <div className="mt-6">
            <SkeletonChart />
          </div>
        )}

        {!loading && data && (
          <>
            <div className="flex flex-col gap-4 py-6 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h1 className="text-2xl font-bold sm:text-3xl">{data.question}</h1>
                <p className="mt-2 text-sm text-muted">
                  {data.city_name}
                  {data.icao ? ` (${data.icao})` : ""} · {data.temp_type} · {data.target_date}
                  {data.point_forecast_c != null &&
                    ` · model pick ${data.point_forecast_c.toFixed(1)}°C`}
                </p>
              </div>
              <div className="flex gap-2">
                {data.url && (
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm no-underline text-text"
                  >
                    Polymarket
                  </a>
                )}
                <button
                  onClick={handleRetrain}
                  className="rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm"
                >
                  Retrain
                </button>
              </div>
            </div>

            {data.history.length > 0 ? (
              <TempChart
                history={data.history}
                forecastDates={data.forecast_dates}
                forecastTemps={data.forecast_temps}
                modelType={data.best_model}
              />
            ) : (
              <p className="rounded-lg border border-border bg-surface p-6 text-muted">
                No temperature history yet — training will fetch Open-Meteo data.
              </p>
            )}

            <BucketCompare buckets={data.buckets} />
            <ModelComparisonTable
              models={data.model_comparison}
              bestModel={data.best_model}
            />
          </>
        )}
      </main>
    </>
  );
}
