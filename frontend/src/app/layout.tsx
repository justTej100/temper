import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Temperature Predictor",
    template: "%s · Temperature Predictor",
  },
  description: "Transparent daily high-temperature forecasts and calibrated Polymarket comparisons.",
  applicationName: "Temperature Predictor",
  icons: { icon: "/icon.svg" },
  openGraph: {
    title: "Temperature Predictor",
    description: "Daily high-temperature forecasts with uncertainty and model transparency.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col antialiased">
        {children}
        <footer className="mt-auto border-t border-border py-8 text-center text-sm text-muted">
          <div className="shell">
            <p>Historical observations from Open-Meteo · Market data from Polymarket</p>
            <p className="mt-1">
              Estimates include uncertainty and can be wrong. Not financial advice.{" "}
              <a
                href="https://polymarket.com/weather/high-temperature"
                className="text-accent no-underline hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                View source markets
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
