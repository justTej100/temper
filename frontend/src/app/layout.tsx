import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Temperature Predictor",
  description: "Daily-high temperature forecasting for active Polymarket markets",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col antialiased">
        {children}
        <footer className="mt-auto border-t border-border py-8 text-center text-sm text-muted">
          <div className="mx-auto max-w-5xl px-6">
            <p>Transparent baselines · ARIMA · SARIMA · Prophet — vs Polymarket weather odds</p>
            <p className="mt-1">
              Historical data: Open-Meteo · Markets:{" "}
              <a
                href="https://polymarket.com/weather/high-temperature"
                className="text-accent no-underline hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                Polymarket
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
