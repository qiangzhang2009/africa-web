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

const api = axios.create({
  baseURL: 'https://africa-web-wuxs.onrender.com/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
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
