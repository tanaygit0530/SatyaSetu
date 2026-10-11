const path = require('path');

const backendApiUrl =
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'https://satyasetu-xvk9.onrender.com';

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
  webpack: (config) => {
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      '@': path.resolve(__dirname),
    };
    return config;
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
