/**
 * Vercel Edge Middleware: CORS Proxy + API Gateway
 *
 * Intercepts /api/* requests from the browser and proxies them to the
 * FastAPI backend on Render.com. Since the proxy runs on the same
 * Vercel Edge Network origin as the static frontend, there are NO
 * CORS issues for the browser — same origin, no preflight.
 *
 * The browser sees:  GET /api/v1/calculate/import-cost  →  Vercel Edge (same origin)
 * Vercel Edge sees:  GET /api/v1/calculate/import-cost → https://africa-web-wuxs.onrender.com/api/v1/...
 */

const BACKEND_ORIGIN = "https://africa-web-wuxs.onrender.com"

export const config = {
  matcher: ["/api/:path*"],
}

export default async function middleware(request: Request) {
  const url = new URL(request.url)

  // Proxy /api/* to FastAPI backend
  const backendPath = url.pathname + url.search
  const backendUrl = BACKEND_ORIGIN + backendPath

  const headers: Record<string, string> = {}
  request.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "host") headers[key] = value
  })

  let body: string | null = null
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

    const responseHeaders: Record<string, string> = {}
    backendResponse.headers.forEach((value, key) => {
      const lk = key.toLowerCase()
      if (lk !== "transfer-encoding" && lk !== "content-encoding") {
        responseHeaders[key] = value
      }
    })

    // Browser is same-origin — allow credentials + specific origin
    const origin = request.headers.get("Origin") || ""
    const allowOrigin = origin.startsWith("https://") ? origin : "https://ec250edc.africa-zero-frontend.pages.dev"

    responseHeaders["Access-Control-Allow-Origin"] = allowOrigin
    responseHeaders["Access-Control-Allow-Credentials"] = "true"
    responseHeaders["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD"
    responseHeaders["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept, Origin"
    responseHeaders["Access-Control-Max-Age"] = "86400"
    responseHeaders["Vary"] = "Origin"

    const responseBody = await backendResponse.text()
    return new Response(responseBody, {
      status: backendResponse.status,
      headers: responseHeaders,
    })
  } catch (err) {
    const origin = request.headers.get("Origin") || ""
    const allowOrigin = origin.startsWith("https://") ? origin : "https://ec250edc.africa-zero-frontend.pages.dev"
    return new Response(
      JSON.stringify({ detail: "Backend unavailable: " + (err as Error).message }),
      {
        status: 502,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": allowOrigin,
          "Access-Control-Allow-Credentials": "true",
          "Vary": "Origin",
        },
      }
    )
  }
}
