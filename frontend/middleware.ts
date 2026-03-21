// Vercel Edge Middleware - handles CORS preflight at Vercel edge
// Uses native Web API (no Next.js dependency needed for Vite projects)

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

  // Handle OPTIONS preflight at Vercel edge — returns immediately, bypasses OnRender
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

  // Pass non-OPTIONS requests through to OnRender (via vercel.json rewrite)
  // Then intercept the response to fix CORS headers (replace * with correct origin)
  const response = await fetch(request)

  // Clone response to modify headers
  const newHeaders = new Headers(response.headers)
  newHeaders.set('Access-Control-Allow-Origin', effectiveOrigin)
  newHeaders.set('Access-Control-Allow-Credentials', 'true')

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  })
}

export const config = {
  matcher: ['/api/:path*'],
}
