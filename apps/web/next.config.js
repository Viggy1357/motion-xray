/** @type {import('next').NextConfig} */
// Motion X Ray — Next.js config (STRUCTURE-ONLY scaffold).
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // Next 15.5.x setting (renamed to proxyClientMaxBodySize only in v16 — do NOT
    // use the v16 name here; this repo pins next@15.5.28). The default 10MB cap
    // truncated raw-body uploads through the /api rewrite, surfacing as API 408s.
    //
    // Value is a NUMBER OF BYTES (not a string like "100mb") to avoid decimal
    // (MB=10^6) vs binary (MiB=2^20) parsing ambiguity: 100 * 1024 * 1024 bytes
    // is exactly 100 MiB, matching the API's authoritative MAX_UPLOAD_MB=100 gate
    // (max_mb * 1024 * 1024 in services/api/app/uploads.py). The API remains the
    // enforcing limit; this only stops Next from truncating before the proxy.
    middlewareClientMaxBodySize: 100 * 1024 * 1024,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.API_INTERNAL_URL || "http://api:8000"}/v1/:path*` }];
  },
};

module.exports = nextConfig;
