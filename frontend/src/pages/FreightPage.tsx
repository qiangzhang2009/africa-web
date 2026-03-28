import { useState, useEffect } from 'react'
import {
  Ship, Calculator, Globe, Package,
  AlertCircle, CheckCircle, ArrowRight, Info,
  Anchor, Plane, MapPin
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
  listFreightCountries, listDestPorts,
  listFreightRoutes,
} from '../data/local'
import { estimateFreightCost } from '../utils/api'
import { track } from '../utils/track'
import type { FreightRoute, FreightEstimateResult } from '../types'

const fmt = (n: number) =>
  new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(n)
const fmtUSD = (n: number) =>
  new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'USD' }).format(n)

function TransportTypeBadge({ type }: { type: string }) {
  const map: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
    sea20gp: { label: '20GP集装箱', icon: <Package className="w-3 h-3" />, color: 'bg-blue-100 text-blue-700' },
    sea40hp: { label: '40GP集装箱', icon: <Package className="w-3 h-3" />, color: 'bg-indigo-100 text-indigo-700' },
    air: { label: '空运', icon: <Plane className="w-3 h-3" />, color: 'bg-amber-100 text-amber-700' },
  }
  const t = map[type] || { label: type, icon: null, color: 'bg-slate-100 text-slate-600' }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${t.color}`}>
      {t.icon}{t.label}
    </span>
  )
}

export default function FreightPage() {
  const navigate = useNavigate()
  const [countries, setCountries] = useState<{ code: string; name_zh: string }[]>([])
  const [ports, setPorts] = useState<{ code: string; name_zh: string }[]>([])
  const [routes, setRoutes] = useState<FreightRoute[]>([])

  const [originCountry, setOriginCountry] = useState('ET')
  const [destPort, setDestPort] = useState('SHA')
  const [quantity, setQuantity] = useState('2000')
  const [transportType, setTransportType] = useState('sea20gp')

  const [result, setResult] = useState<FreightEstimateResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listFreightCountries().then(setCountries).catch(() => {})
    listDestPorts().then(setPorts).catch(() => {})
    listFreightRoutes({ origin_country: originCountry }).then(setRoutes).catch(() => {})
  }, [])

  useEffect(() => {
    if (originCountry) {
      listFreightRoutes({ origin_country: originCountry }).then(setRoutes).catch(() => {})
    }
  }, [originCountry])

  async function handleEstimate() {
    const qty = parseFloat(quantity)
    if (!qty || qty <= 0) {
      setError('请输入正确的货物重量')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await estimateFreightCost({
        origin_country: originCountry,
        dest_port: destPort,
        quantity_kg: qty,
        transport_type: transportType,
      })
      setResult(data)
      track.freightEstimate({ origin: originCountry, dest: destPort, qty, type: transportType })
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '估算失败，请稍后重试'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const selectedCountry = countries.find(c => c.code === originCountry)
  const relevantRoutes = routes.filter(r => r.transport_type === transportType)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center">
            <Ship className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-3xl font-heading font-bold text-slate-900">物流成本估算</h1>
          </div>
        </div>
        <p className="text-slate-600">
          输入货物信息，秒知非洲→中国全程物流成本。包括海运费、保险、清关和国内物流。
          运费占 CIF 到岸成本 20-40%，精准估算才能算准利润。
        </p>
      </div>

      {/* Info banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 mb-8 flex gap-3">
        <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
        <div className="text-sm text-blue-700">
          <strong>估算说明：</strong>海运费为市场参考价（2026年3月），实际价格随淡旺季、燃油附加费波动约 ±15-25%。
          精确报价请联系货代。数据覆盖 53 个非洲国家主要港口路线。
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">

        {/* Left: Input form */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 sticky top-20">
            <h2 className="font-semibold text-slate-900 mb-5 flex items-center gap-2">
              <Calculator className="w-4 h-4 text-blue-500" />
              输入货物信息
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  <Globe className="w-3.5 h-3.5 inline mr-1" />
                  原产国
                </label>
                <select
                  value={originCountry}
                  onChange={e => setOriginCountry(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {countries.map(c => (
                    <option key={c.code} value={c.code}>{c.name_zh}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  <Anchor className="w-3.5 h-3.5 inline mr-1" />
                  目的港
                </label>
                <select
                  value={destPort}
                  onChange={e => setDestPort(e.target.value)}
                  className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {ports.map(p => (
                    <option key={p.code} value={p.code}>{p.name_zh}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  <Package className="w-3.5 h-3.5 inline mr-1" />
                  货物总重量
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    value={quantity}
                    onChange={e => setQuantity(e.target.value)}
                    placeholder="2000"
                    min="1"
                    className="flex-1 px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="px-3 py-2.5 bg-slate-100 text-slate-500 text-sm rounded-lg">kg</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  运输方式
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: 'sea20gp', label: '20GP' },
                    { value: 'sea40hp', label: '40GP' },
                    { value: 'air', label: '空运' },
                  ].map(t => (
                    <button
                      key={t.value}
                      onClick={() => setTransportType(t.value)}
                      className={`px-3 py-2 text-sm rounded-lg border transition-all ${
                        transportType === t.value
                          ? 'bg-blue-50 border-blue-300 text-blue-700 font-medium'
                          : 'border-slate-200 text-slate-600 hover:border-blue-200'
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <button
                onClick={handleEstimate}
                disabled={loading}
                className="w-full py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    正在估算...
                  </>
                ) : (
                  <>
                    <Calculator className="w-4 h-4" />
                    计算物流成本
                  </>
                )}
              </button>

              <button
                onClick={() => navigate(`/cost-calculator?origin=${originCountry}`)}
                className="w-full py-2.5 bg-orange-50 hover:bg-orange-100 text-orange-700 font-medium rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
              >
                一键填入成本精算器
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-3">

          {/* Route overview */}
          <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
            <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-slate-500" />
              {selectedCountry?.name_zh || originCountry} 可用路线
            </h2>
            {relevantRoutes.length === 0 ? (
              <p className="text-sm text-slate-500">暂无该路线的运费数据</p>
            ) : (
              <div className="space-y-2">
                {relevantRoutes.slice(0, 5).map(r => (
                  <div key={r.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
                    <div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-slate-800">{r.origin_port_zh}</span>
                        <span className="text-slate-400">→</span>
                        <span className="font-medium text-slate-800">{r.dest_port_zh}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <TransportTypeBadge type={r.transport_type} />
                        <span className="text-xs text-slate-400">{r.transit_days_min}-{r.transit_days_max}天</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold text-slate-800">
                        ${r.cost_min_usd.toLocaleString()}-${r.cost_max_usd.toLocaleString()}
                      </div>
                      <div className="text-xs text-slate-400">USD / 集装箱</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Estimation result */}
          {result && (
            <div className="space-y-4">
              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-2xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <CheckCircle className="w-5 h-5 text-blue-500" />
                  <h3 className="font-semibold text-blue-900">物流成本估算结果</h3>
                </div>

                <div className="bg-white/80 rounded-xl p-4 mb-4">
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <span className="font-medium text-slate-700">{result.origin_port_zh} ({result.origin_country})</span>
                    <span className="text-slate-400">→</span>
                    <span className="font-medium text-slate-700">{result.dest_port_zh} ({result.dest_port})</span>
                    <TransportTypeBadge type={result.transport_type} />
                  </div>
                  <div className="text-xs text-slate-500 mb-3">
                    {selectedCountry?.name_zh} · 货物 {result.quantity_kg.toLocaleString()} kg
                    · 预计 {result.transit_days}送达
                  </div>

                  <div className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                    <Info className="w-4 h-4 text-blue-500 shrink-0" />
                    <span className="text-sm text-blue-700">{result.container_suggestion}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                  {[
                    { label: '海运费', val: fmt(result.sea_freight_cny), sub: `约 ${fmtUSD(result.sea_freight_usd)} USD` },
                    { label: '港口费', val: fmt(result.port_charges_usd * 7.25), sub: `约 ${fmtUSD(result.port_charges_usd)} USD` },
                    { label: '保险', val: fmt(result.insurance_usd * 7.25), sub: `约 ${fmtUSD(result.insurance_usd)} USD` },
                    { label: '清关代理', val: fmt(result.clearance_agent_fee_cny), sub: '含报关' },
                    { label: '国内物流', val: fmt(result.domestic_logistics_cny), sub: '港口→仓库' },
                    { label: '合计', val: fmt(result.total_freight_cny), sub: `约 ${fmtUSD(result.total_freight_usd)} USD`, bold: true },
                  ].map(item => (
                    <div key={item.label} className={`bg-white/80 rounded-xl p-3 text-center ${item.bold ? 'border-2 border-blue-300' : ''}`}>
                      <div className="text-xs text-slate-500 mb-1">{item.label}</div>
                      <div className={`text-base font-bold ${item.bold ? 'text-blue-700' : 'text-slate-900'}`}>
                        {item.val}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{item.sub}</div>
                    </div>
                  ))}
                </div>

                {result.notes && (
                  <div className="text-xs text-slate-500 bg-white/60 rounded-lg p-2">
                    💡 {result.notes}
                  </div>
                )}
              </div>

              {/* Comparison with cost calculator */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6">
                <h3 className="font-semibold text-slate-900 mb-3">结合关税计算</h3>
                <p className="text-sm text-slate-600 mb-4">
                  物流成本估算是 CIF 到岸成本的重要组成部分。结合 AfricaZero 的成本精算器，
                  可以得到完整的到岸成本和利润测算。
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => navigate(`/cost-calculator?origin=${originCountry}`)}
                    className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2"
                  >
                    <Calculator className="w-4 h-4" />
                    打开成本精算器
                  </button>
                  <button
                    onClick={() => navigate(`/certificate?country=${originCountry}`)}
                    className="px-4 py-2 bg-green-50 hover:bg-green-100 text-green-700 text-sm font-medium rounded-xl transition-colors border border-green-200"
                  >
                    原产地证书办理 →
                  </button>
                </div>
              </div>
            </div>
          )}

          {!result && !loading && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Ship className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-slate-500 mb-2">填写左侧信息，开始估算物流成本</p>
              <p className="text-xs text-slate-400">支持 53 个非洲国家 → 中国主要港口路线</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
