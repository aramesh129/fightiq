/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://aramesh129-fightiq-api.hf.space',
  },
  images: {
    domains: ['baqnadwflpdpkyaxceaa.supabase.co'],
    unoptimized: true,
  },
}
module.exports = nextConfig
