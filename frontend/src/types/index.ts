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
  quantity_kg?: number
  freight_override?: number | null
  exchange_rate?: number | null
}

export interface TariffBreakdown {
  fob_value: number
  quantity_kg: number
  freight: number
  insurance: number
  tariff_rate: number
  tariff_amount: number
  vat_rate: number
  vat_amount: number
  total_cost: number
  savings_vs_mfn: number   // 相比最惠国税率节省的金额
  exchange_rate: number
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
  zero_tariff?: boolean | null   // 新增：是否零关税
  category_guidance?: string | null  // 新增：品类说明
}

export interface HSSearchResponse {
  results: HSSearchResult[]
  has_non_zero_tariff?: boolean
  summary_guidance?: string | null
  error?: string
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

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: number
  email: string
  tier: SubscriptionTier
  is_admin: boolean
  subscribed_at: string | null
  expires_at: string | null
  created_at: string | null
}

export interface AuthResponse {
  access_token: string
  token_type?: string
  user: UserResponse
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  wechat_id?: string
}

// ─── Subscription ─────────────────────────────────────────────────────────────

export interface SubscriptionStatus {
  tier: SubscriptionTier
  expires_at: string | null
  remaining_queries: number | null
  is_active: boolean
  days_remaining: number | null
  api_enabled: boolean
  sub_accounts_remaining: number
  user?: UserResponse
}

export interface SubscriptionHistoryItem {
  id: number
  tier: SubscriptionTier
  amount: number
  currency: string
  payment_method: string | null
  payment_channel: string
  status: string
  started_at: string | null
  expires_at: string | null
  auto_renew: boolean
}

export interface CreateSubscriptionRequest {
  tier: SubscriptionTier
  payment_method: string
  payment_channel?: string
}

// ─── Sub-accounts ─────────────────────────────────────────────────────────────

export interface SubAccountResponse {
  id: number
  email: string
  name: string | null
  is_active: boolean
  created_at: string | null
}

export interface CreateSubAccountRequest {
  email: string
  password: string
  name?: string
}

// ─── API Keys ─────────────────────────────────────────────────────────────────

export interface ApiKeyResponse {
  id: number
  key_prefix: string
  name: string | null
  tier: string
  rate_limit_day: number
  is_active: boolean
  last_used_at: string | null
  created_at: string | null
}

export interface ApiKeyWithPlain {
  id: number
  plain_key: string
  key_prefix: string
  name: string | null
  tier: string
  rate_limit_day: number
  is_active: boolean
  last_used_at: string | null
  created_at: string | null
}

export interface CreateApiKeyRequest {
  name?: string
  rate_limit_day?: number
}

// ─── Admin ────────────────────────────────────────────────────────────────────

export interface AdminUserSummary {
  id: number
  email: string
  tier: SubscriptionTier
  is_admin: boolean
  is_active: boolean
  subscribed_at: string | null
  expires_at: string | null
  created_at: string | null
  latest_subscription: {
    id: number
    tier: SubscriptionTier
    amount: number
    status: string
    started_at: string | null
    expires_at: string | null
  } | null
  sub_accounts_count: number
  api_keys_count: number
}

export interface AdminStats {
  total_users: number
  paying_users: number
  pro_users: number
  enterprise_users: number
  api_keys_active: number
  sub_accounts_active: number
  active_subscriptions: number
  total_revenue: number
  new_users_this_week: number
  expiring_soon_7d: number
}

// ─── Payment ──────────────────────────────────────────────────────────────────

export interface PaymentOrder {
  order_id: string
  tier: SubscriptionTier
  amount: number
  payment_method: string
  qr_code_url?: string
  status: 'pending' | 'paid' | 'expired'
}
