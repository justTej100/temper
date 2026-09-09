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
// Until then the ticker only ever knows about these two seed markets and
// alternates between them — see MarketTicker for why only 2 of these ever
// become real <iframe> embeds no matter how many cards are on screen.
export const torontoMarkets: TorontoMarket[] = [
  {
    id: "highest-temperature-in-toronto-on-september-10-2026-21c",
    question:
      "Will the highest temperature in Toronto be 21\u00b0C on September 10?",
    yesPct: 0,
    noPct: 100,
    embedSlug: "highest-temperature-in-toronto-on-september-10-2026-21c",
    eventUrl:
      "https://polymarket.com/event/highest-temperature-in-toronto-on-september-10-2026",
  },
  {
    id: "highest-temperature-in-toronto-on-september-11-2026-18corbelow",
    question:
      "Will the highest temperature in Toronto be 18\u00b0C or below on September 11?",
    yesPct: 2,
    noPct: 98,
    embedSlug:
      "highest-temperature-in-toronto-on-september-11-2026-18corbelow",
    eventUrl:
      "https://polymarket.com/event/highest-temperature-in-toronto-on-september-11-2026",
  },
];
