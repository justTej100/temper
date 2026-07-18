import type { Metadata } from "next";
import { Header } from "@/components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "PriceForecast",
  description: "On-demand product price dip prediction",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col antialiased">
        {children}
        <footer className="mt-auto border-t border-border py-8 text-center text-sm text-muted">
          <div className="mx-auto max-w-5xl px-6">
            <p>Models: ARIMA · SARIMA · ARIMAX · SARIMAX · Prophet · GARCH</p>
            <p className="mt-1">
              <a
                href="http://localhost:5000"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent no-underline hover:underline"
              >
                MLflow Experiments
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
