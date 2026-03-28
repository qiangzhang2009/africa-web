/**
 * JWT payload 解码工具 — 纯 JS，无需第三方库。
 * JWT payload 是 base64url 编码的 JSON，可直接用 atob 解码。
 * 用于登录后即时恢复用户状态，无需等待后端 API 调用。
 */
export interface JWTPayload {
  sub: string       // user_id
  email: string
  tier: string
  is_admin: boolean
  exp: number       // expiration timestamp
}

// 内存缓存，避免重复解码
let _cachedPayload: JWTPayload | null = null
let _cachedToken: string | null = null

function base64UrlDecode(str: string): string {
  // Replace URL-safe chars
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/')
  // Pad to multiple of 4
  while (base64.length % 4) base64 += '='
  return atob(base64)
}

export function decodeToken(token: string): JWTPayload | null {
  if (token === _cachedToken && _cachedPayload) return _cachedPayload
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payloadStr = base64UrlDecode(parts[1])
    const payload = JSON.parse(payloadStr) as JWTPayload
    // Check expiration
    if (payload.exp && Date.now() / 1000 > payload.exp) {
      return null
    }
    _cachedToken = token
    _cachedPayload = payload
    return payload
  } catch {
    return null
  }
}

export function clearTokenCache() {
  _cachedToken = null
  _cachedPayload = null
}
