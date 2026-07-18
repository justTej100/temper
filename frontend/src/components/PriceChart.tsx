"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { Forecast, PricePoint } from "@/lib/types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler
);

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function PriceChart({
  history,
  forecast,
}: {
  history: PricePoint[];
  forecast: Forecast;
}) {
  const historyDates = history.map((p) => p.date);
  const historyPrices = history.map((p) => p.price);
  const forecastDates = forecast.forecast_dates;
  const forecastPrices = forecast.forecast_prices;

  const allLabels = [...historyDates, ...forecastDates].map(formatDate);

  const historyData = [
    ...historyPrices,
    ...Array(forecastDates.length).fill(null),
  ];

  const forecastData = [
    ...Array(Math.max(historyPrices.length - 1, 0)).fill(null),
    historyPrices[historyPrices.length - 1] ?? null,
    ...forecastPrices,
  ];

  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <Line
        data={{
          labels: allLabels,
          datasets: [
            {
              label: "Price History",
              data: historyData,
              borderColor: "#60a5fa",
              backgroundColor: "rgba(96, 165, 250, 0.1)",
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.1,
              fill: true,
              spanGaps: false,
            },
            {
              label: `Forecast (${forecast.model_type.toUpperCase()})`,
              data: forecastData,
              borderColor: "#ff9900",
              borderWidth: 2,
              borderDash: [6, 4],
              pointRadius: 0,
              tension: 0.3,
              fill: false,
              spanGaps: false,
            },
          ],
        }}
        options={{
          responsive: true,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              labels: { color: "#e8eaed" },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  if (ctx.parsed.y === null) return "";
                  return `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`;
                },
              },
            },
          },
          scales: {
            x: {
              ticks: { color: "#9aa0b4", maxTicksLimit: 12 },
              grid: { color: "#2e3348" },
            },
            y: {
              ticks: {
                color: "#9aa0b4",
                callback: (v) => `$${v}`,
              },
              grid: { color: "#2e3348" },
            },
          },
        }}
      />
    </div>
  );
}
