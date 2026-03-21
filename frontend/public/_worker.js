/**
 * Cloudflare Worker / Pages Function: CORS Proxy + Static File Server
 *
 * - /api/* requests: proxy to FastAPI backend + add CORS headers
 * - All other requests: serve static files via env.ASSETS (Cloudflare Pages built-in)
 *
 * Deploy Pages Function: wrangler pages deploy dist/ --project-name=africa-zero-frontend
 */

const BACKEND_ORIGIN = "https://africa-web-wuxs.onrender.com"

// Default allowed origins (fallback when env.ALLOWED_ORIGINS is not set)
const DEFAULT_ALLOWED_ORIGINS = [
  "http://localhost:5173",
  "http://localhost:3000",
  "https://ec250edc.africa-zero-frontend.pages.dev",
  "https://africa.zxqconsulting.com",
]

function parseAllowedOrigins(env) {
  // Support comma-separated list from Cloudflare Workers environment variable
  const envOrigins = env?.ALLOWED_ORIGINS || ""
  if (envOrigins) {
    return envOrigins.split(",").map((o) => o.trim()).filter(Boolean)
  }
  return DEFAULT_ALLOWED_ORIGINS
}

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || ""
  const allowedOrigins = parseAllowedOrigins(request.env)
  
  // If origin is in allowed list, return it; otherwise use first allowed origin
  const allowOrigin = allowedOrigins.includes(origin) 
    ? origin 
    : allowedOrigins[0] || "*"
  
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  }
}

async function handleRequest(request, env, ctx) {
  const url = new URL(request.url)
  const origin = request.headers.get("Origin") || ""

  // OPTIONS preflight — for both API and static file requests
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(request) })
  }

  // Proxy /api/* to FastAPI backend on Render
  if (url.pathname.startsWith("/api/")) {
    const backendPath = url.pathname + url.search
    const backendUrl = BACKEND_ORIGIN + backendPath

    const headers = {}
    request.headers.forEach((value, key) => {
      if (key.toLowerCase() === "accept-encoding") return // strip — tell backend we don't want compression
      if (key.toLowerCase() !== "host") headers[key] = value
    })

    let body = null
    if (!["GET", "HEAD"].includes(request.method)) {
      try { body = await request.text() } catch (_) {}
    }

    try {
      const backendResponse = await fetch(backendUrl, {
        method: request.method,
        headers,
        body,
        redirect: "follow",
      })

      const responseHeaders = {}
      backendResponse.headers.forEach((value, key) => {
        const lk = key.toLowerCase()
        if (lk !== "transfer-encoding" && lk !== "content-encoding") {
          responseHeaders[key] = value
        }
      })

      const responseBody = await backendResponse.text()
      return new Response(responseBody, {
        status: backendResponse.status,
        headers: { ...responseHeaders, ...corsHeaders(request) },
      })
    } catch (err) {
      return new Response(
        JSON.stringify({ detail: "Backend unavailable: " + err.message }),
        { status: 502, headers: { "Content-Type": "application/json", ...corsHeaders(request) } }
      )
    }
  }

  // Serve static files via Cloudflare Pages built-in ASSETS binding
  if (env && env.ASSETS) {
    return env.ASSETS.fetch(request)
  }

  // Development fallback (no ASSETS binding)
  return fetch(request)
}

export default {
  fetch: handleRequest,
}
