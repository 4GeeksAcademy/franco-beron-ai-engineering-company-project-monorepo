const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://backend:8001";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
