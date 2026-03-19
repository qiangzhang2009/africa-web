import axios from 'axios'
import type {
  TariffCalcInput,
  TariffCalcResult,
  ImportCostInput,
  ImportCostResult,
  HSSearchResult,
  OriginCheckInput,
  OriginCheckResult,
  Country,
} from '../types'

// ─── API Base URL ─────────────────────────────────────────────────────────────
// Production: points to the Cloudflare Worker CORS proxy
//   Deploy the worker at: https://dash.cloudflare.com → Workers & Pages → Create Worker
//   Then set WORKER_URL in Cloudflare Worker's Settings → Variables
//   After deploy, replace the URL below with your worker URL, e.g.:
//   https://africa-web-cors-proxy.abc123.workers.dev
const WORKER_URL =
  typeof import.meta !== 'undefined' && import.meta.env?.VITE_WORKER_URL
    ? String(import.meta.env.VITE_WORKER_URL)
    : 'https://africa-web-cors-proxy.<your-account>.workers.dev'

// Dev: Vite dev server proxies /api/* → http://localhost:8000 (no CORS issues)
const BASE_URL = import.meta.env.DEV
  ? '/api'
  : `${WORKER_URL}`

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
  const { data } = await api.get<{ results: HSSearchResult[] }>('/hs-codes/search', {
    params: { q: query, limit },
  })
  return data.results
}

// ─── Origin Check ─────────────────────────────────────────────────────────────
export async function checkOrigin(input: OriginCheckInput): Promise<OriginCheckResult> {
  const { data } = await api.post<OriginCheckResult>('/origin/check', input)
  return data
}

// ─── Countries ────────────────────────────────────────────────────────────────
export async function listCountries(market?: string): Promise<Country[]> {
  const { data } = await api.get<{ countries: Country[] }>('/countries', {
    params: market ? { market } : {},
  })
  return data.countries
}

// ─── Subscription ─────────────────────────────────────────────────────────────
export async function checkSubscription(email?: string, wechatId?: string) {
  const { data } = await api.get('/subscribe/check', {
    params: email ? { email } : wechatId ? { wechat_id: wechatId } : {},
  })
  return data
}
