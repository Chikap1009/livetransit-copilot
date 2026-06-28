// Central runtime config for the browser-facing URLs.
// Defaults target the local dev stack; in production these are overridden by Vercel
// environment variables (NEXT_PUBLIC_* are inlined into the client bundle at build time):
//   NEXT_PUBLIC_API_BASE   = https://livetransit.duckdns.org
//   NEXT_PUBLIC_TILES_BASE = https://livetransit.duckdns.org/tiles
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export const TILES_BASE =
  process.env.NEXT_PUBLIC_TILES_BASE ?? 'http://localhost:3000';

// WebSocket URL derived from the API base (http -> ws, https -> wss).
export const WS_URL = API_BASE.replace(/^http/, 'ws') + '/ws/vehicles';
