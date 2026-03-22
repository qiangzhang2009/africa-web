import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Globe, Search, CheckCircle,
  ArrowRight, MapPin, ExternalLink, MessageSquare, X,
} from 'lucide-react'
import {
  searchSuppliers, listSupplierCountries,
  getSupplier, getSupplierReviews,
  getSupplierCompare,
} from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'
import type {
  SupplierListItem, Supplier, SupplierReview,
  SupplierCompareResult,
} from '../types'

function StarRating({ score }: { score: number }) {
  return (
    <span className="text-amber-400 font-bold text-sm">
      {score.toFixed(1)} {Array.from({ length: 5 }, (_, i) => (
        <span key={i} className={i < Math.round(score) ? 'text-amber-400' : 'text-slate-300'}>★</span>
      ))}
    </span>
  )
}

function VerifiedBadge({ type }: { type: 'verified' | 'new' | 'pending' }) {
  const map = {
    verified: { label: '🏅 优质认证', color: 'bg-green-50 text-green-700 border-green-200' },
    new: { label: '🆕 新加入', color: 'bg-blue-50 text-blue-700 border-blue-200' },
    pending: { label: '⚠️ 待观察', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  }
  const m = map[type] || map.new
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${m.color}`}>
      {m.label}
    </span>
  )
}

function SupplierCard({
  supplier, onClick,
}: {
  supplier: SupplierListItem
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full bg-white rounded-2xl border border-slate-200 p-5 text-left hover:shadow-lg hover:border-blue-200 transition-all group"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-semibold text-slate-900">{supplier.name_zh}</span>
            <VerifiedBadge type={supplier.status as 'verified' | 'new' | 'pending'} />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Globe className="w-3 h-3" />
            <span>{supplier.country}</span>
            {supplier.region && (
              <>
                <span>·</span>
                <MapPin className="w-3 h-3" />
                <span>{supplier.region}</span>
              </>
            )}
          </div>
        </div>
        {supplier.verified_chamber && (
          <div className="shrink-0 w-7 h-7 bg-green-100 rounded-full flex items-center justify-center" title="商会认证">
            <CheckCircle className="w-4 h-4 text-green-600" />
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1 mb-3">
        {supplier.main_products.slice(0, 3).map((p, i) => (
          <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
            {p}
          </span>
        ))}
        {supplier.main_products.length > 3 && (
          <span className="text-xs text-slate-400">+{supplier.main_products.length - 3}</span>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {supplier.rating_avg > 0 && (
            <div className="flex items-center gap-1">
              <StarRating score={supplier.rating_avg} />
              <span className="text-xs text-slate-400">({supplier.review_count})</span>
            </div>
          )}
          {supplier.export_years > 0 && (
            <span className="text-xs text-slate-500">出口中国 {supplier.export_years} 年</span>
          )}
        </div>
        <div className="flex items-center gap-1 text-sm text-blue-600 font-medium group-hover:text-blue-700">
          查看详情
          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>
    </button>
  )
}

function SupplierDetail({
  supplier, onClose,
}: {
  supplier: Supplier
  onClose: () => void
}) {
  const navigate = useNavigate()
  const [compare, setCompare] = useState<SupplierCompareResult | null>(null)
  const [reviews, setReviews] = useState<SupplierReview[]>([])
  const [showContact, setShowContact] = useState(false)
  const { isLoggedIn, tier } = useAppStore()

  useEffect(() => {
    getSupplierCompare(supplier.id).then(setCompare).catch(() => {})
    getSupplierReviews(supplier.id, 1, 5).then(r => setReviews(r.reviews)).catch(() => {})
  }, [supplier.id])

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl my-8 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 p-6 text-white relative">
          <button onClick={onClose} className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl leading-none">&times;</button>
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center text-2xl shrink-0">
              🌍
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <h2 className="text-xl font-bold">{supplier.name_zh}</h2>
                {supplier.name_en && <span className="text-slate-300 text-sm">{supplier.name_en}</span>}
              </div>
              <div className="flex items-center gap-2 text-slate-300 text-sm mb-2">
                <Globe className="w-3.5 h-3.5" />
                <span>{supplier.country_name_zh || supplier.country}</span>
                {supplier.region && <><span>·</span><MapPin className="w-3.5 h-3.5" /><span>{supplier.region}</span></>}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <VerifiedBadge type={supplier.status as 'verified' | 'new' | 'pending'} />
                {supplier.verified_chamber && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                    <CheckCircle className="w-3 h-3" /> 商会认证
                  </span>
                )}
                {supplier.verified_实地拜访 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                    🏢 实地拜访
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6">
          {/* Quick stats */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: '出口中国', val: `${supplier.export_years}年`, icon: '📅' },
              { label: '年出口量', val: supplier.annual_export_tons ? `${(supplier.annual_export_tons / 1000).toFixed(0)}T` : '—', icon: '📦' },
              { label: '最低起订', val: supplier.min_order_kg ? `${(supplier.min_order_kg / 1000).toFixed(0)}T` : '—', icon: '🔢' },
              { label: '用户评分', val: supplier.rating_avg > 0 ? `${supplier.rating_avg}★` : '暂无', icon: '⭐' },
            ].map(s => (
              <div key={s.label} className="bg-slate-50 rounded-xl p-3 text-center">
                <div className="text-xs text-slate-500 mb-1">{s.label}</div>
                <div className="font-semibold text-slate-800">{s.val}</div>
              </div>
            ))}
          </div>

          {/* Intro */}
          {supplier.intro && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-2">公司简介</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{supplier.intro}</p>
            </div>
          )}

          {/* Products & HS */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-slate-700 mb-2">主营产品</h3>
            <div className="flex flex-wrap gap-2 mb-3">
              {supplier.main_products.map((p, i) => (
                <span key={i} className="px-3 py-1 bg-primary-50 text-primary-700 text-sm rounded-full font-medium border border-primary-200">
                  {p}
                </span>
              ))}
            </div>
            <div className="text-xs text-slate-500">
              HS编码：{supplier.main_hs_codes.join('、')}
            </div>
          </div>

          {/* Trade terms */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="bg-slate-50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">付款方式</div>
              <div className="text-sm font-medium text-slate-800">{supplier.payment_terms || '联系确认'}</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <div className="text-xs text-slate-500 mb-1">最低起订量</div>
              <div className="text-sm font-medium text-slate-800">
                {supplier.min_order_kg ? `${supplier.min_order_kg.toLocaleString()} kg` : '联系确认'}
              </div>
            </div>
          </div>

          {/* Freight estimate */}
          {compare && compare.recommended_route && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm font-semibold text-blue-900">推荐物流路线 + 运费估算</span>
              </div>
              <div className="flex items-center gap-2 text-sm mb-2">
                <span className="text-slate-700">{compare.recommended_route.origin_port_zh}</span>
                <ArrowRight className="w-4 h-4 text-blue-400" />
                <span className="text-slate-700">{compare.recommended_route.dest_port_zh}</span>
                <span className="text-slate-400">·</span>
                <span className="text-blue-700 font-medium">{compare.recommended_route.cost_range_usd}/集装箱</span>
                <span className="text-slate-400">·</span>
                <span className="text-slate-500">{compare.recommended_route.transit_days}</span>
              </div>
              {compare.estimated_freight && (
                <div className="flex items-center gap-3 text-xs text-slate-600">
                  <span>海运费：¥{compare.estimated_freight.sea_freight_cny.toLocaleString()}</span>
                  <span>保险：¥{(compare.estimated_freight.insurance_usd * 7.25).toLocaleString()}</span>
                  <span>清关：¥{compare.estimated_freight.clearance_cny.toLocaleString()}</span>
                  <span className="font-semibold text-blue-700">
                    合计约 ¥{compare.estimated_freight.total_estimate_cny.toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Contact */}
          {(isLoggedIn && tier !== 'free') ? (
            showContact ? (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
                <div className="text-sm font-semibold text-green-800 mb-3">联系方式</div>
                <div className="space-y-2">
                  {supplier.contact_email && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-slate-500 w-16">邮箱：</span>
                      <a href={`mailto:${supplier.contact_email}`} className="text-blue-600 hover:underline">{supplier.contact_email}</a>
                    </div>
                  )}
                  {supplier.contact_phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-slate-500 w-16">电话：</span>
                      <span className="text-slate-800">{supplier.contact_phone}</span>
                    </div>
                  )}
                  {supplier.website && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-slate-500 w-16">网站：</span>
                      <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                        {supplier.website} <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowContact(true)}
                className="w-full py-3 border-2 border-dashed border-green-300 text-green-600 rounded-xl hover:bg-green-50 transition-colors font-medium mb-6"
              >
                查看联系方式（Pro专属）
              </button>
            )
          ) : (
            !isLoggedIn ? (
              <button
                onClick={() => navigate('/login?redirect=/suppliers')}
                className="w-full py-3 border-2 border-dashed border-slate-300 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors font-medium mb-6"
              >
                登录后查看联系方式
              </button>
            ) : (
              <button
                onClick={() => navigate('/pricing')}
                className="w-full py-3 border-2 border-dashed border-amber-300 text-amber-600 rounded-xl hover:bg-amber-50 transition-colors font-medium mb-6"
              >
                升级Pro后查看联系方式
              </button>
            )
          )}

          {/* Reviews */}
          {reviews.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                用户评价（{supplier.review_count} 条）
              </h3>
              <div className="space-y-3">
                {reviews.map(r => (
                  <div key={r.id} className="bg-slate-50 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium text-slate-700">{r.user_email?.split('@')[0] || '匿名用户'}</span>
                      {r.is_verified_deal && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">已验证交易</span>
                      )}
                    </div>
                    <div className="flex gap-4 text-xs text-slate-500 mb-2">
                      <span>质量：{'★'.repeat(Math.round(r.quality_score))}</span>
                      <span>交货：{'★'.repeat(Math.round(r.delivery_score))}</span>
                      <span>沟通：{'★'.repeat(Math.round(r.communication_score))}</span>
                    </div>
                    {r.comment && <p className="text-sm text-slate-600 leading-relaxed">{r.comment}</p>}
                    {r.created_at && (
                      <p className="text-xs text-slate-400 mt-2">{new Date(r.created_at).toLocaleDateString('zh-CN')}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/cost-calculator?origin=${supplier.country}`)}
              className="flex-1 py-3 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl transition-colors"
            >
              一键测算进口成本
            </button>
            <button
              onClick={() => navigate(`/certificate?country=${supplier.country}`)}
              className="flex-1 py-3 bg-green-50 hover:bg-green-100 text-green-700 font-semibold rounded-xl transition-colors border border-green-200"
            >
              了解证书办理
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function SuppliersPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [countries, setCountries] = useState<{
    code: string; name_zh: string; name_en?: string; supplier_count: number; verified_count: number
  }[]>([])
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [selectedCountry, setSelectedCountry] = useState(searchParams.get('country') || '')
  const [keyword, setKeyword] = useState('')
  const [verifiedOnly, setVerifiedOnly] = useState(false)
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null)

  const PAGE_SIZE = 20

  useEffect(() => {
    listSupplierCountries().then(setCountries).catch(() => {})
  }, [])

  const fetchSuppliers = useCallback(async () => {
    setLoading(true)
    try {
      const result = await searchSuppliers({
        country: selectedCountry || undefined,
        keyword: keyword || undefined,
        verified_only: verifiedOnly,
        page,
        page_size: PAGE_SIZE,
      })
      setSuppliers(result.suppliers)
      setTotal(result.total)
    } catch {
      setSuppliers([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [selectedCountry, keyword, verifiedOnly, page])

  useEffect(() => {
    setPage(1)
  }, [selectedCountry, keyword, verifiedOnly])

  useEffect(() => {
    fetchSuppliers()
  }, [fetchSuppliers])

  async function handleOpenSupplier(s: SupplierListItem) {
    try {
      const full = await getSupplier(s.id)
      setSelectedSupplier(full)
    } catch {
      setSelectedSupplier(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center">
            <Globe className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-3xl font-heading font-bold text-slate-900">非洲供应商发现</h1>
          </div>
        </div>
        <p className="text-slate-600">
          从零关税政策 × 原产地合规 × 物流成本三维度，精选非洲认证供应商。
          所有供应商均经过商会认证，已验证出口中国历史。
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: '认证供应商', val: total, suffix: '家', color: 'text-emerald-600' },
          { label: '覆盖国家', val: countries.length, suffix: '国', color: 'text-blue-600' },
          { label: '已认证商会', val: suppliers.filter(s => s.verified_chamber).length, suffix: '家', color: 'text-green-600' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
            <div className={`text-2xl font-bold ${s.color}`}>{s.val}{s.suffix}</div>
            <div className="text-xs text-slate-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              placeholder="搜索供应商名称或产品..."
              className="w-full pl-9 pr-8 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            {keyword && (
              <button onClick={() => setKeyword('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Country filter */}
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-slate-400 shrink-0" />
            <select
              value={selectedCountry}
              onChange={e => setSelectedCountry(e.target.value)}
              className="px-3 py-2.5 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="">全部国家</option>
              {countries.map(c => (
                <option key={c.code} value={c.code}>
                  {c.name_zh} ({c.supplier_count}家)
                </option>
              ))}
            </select>
          </div>

          {/* Verified only */}
          <button
            onClick={() => setVerifiedOnly(!verifiedOnly)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all ${
              verifiedOnly
                ? 'bg-green-50 border-green-300 text-green-700'
                : 'border-slate-300 text-slate-600 hover:border-green-300'
            }`}
          >
            <CheckCircle className={`w-4 h-4 ${verifiedOnly ? 'text-green-600' : 'text-slate-400'}`} />
            仅显示认证供应商
          </button>
        </div>

        {/* Country pills */}
        {countries.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-slate-100">
            {countries.slice(0, 12).map(c => (
              <button
                key={c.code}
                onClick={() => setSelectedCountry(selectedCountry === c.code ? '' : c.code)}
                className={`px-3 py-1.5 text-xs rounded-full border transition-all ${
                  selectedCountry === c.code
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-700 font-medium'
                    : 'bg-white border-slate-200 text-slate-600 hover:border-emerald-200'
                }`}
              >
                {c.name_zh} {c.supplier_count > 0 && <span className="text-slate-400">({c.supplier_count})</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-16">
          <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-500">搜索供应商...</p>
        </div>
      ) : suppliers.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-slate-600 mb-4">未找到匹配的供应商</p>
          <button
            onClick={() => { setSelectedCountry(''); setKeyword(''); setVerifiedOnly(false) }}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm hover:bg-emerald-600 transition-colors"
          >
            清空筛选
          </button>
        </div>
      ) : (
        <>
          <div className="text-sm text-slate-500 mb-4">
            共找到 <strong className="text-slate-700">{total}</strong> 家供应商
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {suppliers.map(s => (
              <SupplierCard key={s.id} supplier={s} onClick={() => handleOpenSupplier(s)} />
            ))}
          </div>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex justify-center gap-2 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 hover:bg-slate-50"
              >
                上一页
              </button>
              <span className="px-4 py-2 text-sm text-slate-600">
                第 {page} / {Math.ceil(total / PAGE_SIZE)} 页
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={page * PAGE_SIZE >= total}
                className="px-4 py-2 border border-slate-300 rounded-lg text-sm disabled:opacity-50 hover:bg-slate-50"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}

      {/* CTA */}
      {suppliers.length > 0 && (
        <div className="mt-8 bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-200 rounded-2xl p-6 text-center">
          <p className="text-sm text-emerald-700 mb-4">
            想找更多供应商？或者您的目标国家不在列表中？
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate('/products')}
              className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white font-medium rounded-xl transition-colors"
            >
              浏览选品清单 →
            </button>
            <a
              href="mailto:zxq@zxqconsulting.com"
              className="px-6 py-2.5 bg-white border border-emerald-300 text-emerald-700 font-medium rounded-xl hover:bg-emerald-50 transition-colors"
            >
              联系我们定制推荐
            </a>
          </div>
        </div>
      )}

      {/* Supplier detail modal */}
      {selectedSupplier && (
        <SupplierDetail
          supplier={selectedSupplier}
          onClose={() => setSelectedSupplier(null)}
        />
      )}
    </div>
  )
}
