/** @type {import('next').NextConfig} */
// Motion X Ray — Next.js config (STRUCTURE-ONLY scaffold).
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_INTERNAL_URL || "http://api:8000"}/v1/:path*` }];
  },
};

module.exports = nextConfig;
