import { NextRequest, NextResponse } from 'next/server'

// Allowed cross-origin domains
const ALLOWED_ORIGINS = [
  'https://africa.zxqconsulting.com',
  'https://global2china.zxqconsulting.com',
  'https://zero.zxqconsulting.com',
  'https://www.zxqconsulting.com',
]

export const config = {
  matcher: ['/api/:path*'],
}

export function middleware(request: NextRequest) {
  const origin = request.headers.get('origin') ?? ''
  const isAllowedOrigin = ALLOWED_ORIGINS.includes(origin)
  const effectiveOrigin = isAllowedOrigin ? origin : ALLOWED_ORIGINS[0]

  // Handle preflight OPTIONS at Vercel edge — bypasses OnRender rewrite entirely
  if (request.method === 'OPTIONS') {
    return new NextResponse(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': effectiveOrigin,
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
        'Access-Control-Max-Age': '600',
      },
    })
  }

  // Pass through to OnRender for actual requests
  const response = NextResponse.next()
  response.headers.set('Access-Control-Allow-Origin', effectiveOrigin)
  response.headers.set('Access-Control-Allow-Credentials', 'true')
  return response
}
