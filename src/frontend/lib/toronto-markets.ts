export interface TorontoMarket {
  /** Stable id used for the Polymarket embed slug and DOM ids. */
  id: string;
  question: string;
  yesPct: number;
  noPct: number;
  /** The `market=` query param Polymarket's embed endpoint expects. */
  embedSlug: string;
  eventUrl: string;
}

// TODO(backend): once the market-selection service exists, this should be
// replaced by a fetch of whatever markets it chooses for the Toronto page.
// Until then every ticker slot falls back to the single seed market below.
export const torontoMarkets: TorontoMarket[] = [
  {
    id: "highest-temperature-in-toronto-on-september-10-2026-22c",
    question:
      "Will the highest temperature in Toronto be 22\u00b0C on September 10?",
    yesPct: 1,
    noPct: 99,
    embedSlug: "highest-temperature-in-toronto-on-september-10-2026-22c",
    eventUrl:
      "https://polymarket.com/event/highest-temperature-in-toronto-on-september-10-2026",
  },
];
