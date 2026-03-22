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
    // 等待 SDK 脚本加载完成
    const checkAndInit = () => {
      if (window.zxqTrack) {
        window.zxqTrack.init({
          tenant: TENANT_SLUG,
          debug: false,
          autoTrack: false, // 我们手动控制页面追踪
        })
        console.log('[Track] zxqTrack SDK initialized for tenant:', TENANT_SLUG)
      } else {
        // SDK 未加载，延迟重试
        setTimeout(checkAndInit, 100)
      }
    }

    checkAndInit()
  }, [])
}

export { TENANT_SLUG }
