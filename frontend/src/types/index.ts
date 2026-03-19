// ─── Country ─────────────────────────────────────────────────────────────────
export interface Country {
  id: number
  code: string         // ISO 3166-1 alpha-2
  name_zh: string
  name_en: string
  in_afcfta: boolean
  has_epa: boolean
}

// ─── HS Code ──────────────────────────────────────────────────────────────────
export interface HSCode {
  id: number
  hs_4: string
  hs_6: string | null
  hs_8: string | null
  hs_10: string | null
  name_zh: string
  name_en: string | null
  mfn_rate: number     // 0-1
  vat_rate: number      // 0-1
  category: string | null
}

// ─── Policy Rule ──────────────────────────────────────────────────────────────
export interface PolicyRule {
  id: number
  market: 'CN' | 'EU' | 'AFCFTA'
  rule_type: 'tariff' | 'origin' | 'quota'
  hs_pattern: string | null
  rule_text: string
  rate: number | null
  effective_date: string | null
}

// ─── User / Subscription ──────────────────────────────────────────────────────
export type SubscriptionTier = 'free' | 'pro' | 'enterprise'

export interface User {
  id: number
  email: string | null
  wechat_id: string | null
  tier: SubscriptionTier
  subscribed_at: string | null
  expires_at: string | null
}

// ─── Tariff Calculation ────────────────────────────────────────────────────────
export type DestinationMarket = 'CN' | 'EU' | 'AFCFTA'

export interface TariffCalcInput {
  hs_code: string
  origin_country: string
  destination: DestinationMarket
  fob_value: number
  currency?: 'USD' | 'CNY'
}

export interface TariffBreakdown {
  fob_value: number
  freight: number
  insurance: number
  tariff_rate: number
  tariff_amount: number
  vat_rate: number
  vat_amount: number
  total_cost: number
  savings_vs_mfn: number   // 相比最惠国税率节省的金额
}

export interface TariffCalcResult {
  success: boolean
  input: TariffCalcInput
  breakdown: TariffBreakdown | null
  origin_qualified: boolean
  origin_rule: string | null
  message: string
}

// ─── Import Cost Calculation ───────────────────────────────────────────────────
export interface ImportCostInput {
  product_name: string
  quantity_kg: number
  fob_per_kg: number
  origin: string
  destination?: DestinationMarket
}

export interface ImportCostBreakdown {
  // 进口成本
  fob_value: number
  international_freight: number
  customs_clearance: number
  tariff: number
  vat: number
  total_import_cost: number

  // 国内加工
  roasting_loss_rate: number  // 烘焙损耗率，如 0.15
  roasted_yield_kg: number     // 烘焙后重量
  domestic_logistics: number   // 国内物流
  packaging_cost_per_unit: number
  total_domestic_cost: number

  // 综合成本
  total_cost: number
  cost_per_package: number    // 每包227g
  suggested_retail_price: number
  payback_packages: number     // 回本需要卖多少包
}

export interface ImportCostResult {
  success: boolean
  input: ImportCostInput
  breakdown: ImportCostBreakdown | null
  origin_certificate_guide: string[] | null
  message: string
}

// ─── HS Search ────────────────────────────────────────────────────────────────
export interface HSSearchResult {
  hs_10: string | null
  name_zh: string
  mfn_rate: number
  category: string | null
  match_score: number
}

// ─── Origin Check ─────────────────────────────────────────────────────────────
export interface OriginCheckInput {
  product_name: string
  hs_code: string
  origin: string
  processing_steps: string[]
  material_sources: string[]
}

export interface OriginCheckResult {
  qualifies: boolean
  rule_applied: string | null
  confidence: number        // 0-1
  reasons: string[]
  suggestions: string[]
}
