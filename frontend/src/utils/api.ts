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
} from '../types'

// ─── API Base URL ─────────────────────────────────────────────────────────────
const BASE_URL = import.meta.env.DEV ? '/api' : ''

const api = axios.create({
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

