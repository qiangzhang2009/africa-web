import { useState } from 'react'
import { checkOrigin } from '../utils/api'
import type { OriginCheckResult } from '../types'

export default function OriginCheckPage() {
  const [hsCode, setHsCode] = useState('')
  const [origin, setOrigin] = useState('')
  const [processing, setProcessing] = useState('')
  const [materials, setMaterials] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<OriginCheckResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleCheck() {
    if (!hsCode || !origin || !processing) {
      setError('请填写必填项')
      return
    }
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await checkOrigin({
        product_name: '',
        hs_code: hsCode,
        origin,
        processing_steps: processing.split('\n').filter(Boolean),
        material_sources: materials.split('\n').filter(Boolean),
      })
      setResult(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '判定失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-heading font-bold text-slate-900 mb-2">原产地自测</h1>
        <p className="text-slate-600">
          填写工艺和原料信息，AI 辅助判断是否符合原产地规则
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 p-6 md:p-8 mb-8">
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              HS编码 * <span className="text-xs text-slate-400">（10位税号）</span>
            </label>
            <input
              type="text"
              value={hsCode}
              onChange={(e) => setHsCode(e.target.value)}
              placeholder="0901.21.00"
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              原产国 * <span className="text-xs text-slate-400">（ISO 2位代码，如 ET）</span>
            </label>
            <input
              type="text"
              value={origin}
              onChange={(e) => setOrigin(e.target.value.toUpperCase())}
              placeholder="ET"
              maxLength={2}
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm uppercase focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              加工工序 * <span className="text-xs text-slate-400">（每行一条）</span>
            </label>
            <textarea
              value={processing}
              onChange={(e) => setProcessing(e.target.value)}
              placeholder={"清洗\n分级\n去壳\n烘焙"}
              rows={4}
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              原料来源 <span className="text-xs text-slate-400">（每行一条，留空则默认为本地原料）</span>
            </label>
            <textarea
              value={materials}
              onChange={(e) => setMaterials(e.target.value)}
              placeholder={"埃塞俄比亚 耶加雪菲产区生豆"}
              rows={3}
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
          onClick={handleCheck}
          disabled={loading}
          className="mt-6 px-8 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors"
        >
          {loading ? 'AI 判定中...' : 'AI 原产地判定'}
        </button>
      </div>

      {result && (
        <div className={`rounded-2xl border p-6 ${result.qualifies ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
          <div className="flex items-center gap-2 mb-4">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${result.qualifies ? 'bg-green-500' : 'bg-amber-500'}`}>
              {result.qualifies ? (
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
              ) : (
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              )}
            </div>
            <span className={`font-semibold ${result.qualifies ? 'text-green-800' : 'text-amber-800'}`}>
              {result.qualifies ? '✓ 可能符合原产地条件' : '⚠ 条件可能不满足'}
            </span>
          </div>

          {result.rule_applied && (
            <div className="text-sm text-slate-700 mb-3">
              <strong>适用规则：</strong>{result.rule_applied}
            </div>
          )}

          {(result.reasons?.length ?? 0) > 0 && (
            <div className="mb-3">
              <div className="text-sm font-medium text-slate-700 mb-2">判断依据</div>
              <ul className="space-y-1">
                {result.reasons.map((r, i) => (
                  <li key={i} className="text-sm text-slate-700 flex gap-2">
                    <span className="text-slate-400">•</span>{r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(result.suggestions?.length ?? 0) > 0 && (
            <div>
              <div className="text-sm font-medium text-slate-700 mb-2">建议</div>
              <ul className="space-y-1">
                {result.suggestions.map((s, i) => (
                  <li key={i} className="text-sm text-slate-600 flex gap-2">
                    <span className="text-primary-500">→</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 text-xs text-slate-500 border-t border-slate-300 pt-3">
            置信度：{Math.round(result.confidence * 100)}% ｜ AI 判定仅供参考，最终以海关认证结果为准
          </div>
        </div>
      )}
    </div>
  )
}
