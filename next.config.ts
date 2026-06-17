import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Output standalone for Vercel (Vercel auto-detects, but keep config explicit)
  // No special config needed for Vercel deployment
};

export default nextConfig;
