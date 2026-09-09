import type { TorontoMarket } from "@/lib/toronto-markets";
import styles from "@/app/toronto/toronto.module.css";

export interface PolymarketMarketCardProps {
  market: TorontoMarket;
  /** Disambiguates DOM ids when the same market is rendered more than once
   * (e.g. duplicated for the seamless marquee loop, or reused as a
   * placeholder in multiple ticker slots). */
  instanceKey: string;
  /** Only the "real" (non-cloned) instance of a market should emit the
   * JSON-LD block, so we don't spam the page with duplicate structured
   * data when a market is repeated to fill the ticker. */
  withStructuredData?: boolean;
}

export default function PolymarketMarketCard({
  market,
  instanceKey,
  withStructuredData = false,
}: PolymarketMarketCardProps) {
  const figureId = `polymarket-${market.id}-${instanceKey}`;
  const iframeSrc = `https://embed.polymarket.com/market?market=${market.embedSlug}&theme=dark&liveactivity=true&border=true&height=300`;

  return (
    <div className={styles.card}>
      {withStructuredData && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebPage",
              name: market.question,
              description: `Prediction market: Yes ${market.yesPct}% \u00b7 No ${market.noPct}% on Polymarket.`,
              url: market.eventUrl,
              publisher: {
                "@type": "Organization",
                name: "Polymarket",
                url: "https://polymarket.com",
              },
            }),
          }}
        />
      )}

      <figure
        className={`polymarket-embed ${styles.figure}`}
        id={figureId}
        aria-label={`Polymarket prediction market: ${market.question}`}
        itemScope
        itemType="https://schema.org/WebPage"
      >
        <div className={styles.frame}>
          <iframe
            title={`${market.question} \u2014 Polymarket Prediction Market`}
            src={iframeSrc}
            width={400}
            height={300}
            frameBorder={0}
            {...{ allowtransparency: "true" }}
          />
        </div>

        <a
          href={market.eventUrl}
          aria-label="View on Polymarket"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.link}
        />

        <figcaption className={styles.srOnly}>
          <strong>{market.question}</strong>
          <br />
          Yes {market.yesPct}% &middot; No {market.noPct}%
          <br />
          <a href={market.eventUrl}>
            View full market &amp; trade on Polymarket
          </a>
        </figcaption>
      </figure>
    </div>
  );
}
