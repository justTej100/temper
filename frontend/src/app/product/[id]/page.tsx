"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/Header";
import { DipAlert, NoDipBanner } from "@/components/DipAlert";
import { DipPredictionPanel } from "@/components/DipPredictionPanel";
import {
  LoadingSpinner,
  SkeletonChart,
} from "@/components/Loading";
import { ModelComparisonTable } from "@/components/ModelComparisonTable";
import { PriceChart } from "@/components/PriceChart";
import {
  dedupePriceHistory,
  getProductForecast,
  pollJobs,
  retrainProduct,
} from "@/lib/api";
import type { ProductForecast } from "@/lib/types";

export default function ProductPage() {
  const params = useParams();
  const productId = Number(params.id);

  const [data, setData] = useState<ProductForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState("Loading forecast...");
  const [error, setError] = useState<string | null>(null);
  const [retraining, setRetraining] = useState(false);

  const loadForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const forecast = await getProductForecast(productId);
      setData({
        ...forecast,
        price_history: dedupePriceHistory(forecast.price_history),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load forecast");
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    if (!Number.isNaN(productId)) {
      loadForecast();
    }
  }, [productId, loadForecast]);

  async function handleRetrain() {
    setRetraining(true);
    setLoading(true);
    setLoadingMessage("Retraining all models...");
    setData(null);
    setError(null);

    try {
      const { job_id } = await retrainProduct(productId);
      await pollJobs([{ job_id }], setLoadingMessage);
      await loadForecast();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retrain failed");
      setLoading(false);
    } finally {
      setRetraining(false);
    }
  }

  return (
    <>
      <Header />

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-12">
        <p className="pt-6">
          <Link href="/" className="text-accent no-underline hover:underline">
            Back to search
          </Link>
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-error">
            {error}
          </div>
        )}

        {loading && <LoadingSpinner message={loadingMessage} />}

        {!loading && data && (
          <>
            <div className="flex flex-col gap-4 py-6 sm:flex-row sm:items-start sm:justify-between">
              <h1 className="text-2xl font-bold sm:text-3xl">
                {data.product_name}
              </h1>
              <button
                onClick={handleRetrain}
                disabled={retraining}
                className="shrink-0 rounded-lg border border-border bg-surface-2 px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-border disabled:opacity-50"
              >
                {retraining ? "Retraining..." : "Retrain Models"}
              </button>
            </div>

            {data.forecast.next_dip_date && data.forecast.next_dip_price ? (
              <DipAlert
                date={data.forecast.next_dip_date}
                price={data.forecast.next_dip_price}
              />
            ) : (
              <NoDipBanner />
            )}

            <DipPredictionPanel prediction={data.dip_prediction} />

            <div className="mt-6">
              <PriceChart
                history={data.price_history}
                forecast={data.forecast}
              />
            </div>

            <ModelComparisonTable
              models={data.model_comparison}
              bestModel={data.best_model}
            />
          </>
        )}

        {loading && !data && <div className="mt-6"><SkeletonChart /></div>}
      </main>
    </>
  );
}