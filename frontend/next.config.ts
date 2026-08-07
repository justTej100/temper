import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allows verification in environments that mount a read-only pre-existing .next directory.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
