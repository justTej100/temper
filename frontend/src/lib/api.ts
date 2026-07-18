import type {
  ForecastJob,
  ProductForecast,
  SearchResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }

  return res.json();
}

export function searchProducts(query: string, forceRefresh = false) {
  return request<SearchResponse>("/api/search/", {
    method: "POST",
    body: JSON.stringify({ query, force_refresh: forceRefresh }),
  });
}

export function getJobStatus(jobId: number) {
  return request<ForecastJob>(`/api/jobs/${jobId}/`);
}

export function getProductForecast(productId: number) {
  return request<ProductForecast>(`/api/products/${productId}/forecast/`);
}

export function retrainProduct(productId: number) {
  return request<{ job_id: number; status: string }>(
    `/api/products/${productId}/retrain/`,
    { method: "POST" }
  );
}

export async function pollJobs(
  jobs: { job_id: number }[],
  onProgress?: (message: string) => void
): Promise<void> {
  const maxAttempts = 120;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const statuses = await Promise.all(
      jobs.map((j) => getJobStatus(j.job_id))
    );

    const allDone = statuses.every(
      (s) => s.status === "complete" || s.status === "failed"
    );

    if (allDone) {
      const failed = statuses.find((s) => s.status === "failed");
      if (failed?.error_message) {
        throw new Error(failed.error_message);
      }
      return;
    }

    const training = statuses.filter((s) => s.status === "training").length;
    const fetching = statuses.filter((s) => s.status === "fetching").length;

    if (training > 0) {
      onProgress?.(`Training ${training} model(s)...`);
    } else if (fetching > 0) {
      onProgress?.("Fetching price history...");
    } else {
      onProgress?.("Queued...");
    }

    await new Promise((r) => setTimeout(r, 2000));
  }

  throw new Error("Training timed out — try again later.");
}

export function dedupePriceHistory(history: { date: string; price: number }[]) {
  const byDay = new Map<string, number>();
  for (const point of history) {
    const day = point.date.slice(0, 10);
    byDay.set(day, point.price);
  }
  return Array.from(byDay.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, price]) => ({ date, price }));
}
