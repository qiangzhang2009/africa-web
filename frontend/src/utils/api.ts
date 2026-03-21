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
} from '../types'

// ─── API Base URL ─────────────────────────────────────────────────────────────
// Production: Vercel rewrite proxy → FastAPI backend on Render.
//   vercel.json rewrites /api/* to https://africa-web-wuxs.onrender.com/api/*
//   Cloudflare Workers deployment uses VITE_WORKER_URL separately.
const BASE_URL = import.meta.env.DEV
  ? '/api'
  : (import.meta.env.VITE_API_URL || import.meta.env.VITE_WORKER_URL || '')

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

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

// ─── Countries ────────────────────────────────────────────────────────────────
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
