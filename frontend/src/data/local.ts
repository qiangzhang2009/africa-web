/**
 * 本地数据加载器
 *
 * 架构说明：
 * 在静态化部署模式下，数据从 /data/*.json 文件读取，无需后端 API。
 * 提供与 api.ts 完全一致的接口，页面代码无需修改即可切换。
 *
 * 使用方式：
 *   import { localData } from '@/data/local'
 *
 *   // 直接使用（与 api.ts 接口一致）
 *   const countries = await localData.listCountries()
 *   const hsResults = await localData.searchHSCodes('咖啡')
 *   const suppliers = await localData.searchSuppliers({ country: 'KE' })
 *
 * 静态数据来源：
 *   dist/data/countries.json     — 非洲 54 国基础数据
 *   dist/data/hs_codes.json      — HS 编码及税率
 *   dist/data/freight_routes.json — 船运路线
 *   dist/data/cert_guides.json   — 原产地证书指南
 *   dist/data/market_products.json — 市场选品分析
 *   dist/data/suppliers.json     — 非洲供应商
 *
 * 数据更新流程：
 *   1. 运行 python -m pipeline.run（爬取最新数据）
 *   2. 运行 npm run build（重新打包前端）
 *   3. 部署 dist/ 目录
 */

import type {
  Country,
  HSSearchResult,
  FreightRoute,
  CertGuide,
  Supplier,
  SupplierSearchResult,
} from '../types'

// ── 数据路径常量 ──────────────────────────────────────────────────────────────

const DATA_BASE = '/data'

const DATA_PATHS = {
  countries: `${DATA_BASE}/countries.json`,
  hs_codes: `${DATA_BASE}/hs_codes.json`,
  freight_routes: `${DATA_BASE}/freight_routes.json`,
  cert_guides: `${DATA_BASE}/cert_guides.json`,
  market_products: `${DATA_BASE}/market_products.json`,
  suppliers: `${DATA_BASE}/suppliers.json`,
} as const

// ── 缓存层（避免重复 fetch）────────────────────────────────────────────────────

const _cache: Map<string, unknown> = new Map()

async function _fetchCached<T>(path: string): Promise<T> {
  if (_cache.has(path)) {
    return _cache.get(path) as T
  }
  const res = await fetch(path)
  if (!res.ok) {
    throw new Error(`无法加载数据文件：${path}（${res.status}）`)
  }
  const data = await res.json()
  _cache.set(path, data)
  return data as T
}

// ── HS 编码零关税状态映射（与后端 router/hs_codes.py 保持一致）────────────────────

const ZERO_TARIFF_CATEGORIES = [
  '咖啡', '可可', '坚果', '矿产', '木材', '皮革',
  '油籽', '香料', '棉麻', '橡胶', '水产', '食品',
]

const NON_ZERO_GUIDANCE: Record<string, string> = {
  '钢铁': '注意：钢铁类产品(72章)目前不在非洲零关税政策范围内，进口需缴纳6-8%的MFN关税。',
  '汽车': '注意：汽车(87章)目前不在非洲零关税政策范围内，且整车进口需3C认证，门槛较高。',
  '电子': '注意：手机及电子产品(85章)进口需3C认证，门槛较高。',
  '服装': '注意：服装纺织品(61-62章)目前不在非洲零关税政策范围内。',
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────

function _pipeToArray(val: string | null | undefined): string[] {
  if (!val) return []
  return val.split('|').map((s) => s.trim()).filter(Boolean)
}

function _normalize_hs(code: string): string {
  return code.replace(/\./g, '').replace(/ /g, '').replace(/-/g, '')
}

function _get_zero_tariff_status(category: string | undefined): {
  zero_tariff: boolean | null
  guidance: string | null
} {
  if (!category) return { zero_tariff: null, guidance: null }
  if (category in NON_ZERO_GUIDANCE) {
    return { zero_tariff: false, guidance: NON_ZERO_GUIDANCE[category] }
  }
  return { zero_tariff: ZERO_TARIFF_CATEGORIES.includes(category), guidance: null }
}

// ── 辅助类型 ──────────────────────────────────────────────────────────────────

interface CountriesPayload {
  countries: Country[]
}

interface HSSearchPayload {
  results: Array<{
    hs_10: string
    name_zh: string
    name_en: string
    mfn_rate: number
    vat_rate: number
    category: string
    zero_tariff: boolean
  }>
}

// ── 本地数据 API（接口与 api.ts 一致）──────────────────────────────────────────

export const localData = {
  /**
   * 获取非洲国家列表
   */
  async listCountries(): Promise<Country[]> {
    const payload = await _fetchCached<CountriesPayload>(DATA_PATHS.countries)
    return payload.countries ?? []
  },

  /**
   * 搜索 HS 编码
   */
  async searchHSCodes(query: string, limit = 10): Promise<HSSearchResult[]> {
    const payload = await _fetchCached<HSSearchPayload>(DATA_PATHS.hs_codes)
    const normalized = _normalize_hs(query)

    // 优先精确匹配 HS 编码
    const exactMatches: HSSearchResult[] = []
    const nameMatches: HSSearchResult[] = []

    for (const r of payload.results) {
      const norm10 = _normalize_hs(r.hs_10 ?? '')
      if (norm10.startsWith(normalized) && exactMatches.length < limit) {
        const tariff = _get_zero_tariff_status(r.category)
        exactMatches.push({
          hs_10: r.hs_10,
          name_zh: r.name_zh,
          name_en: r.name_en,
          mfn_rate: r.mfn_rate,
          vat_rate: r.vat_rate,
          category: r.category,
          match_score: 1.0,
          zero_tariff: tariff.zero_tariff,
          category_guidance: tariff.guidance,
        })
      }
    }

    // 然后模糊匹配品名
    const q = query.toLowerCase()
    for (const r of payload.results) {
      if (
        (r.name_zh?.toLowerCase().includes(q) || r.category?.toLowerCase().includes(q)) &&
        !exactMatches.some((m) => m.hs_10 === r.hs_10) &&
        nameMatches.length < limit - exactMatches.length
      ) {
        const tariff = _get_zero_tariff_status(r.category)
        nameMatches.push({
          hs_10: r.hs_10,
          name_zh: r.name_zh,
          name_en: r.name_en,
          mfn_rate: r.mfn_rate,
          vat_rate: r.vat_rate,
          category: r.category,
          match_score: 0.8,
          zero_tariff: tariff.zero_tariff,
          category_guidance: tariff.guidance,
        })
      }
    }

    const results = [...exactMatches, ...nameMatches]
    return results.slice(0, limit)
  },

  /**
   * 获取船运路线列表
   */
  async listFreightRoutes(params?: {
    origin_country?: string
    dest_port?: string
    transport_type?: string
  }): Promise<FreightRoute[]> {
    const routes = await _fetchCached<FreightRoute[]>(DATA_PATHS.freight_routes)
    return routes.filter((r) => {
      if (params?.origin_country && r.origin_country !== params.origin_country) return false
      if (params?.dest_port && r.dest_port !== params.dest_port) return false
      if (params?.transport_type && r.transport_type !== params.transport_type) return false
      return true
    })
  },

  /**
   * 获取有船运路线的国家列表
   */
  async listFreightCountries(): Promise<{ code: string; name_zh: string; name_en?: string }[]> {
    const routes = await _fetchCached<FreightRoute[]>(DATA_PATHS.freight_routes)
    const countries = await this.listCountries()
    const countryMap = new Map(countries.map((c) => [c.code, c]))

    const seen = new Set<string>()
    const result: { code: string; name_zh: string; name_en?: string }[] = []
    for (const r of routes) {
      if (!seen.has(r.origin_country)) {
        seen.add(r.origin_country)
        const country = countryMap.get(r.origin_country)
        result.push({
          code: r.origin_country,
          name_zh: country?.name_zh ?? r.origin_country,
          name_en: country?.name_en,
        })
      }
    }
    return result.sort((a, b) => a.name_zh.localeCompare(b.name_zh, 'zh'))
  },

  /**
   * 获取目的港列表
   */
  async listDestPorts(): Promise<{ code: string; name_zh: string }[]> {
    const routes = await _fetchCached<FreightRoute[]>(DATA_PATHS.freight_routes)
    const seen = new Set<string>()
    const result: { code: string; name_zh: string }[] = []
    for (const r of routes) {
      if (r.dest_country === 'CN' && !seen.has(r.dest_port)) {
        seen.add(r.dest_port)
        result.push({ code: r.dest_port, name_zh: r.dest_port_zh })
      }
    }
    return result.sort((a, b) => a.name_zh.localeCompare(b.name_zh, 'zh'))
  },

  /**
   * 获取原产地证书指南列表
   */
  async listCertGuides(country?: string): Promise<CertGuide[]> {
    const guides = await _fetchCached<CertGuide[]>(DATA_PATHS.cert_guides)
    if (country) {
      return guides.filter((g) => g.country_code === country.toUpperCase())
    }
    return guides
  },

  /**
   * 获取单个国家的原产地证书指南
   */
  async getCertGuide(countryCode: string): Promise<CertGuide | null> {
    const guides = await this.listCertGuides(countryCode)
    return guides[0] ?? null
  },

  /**
   * 获取原产地证书申请步骤（从 cert_guides 推导出 CertStepsResponse 格式）
   */
  async getCertSteps(countryCode: string): Promise<{
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
  } | null> {
    const guide = await this.getCertGuide(countryCode)
    if (!guide) return null
    // 将 step_sequence 字符串数组转换为步骤对象
    const steps = (guide.step_sequence ?? []).map((desc: string, i: number) => ({
      step: i + 1,
      title: `步骤 ${i + 1}`,
      description: desc,
    }))
    return {
      country_code: guide.country_code,
      country_name_zh: guide.country_name_zh,
      cert_type_zh: guide.cert_type_zh,
      issuing_authority_zh: guide.issuing_authority_zh,
      fee_usd_min: guide.fee_usd_min,
      fee_usd_max: guide.fee_usd_max,
      fee_cny_note: guide.fee_cny_note,
      days_min: guide.days_min,
      days_max: guide.days_max,
      steps,
      documents_required: guide.doc_requirements ?? [],
      notes: guide.notes,
      website_url: guide.website_url,
    }
  },

  /**
   * 获取供应商列表（分页 + 筛选）
   */
  async searchSuppliers(params?: {
    country?: string
    keyword?: string
    hs_code?: string
    verified_only?: boolean
    page?: number
    page_size?: number
  }): Promise<SupplierSearchResult> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const payload = await _fetchCached<any>(DATA_PATHS.suppliers)
    const page = params?.page ?? 1
    const pageSize = params?.page_size ?? 20

    // Transform: pipe-separated strings → arrays, add id
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let filtered: any[] = payload.suppliers.map((s: any, idx: number) => ({
      ...s,
      id: s.id ?? idx + 1,
      main_products: _pipeToArray(s.main_products),
      main_hs_codes: _pipeToArray(s.main_hs_codes),
    }))

    if (params?.country) {
      filtered = filtered.filter((s) => s.country === params.country!.toUpperCase())
    }
    if (params?.keyword) {
      const kw = params.keyword.toLowerCase()
      filtered = filtered.filter(
        (s) =>
          s.name_zh?.toLowerCase().includes(kw) ||
          (s.name_en ?? '').toLowerCase().includes(kw) ||
          s.main_products.some((p: string) => p.toLowerCase().includes(kw)),
      )
    }
    if (params?.hs_code) {
      filtered = filtered.filter((s: Supplier) =>
        s.main_hs_codes.some((h: string) => h.includes(params.hs_code!)),
      )
    }
    if (params?.verified_only) {
      filtered = filtered.filter((s) => s.verified_chamber)
    }

    const total = filtered.length
    const offset = (page - 1) * pageSize
    const suppliers = filtered.slice(offset, offset + pageSize)

    return { suppliers, total, page, page_size: pageSize }
  },

  /**
   * 获取供应商详情
   */
  async getSupplier(id: number): Promise<Supplier | null> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const payload = await _fetchCached<any>(DATA_PATHS.suppliers)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = payload.suppliers.find((s: any, idx: number) => (s.id ?? idx + 1) === id)
    if (!raw) return null
    return {
      ...raw,
      id: raw.id ?? id,
      main_products: _pipeToArray(raw.main_products),
      main_hs_codes: _pipeToArray(raw.main_hs_codes),
    }
  },

  /**
   * 获取有供应商的国家列表
   */
  async listSupplierCountries(): Promise<{
    code: string
    name_zh: string
    name_en?: string
    supplier_count: number
    verified_count: number
  }[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const payload = await _fetchCached<any>(DATA_PATHS.suppliers)
    const countries = await this.listCountries()
    const countryMap = new Map(countries.map((c) => [c.code, c]))

    const map = new Map<string, { total: number; verified: number }>()
    for (const s of payload.suppliers) {
      const existing = map.get(s.country) ?? { total: 0, verified: 0 }
      existing.total++
      if (s.verified_chamber) existing.verified++
      map.set(s.country, existing)
    }

    return Array.from(map.entries())
      .map(([code, stats]) => ({
        code,
        name_zh: countryMap.get(code)?.name_zh ?? code,
        name_en: countryMap.get(code)?.name_en,
        supplier_count: stats.total,
        verified_count: stats.verified,
      }))
      .sort((a, b) => b.supplier_count - a.supplier_count)
  },

  /**
   * 清除缓存（数据更新后调用）
   */
  clearCache(): void {
    _cache.clear()
  },
}

// ── 便捷导出（与 api.ts 接口一一对应）───────────────────────────────────────────

export async function listCountries(): Promise<Country[]> {
  return localData.listCountries()
}

export async function searchHSCodes(query: string, limit = 10): Promise<HSSearchResult[]> {
  return localData.searchHSCodes(query, limit)
}

export async function listFreightRoutes(params?: {
  origin_country?: string
  dest_port?: string
  transport_type?: string
}): Promise<FreightRoute[]> {
  return localData.listFreightRoutes(params)
}

export async function listFreightCountries() {
  return localData.listFreightCountries()
}

export async function listDestPorts() {
  return localData.listDestPorts()
}

export async function listCertGuides(country?: string): Promise<CertGuide[]> {
  return localData.listCertGuides(country)
}

export async function getCertGuide(countryCode: string): Promise<CertGuide | null> {
  return localData.getCertGuide(countryCode)
}

export async function getCertSteps(countryCode: string) {
  return localData.getCertSteps(countryCode)
}

export async function searchSuppliers(params?: {
  country?: string
  keyword?: string
  hs_code?: string
  verified_only?: boolean
  page?: number
  page_size?: number
}): Promise<SupplierSearchResult> {
  return localData.searchSuppliers(params)
}

export async function listSupplierCountries() {
  return localData.listSupplierCountries()
}

export async function getSupplier(id: number): Promise<Supplier | null> {
  return localData.getSupplier(id)
}
