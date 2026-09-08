import type { CSSProperties } from "react";

export interface TemperatureMarketProps {
  id: string;
  label: string;
  probability: number;
  color: string;
}

export default function TemperatureMarket({
  id,
  label,
  probability,
  color,
}: TemperatureMarketProps) {
  return (
    <div
      className="temperature-market"
      data-market-id={id}
      data-label={label}
      data-probability={probability}
      style={
        {
          "--market-color": color,
        } as CSSProperties
      }
    >
      <div className="temperature-market-label">
        <span
          className="temperature-market-dot"
          style={{ backgroundColor: color }}
        />
        <span>{label}</span>
      </div>

      <span className="temperature-market-probability">{probability}%</span>
    </div>
  );
}
