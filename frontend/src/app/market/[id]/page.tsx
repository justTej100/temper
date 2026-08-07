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
  const [jobStage, setJobStage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let detail = await getMarket(marketId);
      if (
        detail.job_status &&
        ["queued", "fetching", "training", "evaluating"].includes(detail.job_status) &&
        !detail.model_comparison.length
      ) {
        setMessage(`Preparing forecast: ${detail.job_status}…`);
        setJobStage(detail.job_status);
        // Poll via retrain status isn't available by id from detail — refetch
        for (let i = 0; i < 90; i++) {
          await new Promise((r) => setTimeout(r, 2000));
          detail = await getMarket(marketId);
          setMessage(`Preparing forecast: ${detail.job_status ?? "running"}…`);
          setJobStage(detail.job_status ?? "running");
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
      setJobStage(detail.job_status);
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
    setError(null);
    try {
      const { job_id } = await retrainMarket(marketId);
      await pollJob(job_id, (s) => {
        setJobStage(s);
        setMessage(`Forecast job: ${s}`);
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retrain failed");
      setLoading(false);
    }
  }

  return (
    <>
      <Header />
      <main className="shell page detail-page">
        <p className="back-link-wrap">
          <Link href="/" className="back-link">
            <span aria-hidden="true">←</span> All forecasts
          </Link>
        </p>

        {error && (
          <div className="notice error" role="alert">
            <strong>Forecast unavailable.</strong>
            <span>{error}</span>
            <button className="text-button" onClick={load}>Try again</button>
          </div>
        )}

        {loading && !data && <LoadingSpinner message={message} />}
        {loading && !data && (
          <div className="loading-detail">
            <SkeletonChart />
          </div>
        )}

        {data && (
          <>
            <div className="detail-header">
              <div>
                <p className="eyebrow">Daily high forecast</p>
                <h1>{data.city_name}</h1>
                <p className="lede">
                  {new Date(`${data.target_date}T12:00:00`).toLocaleDateString(undefined, {
                    weekday: "long", year: "numeric", month: "long", day: "numeric",
                  })}
                </p>
              </div>
              <div className="detail-actions">
                {data.url && (
                  <a
                    href={data.url}
                    target="_blank"
                    rel="noreferrer"
                    className="button secondary"
                  >
                    Open Polymarket <span aria-hidden="true">↗</span>
                    <span className="sr-only"> (opens in a new tab)</span>
                  </a>
                )}
                <button
                  onClick={handleRetrain}
                  className="button primary"
                  disabled={loading || !data.supported}
                >
                  {loading ? "Running…" : "Refresh forecast"}
                </button>
              </div>
            </div>

            {jobStage && jobStage !== "complete" && (
              <div className={`notice ${jobStage === "failed" ? "error" : "info"}`} aria-live="polite">
                <strong>{jobStage === "failed" ? "Forecast job failed" : "Forecast in progress"}</strong>
                <span>{message}</span>
              </div>
            )}

            {!data.supported && (
              <div className="notice warning" role="status">
                <strong>Comparison not supported</strong>
                <span>{data.unsupported_reason || "The market resolution source could not be matched reliably."}</span>
              </div>
            )}

            <section className="prediction-summary" aria-labelledby="prediction-heading">
              <div className="primary-prediction">
                <p className="eyebrow" id="prediction-heading">Predicted high</p>
                <p className="temperature">{data.point_forecast_c != null ? `${data.point_forecast_c.toFixed(1)}°C` : "—"}</p>
                <p>{data.point_forecast_c != null ? `${(data.point_forecast_c * 9 / 5 + 32).toFixed(1)}°F` : "Forecast not generated"}</p>
              </div>
              <dl className="summary-metrics">
                <div>
                  <dt>Typical forecast error</dt>
                  <dd>{data.residual_rmse != null ? `±${data.residual_rmse.toFixed(1)}°C RMSE` : "Not available"}</dd>
                </div>
                <div>
                  <dt>Most likely model bucket</dt>
                  <dd>{[...data.buckets].sort((a, b) => (b.model_prob ?? -1) - (a.model_prob ?? -1))[0]?.label || "Not available"}</dd>
                </div>
                <div>
                  <dt>Selected model</dt>
                  <dd>{data.best_model?.replaceAll("_", " ") || "Not selected"}</dd>
                </div>
              </dl>
            </section>

            {data.history.length > 0 ? (
              <TempChart
                history={data.history}
                forecastDates={data.forecast_dates}
                forecastTemps={data.forecast_temps}
                modelType={data.best_model}
                uncertainty={data.residual_rmse}
              />
            ) : (
              <div className="empty-state">
                <h2>No historical series yet</h2>
                No temperature history yet — training will fetch Open-Meteo data.
              </div>
            )}

            <BucketCompare buckets={data.buckets} />
            <details className="details-panel">
              <summary>Model evaluation and technical details</summary>
              <div className="details-content">
                <ModelComparisonTable models={data.model_comparison} bestModel={data.best_model} />
                <dl className="metadata-list">
                  <div><dt>Historical source</dt><dd>Open-Meteo archive daily highs</dd></div>
                  <div><dt>Location / station</dt><dd>{data.resolution_station || data.icao || "Open-Meteo grid point"}</dd></div>
                  <div><dt>Market resolution source</dt><dd>{data.resolution_source || "Not published"}</dd></div>
                  <div><dt>Local timezone</dt><dd>{data.timezone || "Not available"}</dd></div>
                  <div><dt>Training window</dt><dd>{data.history.length ? `${data.history[0].date} to ${data.history[data.history.length - 1].date}` : "Not available"}</dd></div>
                  <div><dt>History observations</dt><dd>{data.history.length.toLocaleString()} days</dd></div>
                </dl>
              </div>
            </details>

            <aside className="transparency">
              <h2>Limitations and responsible use</h2>
              <p>
                This time-series model uses historical daily highs only. It does not ingest weather-service
                forecasts and may miss abrupt weather changes. The error measure summarizes past backtests,
                not a guaranteed interval. Polymarket odds can change after this page updates. This is
                experimental information, not financial advice.
              </p>
            </aside>
          </>
        )}
      </main>
    </>
  );
}
