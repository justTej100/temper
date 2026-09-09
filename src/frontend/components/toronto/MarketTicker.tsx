import type { TorontoMarket } from "@/lib/toronto-markets";
import PolymarketMarketCard from "./PolymarketMarketCard";
import styles from "@/app/toronto/toronto.module.css";

const CARDS_PER_ROW = 4;

/** Tile the (currently short) markets list up to a minimum row length so the
 * ticker always has enough cards to fill the viewport before it loops. */
function tileMarkets(markets: TorontoMarket[]): TorontoMarket[] {
  if (markets.length === 0) return [];
  const length = Math.max(CARDS_PER_ROW, markets.length);
  return Array.from({ length }, (_, i) => markets[i % markets.length]);
}

interface MarketRowProps {
  markets: TorontoMarket[];
  rowIndex: number;
  direction: "left" | "right";
  durationSeconds: number;
}

function MarketRow({
  markets,
  rowIndex,
  direction,
  durationSeconds,
}: MarketRowProps) {
  const tiled = tileMarkets(markets);
  // Duplicate the row once so translating it exactly -50% loops seamlessly.
  const looped = [...tiled, ...tiled];

  return (
    <div className={styles.row}>
      <div
        className={`${styles.track} ${
          direction === "right" ? styles.trackReverse : ""
        }`}
        style={{ animationDuration: `${durationSeconds}s` }}
      >
        {looped.map((market, i) => (
          <PolymarketMarketCard
            key={`row${rowIndex}-${market.id}-${i}`}
            market={market}
            instanceKey={`row${rowIndex}-${i}`}
            withStructuredData={rowIndex === 0 && i === 0}
          />
        ))}
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
        direction="left"
        durationSeconds={42}
      />
      <MarketRow
        markets={markets}
        rowIndex={1}
        direction="right"
        durationSeconds={48}
      />
    </div>
  );
}
