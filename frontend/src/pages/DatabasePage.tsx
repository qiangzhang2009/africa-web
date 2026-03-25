import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import { api } from '../utils/api'

interface TableStats {
  table_name: string
  record_count: number
}

interface SupplierRecord {
  id: number
  name_zh: string
  name_en: string | null
  country: string
  region: string | null
  main_products: string
  main_hs_codes: string
  contact_email: string | null
  contact_phone: string | null
  website: string | null
  min_order_kg: number | null
  payment_terms: string | null
  export_years: number
  annual_export_tons: number | null
  verified_chamber: number
  verified_实地拜访: number
  verified_sgs: number
  rating_avg: number
  review_count: number
  status: string
  intro: string | null
  certifications: string | null
  created_at: string | null
}

interface CountryRecord {
  id: number
  code: string
  name_zh: string
  name_en: string
  in_afcfta: number
  has_epa: number
}

interface HSCodeRecord {
  id: number
  hs_4: string
  hs_6: string
  hs_8: string
  hs_10: string
  name_zh: string
  name_en: string | null
  mfn_rate: number
  vat_rate: number
  category: string | null
  zero_tariff?: boolean
}

interface FreightRouteRecord {
  id: number
  origin_country: string
  origin_port: string
  origin_port_zh: string
  dest_port: string
  dest_port_zh: string
  transport_type: string
  cost_min_usd: number
  cost_max_usd: number
  transit_days_min: number
  transit_days_max: number
  notes: string | null
}

interface CertGuideRecord {
  id: number
  country_code: string
  country_name_zh: string
  cert_type: string
  cert_type_zh: string
  issuing_authority_zh: string
  fee_usd_min: number
  fee_usd_max: number
  days_min: number
  days_max: number
  doc_requirements: string | null
  step_sequence: string | null
  api_available: number
}

type TabType = 'overview' | 'suppliers' | 'countries' | 'hs-codes' | 'freight' | 'cert-guides' | 'sync'

// Country name map
const COUNTRY_NAMES: Record<string, string> = {
  ET: '埃塞俄比亚', KE: '肯尼亚', TZ: '坦桑尼亚', GH: '加纳', CI: '科特迪瓦',
  ZA: '南非', MG: '马达加斯加', UG: '乌干达', RW: '卢旺达', MU: '毛里求斯',
  SN: '塞内加尔', DJ: '吉布提', NG: '尼日利亚', ZM: '赞比亚', BJ: '贝宁',
  CM: '喀麦隆', MZ: '莫桑比克', GA: '加蓬', CD: '刚果金', TN: '突尼斯',
  MA: '摩洛哥', EG: '埃及', DZ: '阿尔及利亚', SD: '苏丹', BW: '博茨瓦纳',
  NA: '纳米比亚', ZW: '津巴布韦', ML: '马里', NE: '尼日尔', TG: '多哥',
  SL: '塞拉利昂', LR: '利比里亚', BI: '布隆迪', MW: '马拉维',
}

export default function DatabasePage() {
  const navigate = useNavigate()
  const { isLoggedIn, currentUser } = useAppStore()

  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [tableStats, setTableStats] = useState<TableStats[]>([])
  const [suppliers, setSuppliers] = useState<SupplierRecord[]>([])
  const [countries, setCountries] = useState<CountryRecord[]>([])
  const [hsCodes, setHsCodes] = useState<HSCodeRecord[]>([])
  const [freightRoutes, setFreightRoutes] = useState<FreightRouteRecord[]>([])
  const [certGuides, setCertGuides] = useState<CertGuideRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState('')
  const [msg, setMsg] = useState('')

  // Search & filter state
  const [supplierSearch, setSupplierSearch] = useState('')
  const [supplierCountryFilter, setSupplierCountryFilter] = useState('')
  const [hsSearch, setHsSearch] = useState('')
  const [freightCountryFilter, setFreightCountryFilter] = useState('')

  useEffect(() => {
    if (!isLoggedIn || !currentUser?.is_admin) {
      navigate('/')
      return
    }
    loadAllData()
  }, [isLoggedIn, currentUser])

  async function loadAllData() {
    setLoading(true)
    try {
      const [suppliersRes, countriesRes, hsRes, freightRes, certRes] = await Promise.allSettled([
        api.get('/suppliers', { params: { page: 1, page_size: 50 } }),
        api.get('/countries'),
        api.get('/hs-codes/search', { params: { q: 'a', limit: 50 } }),
        api.get('/freight/routes'),
        api.get('/certificate/guides'),
      ])

      if (suppliersRes.status === 'fulfilled') {
        setSuppliers(suppliersRes.value.data.suppliers || [])
        setTableStats(prev => [...prev.filter(t => t.table_name !== 'suppliers'), 
          { table_name: 'suppliers', record_count: suppliersRes.value.data.total || 0 }])
      }
      if (countriesRes.status === 'fulfilled') {
        const data = countriesRes.value.data.countries || countriesRes.value.data.data || []
        setCountries(data)
        setTableStats(prev => [...prev.filter(t => t.table_name !== 'africa_countries'), 
          { table_name: 'africa_countries', record_count: data.length }])
      }
      if (hsRes.status === 'fulfilled') {
        setHsCodes(hsRes.value.data.results || [])
        setTableStats(prev => [...prev.filter(t => t.table_name !== 'hs_codes'), 
          { table_name: 'hs_codes', record_count: hsRes.value.data.results?.length || 0 }])
      }
      if (freightRes.status === 'fulfilled') {
        setFreightRoutes(freightRes.value.data || [])
        setTableStats(prev => [...prev.filter(t => t.table_name !== 'freight_routes'), 
          { table_name: 'freight_routes', record_count: freightRes.value.data?.length || 0 }])
      }
      if (certRes.status === 'fulfilled') {
        setCertGuides(certRes.value.data || [])
        setTableStats(prev => [...prev.filter(t => t.table_name !== 'cert_guides'), 
          { table_name: 'cert_guides', record_count: certRes.value.data?.length || 0 }])
      }
    } catch (e) {
      console.error('Failed to load data:', e)
      setMsg('加载数据失败，请检查网络连接')
    } finally {
      setLoading(false)
    }
  }

  async function handleSyncToNeon() {
    if (!confirm('确定要将本地数据同步到 Neon 云端数据库吗？这将覆盖云端数据。')) return
    setSyncing(true)
    setSyncMsg('正在同步数据到 Neon...')
    try {
      // Re-init DB to ensure latest seed data
      await api.post('/debug/reinit-db')
      setSyncMsg('同步完成！')
      await loadAllData()
    } catch (e) {
      setSyncMsg('同步失败：' + (e as Error).message)
    } finally {
      setSyncing(false)
      setTimeout(() => setSyncMsg(''), 3000)
    }
  }

  const tabs: { id: TabType; label: string; count?: number }[] = [
    { id: 'overview', label: '数据概览' },
    { id: 'suppliers', label: '供应商', count: suppliers.length },
    { id: 'countries', label: '国家', count: countries.length },
    { id: 'hs-codes', label: 'HS编码', count: hsCodes.length },
    { id: 'freight', label: '物流路线', count: freightRoutes.length },
    { id: 'cert-guides', label: '证书指南', count: certGuides.length },
    { id: 'sync', label: '数据同步' },
  ]

  // Filtered data
  const filteredSuppliers = suppliers.filter(s => {
    const matchSearch = !supplierSearch || 
      s.name_zh.toLowerCase().includes(supplierSearch.toLowerCase()) ||
      (s.name_en || '').toLowerCase().includes(supplierSearch.toLowerCase()) ||
      (s.contact_email || '').toLowerCase().includes(supplierSearch.toLowerCase())
    const matchCountry = !supplierCountryFilter || s.country === supplierCountryFilter
    return matchSearch && matchCountry
  })

  const filteredHsCodes = hsCodes.filter(h => 
    !hsSearch || 
    h.name_zh.toLowerCase().includes(hsSearch.toLowerCase()) ||
    h.hs_10.toLowerCase().includes(hsSearch.toLowerCase()) ||
    (h.category || '').toLowerCase().includes(hsSearch.toLowerCase())
  )

  const filteredFreight = freightRoutes.filter(r =>
    !freightCountryFilter || r.origin_country === freightCountryFilter
  )

  // Unique countries for filter dropdowns
  const uniqueCountries = [...new Set(suppliers.map(s => s.country))].sort()

  // Stats cards
  const totalRecords = tableStats.reduce((sum, t) => sum + t.record_count, 0)

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">本地数据库管理</h1>
          <p className="text-slate-500 text-sm mt-1">
            管理 AfricaZero 核心数据 · 共 {totalRecords.toLocaleString()} 条记录
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => navigate('/admin')} className="text-sm text-slate-500 hover:text-slate-700">
            ← 管理后台
          </button>
          <button onClick={loadAllData} disabled={loading} className="text-sm px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg">
            {loading ? '加载中...' : '🔄 刷新'}
          </button>
        </div>
      </div>

      {/* Message */}
      {msg && (
        <div className="mb-4 px-4 py-3 bg-amber-50 border border-amber-200 text-amber-700 rounded-lg text-sm">
          {msg}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
              activeTab === tab.id
                ? 'border-orange-500 text-orange-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
            {tab.count !== undefined && (
              <span className="ml-1.5 text-xs bg-slate-100 px-1.5 py-0.5 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div>
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
            {tableStats.map(t => (
              <div key={t.table_name} className="bg-white rounded-xl border border-slate-200 p-4">
                <div className="text-xs text-slate-500 mb-1">{t.table_name}</div>
                <div className="text-2xl font-bold text-slate-900">{t.record_count}</div>
                <div className="text-xs text-slate-400 mt-1">条记录</div>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="font-semibold text-slate-800 mb-4">快速操作</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <button onClick={loadAllData} disabled={loading} className="p-4 border border-slate-200 rounded-xl hover:bg-slate-50 text-center disabled:opacity-50">
                <div className="text-2xl mb-2">🔄</div>
                <div className="text-sm font-medium text-slate-700">刷新数据</div>
              </button>
              <button onClick={handleSyncToNeon} disabled={syncing} className="p-4 border border-slate-200 rounded-xl hover:bg-slate-50 text-center disabled:opacity-50">
                <div className="text-2xl mb-2">⬆️</div>
                <div className="text-sm font-medium text-slate-700">同步到Neon</div>
              </button>
              <button onClick={() => navigate('/suppliers')} className="p-4 border border-slate-200 rounded-xl hover:bg-slate-50 text-center">
                <div className="text-2xl mb-2">🔍</div>
                <div className="text-sm font-medium text-slate-700">前端预览</div>
              </button>
              <button onClick={() => navigate('/database')} className="p-4 border border-slate-200 rounded-xl hover:bg-slate-50 text-center">
                <div className="text-2xl mb-2">📊</div>
                <div className="text-sm font-medium text-slate-700">数据分析</div>
              </button>
            </div>
            {syncMsg && (
              <div className="mt-4 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm">
                {syncMsg}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'suppliers' && (
        <div>
          {/* Filters */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <input
                type="text"
                value={supplierSearch}
                onChange={e => setSupplierSearch(e.target.value)}
                placeholder="搜索供应商名称、邮箱..."
                className="flex-1 px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
              />
              <select
                value={supplierCountryFilter}
                onChange={e => setSupplierCountryFilter(e.target.value)}
                className="px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
              >
                <option value="">全部国家</option>
                {uniqueCountries.map(c => (
                  <option key={c} value={c}>{COUNTRY_NAMES[c] || c} ({c})</option>
                ))}
              </select>
              <button onClick={() => { setSupplierSearch(''); setSupplierCountryFilter('') }} className="text-sm text-slate-500 hover:text-slate-700 px-3">
                清除
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">供应商信息</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">国家</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">主营产品</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">联系方式</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">最小订单</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">认证</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">状态</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">加载中...</td></tr>
                  ) : filteredSuppliers.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-12 text-center text-slate-400">暂无数据</td></tr>
                  ) : filteredSuppliers.map(s => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800">{s.name_zh}</div>
                        <div className="text-xs text-slate-400">{s.name_en || '-'}</div>
                        <div className="text-xs text-slate-400 mt-1">ID: {s.id}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs font-medium">
                          {s.country}
                        </span>
                        <div className="text-xs text-slate-400 mt-1">{COUNTRY_NAMES[s.country] || s.region || '-'}</div>
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="text-xs text-slate-600 truncate">{s.main_products}</div>
                        <div className="text-xs text-slate-400 mt-1">HS: {s.main_hs_codes}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-xs text-slate-600">{s.contact_email || '-'}</div>
                        <div className="text-xs text-slate-400 mt-1">{s.min_order_kg ? `${s.min_order_kg.toLocaleString()} kg` : '-'}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {s.verified_chamber === 1 && (
                            <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs">商会认证</span>
                          )}
                          {s.verified_实地拜访 === 1 && (
                            <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">实地拜访</span>
                          )}
                          {s.verified_sgs === 1 && (
                            <span className="px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">SGS</span>
                          )}
                          {s.verified_chamber === 0 && s.verified_实地拜访 === 0 && s.verified_sgs === 0 && (
                            <span className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded text-xs">未认证</span>
                          )}
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          ⭐ {s.rating_avg.toFixed(1)} ({s.review_count}条评价)
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          s.status === 'verified' ? 'bg-green-100 text-green-700' :
                          s.status === 'new' ? 'bg-amber-100 text-amber-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {s.status === 'verified' ? '已验证' : s.status === 'new' ? '新增' : '已屏蔽'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-slate-200 text-sm text-slate-500">
              显示 {filteredSuppliers.length} / {suppliers.length} 条记录
            </div>
          </div>
        </div>
      )}

      {activeTab === 'countries' && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">代码</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">国家名称</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">英文名</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">中非合作</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">EPA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {countries.map((c, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-slate-100 rounded font-mono text-sm">{c.code}</span>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800">{c.name_zh}</td>
                      <td className="px-4 py-3 text-slate-600">{c.name_en}</td>
                      <td className="px-4 py-3">
                        {c.in_afcfta === 1 ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">✓ 中非合作论坛</span>
                        ) : (
                          <span className="px-2 py-1 bg-slate-100 text-slate-500 rounded text-xs">否</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {c.has_epa === 1 ? (
                          <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">✓ 贸易协定</span>
                        ) : (
                          <span className="px-2 py-1 bg-slate-100 text-slate-500 rounded text-xs">否</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-slate-200 text-sm text-slate-500">
              共 {countries.length} 个非洲国家
            </div>
          </div>
        </div>
      )}

      {activeTab === 'hs-codes' && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
            <input
              type="text"
              value={hsSearch}
              onChange={e => setHsSearch(e.target.value)}
              placeholder="搜索 HS 编码或产品名称..."
              className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
            />
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">HS编码</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">产品名称</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">品类</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">MFN税率</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">增值税</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">零关税</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredHsCodes.map((h, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-mono text-slate-800">{h.hs_10}</td>
                      <td className="px-4 py-3 text-slate-700">{h.name_zh}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-slate-100 rounded text-xs">{h.category || '-'}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{(h.mfn_rate * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-slate-600">{(h.vat_rate * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3">
                        {h.zero_tariff === true ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">✓ 零关税</span>
                        ) : h.zero_tariff === false ? (
                          <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs">✗ 不适用</span>
                        ) : (
                          <span className="px-2 py-1 bg-slate-100 text-slate-500 rounded text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-slate-200 text-sm text-slate-500">
              共 {filteredHsCodes.length} 条记录
            </div>
          </div>
        </div>
      )}

      {activeTab === 'freight' && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4">
            <select
              value={freightCountryFilter}
              onChange={e => setFreightCountryFilter(e.target.value)}
              className="px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-400 outline-none"
            >
              <option value="">全部国家</option>
              {[...new Set(freightRoutes.map(r => r.origin_country))].sort().map(c => (
                <option key={c} value={c}>{COUNTRY_NAMES[c] || c}</option>
              ))}
            </select>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">起点</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">目的港</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">运输方式</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">运费范围(USD)</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">运输时间</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">备注</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredFreight.map(r => (
                    <tr key={r.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800">{r.origin_port_zh}</div>
                        <div className="text-xs text-slate-400">{COUNTRY_NAMES[r.origin_country]} ({r.origin_country})</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-800">{r.dest_port_zh}</div>
                        <div className="text-xs text-slate-400">{r.dest_port}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-slate-100 rounded text-xs">
                          {r.transport_type === 'sea20gp' ? '20GP集装箱' :
                           r.transport_type === 'sea40hp' ? '40GP集装箱' :
                           r.transport_type === 'air' ? '空运' : r.transport_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-700">
                        ${r.cost_min_usd.toLocaleString()} - ${r.cost_max_usd.toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {r.transit_days_min}-{r.transit_days_max}天
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 max-w-xs truncate">
                        {r.notes || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-slate-200 text-sm text-slate-500">
              共 {filteredFreight.length} 条物流路线
            </div>
          </div>
        </div>
      )}

      {activeTab === 'cert-guides' && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">国家</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">证书类型</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">发证机构</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">费用</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">办理时间</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-slate-500">文件要求</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {certGuides.map(c => (
                    <tr key={c.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 bg-slate-100 rounded font-medium text-xs">{c.country_code}</span>
                        <div className="text-sm text-slate-800 mt-1">{c.country_name_zh}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-700">{c.cert_type_zh}</td>
                      <td className="px-4 py-3 text-slate-600 max-w-xs">{c.issuing_authority_zh}</td>
                      <td className="px-4 py-3 text-slate-600">
                        ${c.fee_usd_min}-{c.fee_usd_max} USD
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {c.days_min}-{c.days_max}天
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 max-w-xs">
                        {c.doc_requirements ? JSON.parse(c.doc_requirements).slice(0, 3).join(', ') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-3 border-t border-slate-200 text-sm text-slate-500">
              共 {certGuides.length} 个国家的证书指南
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sync' && (
        <div>
          <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
            <h2 className="font-semibold text-slate-800 mb-2">数据同步说明</h2>
            <p className="text-sm text-slate-600 mb-4">
              AfricaZero 使用 PostgreSQL 数据库（Neon 免费版）存储所有数据。
              系统启动时会自动将种子数据（供应商、国家、HS编码等）写入数据库。
            </p>
            <div className="p-4 bg-amber-50 rounded-lg text-sm text-amber-800">
              <strong>⚠️ 注意：</strong> 点击"同步到Neon"会重新初始化数据库，覆盖云端所有数据。
              如需备份，请先导出数据。
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">☁️</div>
                <div>
                  <h3 className="font-medium text-slate-800">Neon 云端数据库</h3>
                  <p className="text-sm text-slate-500">OnRender 托管</p>
                </div>
              </div>
              <div className="space-y-2 text-sm mb-4">
                {tableStats.map(t => (
                  <div key={t.table_name} className="flex justify-between">
                    <span className="text-slate-600">{t.table_name}</span>
                    <span className="font-medium text-slate-800">{t.record_count} 条</span>
                  </div>
                ))}
              </div>
              <button
                onClick={handleSyncToNeon}
                disabled={syncing}
                className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                ⬆️ 同步数据到 Neon
              </button>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl">💻</div>
                <div>
                  <h3 className="font-medium text-slate-800">本地数据库</h3>
                  <p className="text-sm text-slate-500">africa_zero.db</p>
                </div>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-600 mb-4">
                本地开发时使用 SQLite 数据库，路径：
                <code className="block mt-1 text-xs bg-slate-100 px-2 py-1 rounded">
                  africa-zero/data/africa_zero.db
                </code>
              </div>
              <button
                onClick={() => navigate('/database')}
                className="w-full py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                🔧 打开本地数据库
              </button>
            </div>
          </div>

          {syncMsg && (
            <div className="mt-4 px-4 py-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-sm">
              {syncMsg}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
