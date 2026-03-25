import axios from 'axios'
import type {
  TariffCalcInput,
  TariffCalcResult,
  ImportCostInput,
  ImportCostResult,
  HSSearchResult,
  HSSearchResponse,
  OriginCheckInput,
  OriginCheckResult,
  Country,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  SubscriptionStatus,
  SubscriptionHistoryItem,
  CreateSubscriptionRequest,
  SubAccountResponse,
  CreateSubAccountRequest,
  ApiKeyResponse,
  ApiKeyWithPlain,
  CreateApiKeyRequest,
  AdminUserSummary,
  AdminStats,
  FreightRoute,
  FreightEstimateInput,
  FreightEstimateResult,
  CertGuide,
  CertStepsResponse,
  CertDocGenerateInput,
  CertDocGenerateResult,
  Supplier,
  SupplierSearchResult,
  SupplierReview,
  SupplierReviewCreate,
  SupplierCompareResult,
} from '../types'

// ─── API Base URL ─────────────────────────────────────────────────────────────
const BASE_URL = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? '/api' : '')

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Auth interceptor ─────────────────────────────────────────────────────────
const TOKEN_KEY = 'africa_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── Auth ─────────────────────────────────────────────────────────────────────
export async function login(data: LoginRequest): Promise<AuthResponse> {
  const { data: resp } = await api.post<AuthResponse>('/auth/login', data)
  setToken(resp.access_token)
  return resp
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const { data: resp } = await api.post<AuthResponse>('/auth/register', data)
  setToken(resp.access_token)
  return resp
}

export async function getMe() {
  const { data } = await api.get('/auth/me')
  return data
}

export async function getDailyUsage(): Promise<{ remaining_today: number; used_today: number; max_free_daily: number; tier: string }> {
  const { data } = await api.get('/auth/daily-usage')
  return data
}

// ─── Tariff ───────────────────────────────────────────────────────────────────
export async function calculateTariff(input: TariffCalcInput): Promise<TariffCalcResult> {
  const { data } = await api.post<TariffCalcResult>('/calculate/tariff', input)
  return data
}

// ─── Import Cost ──────────────────────────────────────────────────────────────
export async function calculateImportCost(input: ImportCostInput): Promise<ImportCostResult> {
  const { data } = await api.post<ImportCostResult>('/calculate/import-cost', input)
  return data
}

// ─── HS Code Search ──────────────────────────────────────────────────────────
export async function searchHSCodes(query: string, limit = 10): Promise<HSSearchResult[]> {
  try {
    const { data } = await api.get<HSSearchResponse | null>('/hs-codes/search', {
      params: { q: query, limit },
    })
    if (!data) return []
    return data.results ?? []
  } catch {
    return []
  }
}

// ─── Origin Check ─────────────────────────────────────────────────────────────
export async function checkOrigin(input: OriginCheckInput): Promise<OriginCheckResult> {
  const { data } = await api.post<OriginCheckResult>('/origin/check', input)
  return data
}

// ─── Countries ───────────────────────────────────────────────────────────────
export async function listCountries(market?: string): Promise<Country[]> {
  const { data } = await api.get<{ countries?: Country[]; data?: Country[] }>('/countries', {
    params: market ? { market } : {},
  })
  return data.countries ?? data.data ?? []
}

// ─── Subscription ─────────────────────────────────────────────────────────────
export async function checkSubscription(email?: string, wechatId?: string) {
  const { data } = await api.get('/subscribe/check', {
    params: email ? { email } : wechatId ? { wechat_id: wechatId } : {},
  })
  return data
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  const { data } = await api.get<SubscriptionStatus>('/subscribe/status')
  return data
}

export async function createSubscription(req: CreateSubscriptionRequest): Promise<SubscriptionStatus> {
  const { data } = await api.post<SubscriptionStatus>('/subscribe/create', req)
  return data
}

export async function getSubscriptionHistory(): Promise<SubscriptionHistoryItem[]> {
  const { data } = await api.get<SubscriptionHistoryItem[]>('/subscribe/history')
  return data
}

// ─── Sub-accounts ─────────────────────────────────────────────────────────────
export async function listSubAccounts(): Promise<SubAccountResponse[]> {
  const { data } = await api.get<SubAccountResponse[]>('/sub-accounts')
  return data
}

export async function createSubAccount(
  email: string,
  password: string,
  name?: string,
): Promise<SubAccountResponse> {
  const req: CreateSubAccountRequest = { email, password, name }
  const { data } = await api.post<SubAccountResponse>('/sub-accounts', req)
  return data
}

export async function deleteSubAccount(id: number) {
  const { data } = await api.delete(`/sub-accounts/${id}`)
  return data
}

// ─── API Keys ─────────────────────────────────────────────────────────────────
export async function listApiKeys(): Promise<ApiKeyResponse[]> {
  const { data } = await api.get<ApiKeyResponse[]>('/api-keys')
  return data
}

export async function createApiKey(req?: CreateApiKeyRequest): Promise<ApiKeyWithPlain> {
  const { data } = await api.post<ApiKeyWithPlain>('/api-keys', req ?? {})
  return data
}

export async function revokeApiKey(id: number) {
  const { data } = await api.delete(`/api-keys/${id}`)
  return data
}

// ─── Admin ────────────────────────────────────────────────────────────────────
export async function adminListUsers(params: {
  page?: number
  page_size?: number
  tier?: string
  search?: string
}): Promise<{ total: number; page: number; page_size: number; users: AdminUserSummary[] }> {
  const { data } = await api.get('/admin/users', { params })
  return data
}

export async function adminGetStats(): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>('/admin/stats')
  return data
}

export async function adminUpdateUser(userId: number, body: Record<string, unknown>) {
  const { data } = await api.patch(`/admin/users/${userId}`, body)
  return data
}

export async function adminCreateSubscription(userId: number, tier: string) {
  const { data } = await api.post('/admin/subscriptions', {
    user_id: userId,
    tier,
    amount: tier === 'pro' ? 99 : 298,
    payment_method: 'manual',
    payment_channel: 'manual',
  })
  return data
}

// ─── Freight ─────────────────────────────────────────────────────────────────
export async function listFreightRoutes(params?: {
  origin_country?: string
  dest_port?: string
  transport_type?: string
}) {
  const { data } = await api.get('/freight/routes', { params })
  return data as FreightRoute[]
}

export async function listFreightCountries() {
  const { data } = await api.get('/freight/routes/countries')
  return data as { code: string; name_zh: string; name_en?: string }[]
}

export async function listDestPorts() {
  const { data } = await api.get('/freight/routes/ports')
  return data as { code: string; name_zh: string }[]
}

export async function estimateFreightCost(input: FreightEstimateInput) {
  const { data } = await api.post<FreightEstimateResult>('/freight/estimate', input)
  return data
}

// ─── Certificate ──────────────────────────────────────────────────────────────
export async function listCertGuides(country?: string) {
  const { data } = await api.get('/certificate/guides', {
    params: country ? { country } : {},
  })
  return data as CertGuide[]
}

export async function getCertGuide(countryCode: string) {
  const { data } = await api.get<CertGuide>(`/certificate/guides/${countryCode}`)
  return data
}

export async function getCertSteps(countryCode: string) {
  const { data } = await api.get<CertStepsResponse>(`/certificate/steps`, {
    params: { country_code: countryCode },
  })
  return data
}

export async function startCertApplication(input: {
  hs_code: string
  origin_country: string
  cert_type?: string
}) {
  const { data } = await api.post('/certificate/application/start', input)
  return data as { message: string; application_id: number }
}

export async function getMyCertApplications() {
  const { data } = await api.get('/certificate/application')
  return data as Array<{
    id: number
    hs_code: string
    origin_country: string
    cert_type: string
    status: string
    current_step: number
    steps_completed: Record<string, boolean>
    ai_doc_generated: boolean
    submitted_at?: string
    cert_number?: string
    created_at?: string
  }>
}

export async function generateCertDocument(input: CertDocGenerateInput) {
  const { data } = await api.post<CertDocGenerateResult>(
    '/certificate/document/generate',
    input,
  )
  return data
}

// ─── Supplier ─────────────────────────────────────────────────────────────────
export async function searchSuppliers(params?: {
  country?: string
  keyword?: string
  hs_code?: string
  verified_only?: boolean
  page?: number
  page_size?: number
}): Promise<SupplierSearchResult> {
  const { data } = await api.get<SupplierSearchResult>('/suppliers', { params })
  return data
}

export async function listSupplierCountries() {
  const { data } = await api.get('/suppliers/countries')
  return data as {
    code: string
    name_zh: string
    name_en?: string
    supplier_count: number
    verified_count: number
  }[]
}

export async function getSupplier(id: number) {
  const { data } = await api.get<Supplier>(`/suppliers/${id}`)
  return data
}

export async function getSupplierReviews(
  supplierId: number,
  page = 1,
  pageSize = 10,
) {
  const { data } = await api.get(`/suppliers/${supplierId}/reviews`, {
    params: { page, page_size: pageSize },
  })
  return data as { reviews: SupplierReview[]; total: number; page: number; page_size: number }
}

export async function createSupplierReview(review: SupplierReviewCreate) {
  const { data } = await api.post(
    `/suppliers/${review.supplier_id}/reviews`,
    review,
  )
  return data as { message: string; review_id: number; new_rating: number }
}

export async function getSupplierCompare(supplierId: number) {
  const { data } = await api.get<SupplierCompareResult>(
    `/suppliers/${supplierId}/compare`,
  )
  return data
}
