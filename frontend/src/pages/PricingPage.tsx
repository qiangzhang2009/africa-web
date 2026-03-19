import { useState } from 'react'
import { useAppStore } from '../hooks/useAppStore'
import { calculateTariff } from '../utils/api'
import type { TariffCalcResult, DestinationMarket } from '../types'

// Ethiopia coffee presets
const PRESETS = [
  { label: '埃塞俄比亚 耶加雪菲', hs10: '0901.21.00', origin: 'ET', originName: '埃塞俄比亚' },
  { label: '埃塞俄比亚 西达摩', hs10: '0901.21.00', origin: 'ET', originName: '埃塞俄比亚' },
  { label: '肯尼亚 阿拉比卡', hs10: '0901.21.00', origin: 'KE', originName: '肯尼亚' },
  { label: '卢旺达 精品咖啡', hs10: '0901.21.00', origin: 'RW', originName: '卢旺达' },
  { label: '坦桑尼亚 咖啡', hs10: '0901.21.00', origin: 'TZ', originName: '坦桑尼亚' },
]

function formatCurrency(n: number, currency = 'CNY') {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(n)
}

export default function CalculatorPage() {
  const { tier, remainingToday, decrementFreeQuery } = useAppStore()

  const [preset, setPreset] = useState<string>('')
  const [hsCode, setHsCode] = useState('0901.21.00')
  const [origin, setOrigin] = useState('ET')
  const [destination, setDestination] = useState<DestinationMarket>('CN')
  const [fobValue, setFobValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TariffCalcResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isPro = tier !== 'free'

  async function handleCalculate() {
    if (!fobValue || parseFloat(fobValue) <= 0) {
      setError('请输入有效的FOB货值')
      return
    }
    if (!isPro && remainingToday <= 0) {
      setError('今日免费次数已用完，请开通 Pro 版')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await calculateTariff({
        hs_code: hsCode,
        origin_country: origin,
        destination,
        fob_value: parseFloat(fobValue),
      })
      setResult(data)
      decrementFreeQuery()
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || '计算失败，请重试')
      } else {
        setError('计算失败，请重试')
      }
    } finally {
      setLoading(false)
    }
  }

  function applyPreset(label: string) {
    const p = PRESETS.find((x) => x.label === label)
    if (p) {
      setPreset(label)
      setHsCode(p.hs10)
      setOrigin(p.origin)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">关税计算器</h1>
        <p className="text-slate-600">输入商品信息，自动计算关税节省金额与到岸总成本</p>
        {!isPro && (
          <div className="mt-3 inline-flex items-center gap-2 text-sm bg-amber-50 text-amber-700 px-3 py-1.5 rounded-lg">
            <span>今日剩余免费次数：<strong>{remainingToday}</strong> / 3</span>
            <Link to="/pricing" className="underline hover:no-underline">升级 Pro</Link>
          </div>
        )}
      </div>

      {/* Calculator Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div className="p-6 md:p-8">
          {/* Presets */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-2">
              快速选择品类
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => applyPreset(p.label)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                    preset === p.label
                      ? 'bg-primary-50 border-primary-300 text-primary-700 font-medium'
                      : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300 hover:text-primary-600'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* HS Code */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                HS编码 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
                placeholder="如 0901.21.00"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <p className="mt-1 text-xs text-slate-400">10位HS税号，可在 HS编码查询 页搜索</p>
            </div>

            {/* Origin */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                原产国 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                placeholder="如 ET（埃塞俄比亚）"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent uppercase"
                maxLength={2}
              />
            </div>

            {/* Destination */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                目的地市场 <span className="text-red-500">*</span>
              </label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value as DestinationMarket)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="CN">🇨🇳 中国（零关税）</option>
                <option value="EU">🇪🇺 欧盟（EPA估算）</option>
                <option value="AFCFTA">🌍 非洲内部（AfCFTA估算）</option>
              </select>
            </div>

            {/* FOB Value */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                FOB货值（USD） <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={fobValue}
                onChange={(e) => setFobValue(e.target.value)}
                placeholder="如 120"
                min="0"
                step="0.01"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            onClick={handleCalculate}
            disabled={loading || (!isPro && remainingToday <= 0)}
            className="mt-6 w-full md:w-auto px-8 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors"
          >
            {loading ? '计算中...' : '计算关税'}
          </button>
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
          <div className="p-6 md:p-8">
            {/* Success banner */}
            <div className={`p-4 rounded-xl mb-6 ${result.origin_qualified ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
              <p className={`font-semibold ${result.origin_qualified ? 'text-green-800' : 'text-amber-800'}`}>
                {result.origin_qualified
                  ? `✓ 原产地符合零关税条件：${result.origin_rule || '非洲建交国产'}`
                  : `⚠ ${result.message}`}
              </p>
            </div>

            {result.breakdown && (
              <div>
                <h3 className="font-semibold text-slate-900 mb-4">成本分解</h3>
                <div className="space-y-3">
                  {[
                    { label: 'FOB货值', value: result.breakdown.fob_value, unit: 'USD' },
                    { label: '国际运费', value: result.breakdown.freight, unit: 'USD' },
                    { label: '保险', value: result.breakdown.insurance, unit: 'USD' },
                    { label: `关税税率`, value: `${(result.breakdown.tariff_rate * 100).toFixed(1)}%`, unit: '' },
                    { label: '关税金额', value: result.breakdown.tariff_amount, unit: 'USD' },
                    { label: `增值税税率`, value: `${(result.breakdown.vat_rate * 100).toFixed(0)}%`, unit: '' },
                    { label: '增值税', value: result.breakdown.vat_amount, unit: 'CNY' },
                    { label: '到岸总成本', value: result.breakdown.total_cost, unit: 'CNY', highlight: true },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className={`flex justify-between items-center py-2 ${item.highlight ? 'border-t-2 border-slate-200 font-semibold text-slate-900' : 'border-t border-slate-100 text-slate-700'}`}
                    >
                      <span>{item.label}</span>
                      <span>
                        {typeof item.value === 'number'
                          ? formatCurrency(item.value, item.unit === 'CNY' ? 'CNY' : 'USD')
                          : item.value}
                      </span>
                    </div>
                  ))}

                  {result.breakdown.savings_vs_mfn > 0 && (
                    <div className="flex justify-between items-center py-3 px-4 bg-green-50 rounded-lg text-green-800 font-semibold">
                      <span>相比MFN税率节省</span>
                      <span>{formatCurrency(result.breakdown.savings_vs_mfn, 'CNY')}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!isPro && (
              <div className="mt-6 p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <p className="text-sm text-slate-600 mb-3">
                  Pro 版解锁：无限次计算 + PDF报告导出 + HS编码无限查
                </p>
                <Link
                  to="/pricing"
                  className="inline-flex items-center gap-1 text-sm text-primary-600 font-medium hover:text-primary-700"
                >
                  开通 Pro 版 →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info box */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-sm text-blue-800">
          <strong>提示：</strong>以上计算基于2026年5月1日起生效的中国对非洲53个建交国零关税政策。
          实际通关时，原产地需经海关认证，详情请参考<a href="/origin-check" className="underline">原产地自测</a>。
          数据仅供参考，不构成法律建议。
        </p>
      </div>
    </div>
  )
}
</think>


<tool_call>
<invoke name="Write">
<parameter name="contents">import { Link } from 'react-router-dom'

const plans = [
  {
    id: 'free',
    name: '免费版',
    price: '¥0',
    period: '永久',
    description: '适合初步了解关税计算',
    features: [
      '每天 3 次关税计算',
      '埃塞俄比亚咖啡品类',
      '中国零关税计算',
      '基础成本估算',
    ],
    cta: '当前方案',
    ctaStyle: 'bg-slate-100 text-slate-600 cursor-default',
    popular: false,
  },
  {
    id: 'pro',
    name: 'Pro 版',
    price: '¥99',
    period: '/年',
    badge: '最受欢迎',
    description: '适合咖啡电商、精品烘焙店主',
    features: [
      '无限次关税计算',
      '全品类覆盖（咖啡/可可/坚果）',
      '多市场计算（中国/欧盟/非洲）',
      '完整成本精算器',
      '原产地AI合规自测',
      'PDF报告导出',
      'HS编码无限查询',
      '邮件支持',
    ],
    cta: '开通 Pro',
    ctaStyle: 'bg-primary-500 hover:bg-primary-600 text-white',
    popular: true,
  },
  {
    id: 'enterprise',
    name: '企业版',
    price: '¥298',
    period: '/年',
    description: '适合贸易公司、报关行',
    features: [
      'Pro 版全部功能',
      '5 个子账号',
      'API 调用权限',
      '批量计算',
      '专属客服',
      '优先数据更新',
    ],
    cta: '开通企业版',
    ctaStyle: 'bg-slate-700 hover:bg-slate-800 text-white',
    popular: false,
  },
]

export default function PricingPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
      <div className="text-center mb-14">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-3">
          简单透明的定价
        </h1>
        <p className="text-slate-600">
          按年订阅，随时取消。5月1日零关税生效前，Pro 版先到先得。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative bg-white rounded-2xl border-2 p-6 ${
              plan.popular
                ? 'border-primary-500 shadow-xl shadow-primary-100'
                : 'border-slate-200'
            }`}
          >
            {plan.badge && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="bg-primary-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
                  {plan.badge}
                </span>
              </div>
            )}

            <div className="mb-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-1">{plan.name}</h2>
              <p className="text-sm text-slate-500">{plan.description}</p>
            </div>

            <div className="mb-6">
              <span className="text-3xl font-heading font-bold text-slate-900">{plan.price}</span>
              <span className="text-slate-500 text-sm">{plan.period}</span>
            </div>

            <ul className="space-y-3 mb-8">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-700">
                  <svg className="w-4 h-4 text-green-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  {f}
                </li>
              ))}
            </ul>

            {plan.id === 'free' ? (
              <div className={plan.ctaStyle + ' w-full text-center py-2.5 rounded-xl text-sm font-medium'}>
                {plan.cta}
              </div>
            ) : (
              <Link
                to="/dashboard"
                className={`block w-full text-center py-2.5 rounded-xl text-sm font-medium transition-colors ${plan.ctaStyle}`}
              >
                {plan.cta}
              </Link>
            )}
          </div>
        ))}
      </div>

      {/* Payment notice */}
      <div className="text-center">
        <p className="text-sm text-slate-500 mb-3">
          支付方式：微信 / 支付宝收款码转账，付款后联系客服开通
        </p>
        <p className="text-sm text-slate-400">
          企业对公转账、发票需求请联系：<a href="mailto:hello@africa-zero.com" className="text-primary-600 hover:underline">hello@africa-zero.com</a>
        </p>
      </div>

      {/* FAQ */}
      <div className="mt-16">
        <h2 className="text-xl font-heading font-bold text-slate-900 mb-6 text-center">常见问题</h2>
        <div className="space-y-4 max-w-2xl mx-auto">
          {[
            {
              q: '免费版用完了怎么办？',
              a: '每天有3次免费计算机会，用完后可开通 Pro 版（99元/年）无限制使用。',
            },
            {
              q: '关税计算结果准确吗？',
              a: '中国零关税政策基于国务院公告，税率数据来自海关总署。欧盟和非洲部分为规则估算，如有疑问请以海关确认为准。',
            },
            {
              q: '如何开通 Pro 版？',
              a: '联系客服微信（公众号底部），转账后1小时内开通。',
            },
            {
              q: '可以退款吗？',
              a: '开通后7天内如对产品不满意，可申请全额退款。',
            },
          ].map((faq) => (
            <div key={faq.q} className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="font-medium text-slate-900 mb-1">{faq.q}</h3>
              <p className="text-sm text-slate-600">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
