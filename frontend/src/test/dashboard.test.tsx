import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import { BucketCompare } from "@/components/BucketCompare";
import { TempChart } from "@/components/TempChart";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    listMarkets: vi.fn(),
    listEdges: vi.fn(),
    triggerSync: vi.fn(),
    pollJob: vi.fn(),
  };
});

const market = {
  id: 1,
  question: "Highest temperature in Austin on August 8?",
  city_name: "Austin",
  temp_type: "high" as const,
  target_date: "2026-08-08",
  volume: 1000,
  url: "https://polymarket.com/example",
  top_bucket_label: "100°F",
  top_bucket_price: 0.42,
  max_edge: 0.09,
  best_model: "seasonal_naive",
  point_forecast_c: 37.4,
};

describe("prediction dashboard", () => {
  beforeEach(() => {
    vi.mocked(api.listEdges).mockResolvedValue([]);
    vi.mocked(api.listMarkets).mockResolvedValue([market]);
  });

  it("shows loading then a forecast and supports filtering", async () => {
    render(<HomePage />);
    expect(screen.getByLabelText("Loading market forecasts")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Austin" })).toBeInTheDocument();
    expect(screen.getByText("37.4°C")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search city or date"), { target: { value: "Boston" } });
    expect(screen.getByRole("heading", { name: "No matching forecasts" })).toBeInTheDocument();
  });

  it("shows an actionable error", async () => {
    vi.mocked(api.listMarkets).mockRejectedValueOnce(new Error("Network unavailable"));
    render(<HomePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("explains the empty state", async () => {
    vi.mocked(api.listMarkets).mockResolvedValueOnce([]);
    render(<HomePage />);
    expect(await screen.findByRole("heading", { name: "No active markets yet" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Refresh markets" }).length).toBeGreaterThan(0);
  });

  it("announces live sync progress", async () => {
    vi.mocked(api.triggerSync).mockResolvedValue({ job_id: 4, status: "queued" });
    vi.mocked(api.pollJob).mockImplementation(async (_id, progress) => progress?.("training"));
    render(<HomePage />);
    await screen.findByRole("heading", { name: "Austin" });
    fireEvent.click(screen.getAllByRole("button", { name: "Refresh markets" })[0]);
    await waitFor(() => expect(screen.getByText("Catalog refresh complete")).toBeInTheDocument());
  });
});

describe("accessible forecast data", () => {
  it("provides chart summary and a text table", () => {
    render(
      <TempChart
        history={[{ date: "2026-08-01", temp_c: 31 }]}
        forecastDates={["2026-08-02"]}
        forecastTemps={[33]}
        modelType="seasonal_naive"
        uncertainty={1.5}
      />
    );
    expect(screen.getByText(/predicts 33.0°C/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Forecast daily high/ })).toBeInTheDocument();
  });

  it("labels non-color probability differences", () => {
    render(
      <BucketCompare buckets={[{ id: 1, label: "33°C", temp_c: 33, yes_price: 0.3, model_prob: 0.4, edge: 0.1 }]} />
    );
    expect(screen.getByText(/notable disagreement/)).toBeInTheDocument();
  });
});
