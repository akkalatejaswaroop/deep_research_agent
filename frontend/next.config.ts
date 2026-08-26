import type { NextConfig } from "next";

const API_PORT = process.env.API_PORT || process.env.NEXT_PUBLIC_API_PORT || "8000";

const nextConfig: NextConfig = {
  images: { unoptimized: true },
  // Do NOT use static export in development — it breaks rewrites/SSE proxy
  output: process.env.NODE_ENV === "production" ? "export" : undefined,
  async rewrites() {
    // Proxy all /api/* requests to FastAPI backend.
    // X-Accel-Buffering: no is set by the backend; Next.js passes it through.
    return [
      {
        source: "/api/:path*",
        destination: `http://127.0.0.1:${API_PORT}/api/:path*`,
      },
      {
        source: "/health",
        destination: `http://127.0.0.1:${API_PORT}/health`,
      },
    ];
  },
  // Allow larger bodies for SSE streams
  experimental: {},
};

export default nextConfig;
