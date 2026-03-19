/**
 * Cloudflare Worker: CORS Proxy + Static Site Router
 * 
 * 1. Intercepts ALL OPTIONS preflight requests → returns proper CORS headers (200 OK)
 *    This bypasses the Render/Cloudflare platform-level CORS blocking.
 * 
 * 2. For GET/POST API requests to /api/* → proxies to the backend
 *    and adds CORS headers to the response.
 * 
 * 3. Serves all static assets from the root.
 * 
 * Deploy this as a separate Cloudflare Worker bound to the same zone as
 * your static site, OR as a standalone worker at e.g. api.africa-zero.com
 * that the frontend calls instead of the Render backend directly.
 */

const BACKEND_ORIGIN = "https://africa-web-wuxs.onrender.com"
const ALLOWED_ORIGIN = "https://africa-web-1.onrender.com"

const ALLOWED_ORIGINS = new Set([
  "https://africa-web-1.onrender.com",
  "http://localhost:5173",
  "http://localhost:3000",
])

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || ""
  // Allow all known AfricaZero origins (safe: these are our own domains)
  const allowOrigin = ALLOWED_ORIGINS.has(origin) ? origin : ALLOWED_ORIGINS.values().next().value
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  }
}

function buildResponse(status, body, contentType, headers, isOptions = false) {
  const allHeaders = { ...headers }
  if (isOptions || headers["Access-Control-Allow-Origin"]) {
    // Merge CORS headers
    const cors = {
      "Access-Control-Allow-Origin": headers["Access-Control-Allow-Origin"] || ALLOWED_ORIGIN,
      "Access-Control-Allow-Credentials": "true",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
      "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
      "Access-Control-Max-Age": "86400",
      "Vary": "Origin",
    }
    Object.assign(allHeaders, cors)
  }
  return new Response(body, {
    status,
    headers: new Headers(allHeaders),
  })
}

async function handleRequest(request) {
  const url = new URL(request.url)
  const method = request.method

  // ── CORS preflight ─────────────────────────────────────────────────────────
  if (method === "OPTIONS") {
    const origin = request.headers.get("Origin") || ""
    const allowOrigin = ALLOWED_ORIGINS.has(origin) ? origin : ALLOWED_ORIGIN

    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": allowOrigin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
        "Access-Control-Max-Age": "86400",
        "Vary": "Origin",
      },
    })
  }

  // ── API proxy (/api/*) ─────────────────────────────────────────────────────
  if (url.pathname.startsWith("/api/")) {
    const backendPath = url.pathname + url.search
    const backendUrl = BACKEND_ORIGIN + backendPath

    // Build modified request to backend
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
      const origin = request.headers.get("Origin") || ""
      const allowOrigin = ALLOWED_ORIGINS.has(origin) ? origin : ALLOWED_ORIGIN

      return new Response(responseBody, {
        status: backendResponse.status,
        headers: new Headers({
          ...responseHeaders,
          "Access-Control-Allow-Origin": allowOrigin,
          "Access-Control-Allow-Credentials": "true",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
          "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
          "Access-Control-Max-Age": "86400",
          "Vary": "Origin",
        }),
      })
    } catch (err) {
      return new Response(JSON.stringify({ detail: "Backend unavailable: " + err.message }), {
        status: 502,
        headers: new Headers({
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
          "Access-Control-Allow-Credentials": "true",
          "Vary": "Origin",
        }),
      })
    }
  }

  // ── Static assets / SPA fallback ───────────────────────────────────────────
  // Forward to origin (Render static site)
  return fetch(request)
}

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request))
})
