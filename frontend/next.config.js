// Load environment variables from root directory
require('dotenv').config({ path: '../.env' })

const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true"
})

// Only enable PWA if not building in Docker
const withPWA = process.env.DOCKER_BUILD ? 
  (config) => config :  // Pass through config without PWA
  require("next-pwa")({
    dest: "public",
    disable: process.env.NODE_ENV === "development"
  })

module.exports = withBundleAnalyzer(
  withPWA({
    reactStrictMode: true,
    images: {
      remotePatterns: [
        {
          protocol: "http",
          hostname: "localhost"
        },
        {
          protocol: "http",
          hostname: "127.0.0.1"
        },
        {
          protocol: "https",
          hostname: "**"
        }
      ]
    },
    experimental: {
      serverComponentsExternalPackages: ["sharp", "onnxruntime-node"]
    }
  })
)