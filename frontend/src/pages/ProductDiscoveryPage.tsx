import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle, AlertCircle, TrendingUp, Calculator, Zap, Bookmark, BookmarkCheck } from 'lucide-react'
import { PRODUCTS, CATEGORY_GROUPS, filterProducts, type Product } from '../data/products'
import { calculateImportCost } from '../utils/api'
import { useAppStore } from '../hooks/useAppStore'
import { track } from '../utils/track'
import type { ImportCostResult } from '../types'

// Country name to code mapping
const COUNTRY_NAME_TO_CODE: Record<string, string> = {
  '埃塞俄比亚': 'ET', '肯尼亚': 'KE', '卢旺达': 'RW', '坦桑尼亚': 'TZ', '科特迪瓦': 'CI',
  '加纳': 'GH', '尼日利亚': 'NG', '喀麦隆': 'CM', '苏丹': 'SD', '安哥拉': 'AO',
  '赞比亚': 'ZM', '刚果（金）': 'CD', '刚果（布）': 'CG', '南非': 'ZA',
  '加蓬': 'GA', '莫桑比克': 'MZ', '贝宁': 'BJ', '埃及': 'EG',
  '马达加斯加': 'MG', '科摩罗': 'KM', '马里': 'ML', '布基纳法索': 'BF',
}

function fmt(n: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(n)
}

export default function ProductDiscoveryPage() {
  const [activeFilter, setActiveFilter] = useState('all')
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null)
  const [previewResult, setPreviewResult] = useState<{ product: Product; data: ImportCostResult } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const { addToInterestList, removeFromInterestList, isInInterestList } = useAppStore()

  const filtered = filterProducts(PRODUCTS, activeFilter)

  // Quick preview calculation
  async function handleQuickPreview(product: Product) {
    const originCode = product.originCountryCodes[0]
    if (!product.defaultQty || !product.defaultPrice || !originCode) {
      setPreviewError('该品类暂无默认参数，请手动调整')
      track.productQuickPreview(product.name, false)
      return
    }

    setPreviewLoading(true)
    setPreviewError(null)
    setPreviewResult(null)

    try {
      const data = await calculateImportCost({
        product_name: product.name,
        quantity_kg: product.defaultQty,
        fob_per_kg: product.defaultPrice,
        origin: originCode,
      })
      setPreviewResult({ product, data })
      track.productQuickPreview(product.name, true)
    } catch {
      setPreviewError('计算失败，请稍后重试')
      track.productQuickPreview(product.name, false)
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">非洲选品清单</h1>
        <p className="text-slate-600">
          基于零关税政策 × 非洲优势货源 × 入门门槛，筛选出的可行品类。标注难度和适合人群，小白也能看懂。
        </p>
      </div>

      {/* Beginner guidance */}
      <div className="bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 border border-orange-200 rounded-2xl p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-orange-100 rounded-xl flex items-center justify-center shrink-0">
            <span className="text-xl">🤔</span>
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-slate-900 mb-1">不知道做什么方向？先回答三个问题</h2>
            <p className="text-sm text-slate-600 mb-4 leading-relaxed">
              选品是新人最难的部分。我们把问题拆成三步，帮助你快速找到适合的方向——不需要经验，只需要知道自己属于哪类。
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              {[
                {
                  icon: '💼',
                  q: '你有多少启动资金？',
                  a: '小额试水 (<¥5万)：咖啡，腰果、芝麻、葵花籽',
                  b: '中等规模 (¥5-50万)：皮革、香料，牛油果、乳木果油',
                  c: '大宗贸易 (>¥50万)：矿产品、原油、天然橡胶',
                },
                {
                  icon: '🏭',
                  q: '你有没有下游渠道？',
                  a: '有食品/工厂渠道 → 选原材料 B2B',
                  b: '有零售/私域资源 → 选咖啡/可可/精油走品牌路线',
                  c: '没有渠道 → 先做选品调研+小批量找感觉',
                },
                {
                  icon: '📦',
                  q: '你想做零售还是批发？',
                  a: '零售/私域 → 咖啡、可可、乳木果油（品牌溢价高）',
                  b: 'B2B供货 → 芝麻，腰果仁（走量稳定）',
                  c: '供应链服务 → 找下游买家再进货',
                },
              ].map((card, i) => (
                <div key={i} className="bg-white/80 rounded-xl p-4 border border-orange-100">
                  <div className="text-xl mb-2">{card.icon}</div>
                  <div className="text-sm font-semibold text-slate-700 mb-2">{card.q}</div>
                  <div className="space-y-1">
                    {[card.a, card.b, card.c].map((t, j) => (
                      <div key={j} className="text-xs text-slate-500 leading-relaxed">• {t}</div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                to="/getting-started"
                onClick={() => track.productNav('/getting-started')}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                新手入门完整路线图
              </Link>
              <button
                onClick={() => { setActiveFilter('easy'); track.productFilterChange('easy', filterProducts(PRODUCTS, 'easy').length) }}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-orange-50 text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:border-orange-300 transition-colors"
              >
                查看「入门级」品类
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORY_GROUPS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setActiveFilter(f.value); track.productFilterChange(f.value, filterProducts(PRODUCTS, f.value).length) }}
            className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
              activeFilter === f.value
                ? 'bg-primary-500 text-white border-primary-500'
                : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300 hover:text-primary-600'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Results count */}
      <p className="text-sm text-slate-500 mb-4">{filtered.length} 个品类</p>

      {/* Product list */}
      <div className="space-y-4">
        {filtered.map((product) => {
          const isExpanded = expandedProduct === product.hsCode
          const isPreviewing = previewResult?.product.hsCode === product.hsCode
          return (
            <div
              key={product.hsCode + product.name}
              className={`bg-white rounded-2xl border transition-colors ${
                isExpanded || isPreviewing ? 'border-primary-300 shadow-md' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {/* Card header */}
              <button
                className="w-full text-left p-5"
                onClick={() => {
                  setExpandedProduct(isExpanded ? null : product.hsCode)
                  setPreviewResult(null)
                  if (!isExpanded) track.productExpand(product.name, product.hsCode)
                }}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold text-slate-900">{product.name}</span>
                      <span className="text-xs text-slate-400">{product.nameEn}</span>
                      <span className="font-mono text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                        {product.hsCode}
                      </span>
                      {product.zeroTariff ? (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded-full">
                          <CheckCircle className="w-3 h-3" />
                          零关税
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-full">
                          <AlertCircle className="w-3 h-3" />
                          不适用
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
                      <span>MFN基准税率：{product.mfnRate}</span>
                      <span>主要产区：{product.originCountries.join('、')}</span>
                      <span className={
                        product.difficulty === '🥉 入门' ? 'text-green-600' :
                        product.difficulty === '🥈 中等' ? 'text-yellow-600' : 'text-red-600'
                      }>
                        {product.difficulty}
                      </span>
                      {product.tier === 'pro' && (
                        <span className="text-orange-500 font-medium">Pro</span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className={`w-4 h-4 text-slate-400 mt-1 shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>
              </button>

              {/* Expanded content */}
              {(isExpanded || isPreviewing) && (
                <div className="px-5 pb-5 border-t border-slate-100 pt-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">适合人群</div>
                      <div className="text-sm text-slate-800">{product.suitable}</div>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">难度</div>
                      <div className="text-sm text-slate-800">{product.difficulty}</div>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-4">
                      <div className="text-xs font-medium text-slate-500 mb-1">零关税节省</div>
                      <div className="text-sm text-slate-800">vs MFN省{product.mfnRate}</div>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 mb-4">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-amber-800 mb-1">风险提示</p>
                        <p className="text-xs text-amber-700 leading-relaxed">{product.riskNote}</p>
                      </div>
                    </div>
                  </div>

                  <div className="bg-green-50 border border-green-100 rounded-xl p-4 mb-5">
                    <div className="flex items-start gap-2">
                      <TrendingUp className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-green-800 mb-1">商业模式建议</p>
                        <p className="text-xs text-green-700 leading-relaxed">{product.modelTip}</p>
                      </div>
                    </div>
                  </div>

                  {/* Quick preview result */}
                  {isPreviewing && previewResult && previewResult.data && previewResult.data.breakdown && (
                    <div className="bg-gradient-to-br from-primary-50 to-sky-50 border border-primary-200 rounded-xl p-4 mb-5">
                      <div className="flex items-center gap-2 mb-3">
                        <Calculator className="w-4 h-4 text-primary-600" />
                        <span className="text-sm font-semibold text-primary-800">快速估算结果（{product.defaultQty}kg / ${product.defaultPrice}/kg）</span>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-white/80 rounded-lg p-3 text-center">
                          <div className="text-xs text-slate-500 mb-1">FOB货值</div>
                          <div className="text-sm font-bold text-slate-900">{fmt(previewResult.data.breakdown.fob_value)}</div>
                        </div>
                        <div className="bg-white/80 rounded-lg p-3 text-center">
                          <div className="text-xs text-slate-500 mb-1">国际运费</div>
                          <div className="text-sm font-bold text-slate-900">{fmt(previewResult.data.breakdown.international_freight)}</div>
                        </div>
                        <div className="bg-white/80 rounded-lg p-3 text-center">
                          <div className="text-xs text-slate-500 mb-1">关税</div>
                          <div className="text-sm font-bold text-green-600">{product.zeroTariff ? '¥0' : fmt(previewResult.data.breakdown.tariff)}</div>
                        </div>
                        <div className="bg-white/80 rounded-lg p-3 text-center border-2 border-primary-200">
                          <div className="text-xs text-slate-500 mb-1">到岸总成本</div>
                          <div className="text-sm font-bold text-primary-700">{fmt(previewResult.data.breakdown.total_cost)}</div>
                        </div>
                      </div>
                      <div className="mt-2 text-xs text-primary-700 text-center">
                        原产国：{COUNTRY_NAME_TO_CODE[product.originCountries[0]] || product.originCountryCodes[0]} · 回本需卖 {previewResult.data.breakdown.payback_packages} 包
                      </div>
                    </div>
                  )}

                  {previewError && isPreviewing && (
                    <div className="bg-red-50 border border-red-200 rounded-xl p-3 mb-5 text-sm text-red-700">
                      {previewError}
                    </div>
                  )}

                  {/* Action buttons */}
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        if (isInInterestList(product.hsCode)) {
                          removeFromInterestList(product.hsCode)
                          track.productRemoveInterest(product.name, product.hsCode)
                        } else {
                          addToInterestList({
                            hsCode: product.hsCode,
                            name: product.name,
                            originCountries: product.originCountries,
                            originCountryCodes: product.originCountryCodes,
                            mfnRate: product.mfnRate,
                            zeroTariff: product.zeroTariff,
                            difficulty: product.difficulty,
                            addedAt: Date.now(),
                            defaultQty: product.defaultQty,
                            defaultPrice: product.defaultPrice,
                          })
                          track.productAddInterest(product.name, product.hsCode)
                        }
                      }}
                      className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                        isInInterestList(product.hsCode)
                          ? 'bg-orange-100 border border-orange-300 text-orange-700 hover:bg-orange-200'
                          : 'bg-white border border-slate-300 text-slate-700 hover:border-primary-400'
                      }`}
                    >
                      {isInInterestList(product.hsCode) ? (
                        <><BookmarkCheck className="w-4 h-4" />已加入清单</>
                      ) : (
                        <><Bookmark className="w-4 h-4" />加入意向清单</>
                      )}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleQuickPreview(product)
                        if (!isExpanded) setExpandedProduct(product.hsCode)
                      }}
                      disabled={previewLoading && previewResult?.product.hsCode === product.hsCode}
                      className="flex items-center gap-1.5 px-4 py-2 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {previewLoading && previewResult?.product.hsCode === product.hsCode ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          计算中...
                        </>
                      ) : (
                        <>
                          <Zap className="w-4 h-4" />
                          快速估算
                        </>
                      )}
                    </button>
                    <Link
                      to={`/cost-calculator?product=${encodeURIComponent(product.name)}&qty=${product.defaultQty || ''}&price=${product.defaultPrice || ''}&origin=${product.originCountryCodes[0] || ''}`}
                      onClick={() => track.productNav('/cost-calculator', { product: product.name, origin: product.originCountryCodes[0] || '' })}
                      className="flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      <Calculator className="w-4 h-4" />
                      完整成本精算 →
                    </Link>
                    <Link
                      to={`/calculator?hs=${product.hsCode}&origin=${product.originCountryCodes[0] || ''}`}
                      onClick={() => track.productNav('/calculator', { hs: product.hsCode, origin: product.originCountryCodes[0] || '' })}
                      className="flex items-center gap-1.5 px-4 py-2 bg-slate-700 hover:bg-slate-800 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      关税计算 →
                    </Link>
                    <Link
                      to={`/origin-check?hs=${product.hsCode}&origin=${product.originCountryCodes[0] || ''}`}
                      onClick={() => track.productNav('/origin-check', { hs: product.hsCode, origin: product.originCountryCodes[0] || '' })}
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-sm font-medium rounded-lg transition-colors"
                    >
                      原产地自测 →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom CTA */}
      <div className="mt-12 text-center">
        <p className="text-sm text-slate-500 mb-4">
          选好品类后，用工具验证成本和原产地资格
        </p>
        <div className="flex justify-center gap-3">
          <Link
            to="/cost-calculator"
            className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-medium rounded-xl transition-colors"
          >
            成本精算器
          </Link>
          <Link
            to="/origin-check"
            className="px-6 py-3 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 font-medium rounded-xl transition-colors"
          >
            原产地自测
          </Link>
        </div>
      </div>
    </div>
  )
}
