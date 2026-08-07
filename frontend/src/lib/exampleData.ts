import type { MarketDetail } from "./types";

/** Static NYC high-temp demo — no backend required. */
export const EXAMPLE_MARKET: MarketDetail = {
  id: 0,
  question: "Highest temperature in New York City on August 5?",
  city_id: 0,
  city_name: "New York City",
  icao: "KLGA",
  timezone: "America/New_York",
  data_source: "open-meteo",
  resolution_source: "curated-polymarket-station",
  resolution_station: "KLGA",
  supported: true,
  unsupported_reason: "",
  temp_type: "high",
  target_date: "2026-08-05",
  volume: 42000,
  url: "https://polymarket.com/weather/high-temperature",
  history: Array.from({ length: 120 }, (_, i) => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - (120 - i));
    const temp = 28 + Math.sin(i / 8) * 4 + Math.cos(i / 15) * 2;
    return { date: d.toISOString().slice(0, 10), temp_c: Math.round(temp * 10) / 10 };
  }),
  forecast_dates: Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() + i + 1);
    return d.toISOString().slice(0, 10);
  }),
  forecast_temps: [31.2, 32.1, 33.0, 32.4, 31.8, 30.5, 29.9, 30.2, 31.0, 31.5, 32.0, 31.4, 30.8, 30.1],
  point_forecast_c: 32.4,
  residual_rmse: 1.8,
  buckets: [
    { id: 1, label: "30°C", temp_c: 30, yes_price: 0.08, model_prob: 0.06, edge: -0.02 },
    { id: 2, label: "31°C", temp_c: 31, yes_price: 0.18, model_prob: 0.14, edge: -0.04 },
    { id: 3, label: "32°C", temp_c: 32, yes_price: 0.29, model_prob: 0.34, edge: 0.05 },
    { id: 4, label: "33°C", temp_c: 33, yes_price: 0.22, model_prob: 0.28, edge: 0.06 },
    { id: 5, label: "34°C", temp_c: 34, yes_price: 0.14, model_prob: 0.12, edge: -0.02 },
    { id: 6, label: "35°C or higher", temp_c: 35, yes_price: 0.09, model_prob: 0.06, edge: -0.03 },
  ],
  model_comparison: [
    { model_type: "seasonal_naive", mae: 1.42, bias: 0.1, rmse: 1.81, is_best: true, params: {} },
    { model_type: "prophet", mae: 1.55, bias: -0.2, rmse: 1.95, is_best: false, params: {} },
    { model_type: "sarima", mae: 1.61, bias: 0.3, rmse: 2.02, is_best: false, params: {} },
    { model_type: "last_value", mae: 1.74, bias: 0.4, rmse: 2.18, is_best: false, params: {} },
    { model_type: "arima", mae: 1.88, bias: -0.1, rmse: 2.35, is_best: false, params: {} },
  ],
  best_model: "seasonal_naive",
  job_status: "complete",
};
