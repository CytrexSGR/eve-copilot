/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  basePath: '/ectmap',
  assetPrefix: '/ectmap',
  output: 'standalone',
  experimental: {
    turbo: {},
  },
};

export default nextConfig;
