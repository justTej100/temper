import type {
  EdgeOut,
  ForecastJob,
  MarketDetail,
  MarketListItem,
} from "./types";

const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
export const API_URL = (configuredUrl || "http://localhost:8000").replace(/\/+$/, "");
export const API_DOCS_URL = `${API_URL}/docs`;

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
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || body.error || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

export function listMarkets(params?: { sort?: string; limit?: number }) {
  const q = new URLSearchParams();
  if (params?.sort) q.set("sort", params.sort);
  if (params?.limit) q.set("limit", String(params.limit));
  const suffix = q.toString() ? `?${q}` : "";
  return request<MarketListItem[]>(`/api/markets/${suffix}`);
}

export function getMarket(id: number) {
  return request<MarketDetail>(`/api/markets/${id}`);
}

export function retrainMarket(id: number) {
  return request<{ job_id: number; status: string }>(`/api/markets/${id}/train`, {
    method: "POST",
  });
}

export function getJob(id: number) {
  return request<ForecastJob>(`/api/jobs/${id}`);
}

export function listEdges() {
  return request<EdgeOut[]>("/api/edges/");
}

export function triggerSync() {
  return request<{ job_id: number; status: string }>("/api/sync/", { method: "POST" });
}

export async function pollJob(
  jobId: number,
  onProgress?: (status: string) => void
): Promise<void> {
  for (let i = 0; i < 120; i++) {
    const job = await getJob(jobId);
    onProgress?.(job.status);
    if (job.status === "complete") return;
    if (job.status === "failed") {
      throw new Error(job.error_message || "Forecast job failed");
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("Training timed out");
}
