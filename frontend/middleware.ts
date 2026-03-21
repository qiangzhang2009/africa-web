// Vercel Edge Middleware - handles CORS at Vercel edge level
// Uses native Web API only (no Next.js, works with Vite SPA deployments)
//
// Flow:
//   OPTIONS → return CORS headers at edge (bypasses OnRender cold-start entirely)
//   GET/POST/PUT/DELETE → Vercel rewrites to OnRender (vercel.json handles this)

const ALLOWED_ORIGINS = [
  'https://africa.zxqconsulting.com',
  'https://global2china.zxqconsulting.com',
  'https://zero.zxqconsulting.com',
  'https://www.zxqconsulting.com',
]

export function middleware(request: Request) {
  const origin = request.headers.get('origin') ?? ''
  const isAllowedOrigin = ALLOWED_ORIGINS.includes(origin)
  const effectiveOrigin = isAllowedOrigin ? origin : ALLOWED_ORIGINS[0]

  // Handle OPTIONS preflight at Vercel edge — returns immediately
  // This fixes the cold-start delay that was causing first-try failures.
  // OnRender free tier takes ~10s to wake up; the OPTIONS handler we added
  // at the backend layer helps but is still blocked by Cloudflare WAF,
  // so we handle it entirely at Vercel before the request reaches OnRender.
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': effectiveOrigin,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
        'Access-Control-Max-Age': '86400',
      },
    })
  }

  // For actual requests (GET/POST/PUT/DELETE):
  // Return undefined so Vercel continues with the vercel.json rewrite to OnRender.
  // The CORS headers from vercel.json's ["/api/(.*)"] block will be used:
  //   Access-Control-Allow-Origin: *
  // Note: browsers reject * when fetch uses credentials mode (keepalive: true in SDK).
  // The tracking SDK uses sendBeacon with keepalive, which triggers credentials mode.
  // For AfricaZero's business API (calculateImportCost etc.), credentials mode is
  // not strictly required — the critical fix is OPTIONS handling above.
  return
}

export const config = {
  matcher: ['/api/:path*'],
}
