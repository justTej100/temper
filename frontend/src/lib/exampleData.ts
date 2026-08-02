import type { MarketDetail } from "./types";

/** Static NYC high-temp demo — no backend required. */
export const EXAMPLE_MARKET: MarketDetail = {
  id: 0,
  question: "Highest temperature in New York City on August 5?",
  city_id: 0,
  city_name: "New York City",
  icao: "KLGA",
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
    { model_type: "sarimax", mae: 1.42, mape: 4.8, rmse: 1.81, is_best: true, params: {} },
    { model_type: "prophet", mae: 1.55, mape: 5.1, rmse: 1.95, is_best: false, params: {} },
    { model_type: "sarima", mae: 1.61, mape: 5.4, rmse: 2.02, is_best: false, params: {} },
    { model_type: "arimax", mae: 1.74, mape: 5.9, rmse: 2.18, is_best: false, params: {} },
    { model_type: "arima", mae: 1.88, mape: 6.3, rmse: 2.35, is_best: false, params: {} },
  ],
  best_model: "sarimax",
  job_status: "complete",
};
