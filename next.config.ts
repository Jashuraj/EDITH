import type { NextConfig } from "next";

// Root-level endpoints used by the original EDITH HUD / mobile PWA / VNC portal.
const LEGACY = [
  "cmd", "state", "telemetry", "status", "ping", "health", "models", "models/switch", "weather",
  "emergency_stop", "emergency_resume", "mobile/config", "stream/screen", "stream/mjpeg",
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async redirects() {
    return [
      // Relative asset paths in the original pages need the /mobile/ and /vnc/ directory URLs.
      { source: "/mobile", destination: "/mobile/index.html", permanent: false },
      { source: "/vnc", destination: "/vnc/index.html", permanent: false },
    ];
  },
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/", destination: "/index.html" },
        ...LEGACY.map((p) => ({ source: `/${p}`, destination: `/api/compat/${p}` })),
        { source: "/voice/:path*", destination: "/api/compat/voice/:path*" },
        { source: "/vision/:path*", destination: "/api/compat/vision/:path*" },
        { source: "/audio/:path*", destination: "/api/compat/audio/:path*" },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
