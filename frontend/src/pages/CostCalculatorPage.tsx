import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { calculateImportCost } from '../utils/api'
import { track } from '../utils/track'
import type { ImportCostResult } from '../types'

function fmt(n: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(n)
}

// ─── 快速选择预置（关联选品清单）──────────────────────────────────────────────
type Origin = { code: string; name: string }

const PRESET_CATEGORIES = [
  {
    label: '🥉 入门级（小额试水 <¥5万）',
    color: 'bg-green-50 border-green-200',
    items: [
      { label: '埃塞俄比亚 耶加雪菲', name: '埃塞俄比亚耶加雪菲生豆', qty: '20', price: '6', origin: { code: 'ET', name: '埃塞俄比亚' }, note: '精品咖啡，电商热销' },
      { label: '肯尼亚 AA', name: '肯尼亚AA生豆', qty: '30', price: '7', origin: { code: 'KE', name: '肯尼亚' }, note: '酸感强，精品烘焙商首选' },
      { label: '加纳 可可豆', name: '加纳可可豆', qty: '50', price: '3.5', origin: { code: 'GH', name: '加纳' }, note: '全球最大可可产区之一' },
      { label: '科特迪瓦 可可豆', name: '科特迪瓦可可豆', qty: '100', price: '2.8', origin: { code: 'CI', name: '科特迪瓦' }, note: '产量大，性价比高' },
      { label: '坦桑尼亚 腰果仁', name: '坦桑尼亚腰果仁', qty: '10', price: '5.5', origin: { code: 'TZ', name: '坦桑尼亚' }, note: '非洲腰果主产国' },
      { label: '苏丹 芝麻', name: '苏丹芝麻', qty: '20', price: '1.4', origin: { code: 'SD', name: '苏丹' }, note: '全球最大芝麻出口国之一' },
      { label: '马达加斯加 香草', name: '马达加斯加香草', qty: '1', price: '120', origin: { code: 'MG', name: '马达加斯加' }, note: '全球香草80%来自此地' },
    ],
  },
  {
    label: '🥈 中等级（¥5-50万）',
    color: 'bg-yellow-50 border-yellow-200',
    items: [
      { label: '埃塞俄比亚 生牛皮', name: '埃塞俄比亚生牛皮', qty: '20', price: '1.2', origin: { code: 'ET', name: '埃塞俄比亚' }, note: '皮革质量优良' },
      { label: '贝宁 棉花', name: '贝宁棉花', qty: '50', price: '1.8', origin: { code: 'BJ', name: '贝宁' }, note: '非洲重要产棉国' },
      { label: '加蓬 热带硬木', name: '加蓬硬木原木', qty: '30', price: '0.4', origin: { code: 'GA', name: '加蓬' }, note: 'FSC认证硬木资源丰富' },
      { label: '坦桑尼亚 丁香', name: '坦桑尼亚丁香', qty: '5', price: '15', origin: { code: 'TZ', name: '坦桑尼亚' }, note: '香料贸易小众赛道' },
    ],
  },
  {
    label: '🥇 有门槛（¥50万以上）',
    color: 'bg-red-50 border-red-200',
    items: [
      { label: '赞比亚 铜矿砂', name: '赞比亚铜矿砂', qty: '500', price: '0.2', origin: { code: 'ZM', name: '赞比亚' }, note: '大宗商品，需稳定下游' },
      { label: '刚果（金）钴矿砂', name: '刚果金钴矿砂', qty: '100', price: '8', origin: { code: 'CD', name: '刚果（金）' }, note: '新能源产业链热门' },
      { label: '南非 锰矿', name: '南非锰矿', qty: '1000', price: '0.08', origin: { code: 'ZA', name: '南非' }, note: '钢铁厂直供，需规模运作' },
    ],
  },
]

type PresetItem = {
  label: string
  name: string
  qty: string
  price: string
  origin: Origin
  note: string
}

export default function CostCalculatorPage() {
  const [searchParams] = useSearchParams()

  const [productName, setProductName] = useState('')
  const [quantityKg, setQuantityKg] = useState('')
  const [fobPerKg, setFobPerKg] = useState('')
  const [origin, setOrigin] = useState('ET')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportCostResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string>('🥉 入门级（小额试水 <¥5万）')

  // Auto-fill from URL params (passed from product detail page)
  useEffect(() => {
    const p = searchParams.get('product')
    const q = searchParams.get('qty')
    const pr = searchParams.get('price')
    const o = searchParams.get('origin')
    if (p) setProductName(decodeURIComponent(p))
    if (q) setQuantityKg(q)
    if (pr) setFobPerKg(pr)
    if (o) setOrigin(o)
  }, [searchParams])

  function applyPreset(item: PresetItem) {
    setProductName(item.name)
    setQuantityKg(item.qty)
    setFobPerKg(item.price)
    setOrigin(item.origin.code)
    track.costSelectPreset(item.label, item.origin.code)
  }

  async function handleCalc() {
    if (!productName || !quantityKg || !fobPerKg) {
      setError('请填写所有必填项，或从下方选择一个品类')
      track.calcError('cost_calc_missing_fields')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const input = {
        product_name: productName,
        quantity_kg: parseFloat(quantityKg),
        fob_per_kg: parseFloat(fobPerKg),
        origin,
      }
      const data = await calculateImportCost(input)
      setResult(data)
      track.costSubmit(input, data.success)
      if (data.success) {
        track.costResultShown(data as unknown as Record<string, unknown>)
      } else {
        track.calcError(`cost_calc_failed: ${data.message}`)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'network_error'
      setError('计算失败，请稍后重试。如果问题持续，请检查网络连接。')
      track.calcError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">成本精算器</h1>
        <p className="text-slate-600">
          输入采购信息，一键获取完整到岸成本、回本测算与原产地证书指南。
        </p>
      </div>

      {/* 选品清单关联提示 */}
      <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-6 flex items-start gap-3">
        <span className="text-xl mt-0.5 shrink-0">💡</span>
        <div>
          <p className="text-sm font-medium text-orange-800 mb-1">不知道选什么品类？先看选品清单</p>
          <p className="text-xs text-orange-700 mb-2">选品清单按「零关税覆盖 × 资金门槛 × 下游渠道」三维筛选，适合新人的品类已标注「入门级」。</p>
          <Link
            to="/products"
            className="inline-flex items-center gap-1 text-xs text-orange-600 font-semibold hover:text-orange-700"
          >
            浏览完整选品清单 → 找到适合你的品类后再回来精算成本
          </Link>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 mb-8">
        {/* 快速选择预置 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <p className="block text-sm font-semibold text-slate-700">快速选择（按资金规模）</p>
            <p className="text-xs text-slate-400">点击即可填入估算数据</p>
          </div>

          {/* 分类切换 */}
          <div className="flex flex-wrap gap-2 mb-3">
            {PRESET_CATEGORIES.map((cat) => (
              <button
                key={cat.label}
                onClick={() => { setActiveCategory(cat.label); track.costSelectCategory(cat.label) }}
                className={`px-3 py-1 text-xs rounded-full border transition-colors font-medium ${
                  activeCategory === cat.label
                    ? 'bg-orange-500 text-white border-orange-500'
                    : 'bg-white border-slate-200 text-slate-600 hover:border-orange-300'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          {/* 当前分类下的选项 */}
          {PRESET_CATEGORIES.map((cat) => (
            activeCategory === cat.label && (
              <div key={cat.label} className={`border rounded-xl p-4 ${cat.color}`}>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                  {cat.items.map((item) => (
                    <button
                      key={item.label}
                      onClick={() => applyPreset(item)}
                      className="text-left bg-white rounded-lg border border-white/80 p-2.5 hover:border-primary-300 hover:shadow-sm transition-all group"
                    >
                      <div className="text-sm font-medium text-slate-800 group-hover:text-primary-600 transition-colors leading-tight mb-0.5">
                        {item.label}
                      </div>
                      <div className="text-xs text-slate-400">
                        {item.qty}kg · ${item.price}/kg · {item.origin.name}
                      </div>
                      <div className="text-xs text-orange-600 mt-0.5">{item.note}</div>
                    </button>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-white/50 flex items-center gap-2">
                  <Link
                    to={`/products?q=${encodeURIComponent(activeCategory.split('（')[0])}`}
                    className="text-xs text-orange-700 font-medium hover:text-orange-800"
                  >
                    查看该类别全部品类 →
                  </Link>
                  <span className="text-xs text-slate-400">|</span>
                  <Link
                    to="/hs-lookup"
                    className="text-xs text-orange-700 font-medium hover:text-orange-800"
                  >
                    查询精确HS编码 →
                  </Link>
                </div>
              </div>
            )
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="block text-sm font-medium text-slate-700 mb-1.5">商品名称 *</p>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="从上方选择或手动输入"
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <p className="block text-sm font-medium text-slate-700 mb-1.5">采购量（kg）*</p>
            <input
              type="number"
              value={quantityKg}
              onChange={(e) => setQuantityKg(e.target.value)}
              placeholder="如 20"
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <p className="block text-sm font-medium text-slate-700 mb-1.5">FOB单价（USD/kg）*</p>
            <input
              type="number"
              value={fobPerKg}
              onChange={(e) => setFobPerKg(e.target.value)}
              placeholder="如 6"
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <p className="block text-sm font-medium text-slate-700 mb-1.5">原产国</p>
            <select
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
            >
              <option value="ET">🇪🇹 埃塞俄比亚</option>
              <option value="KE">🇰🇪 肯尼亚</option>
              <option value="GH">🇬🇭 加纳</option>
              <option value="CI">🇨🇮 科特迪瓦</option>
              <option value="TZ">🇹🇿 坦桑尼亚</option>
              <option value="UG">🇺🇬 乌干达</option>
              <option value="RW">🇷🇼 卢旺达</option>
              <option value="ZM">🇿🇲 赞比亚</option>
              <option value="CD">🇨🇩 刚果（金）</option>
              <option value="ZA">🇿🇦 南非</option>
              <option value="SD">🇸🇩 苏丹</option>
              <option value="MG">🇲🇬 马达加斯加</option>
              <option value="GA">🇬🇦 加蓬</option>
              <option value="BJ">🇧🇯 贝宁</option>
              <option value="MZ">🇲🇿 莫桑比克</option>
              <option value="NG">🇳🇬 尼日利亚</option>
              <option value="EG">🇪🇬 埃及</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg flex items-center gap-2">
            <span>⚠️</span>
            <div>
              <p>{error}</p>
              <p className="text-xs text-red-500 mt-1">
                如果计算持续失败，请检查：①网络连接 ②FOB单价是否为数字 ③采购量是否&gt;0
              </p>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-3 mt-6">
          <button
            onClick={handleCalc}
            disabled={loading}
            className="px-8 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? '计算中...' : '精算成本'}
          </button>
          <Link
            to="/hs-lookup"
            className="px-6 py-3 bg-white border border-slate-300 hover:border-primary-400 text-slate-700 font-medium rounded-xl transition-colors text-sm"
          >
            先查HS编码
          </Link>
          <Link
            to="/products"
            className="px-6 py-3 bg-orange-50 border border-orange-200 hover:border-orange-400 text-orange-700 font-medium rounded-xl transition-colors text-sm"
          >
            浏览选品清单
          </Link>
        </div>
      </div>

      {result && result.breakdown && (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: '到岸总成本', value: fmt(result.breakdown.total_cost), highlight: true },
              { label: '每包成本', value: fmt(result.breakdown.cost_per_package) },
              { label: '建议零售价', value: fmt(result.breakdown.suggested_retail_price) },
              { label: '回本需卖', value: `${result.breakdown.payback_packages} 包` },
            ].map((card) => (
              <div key={card.label} className={`bg-white rounded-xl border p-4 ${card.highlight ? 'border-primary-300 bg-primary-50' : 'border-slate-200'}`}>
                <div className="text-xs text-slate-500 mb-1">{card.label}</div>
                <div className={`text-lg font-heading font-bold ${card.highlight ? 'text-primary-700' : 'text-slate-900'}`}>
                  {card.value}
                </div>
              </div>
            ))}
          </div>

          {/* Breakdown */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-900 mb-4">完整成本分解</h3>
            <div className="space-y-2">
              {[
                { label: 'FOB货值', value: fmt(result.breakdown.fob_value) },
                { label: '国际运费', value: fmt(result.breakdown.international_freight) },
                { label: '清关杂费', value: fmt(result.breakdown.customs_clearance) },
                { label: '关税（零关税）', value: '¥0.00', green: true },
                { label: '增值税（13%）', value: fmt(result.breakdown.vat) },
                { label: '进口总成本', value: fmt(result.breakdown.total_import_cost), bold: true },
              ].map((row) => (
                <div key={row.label} className={`flex justify-between py-2 border-b border-slate-100 ${row.bold ? 'font-semibold text-slate-900 border-t-2 border-slate-200 mt-2' : 'text-slate-700'} ${row.green ? 'text-green-700' : ''}`}>
                  <span>{row.label}</span>
                  <span>{row.value}</span>
                </div>
              ))}
              <div className="flex justify-between py-2 border-b border-slate-100 text-slate-700">
                <span>烘焙损耗（{result.breakdown.roasting_loss_rate * 100}%）</span>
                <span className="text-slate-500">剩余 {result.breakdown.roasted_yield_kg.toFixed(2)} kg</span>
              </div>
              {[
                { label: '国内物流', value: fmt(result.breakdown.domestic_logistics) },
                { label: '分装成本', value: fmt(result.breakdown.packaging_cost_per_unit) },
                { label: '综合成本', value: fmt(result.breakdown.total_cost), bold: true },
              ].map((row) => (
                <div key={row.label} className={`flex justify-between py-2 ${row.bold ? 'font-bold text-slate-900 border-t-2 border-primary-200 mt-2' : 'text-slate-700'}`}>
                  <span>{row.label}</span>
                  <span>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Next steps */}
          <div className="bg-gradient-to-br from-orange-50 to-amber-50 border border-orange-200 rounded-xl p-5">
            <p className="text-sm font-semibold text-orange-800 mb-3">下一步做什么？</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Link
                to="/origin-check"
                className="bg-white border border-orange-200 rounded-lg p-3 hover:border-orange-400 transition-colors group"
              >
                <div className="text-sm font-medium text-orange-800 group-hover:text-orange-900">🔍 原产地自测</div>
                <div className="text-xs text-orange-600 mt-0.5">验证货物是否符合零关税原产地规则</div>
              </Link>
              <Link
                to="/calculator"
                className="bg-white border border-orange-200 rounded-lg p-3 hover:border-orange-400 transition-colors group"
              >
                <div className="text-sm font-medium text-orange-800 group-hover:text-orange-900">📊 多市场对比</div>
                <div className="text-xs text-orange-600 mt-0.5">对比中国/欧盟/AfCFTA各市场关税</div>
              </Link>
              <Link
                to="/getting-started"
                className="bg-white border border-orange-200 rounded-lg p-3 hover:border-orange-400 transition-colors group"
              >
                <div className="text-sm font-medium text-orange-800 group-hover:text-orange-900">📋 新手入门</div>
                <div className="text-xs text-orange-600 mt-0.5">从选品到落地的完整路线图</div>
              </Link>
            </div>
          </div>

          {/* Origin certificate guide */}
          {result.origin_certificate_guide && result.origin_certificate_guide.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900 mb-4">📋 原产地证书办理指南</h3>
              <ol className="space-y-2">
                {result.origin_certificate_guide.map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm text-slate-700">
                    <span className="shrink-0 w-6 h-6 bg-primary-100 text-primary-700 rounded-full flex items-center justify-center text-xs font-bold">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}

      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <strong>注意：</strong>以上为估算值。实际成本受汇率波动、清关效率、市场行情影响较大，仅供参考。咖啡烘焙损耗率按15%估算，实际以货物检验为准。
      </div>
    </div>
  )
}
