import { useState } from 'react'
import { calculateImportCost } from '../utils/api'
import type { ImportCostResult } from '../types'

function fmt(n: number) {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(n)
}

export default function CostCalculatorPage() {
  const [productName, setProductName] = useState('')
  const [quantityKg, setQuantityKg] = useState('')
  const [fobPerKg, setFobPerKg] = useState('')
  const [origin, setOrigin] = useState('ET')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ImportCostResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleCalc() {
    if (!productName || !quantityKg || !fobPerKg) {
      setError('请填写所有必填项')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await calculateImportCost({
        product_name: productName,
        quantity_kg: parseFloat(quantityKg),
        fob_per_kg: parseFloat(fobPerKg),
        origin,
      })
      setResult(data)
    } catch {
      setError('计算失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">成本精算器</h1>
        <p className="text-slate-600">
          输入采购信息，一键获取完整到岸成本、回本测算与原产地证书指南。
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 mb-8">
        {/* Presets */}
        <div className="mb-6">
          <p className="block text-sm font-medium text-slate-700 mb-2">快速选择</p>
          <div className="flex flex-wrap gap-2">
            {[
              { label: '埃塞俄比亚 耶加雪菲', qty: '20', price: '6' },
              { label: '埃塞俄比亚 西达摩', qty: '20', price: '5.5' },
              { label: '肯尼亚 阿拉比卡', qty: '30', price: '7' },
            ].map((p) => (
              <button
                key={p.label}
                onClick={() => {
                  setProductName(p.label)
                  setQuantityKg(p.qty)
                  setFobPerKg(p.price)
                  setOrigin('ET')
                }}
                className="px-3 py-1.5 text-sm bg-white border border-slate-200 text-slate-600 rounded-lg hover:border-primary-300 hover:text-primary-600 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="block text-sm font-medium text-slate-700 mb-1.5">商品名称 *</p>
            <input
              type="text"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="如 埃塞俄比亚 耶加雪菲"
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
            <p className="block text-sm font-medium text-slate-700 mb-1.5">原产国代码</p>
            <input
              type="text"
              value={origin}
              onChange={(e) => setOrigin(e.target.value.toUpperCase())}
              placeholder="ET"
              maxLength={2}
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm uppercase focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">
            {error}
          </div>
        )}

        <button
          onClick={handleCalc}
          disabled={loading}
          className="mt-6 px-8 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
        >
          {loading ? '计算中...' : '精算成本'}
        </button>
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
                { label: '关税（零关税）', value: '¥0.00' },
                { label: '增值税（13%）', value: fmt(result.breakdown.vat) },
                { label: '进口总成本', value: fmt(result.breakdown.total_import_cost), bold: true },
              ].map((row) => (
                <div key={row.label} className={`flex justify-between py-2 border-b border-slate-100 ${row.bold ? 'font-semibold text-slate-900 border-t-2 border-slate-200 mt-2' : 'text-slate-700'}`}>
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

          {/* Origin certificate guide */}
          {result.origin_certificate_guide && (
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
        <strong>注意：</strong>以上为估算值。实际成本受汇率波动、清关效率、市场行情影响较大，仅供参考。
      </div>
    </div>
  )
}
