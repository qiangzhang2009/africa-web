import { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAppStore } from '../hooks/useAppStore'
import { calculateTariff, searchHSCodes } from '../utils/api'
import { track } from '../utils/track'
import type { TariffCalcResult, DestinationMarket, HSSearchResult } from '../types'

// ─── Product form presets ────────────────────────────────────────────────────
const PRESETS = [
  // 生豆
  {
    group: '生咖啡豆（未焙炒）',
    label: '埃塞俄比亚 耶加雪菲',
    hs10: '0901.11.00',
    origin: 'ET',
    originName: '埃塞俄比亚',
    freight: 5.0,
    defaultQty: 60,
    note: '水洗处理，SC级别',
  },
  {
    group: '生咖啡豆（未焙炒）',
    label: '埃塞俄比亚 西达摩',
    hs10: '0901.11.00',
    origin: 'ET',
    originName: '埃塞俄比亚',
    freight: 5.0,
    defaultQty: 60,
    note: '日晒处理',
  },
  {
    group: '生咖啡豆（未焙炒）',
    label: '肯尼亚 阿拉比卡',
    hs10: '0901.11.00',
    origin: 'KE',
    originName: '肯尼亚',
    freight: 4.5,
    defaultQty: 60,
    note: 'AA/AB级别',
  },
  {
    group: '生咖啡豆（未焙炒）',
    label: '卢旺达 精品咖啡',
    hs10: '0901.11.00',
    origin: 'RW',
    originName: '卢旺达',
    freight: 5.5,
    defaultQty: 60,
    note: '波旁种',
  },
  {
    group: '生咖啡豆（未焙炒）',
    label: '坦桑尼亚 咖啡',
    hs10: '0901.11.00',
    origin: 'TZ',
    originName: '坦桑尼亚',
    freight: 4.0,
    defaultQty: 60,
    note: '乞力马扎罗产区',
  },
  {
    group: '生咖啡豆（未焙炒）',
    label: '加纳 可可豆',
    hs10: '1801.00.00',
    origin: 'GH',
    originName: '加纳',
    freight: 4.5,
    defaultQty: 100,
    note: '出口级可可豆',
  },
  // 烘焙豆
  {
    group: '已焙炒咖啡豆',
    label: '埃塞俄比亚 耶加雪菲（烘焙）',
    hs10: '0901.21.00',
    origin: 'ET',
    originName: '埃塞俄比亚',
    freight: 6.0,
    defaultQty: 20,
    note: '中深度烘焙',
  },
  {
    group: '已焙炒咖啡豆',
    label: '肯尼亚 阿拉比卡（烘焙）',
    hs10: '0901.21.00',
    origin: 'KE',
    originName: '肯尼亚',
    freight: 5.5,
    defaultQty: 20,
    note: '中度烘焙',
  },
  // 速溶
  {
    group: '咖啡浓缩精汁/速溶',
    label: '埃塞俄比亚 速溶咖啡',
    hs10: '2101.11.00',
    origin: 'ET',
    originName: '埃塞俄比亚',
    freight: 8.0,
    defaultQty: 10,
    note: '冻干速溶',
  },
  {
    group: '坚果/其他',
    label: '坦桑尼亚 腰果',
    hs10: '0801.32.00',
    origin: 'TZ',
    originName: '坦桑尼亚',
    freight: 4.0,
    defaultQty: 50,
    note: '去壳腰果',
  },
]

// Group presets by product form
const GROUPED_PRESETS = PRESETS.reduce<Record<string, typeof PRESETS>>((acc, p) => {
  if (!acc[p.group]) acc[p.group] = []
  acc[p.group].push(p)
  return acc
}, {})

// ─── Default exchange rate ────────────────────────────────────────────────────
const DEFAULT_EXCHANGE_RATE = 7.25

function fmt(n: number, currency = 'CNY') {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency, minimumFractionDigits: 2 }).format(n)
}

export default function CalculatorPage() {
  const { tier, remainingToday, decrementFreeQuery, syncCounter } = useAppStore()
  const [searchParams] = useSearchParams()

  useEffect(() => { syncCounter() }, [])

  // Auto-fill from URL params (passed from product detail or other pages)
  useEffect(() => {
    const hs = searchParams.get('hs')
    const o = searchParams.get('origin')
    if (hs) {
      setHsCode(hs)
      setHsSearch(hs)
    }
    if (o) {
      setOrigin(o)
      // Update originName too if possible
      const found = PRESETS.find(p => p.origin === o)
      if (found) setOriginName(found.originName)
    }
  }, [searchParams])

  // ── Form state ──
  const [preset, setPreset] = useState<string>('')
  const [hsCode, setHsCode] = useState('0901.11.00')
  const [origin, setOrigin] = useState('ET')
  const [originName, setOriginName] = useState('埃塞俄比亚')
  const [destination, setDestination] = useState<DestinationMarket>('CN')
  const [quantityKg, setQuantityKg] = useState('60')
  const [fobValue, setFobValue] = useState('')
  const [freightMode, setFreightMode] = useState('lcl')
  const [freightManual, setFreightManual] = useState('')
  const [exchangeRate, setExchangeRate] = useState(DEFAULT_EXCHANGE_RATE.toString())

  // ── HS autocomplete ──
  const [hsSearch, setHsSearch] = useState('')
  const [hsSuggestions, setHsSuggestions] = useState<HSSearchResult[]>([])
  const [showHsDropdown, setShowHsDropdown] = useState(false)
  const [hsSearchLoading, setHsSearchLoading] = useState(false)
  const hsInputRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout>>()

  // ── Result / loading ──
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TariffCalcResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isPro = tier !== 'free'

  // ── Apply preset ──
  function applyPreset(label: string) {
    const p = PRESETS.find((x) => x.label === label)
    if (!p) return
    setPreset(label)
    setHsCode(p.hs10)
    setOrigin(p.origin)
    setOriginName(p.originName)
    setQuantityKg(p.defaultQty.toString())
    setFreightMode('lcl')
    setFreightManual('')
    setHsSearch('')
    setShowHsDropdown(false)
    track.calcSelectPreset(label, p.group, p.hs10, p.origin)
  }

  // ── HS search ──
  function handleHsSearchChange(val: string) {
    setHsCode(val)
    setHsSearch(val)
    if (searchTimeout.current) clearTimeout(searchTimeout.current)

    if (val.length < 2) {
      setHsSuggestions([])
      setShowHsDropdown(false)
      return
    }

    setHsSearchLoading(true)
    searchTimeout.current = setTimeout(async () => {
      try {
        const results = await searchHSCodes(val, 8)
        setHsSuggestions(results)
        setShowHsDropdown(true)
        track.calcSearchHs(val, results.length)
      } catch {
        setHsSuggestions([])
      } finally {
        setHsSearchLoading(false)
      }
    }, 350)
  }

  function applyHsSuggestion(item: HSSearchResult) {
    setHsCode(item.hs_10 || hsCode)
    setHsSearch(item.hs_10 || '')
    setShowHsDropdown(false)
  }

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (hsInputRef.current && !hsInputRef.current.contains(e.target as Node)) {
        setShowHsDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // ── Calculate ──
  async function handleCalculate() {
    if (!fobValue || parseFloat(fobValue) <= 0) {
      setError('请输入有效的FOB货值')
      track.calcError('invalid_fob_value')
      return
    }
    if (!isPro && remainingToday <= 0) {
      setError('今日免费次数已用完，请开通 Pro 版')
      track.calcError('quota_exceeded')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const freightVal = freightMode === 'manual' && freightManual
        ? parseFloat(freightManual)
        : null

      const input = {
        hs_code: hsCode,
        origin,
        destination,
        fob_value: parseFloat(fobValue),
        quantity_kg: parseFloat(quantityKg),
        freight_mode: freightMode,
      }

      const data = await calculateTariff({
        hs_code: hsCode,
        origin_country: origin,
        destination,
        fob_value: parseFloat(fobValue),
        quantity_kg: parseFloat(quantityKg),
        freight_override: freightVal,
        exchange_rate: parseFloat(exchangeRate),
      })
      setResult(data)
      track.calcSubmit(input, data.success)
      if (data.success) {
        track.calcResultShown(data as unknown as Record<string, unknown>)
        decrementFreeQuery()
      } else {
        track.calcError(`calc_failed: ${data.message}`)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'network_error'
      setError('计算失败，请检查网络后重试')
      track.calcError(msg)
    } finally {
      setLoading(false)
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

          {/* ── Step 1: Quick select ── */}
          <div className="mb-6">
            <p className="block text-sm font-medium text-slate-700 mb-2">
              ① 快速选择品类 <span className="text-slate-400 font-normal">（自动填入HS编码、原产国、参考运费）</span>
            </p>
            {Object.entries(GROUPED_PRESETS).map(([group, items]) => (
              <div key={group} className="mb-3">
                <p className="text-xs text-slate-400 mb-1.5 font-medium uppercase tracking-wide">{group}</p>
                <div className="flex flex-wrap gap-2">
                  {items.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => applyPreset(p.label)}
                      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                        preset === p.label
                          ? 'bg-primary-50 border-primary-300 text-primary-700 font-medium'
                          : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300 hover:text-primary-600'
                      }`}
                      title={p.note}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* ── Step 2: HS code with autocomplete ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div ref={hsInputRef} className="relative">
              <p className="block text-sm font-medium text-slate-700 mb-1.5">
                ② HS编码 <span className="text-red-500">*</span>
              </p>
              <div className="relative">
                <input
                  type="text"
                  value={hsSearch || hsCode}
                  onChange={(e) => handleHsSearchChange(e.target.value)}
                  onFocus={() => hsSuggestions.length > 0 && setShowHsDropdown(true)}
                  placeholder="0901.11.00"
                  className="w-full px-3.5 py-2.5 pr-8 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                {hsSearchLoading && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2">
                    <div className="w-4 h-4 border-2 border-primary-300 border-t-primary-600 rounded-full animate-spin" />
                  </div>
                )}
              </div>
              {showHsDropdown && hsSuggestions.length > 0 && (
                <ul className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {hsSuggestions.map((item, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        onClick={() => applyHsSuggestion(item)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-primary-50 flex items-center justify-between gap-2"
                      >
                        <span className="font-mono text-primary-700 font-medium">{item.hs_10}</span>
                        <span className="text-slate-500 truncate">{item.name_zh}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-1 text-xs text-slate-400">
                或在 <Link to="/hs-lookup" className="text-primary-600 hover:underline">HS编码查询</Link> 页搜索
              </p>
            </div>

            {/* Origin (auto-filled by preset) */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">
                原产国 <span className="text-red-500">*</span>
              </p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value.toUpperCase())}
                  placeholder="ET"
                  maxLength={2}
                  className="w-16 px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm uppercase font-mono focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <span className="text-slate-500 text-sm">{originName}</span>
              </div>
            </div>

            {/* Destination */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">目的地市场 <span className="text-red-500">*</span></p>
              <select
                value={destination}
                onChange={(e) => { setDestination(e.target.value as DestinationMarket); track.calcChangeDestination(e.target.value) }}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="CN">🇨🇳 中国（零关税）</option>
                <option value="EU">🇪🇺 欧盟（EPA估算）</option>
                <option value="AFCFTA">🌍 非洲内部（AfCFTA估算）</option>
              </select>
            </div>

            {/* Quantity */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">
                采购量（kg） <span className="text-red-500">*</span>
              </p>
              <input
                type="number"
                value={quantityKg}
                onChange={(e) => setQuantityKg(e.target.value)}
                placeholder="60"
                min="1"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* FOB value */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">
                FOB货值（USD） <span className="text-red-500">*</span>
              </p>
              <input
                type="number"
                value={fobValue}
                onChange={(e) => setFobValue(e.target.value)}
                placeholder="如 360（对应 60kg × $6/kg）"
                min="0"
                step="0.01"
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Freight method */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">国际运费方式</p>
              <select
                value={freightMode}
                onChange={(e) => {
                  setFreightMode(e.target.value)
                  if (e.target.value !== 'manual') setFreightManual('')
                }}
                className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="lcl">海运拼箱（LCL）— $3.5-5.5/kg</option>
                <option value="air">空运拼货 — $6-8/kg</option>
                <option value="fcl">整柜海运（FCL）— $2-3/kg（大货）</option>
                <option value="manual">手动输入运费</option>
              </select>
              {freightMode === 'manual' && (
                <div className="mt-2 flex items-center gap-1">
                  <input
                    type="number"
                    value={freightManual}
                    onChange={(e) => setFreightManual(e.target.value)}
                    placeholder="总运费 USD"
                    min="0"
                    step="1"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <span className="text-slate-400 text-sm">USD</span>
                </div>
              )}
              <p className="mt-1 text-xs text-slate-400">
                {freightMode === 'lcl' && '适用于60kg以下小批量，拼箱共担柜费'}
                {freightMode === 'air' && '适用于急需补货或样品，时效7-12天'}
                {freightMode === 'fcl' && '需20英尺整柜，建议采购量≥250kg'}
                {freightMode === 'manual' && '输入总运费金额，由货代报价'}
              </p>
            </div>

            {/* Exchange rate */}
            <div>
              <p className="block text-sm font-medium text-slate-700 mb-1.5">汇率 USD→CNY</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  placeholder="7.25"
                  min="0"
                  step="0.01"
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <button
                  type="button"
                  onClick={() => setExchangeRate(DEFAULT_EXCHANGE_RATE.toString())}
                  className="shrink-0 text-xs text-slate-400 hover:text-primary-600 underline"
                >
                  重置
                </button>
              </div>
              <p className="mt-1 text-xs text-slate-400">参考值：默认7.25（2026年3月），可按需锁定</p>
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

      {/* ── Result ── */}
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

            {result.breakdown && (() => {
              const bd = result.breakdown
              const qtyKg = bd.quantity_kg
              const fxRate = bd.exchange_rate
              const freightPerKg = qtyKg > 0 ? (bd.freight / qtyKg).toFixed(2) : '—'
              return (
              <div>
                <h3 className="font-semibold text-slate-900 mb-4">成本分解</h3>
                <div className="space-y-3">
                  {[
                    { label: 'FOB货值', value: bd.fob_value, unit: 'USD', note: `${qtyKg} kg` },
                    { label: '国际运费', value: bd.freight, unit: 'USD', note: `参考：${freightPerKg} $/kg` },
                    { label: '保险（约0.5%）', value: bd.insurance, unit: 'USD' },
                    { label: '关税税率', value: `${(bd.tariff_rate * 100).toFixed(1)}%`, unit: '' },
                    { label: '关税金额', value: bd.tariff_amount, unit: 'CNY' },
                    { label: `增值税税率`, value: `${(bd.vat_rate * 100).toFixed(0)}%`, unit: '' },
                    { label: '增值税', value: bd.vat_amount, unit: 'CNY' },
                    { label: `汇率 USD→CNY`, value: fxRate.toFixed(4), unit: '' },
                    { label: '到岸总成本', value: bd.total_cost, unit: 'CNY', highlight: true },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className={`flex justify-between items-center py-2 ${item.highlight ? 'border-t-2 border-slate-200 font-semibold text-slate-900' : 'border-t border-slate-100 text-slate-700'}`}
                    >
                      <div className="flex flex-col">
                        <span>{item.label}</span>
                        {item.note && <span className="text-xs text-slate-400">{item.note}</span>}
                      </div>
                      <span>
                        {typeof item.value === 'number'
                          ? fmt(item.value, item.unit === 'CNY' ? 'CNY' : 'USD')
                          : item.value}
                      </span>
                    </div>
                  ))}

                  {bd.savings_vs_mfn > 0 && (
                    <div className="flex justify-between items-center py-3 px-4 bg-green-50 rounded-lg text-green-800 font-semibold">
                      <span>相比MFN税率节省</span>
                      <span>{fmt(bd.savings_vs_mfn, 'CNY')}</span>
                    </div>
                  )}
                </div>
              </div>
              )
            })()}

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
