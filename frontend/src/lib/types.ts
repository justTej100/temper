export type TempType = "high";
export type JobStatus =
  | "queued"
  | "fetching"
  | "training"
  | "evaluating"
  | "complete"
  | "failed";

export interface MarketListItem {
  id: number;
  question: string;
  city_name: string;
  temp_type: TempType;
  target_date: string;
  volume: number;
  url: string;
  top_bucket_label: string | null;
  top_bucket_price: number | null;
  max_edge: number | null;
  best_model: string | null;
}

export interface Bucket {
  id: number;
  label: string;
  temp_c: number | null;
  yes_price: number;
  model_prob: number | null;
  edge: number | null;
}

export interface ModelComparison {
  model_type: string;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  is_best: boolean;
  params: Record<string, unknown>;
}

export interface MarketDetail {
  id: number;
  question: string;
  city_id: number;
  city_name: string;
  icao: string;
  timezone: string;
  data_source: string;
  resolution_source: string;
  resolution_station: string;
  supported: boolean;
  unsupported_reason: string;
  temp_type: TempType;
  target_date: string;
  volume: number;
  url: string;
  history: { date: string; temp_c: number }[];
  forecast_dates: string[];
  forecast_temps: number[];
  point_forecast_c: number | null;
  residual_rmse: number | null;
  buckets: Bucket[];
  model_comparison: ModelComparison[];
  best_model: string | null;
  job_status: JobStatus | null;
}

export interface ForecastJob {
  id: number;
  market_id: number | null;
  job_type: "sync" | "forecast" | "scheduled";
  status: JobStatus;
  error_message: string;
  attempts: number;
  updated_at: string;
  created_at: string;
  completed_at: string | null;
}

export interface EdgeOut {
  market_id: number;
  question: string;
  city_name: string;
  bucket_label: string;
  model_prob: number;
  market_prob: number;
  edge: number;
  target_date: string;
}
