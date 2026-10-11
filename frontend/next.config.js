/** @type {import('next').NextConfig} */
const backendApiUrl =
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

const cleanBackendUrl = backendApiUrl.replace(/\/api\/v1\/?$/, '');

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${cleanBackendUrl}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
