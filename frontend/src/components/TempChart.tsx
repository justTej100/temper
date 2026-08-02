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
  });
}

export function TempChart({
  history,
  forecastDates,
  forecastTemps,
  modelType,
}: {
  history: { date: string; temp_c: number }[];
  forecastDates: string[];
  forecastTemps: number[];
  modelType?: string | null;
}) {
  const historyDates = history.map((p) => p.date);
  const historyTemps = history.map((p) => p.temp_c);
  const labels = [...historyDates, ...forecastDates].map(formatDate);
  const historyData = [...historyTemps, ...Array(forecastDates.length).fill(null)];
  const forecastData = [
    ...Array(Math.max(historyTemps.length - 1, 0)).fill(null),
    historyTemps[historyTemps.length - 1] ?? null,
    ...forecastTemps,
  ];

  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <Line
        data={{
          labels,
          datasets: [
            {
              label: "Observed",
              data: historyData,
              borderColor: "#60a5fa",
              backgroundColor: "rgba(96, 165, 250, 0.1)",
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.15,
              fill: true,
              spanGaps: false,
            },
            {
              label: `Forecast${modelType ? ` (${modelType.toUpperCase()})` : ""}`,
              data: forecastData,
              borderColor: "#34d399",
              borderWidth: 2,
              borderDash: [6, 4],
              pointRadius: 0,
              tension: 0.25,
              fill: false,
              spanGaps: false,
            },
          ],
        }}
        options={{
          responsive: true,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { labels: { color: "#e8eaed" } },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  if (ctx.parsed.y === null) return "";
                  return `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}°C`;
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
                callback: (v) => `${v}°C`,
              },
              grid: { color: "#2e3348" },
            },
          },
        }}
      />
    </div>
  );
}
