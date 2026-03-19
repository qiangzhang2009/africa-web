/**
 * Cloudflare Worker: CORS Proxy + Static Site Router
 *
 * 1. OPTIONS preflight → returns CORS headers (bypasses Render free-tier CORS block)
 * 2. GET/POST /api/* → proxies to FastAPI backend + adds CORS headers
 *
 * Deploy: from `africa-zero/frontend` run `npx wrangler deploy`
 * Env vars (Dashboard → Settings → Variables): BACKEND_ORIGIN, ALLOWED_ORIGINS, WORKER_ORIGIN
 */

function readConfig(env) {
  const BACKEND_ORIGIN = (
    env.BACKEND_ORIGIN ||
    env.ASSETS_URL ||
    "https://africa-web-wuxs.onrender.com"
  ).replace(/\/$/, "")

  const ALLOWED_ORIGINS = new Set(
    (env.ALLOWED_ORIGINS || "https://africa-web-1.onrender.com")
      .split(",")
      .map((o) => o.trim())
      .filter(Boolean)
  )

  const WORKER_ORIGIN = (
    env.WORKER_ORIGIN ||
    "https://africa-web-cors-proxy"
  ).replace(/\/$/, "")

  return { BACKEND_ORIGIN, ALLOWED_ORIGINS, WORKER_ORIGIN }
}

function resolveAllowOrigin(request, ALLOWED_ORIGINS, WORKER_ORIGIN) {
  const origin = request.headers.get("Origin") || ""
  return ALLOWED_ORIGINS.has(origin)
    ? origin
    : (ALLOWED_ORIGINS.values().next().value || WORKER_ORIGIN)
}

function corsHeaders(allowOrigin) {
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  }
}

async function handleRequest(request, env) {
  const { BACKEND_ORIGIN, ALLOWED_ORIGINS, WORKER_ORIGIN } = readConfig(env)
  const url = new URL(request.url)
  const method = request.method

  if (method === "OPTIONS") {
    const allowOrigin = resolveAllowOrigin(request, ALLOWED_ORIGINS, WORKER_ORIGIN)
    return new Response(null, {
      status: 204,
      headers: corsHeaders(allowOrigin),
    })
  }

  if (url.pathname.startsWith("/api/")) {
    const backendPath = url.pathname + url.search
    const backendUrl = BACKEND_ORIGIN + backendPath

    const headers = {}
    request.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "host") {
        headers[key] = value
      }
    })

    let body = null
    if (method !== "GET" && method !== "HEAD") {
      try {
        body = await request.text()
      } catch (_) {}
    }

    try {
      const backendResponse = await fetch(backendUrl, {
        method,
        headers,
        body,
        redirect: "follow",
      })

      const responseHeaders = {}
      backendResponse.headers.forEach((value, key) => {
        if (key.toLowerCase() !== "transfer-encoding") {
          responseHeaders[key] = value
        }
      })

      const responseBody = await backendResponse.text()
      const allowOrigin = resolveAllowOrigin(request, ALLOWED_ORIGINS, WORKER_ORIGIN)

      return new Response(responseBody, {
        status: backendResponse.status,
        headers: new Headers({
          ...responseHeaders,
          ...corsHeaders(allowOrigin),
        }),
      })
    } catch (err) {
      return new Response(JSON.stringify({ detail: "Backend unavailable: " + err.message }), {
        status: 502,
        headers: new Headers({
          "Content-Type": "application/json",
          ...corsHeaders(WORKER_ORIGIN),
        }),
      })
    }
  }

  return fetch(request)
}

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env)
  },
}
