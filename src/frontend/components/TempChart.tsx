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
  uncertainty,
}: {
  history: { date: string; temp_c: number }[];
  forecastDates: string[];
  forecastTemps: number[];
  modelType?: string | null;
  uncertainty?: number | null;
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
  const forecastPadding = Array(historyTemps.length).fill(null);
  const upperData = [...forecastPadding, ...forecastTemps.map((value) => value + (uncertainty ?? 0))];
  const lowerData = [...forecastPadding, ...forecastTemps.map((value) => value - (uncertainty ?? 0))];
  const lastObserved = history.at(-1);
  const targetForecast = forecastTemps.at(-1);
  const targetDate = forecastDates.at(-1);

  return (
    <section className="chart-card" aria-labelledby="temperature-chart-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Observed and predicted highs</p>
          <h2 id="temperature-chart-title">Temperature trend</h2>
        </div>
        <p>°C · dashed line indicates forecast</p>
      </div>
      <p className="chart-summary" id="temperature-chart-summary">
        {lastObserved
          ? `The latest observation was ${lastObserved.temp_c.toFixed(1)}°C on ${formatDate(lastObserved.date)}. `
          : ""}
        {targetForecast != null && targetDate
          ? `The ${modelType?.replaceAll("_", " ") || "selected"} model predicts ${targetForecast.toFixed(1)}°C for ${formatDate(targetDate)}${uncertainty ? `, with historical RMSE of ${uncertainty.toFixed(1)}°C` : ""}.`
          : "No forecast values are available yet."}
      </p>
      <div className="chart-wrap">
      <Line
        role="img"
        aria-label="Line chart of observed and forecast daily high temperatures. A text summary and data table follow."
        data={{
          labels,
          datasets: [
            {
              label: uncertainty ? `Upper uncertainty guide (+${uncertainty.toFixed(1)}°C)` : "Upper guide",
              data: upperData,
              borderColor: "rgba(0,0,0,0)",
              backgroundColor: "rgba(88, 86, 214, 0.14)",
              pointRadius: 0,
              fill: "+1",
            },
            {
              label: uncertainty ? `Lower uncertainty guide (-${uncertainty.toFixed(1)}°C)` : "Lower guide",
              data: lowerData,
              borderColor: "rgba(0,0,0,0)",
              pointRadius: 0,
            },
            {
              label: "Observed",
              data: historyData,
              borderColor: "#0066cc",
              backgroundColor: "rgba(0, 102, 204, 0.08)",
              borderWidth: 3,
              pointRadius: 0,
              tension: 0.15,
              fill: true,
              spanGaps: false,
            },
            {
              label: `Forecast${modelType ? ` (${modelType.toUpperCase()})` : ""}`,
              data: forecastData,
              borderColor: "#7c3aed",
              borderWidth: 3,
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
            legend: {
              labels: {
                color: "#6b7280",
                filter: (item) => !item.text.includes("guide"),
              },
            },
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
              ticks: { color: "#6b7280", maxTicksLimit: 10 },
              grid: { color: "rgba(128, 128, 128, 0.22)" },
            },
            y: {
              ticks: {
                color: "#6b7280",
                callback: (v) => `${v}°C`,
              },
              grid: { color: "rgba(128, 128, 128, 0.22)" },
            },
          },
        }}
      />
      </div>
      <details className="chart-data">
        <summary>View forecast data as text</summary>
        <div className="table-scroll" tabIndex={0}>
          <table>
            <caption>Forecast daily high temperatures in degrees Celsius</caption>
            <thead><tr><th scope="col">Date</th><th scope="col">Forecast</th><th scope="col">Uncertainty guide</th></tr></thead>
            <tbody>
              {forecastDates.map((date, index) => (
                <tr key={date}>
                  <th scope="row">{new Date(`${date}T12:00:00`).toLocaleDateString()}</th>
                  <td>{forecastTemps[index]?.toFixed(1)}°C</td>
                  <td>{uncertainty ? `±${uncertainty.toFixed(1)}°C RMSE` : "Not available"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
