import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

vi.mock("react-chartjs-2", () => ({
  Line: (props: { "aria-label"?: string }) => (
    <div role="img" aria-label={props["aria-label"] || "Temperature chart"} />
  ),
}));
