import type { DipPrediction } from "@/lib/types";

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatDate(value: string | null) {
  if (!value) return "Unknown";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const recommendationCopy: Record<string, string> = {
  buy: "Buy now",
  watch: "Watch closely",
  wait: "Wait for a dip",
};

export function DipPredictionPanel({ prediction }: { prediction: DipPrediction | null }) {
  if (!prediction) return null;

  const windows = ["3d", "7d", "14d", "30d"];
  const recommendation = recommendationCopy[prediction.recommendation] ?? "Watch closely";
  const thresholdPercent = Math.round(prediction.dip_threshold * 100);

  return (
    <section className="mt-6 rounded-lg border border-border bg-surface p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">
            Shared dip timing model
          </p>
          <h2 className="mt-1 text-xl font-semibold">{recommendation}</h2>
          <p className="mt-1 text-sm text-muted">
            Chance of a {thresholdPercent}%+ price dip by window.
          </p>
        </div>
        <div className="rounded-md border border-border bg-surface-2 px-3 py-2 text-sm">
          <span className="text-muted">Confidence</span>{" "}
          <span className="font-semibold capitalize text-text">{prediction.confidence}</span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {windows.map((window) => (
          <div key={window} className="rounded-md border border-border bg-surface-2 p-3">
            <p className="text-xs uppercase tracking-wide text-muted">Next {window.replace("d", " days")}</p>
            <p className="mt-1 text-2xl font-semibold">
              {formatPercent(prediction.probabilities[window] ?? 0)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <p className="rounded-md bg-surface-2 px-3 py-2">
          <span className="text-muted">Expected dip date:</span>{" "}
          <span className="font-medium">{formatDate(prediction.expected_dip_date)}</span>
        </p>
        <p className="rounded-md bg-surface-2 px-3 py-2">
          <span className="text-muted">Expected dip price:</span>{" "}
          <span className="font-medium">
            {prediction.expected_dip_price ? `$${prediction.expected_dip_price.toFixed(2)}` : "Unknown"}
          </span>
        </p>
      </div>
    </section>
  );
}