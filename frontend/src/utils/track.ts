/**
 * AfricaZero 追踪工具
 * 封装 zxqTrack SDK，提供类型安全的追踪 API
 */

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

// 工具名常量
const TOOLS = {
  TARIFF_CALCULATOR: 'tariff_calculator',
  COST_CALCULATOR: 'cost_calculator',
  HS_LOOKUP: 'hs_lookup',
  ORIGIN_CHECK: 'origin_check',
  PRODUCT_DISCOVERY: 'product_discovery',
  PRICING: 'pricing',
  DASHBOARD: 'dashboard',
  HOME: 'home',
  FREIGHT: 'freight',
  CERTIFICATE: 'certificate',
  SUPPLIERS: 'suppliers',
} as const

type ToolName = string

type TrackFn = (data?: Record<string, unknown>) => void

interface TrackAPI {
  // 通用
  page: (data?: Record<string, unknown>) => void

  // 关税计算器
  calcSelectPreset: (presetLabel: string, group: string, hsCode: string, origin: string) => void
  calcSearchHs: (query: string, resultCount: number) => void
  calcChangeDestination: (market: string) => void
  calcSubmit: (input: Record<string, unknown>, success: boolean) => void
  calcResultShown: (result: Record<string, unknown>) => void
  calcError: (error: string) => void

  // 成本精算器
  costSelectCategory: (category: string) => void
  costSelectPreset: (productLabel: string, origin: string) => void
  costSubmit: (input: Record<string, unknown>, success: boolean) => void
  costResultShown: (result: Record<string, unknown>) => void

  // HS编码查询
  hsSearch: (query: string, resultCount: number, zeroTariffCount: number) => void
  hsBrowseCategory: (category: string) => void
  hsQuickLink: (target: string) => void

  // 原产地自测
  originSubmit: (input: Record<string, unknown>, success: boolean) => void
  originResultShown: (result: Record<string, unknown>) => void

  // 选品发现
  productFilterChange: (filter: string, count: number) => void
  productExpand: (productName: string, hsCode: string) => void
  productQuickPreview: (productName: string, success: boolean) => void
  productAddInterest: (productName: string, hsCode: string) => void
  productRemoveInterest: (productName: string, hsCode: string) => void
  productNav: (target: string, params?: Record<string, string>) => void

  // 定价页
  pricingCtaClick: (planId: string, planName: string) => void

  // 主页
  homeCtaClick: (ctaLabel: string, targetPath: string) => void

  // 物流成本估算
  freightEstimate: (params: Record<string, unknown>) => void

  // 原产地证书
  certDocGenerate: (success: boolean, country: string) => void

  // 供应商发现
  supplierSearch: (params: Record<string, unknown>) => void
  supplierOpen: (supplierId: number, country: string) => void

  // 通用点击
  click: (label: string, category?: string, data?: Record<string, unknown>) => void
}

function safeTool(tool: ToolName, action: string): TrackFn {
  return (data) => {
    try {
      window.zxqTrack?.tool(tool, action, data)
    } catch {
      // SDK 未加载时静默忽略
    }
  }
}

export const track: TrackAPI = {
  // 通用页面追踪（只触发一次）
  page: (() => {
    let fired = false
    return (data) => {
      if (fired) return
      fired = true
      try {
        window.zxqTrack?.pageView(data)
      } catch {}
    }
  })(),

  // ── 关税计算器 ──────────────────────────────────────────────────────────────
  calcSelectPreset: (presetLabel, group, hsCode, origin) => {
    safeTool(TOOLS.TARIFF_CALCULATOR, 'select_preset')({
      preset_label: presetLabel,
      group,
      hs_code: hsCode,
      origin,
    })
  },

  calcSearchHs: (query, resultCount) => {
    safeTool(TOOLS.TARIFF_CALCULATOR, 'search_hs')({
      query,
      result_count: resultCount,
    })
  },

  calcChangeDestination: (market) => {
    safeTool(TOOLS.TARIFF_CALCULATOR, 'change_destination')({ market })
  },

  calcSubmit: (input, success) => {
    safeTool(TOOLS.TARIFF_CALCULATOR, success ? 'submit_success' : 'submit_error')({
      hs_code: input.hs_code,
      origin: input.origin,
      destination: input.destination,
      fob_value: input.fob_value,
      quantity_kg: input.quantity_kg,
      freight_mode: input.freight_mode,
    })
  },

  calcResultShown: (result) => {
    const bd = result.breakdown as Record<string, unknown> | undefined
    safeTool(TOOLS.TARIFF_CALCULATOR, 'result_shown')({
      qualified: result.origin_qualified,
      tariff_amount_cny: bd?.tariff_amount,
      savings_cny: bd?.savings_vs_mfn,
      destination: (result.input as Record<string, unknown>)?.destination,
    })
  },

  calcError: (error) => {
    safeTool(TOOLS.TARIFF_CALCULATOR, 'error')({ error_message: error })
  },

  // ── 成本精算器 ───────────────────────────────────────────────────────────────
  costSelectCategory: (category) => {
    safeTool(TOOLS.COST_CALCULATOR, 'select_category')({ category })
  },

  costSelectPreset: (productLabel, origin) => {
    safeTool(TOOLS.COST_CALCULATOR, 'select_preset')({
      product_label: productLabel,
      origin,
    })
  },

  costSubmit: (input, success) => {
    safeTool(TOOLS.COST_CALCULATOR, success ? 'submit_success' : 'submit_error')({
      product_name: input.product_name,
      quantity_kg: input.quantity_kg,
      fob_per_kg: input.fob_per_kg,
      origin: input.origin,
    })
  },

  costResultShown: (result) => {
    const bd = result.breakdown as Record<string, unknown> | undefined
    const certGuide = result.origin_certificate_guide as unknown[]
    safeTool(TOOLS.COST_CALCULATOR, 'result_shown')({
      total_cost_cny: bd?.total_cost,
      suggested_retail_price_cny: bd?.suggested_retail_price,
      payback_packages: bd?.payback_packages,
      has_certificate_guide: (certGuide?.length ?? 0) > 0,
    })
  },

  // ── HS编码查询 ───────────────────────────────────────────────────────────────
  hsSearch: (query, resultCount, zeroTariffCount) => {
    safeTool(TOOLS.HS_LOOKUP, 'search')({
      query,
      result_count: resultCount,
      zero_tariff_count: zeroTariffCount,
    })
  },

  hsBrowseCategory: (category) => {
    safeTool(TOOLS.HS_LOOKUP, 'browse_category')({ category })
  },

  hsQuickLink: (target) => {
    safeTool(TOOLS.HS_LOOKUP, 'quick_link')({ target })
  },

  // ── 原产地自测 ──────────────────────────────────────────────────────────────
  originSubmit: (input, success) => {
    safeTool(TOOLS.ORIGIN_CHECK, success ? 'submit_success' : 'submit_error')({
      hs_code: (input.hs_code as string) || '',
      origin: (input.origin as string) || '',
      processing_steps_count: (input.processing_steps as string[])?.length ?? 0,
    })
  },

  originResultShown: (result) => {
    safeTool(TOOLS.ORIGIN_CHECK, 'result_shown')({
      qualifies: result.qualifies,
      confidence: result.confidence,
      rule_applied: result.rule_applied,
    })
  },

  // ── 选品发现 ────────────────────────────────────────────────────────────────
  productFilterChange: (filter, count) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, 'filter_change')({ filter, product_count: count })
  },

  productExpand: (productName, hsCode) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, 'expand_product')({ product_name: productName, hs_code: hsCode })
  },

  productQuickPreview: (productName, success) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, success ? 'quick_preview_success' : 'quick_preview_error')({
      product_name: productName,
    })
  },

  productAddInterest: (productName, hsCode) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, 'add_interest')({
      product_name: productName,
      hs_code: hsCode,
    })
  },

  productRemoveInterest: (productName, hsCode) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, 'remove_interest')({
      product_name: productName,
      hs_code: hsCode,
    })
  },

  productNav: (target, params) => {
    safeTool(TOOLS.PRODUCT_DISCOVERY, 'nav_to_tool')({ target, ...params })
  },

  // ── 定价页 ────────────────────────────────────────────────────────────────
  pricingCtaClick: (planId, planName) => {
    safeTool(TOOLS.PRICING, 'cta_click')({ plan_id: planId, plan_name: planName })
  },

  // ── 主页 ─────────────────────────────────────────────────────────────────
  homeCtaClick: (ctaLabel, targetPath) => {
    safeTool(TOOLS.HOME, 'cta_click')({ cta_label: ctaLabel, target_path: targetPath })
  },

  // ── 物流成本估算 ─────────────────────────────────────────────────────────
  freightEstimate: (params) => {
    safeTool(TOOLS.FREIGHT, 'estimate')({
      origin: params.origin,
      dest: params.dest,
      qty_kg: params.qty,
      transport_type: params.type,
    })
  },

  // ── 原产地证书 ──────────────────────────────────────────────────────────
  certDocGenerate: (success, country) => {
    safeTool(TOOLS.CERTIFICATE, success ? 'doc_generate_success' : 'doc_generate_error')({ country })
  },

  // ── 供应商发现 ──────────────────────────────────────────────────────────
  supplierSearch: (params) => {
    safeTool(TOOLS.SUPPLIERS, 'search')({
      country: params.country,
      keyword: params.keyword,
      verified_only: params.verified_only,
    })
  },

  supplierOpen: (supplierId, country) => {
    safeTool(TOOLS.SUPPLIERS, 'open_supplier')({
      supplier_id: supplierId,
      country,
    })
  },

  // ── 通用 ──────────────────────────────────────────────────────────────────
  click: (label, category = 'general', data) => {
    try {
      window.zxqTrack?.click(label, category, data)
    } catch {}
  },
}
