import { afterEach, describe, expect, it, vi } from "vitest";

describe("frontend API configuration", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("uses and normalizes a production API URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://temperature-api.example/");
    const { API_DOCS_URL, API_URL } = await import("@/lib/api");
    expect(API_URL).toBe("https://temperature-api.example");
    expect(API_DOCS_URL).toBe("https://temperature-api.example/docs");
  });

  it("retains a safe local development default", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    const { API_URL } = await import("@/lib/api");
    expect(API_URL).toBe("http://localhost:8000");
  });
});
