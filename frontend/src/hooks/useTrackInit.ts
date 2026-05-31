import { useEffect } from 'react'

const TENANT_SLUG = 'africa'

declare global {
  interface Window {
    zxqTrack?: {
      init: (opts: { tenant: string; apiUrl?: string; debug?: boolean; autoTrack?: boolean }) => void
      pageView: (data?: Record<string, unknown>) => void
      click: (label: string, category?: string, data?: Record<string, unknown>) => void
      form: (name: string, success: boolean, fields?: Record<string, unknown>) => void
      tool: (name: string, action: string, data?: Record<string, unknown>) => void
      ai: (analysisType: string, action: string, params?: Record<string, unknown>) => void
      scroll: (depth: number) => void
      custom: (name: string, data?: Record<string, unknown>) => void
      track: (type: string, data?: Record<string, unknown>) => void
      getVisitorId: () => string
      getSessionId: () => string
      getPageDuration: () => number
      getSessionDuration: () => number
      initAutoTracking: () => void
      startToolTimer: (name: string) => void
      endToolTimer: (name: string) => number
    }
  }
}

/**
 * 初始化 zxqTrack SDK
 * 确保在应用启动时调用一次
 */
export function useTrackInit() {
  useEffect(() => {
    // Track SDK proxy: backend /geo/ip endpoint avoids browser CORS
    // (ipapi.co doesn't send Access-Control-Allow-Origin, blocking the SDK's direct call)
    const trackProxyBase = import.meta.env.VITE_TRACK_PROXY_URL ?? ''

    // Wait for SDK script to load, then init
    const checkAndInit = () => {
      if (window.zxqTrack) {
        window.zxqTrack.init({
          tenant: TENANT_SLUG,
          debug: false,
          autoTrack: false, // we handle page tracking manually
          ...(trackProxyBase ? { apiUrl: trackProxyBase } : {}),
        })
        console.log('[Track] zxqTrack SDK initialized for tenant:', TENANT_SLUG)
      } else {
        setTimeout(checkAndInit, 100)
      }
    }

    checkAndInit()
  }, [])
}

export { TENANT_SLUG }
