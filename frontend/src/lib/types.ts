export type JobStatus = "pending" | "fetching" | "training" | "complete" | "failed";

export interface SearchResult {
  product_id: number;
  name: string;
  status: "ready" | "processing" | "failed" | "timeout";
  job_id: number | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
}

export interface ForecastJob {
  id: number;
  product: number;
  product_name: string;
  status: JobStatus;
  error_message: string;
  created_at: string;
  completed_at: string | null;
}

export interface ModelComparison {
  model_type: string;
  params: Record<string, unknown>;
  mae: number;
  mape: number;
  rmse: number;
  is_best: boolean;
  is_comparable: boolean;
  trained_at: string;
}

export interface PricePoint {
  date: string;
  price: number;
}

export interface Forecast {
  forecast_dates: string[];
  forecast_prices: number[];
  next_dip_date: string | null;
  next_dip_price: number | null;
  model_type: string;
}

export interface ProductForecast {
  product_id: number;
  product_name: string;
  price_history: PricePoint[];
  forecast: Forecast;
  model_comparison: ModelComparison[];
  best_model: string;
}
