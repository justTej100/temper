"use client";

import Link from "next/link";
import { BucketCompare } from "@/components/BucketCompare";
import { Header } from "@/components/Header";
import { ModelComparisonTable } from "@/components/ModelComparisonTable";
import { TempChart } from "@/components/TempChart";
import { EXAMPLE_MARKET } from "@/lib/exampleData";

export default function ExamplePage() {
  const data = EXAMPLE_MARKET;
  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 pb-12">
        <p className="pt-6">
          <Link href="/" className="text-accent no-underline hover:underline">
            ← Markets
          </Link>
        </p>
        <div className="mt-4 rounded-lg border border-accent/40 bg-accent/10 px-4 py-3 text-sm text-accent">
          Example market — static demo data. No training or Polymarket sync.
        </div>
        <div className="py-6">
          <h1 className="text-2xl font-bold sm:text-3xl">{data.question}</h1>
          <p className="mt-2 text-sm text-muted">
            {data.city_name} ({data.icao}) · model pick {data.point_forecast_c}°C
          </p>
        </div>
        <TempChart
          history={data.history}
          forecastDates={data.forecast_dates}
          forecastTemps={data.forecast_temps}
          modelType={data.best_model}
        />
        <BucketCompare buckets={data.buckets} />
        <ModelComparisonTable
          models={data.model_comparison}
          bestModel={data.best_model}
        />
      </main>
    </>
  );
}
