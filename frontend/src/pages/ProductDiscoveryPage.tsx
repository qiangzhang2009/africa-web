import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle, AlertCircle, TrendingUp, Package } from 'lucide-react'
import { PRODUCTS, CATEGORY_GROUPS, filterProducts } from '../data/products'

export default function ProductDiscoveryPage() {
  const [activeFilter, setActiveFilter] = useState('all')
  const [expandedProduct, setExpandedProduct] = useState<string | null>(null)

  const filtered = filterProducts(PRODUCTS, activeFilter)

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
                  a: '小额试水 (<¥5万)：咖啡、腰果、芝麻、葵花籽',
                  b: '中等规模 (¥5-50万)：皮革、香料、牛油果、乳木果油',
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
                  b: 'B2B供货 → 芝麻、腰果仁（走量稳定）',
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
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                新手入门完整路线图
              </Link>
              <button
                onClick={() => setActiveFilter('easy')}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-orange-50 text-slate-700 text-sm font-medium rounded-lg border border-slate-200 hover:border-orange-300 transition-colors"
              >
                查看「入门级」品类
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pro callout */}
      <div className="bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-xl p-4 mb-8 flex items-start gap-3">
        <Package className="w-5 h-5 text-orange-500 mt-0.5 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-orange-800 mb-1">标注「有门槛 / Pro」品类的完整信息</p>
          <p className="text-xs text-orange-700 leading-relaxed">
            矿产品（铜、钴、锰、铬、铝土矿）和部分加工品需要更大的资金规模、物流安排和资质要求。开通 Pro 后解锁详细供应链分析。
          </p>
        </div>
        <Link
          to="/pricing"
          className="shrink-0 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white text-xs font-semibold rounded-lg transition-colors"
        >
          开通 Pro
        </Link>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORY_GROUPS.map((f) => (
          <button
            key={f.value}
            onClick={() => setActiveFilter(f.value)}
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
          return (
            <div
              key={product.hsCode + product.name}
              className={`bg-white rounded-2xl border transition-colors ${
                isExpanded ? 'border-primary-300 shadow-md' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              {/* Card header */}
              <button
                className="w-full text-left p-5"
                onClick={() => setExpandedProduct(isExpanded ? null : product.hsCode)}
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
              {isExpanded && (
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

                  <div className="flex gap-3">
                    <Link
                      to={`/hs-lookup?q=${encodeURIComponent(product.name)}`}
                      className="flex items-center gap-1.5 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      查询HS详情 →
                    </Link>
                    <Link
                      to="/cost-calculator"
                      className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 text-sm font-medium rounded-lg transition-colors"
                    >
                      成本精算 →
                    </Link>
                    <Link
                      to="/origin-check"
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
