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
  remaining_today?: number
  max_free_daily?: number
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

// ─── Freight ─────────────────────────────────────────────────────────────────

export interface FreightRoute {
  id: number
  origin_country: string
  origin_port: string
  origin_port_zh: string
  dest_country: string
  dest_port: string
  dest_port_zh: string
  transport_type: string
  cost_min_usd: number
  cost_max_usd: number
  transit_days_min: number
  transit_days_max: number
  notes?: string
}

export interface FreightEstimateInput {
  origin_country: string
  dest_port: string
  quantity_kg: number
  transport_type?: string
}

export interface FreightEstimateResult {
  origin_country: string
  origin_port: string
  origin_port_zh: string
  dest_port: string
  dest_port_zh: string
  transport_type: string
  quantity_kg: number
  container_suggestion: string
  sea_freight_usd: number
  sea_freight_cny: number
  port_charges_usd: number
  insurance_usd: number
  clearance_agent_fee_cny: number
  domestic_logistics_cny: number
  total_freight_cny: number
  total_freight_usd: number
  transit_days: string
  notes?: string
  breakdown: Record<string, unknown>
}

// ─── Certificate ───────────────────────────────────────────────────────────────

export interface CertGuide {
  id: number
  country_code: string
  country_name_zh: string
  cert_type: string
  cert_type_zh: string
  issuing_authority: string
  issuing_authority_zh: string
  website_url?: string
  fee_usd_min: number
  fee_usd_max: number
  fee_cny_note?: string
  days_min: number
  days_max: number
  doc_requirements: string[]
  step_sequence: string[]
  api_available: boolean
  notes?: string
}

export interface CertStepsResponse {
  country_code: string
  country_name_zh: string
  cert_type_zh: string
  issuing_authority_zh: string
  fee_usd_min: number
  fee_usd_max: number
  fee_cny_note?: string
  days_min: number
  days_max: number
  steps: Array<{ step: number; title: string; description: string }>
  documents_required: string[]
  notes?: string
  website_url?: string
}

export interface CertDocGenerateInput {
  hs_code: string
  origin_country: string
  processing_steps: string[]
  material_sources: string[]
  exporter_name?: string
  importer_name?: string
  product_description?: string
  fob_value_usd?: number
  quantity_kg?: number
  destination_country?: string
}

export interface CertDocGenerateResult {
  document_type: string
  content: string
  format: string
  generated_at: string
  usage_note: string
}

// ─── Supplier ──────────────────────────────────────────────────────────────────

export interface Supplier {
  id: number
  name_zh: string
  name_en?: string
  country: string
  country_name_zh?: string
  region?: string
  main_products: string[]
  main_hs_codes: string[]
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  website?: string
  min_order_kg?: number
  payment_terms?: string
  export_years: number
  annual_export_tons?: number
  verified_chamber: boolean
  verified_实地拜访: boolean
  verified_sgs: boolean
  rating_avg: number
  review_count: number
  status: string
  intro?: string
  certifications: string[]
}

export interface SupplierListItem {
  id: number
  name_zh: string
  country: string
  region?: string
  main_products: string[]
  main_hs_codes: string[]
  export_years: number
  verified_chamber: boolean
  rating_avg: number
  review_count: number
  status: string
  min_order_kg?: number
}

export interface SupplierSearchResult {
  suppliers: SupplierListItem[]
  total: number
  page: number
  page_size: number
}

export interface SupplierReview {
  id: number
  supplier_id: number
  user_email?: string
  quality_score: number
  delivery_score: number
  communication_score: number
  comment?: string
  is_verified_deal: boolean
  created_at?: string
}

export interface SupplierReviewCreate {
  supplier_id: number
  quality_score: number
  delivery_score: number
  communication_score: number
  comment?: string
  is_verified_deal?: boolean
}

export interface SupplierCompareResult {
  supplier: Supplier
  recommended_route: {
    origin_port: string
    origin_port_zh: string
    dest_port: string
    dest_port_zh: string
    transit_days: string
    cost_range_usd: string
  } | null
  estimated_freight: {
    sea_freight_usd: number
    sea_freight_cny: number
    insurance_usd: number
    clearance_cny: number
    total_estimate_cny: number
  } | null
}
