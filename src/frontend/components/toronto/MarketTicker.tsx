import type { TorontoMarket } from "@/lib/toronto-markets";
import PolymarketMarketCard from "./PolymarketMarketCard";
import PolymarketMarketCardStatic from "./PolymarketMarketCardStatic";
import styles from "@/app/toronto/toronto.module.css";

// How many cards are laid out before the row's loop repeats. This is a
// purely visual/animation knob now — it's cheap to make this bigger because
// only one card per row is ever a real iframe (see MarketRow below).
const ROW_LENGTH = 8;

/** Alternates through the (currently 2) markets. `offset` lets each row
 * start on a different market so the two rows don't mirror each other. */
function buildRow(markets: TorontoMarket[], offset: number): TorontoMarket[] {
  if (markets.length === 0) return [];
  return Array.from(
    { length: ROW_LENGTH },
    (_, i) => markets[(i + offset) % markets.length]
  );
}

interface MarketRowProps {
  markets: TorontoMarket[];
  rowIndex: number;
  offset: number;
  direction: "left" | "right";
  durationSeconds: number;
}

function MarketRow({
  markets,
  rowIndex,
  offset,
  direction,
  durationSeconds,
}: MarketRowProps) {
  const base = buildRow(markets, offset);
  // Duplicate once so translating exactly -50% loops seamlessly.
  const looped = [...base, ...base];

  return (
    <div className={styles.row}>
      <div
        className={`${styles.track} ${
          direction === "right" ? styles.trackReverse : ""
        }`}
        style={{ animationDuration: `${durationSeconds}s` }}
      >
        {looped.map((market, i) => {
          // Only the first card in each row is a real, live embed. Every
          // other card here — including the entire looped duplicate half —
          // is the static, zero-network stand-in. That caps the whole page
          // at exactly 2 real <iframe>s, no matter how long the row gets.
          const isLive = i === 0;
          const key = `row${rowIndex}-${market.id}-${i}`;

          return isLive ? (
            <PolymarketMarketCard
              key={key}
              market={market}
              instanceKey={`row${rowIndex}-live`}
              withStructuredData
            />
          ) : (
            <PolymarketMarketCardStatic key={key} market={market} />
          );
        })}
      </div>
    </div>
  );
}

export interface MarketTickerProps {
  markets: TorontoMarket[];
}

export default function MarketTicker({ markets }: MarketTickerProps) {
  return (
    <div className={styles.ticker}>
      <MarketRow
        markets={markets}
        rowIndex={0}
        offset={0}
        direction="left"
        durationSeconds={42}
      />
      <MarketRow
        markets={markets}
        rowIndex={1}
        offset={1}
        direction="right"
        durationSeconds={48}
      />
    </div>
  );
}
