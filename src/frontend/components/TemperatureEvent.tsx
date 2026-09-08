"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import TemperatureMarket from "./TemperatureMarket";

const MARKET_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#22c55e",
  "#f59e0b",
  "#a855f7",
  "#06b6d4",
  "#ec4899",
];

export interface TemperatureMarketData {
  id: string;
  label: string;
  probability: number;
  history: {
    time: string;
    probability: number;
  }[];
}

export interface TemperatureEventProps {
  location: string;
  date: string;
  markets: TemperatureMarketData[];
}

export default function TemperatureEvent({
  location,
  date,
  markets,
}: TemperatureEventProps) {
  // Recharts needs one row per timestamp with a column per market.
  const chartData = markets.length
    ? markets[0].history.map((point, index) => {
        const dataPoint: Record<string, string | number> = {
          time: point.time,
        };

        markets.forEach((market) => {
          const historyPoint = market.history[index];

          if (historyPoint) {
            dataPoint[market.id] = historyPoint.probability;
          }
        });

        return dataPoint;
      })
    : [];

  return (
    <div className="temperature-event">
      <div className="temperature-event-header">
        <div>
          <h2>Temperature on {date}</h2>
          <p>{location}</p>
        </div>
      </div>

      <div className="temperature-event-chart">
        <ResponsiveContainer width="100%" height={350}>
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" />

            <XAxis dataKey="time" />

            <YAxis domain={[0, 100]} tickFormatter={(value) => `${value}%`} />

            <Tooltip
              formatter={(value, name) => [
                `${value}%`,
                markets.find((market) => market.id === name)?.label ?? name,
              ]}
            />

            {markets.map((market, index) => (
              <Line
                key={market.id}
                type="monotone"
                dataKey={market.id}
                name={market.id}
                stroke={MARKET_COLORS[index % MARKET_COLORS.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="temperature-event-markets">
        {markets.map((market, index) => (
          <TemperatureMarket
            key={market.id}
            id={market.id}
            label={market.label}
            probability={market.probability}
            color={MARKET_COLORS[index % MARKET_COLORS.length]}
          />
        ))}
      </div>
    </div>
  );
}
