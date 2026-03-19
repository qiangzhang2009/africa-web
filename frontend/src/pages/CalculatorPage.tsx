import { useState } from 'react'
import { Link } from 'react-router-dom'
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
    } catch {
      setError('计算失败，请重试')
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
            <p className="block text-sm font-medium text-slate-700 mb-2">快速选择品类</p>
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
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">HS编码 <span className="text-red-500">*</span></p>
              <input
                type="text"
                value={hsCode}
                onChange={(e) => setHsCode(e.target.value)}
                placeholder="0901.21.00"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <p className="mt-1 text-xs text-slate-400">可在 HS编码查询 页搜索</p>
            </div>

            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">原产国 <span className="text-red-500">*</span></p>
              <input
                type="text"
                value={origin}
                onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                placeholder="ET（埃塞俄比亚）"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 uppercase"
                maxLength={2}
              />
            </div>

            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">目的地市场 <span className="text-red-500">*</span></p>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value as DestinationMarket)}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="CN">🇨🇳 中国（零关税）</option>
                <option value="EU">🇪🇺 欧盟（EPA估算）</option>
                <option value="AFCFTA">🌍 非洲内部（AfCFTA估算）</option>
              </select>
            </div>

            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">FOB货值（USD） <span className="text-red-500">*</span></p>
              <input
                type="number"
                value={fobValue}
                onChange={(e) => setFobValue(e.target.value)}
                placeholder="如 120"
                min="0"
                step="0.01"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
              {error}
            </div>
          )}

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

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
        <strong>提示：</strong>以上计算基于2026年5月1日起生效的中国对非洲53个建交国零关税政策。
        实际通关时，原产地需经海关认证，详情请参考<a href="/origin-check" className="underline">原产地自测</a>。
        数据仅供参考，不构成法律建议。
      </div>
    </div>
  )
}
