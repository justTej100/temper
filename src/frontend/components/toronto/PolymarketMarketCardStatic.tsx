import type { TorontoMarket } from "@/lib/toronto-markets";
import styles from "@/app/toronto/toronto.module.css";

/**
 * The ticker only ever loads two real <iframe> embeds (one live market per
 * row — see MarketTicker). Every other visible card, including the whole
 * duplicated half used to loop the scroll seamlessly, renders this instead:
 * a plain summary of the same market with no iframe and no network request.
 *
 * It's marked aria-hidden because it's decorative background filler, not
 * new information — the real, accessible widget for each market is the one
 * live card. (Eventually these get blurred into a background texture;
 * for now they're left plain.)
 */
export default function PolymarketMarketCardStatic({
  market,
}: {
  market: TorontoMarket;
}) {
  return (
    <div className={styles.card} aria-hidden="true">
      <div className={styles.staticFrame}>
        <p className={styles.staticQuestion}>{market.question}</p>
        <div className={styles.staticOdds}>
          <span className={styles.staticYes}>Yes {market.yesPct}%</span>
          <span className={styles.staticNo}>No {market.noPct}%</span>
        </div>
        <span className={styles.staticBrand}>Polymarket</span>
      </div>
    </div>
  );
}
