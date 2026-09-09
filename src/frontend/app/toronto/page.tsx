import type { Metadata } from "next";
import MarketTicker from "@/components/toronto/MarketTicker";
import { torontoMarkets } from "@/lib/toronto-markets";
import styles from "./toronto.module.css";

export const metadata: Metadata = {
  title: "Toronto | Temperature Predictor",
  description: "Live temperature prediction markets for Toronto.",
};

export default function TorontoPage() {
  return (
    <div className={styles.page}>
      <header className={styles.bandTop} aria-hidden="true" />

      <div className={styles.gap} aria-hidden="true" />

      <section
        className={styles.content}
        aria-label="Toronto temperature prediction markets"
      >
        <MarketTicker markets={torontoMarkets} />
      </section>

      <div className={styles.gap} aria-hidden="true" />

      <footer className={styles.bandBottom} aria-hidden="true" />
    </div>
  );
}
