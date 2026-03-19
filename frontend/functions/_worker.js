/**
 * Cloudflare Pages Function: CORS Proxy + API Gateway
 *
 * All requests to /api/* are proxied to the FastAPI backend on Render.com,
 * with CORS headers added for browser access. Same-origin routing means no
 * preflight, no CORS drama, and no 10s Render timeout for the browser.
 *
 * Deploy: push to GitHub → Cloudflare Pages auto-deploys.
 * Backend remains at: https://africa-web-wuxs.onrender.com
 */

const BACKEND_ORIGIN = "https://africa-web-wuxs.onrender.com"

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || ""
  const allowOrigin = origin.startsWith("https://")
    ? origin
    : "https://ec250edc.africa-zero-frontend.pages.dev"
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  }
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url)

  // OPTIONS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(request) })
  }

  // Proxy /api/* to FastAPI backend
  if (url.pathname.startsWith("/api/")) {
    const backendPath = url.pathname + url.search
    const backendUrl = BACKEND_ORIGIN + backendPath

    const headers = {}
    request.headers.forEach((value, key) => {
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

  // All other requests → serve static files (handled by Pages default)
  return fetch(request)
}
