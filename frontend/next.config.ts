import type { NextConfig } from "next";

const API_PORT = process.env.API_PORT || process.env.NEXT_PUBLIC_API_PORT || "8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/copilotkit',
        destination: `http://127.0.0.1:${API_PORT}/api/copilotkit/`,
      },
      {
        source: '/api/:path*',
        destination: `http://127.0.0.1:${API_PORT}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
